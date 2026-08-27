from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.geo_loop import due_watch_prompts, pick_sample_batches, summarize_runs
from app.models import (
    BacklinkGap,
    DemandSignal,
    DistributionJob,
    GeoAsset,
    GeoObservation,
    GeoPrompt,
    GeoSampleResult,
    GeoSampleRun,
    GeoTicket,
    Inquiry,
    Market,
    OnsiteIssue,
    OutreachItem,
    PageSpeedAudit,
    SeoPage,
    SeoPerformanceRow,
    SerpRun,
    SitePage,
    Tenant,
    User,
    WorkOrder,
)
from app.llm import status_label
from app.onsite_analyzer import rank_distribution
from app.routers.onsite.constants import OPENISH
from app.routers.onsite.common import decorate_weekly_issues, load_weekly_onsite_issues
from app.onsite_loop import dropped_restore_id, weekly_pin_state
from app.geo_loop import (
    FACT_PACK_BLOCK,
    cite_stage,
    cite_stage_label,
    fact_pack_ready,
    last_sampled_at_by_prompt,
    load_fact_pack,
    prompt_batch_rows,
    prompt_compare_note_for,
    prompt_trend_points,
    recorded_from_label,
    trend_note,
    trust_map_for_tenant,
    watch_state,
)
from app.customer_brief import build_customer_brief
from app.report_export import pdf_response
from app.site_identity import adopt_live_site
from app.schemas import (
    CustomerBriefOut,
    DashboardSummary,
    WorkbenchChain,
    WorkbenchItem,
    WorkbenchOut,
    WorkbenchSeoBucket,
    WorkbenchSeoPerformance,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

ISSUE_RANK = {"critical": 0, "high": 1, "low": 2}


def _summary_for(user: User, db: Session) -> DashboardSummary:
    tid = user.tenant_id
    tenant = db.get(Tenant, tid)
    if tenant is not None and adopt_live_site(db, tenant):
        db.commit()
    markets = db.query(func.count(Market.id)).filter(Market.tenant_id == tid).scalar() or 0
    priority = (
        db.query(func.count(Market.id)).filter(Market.tenant_id == tid, Market.status == "priority").scalar() or 0
    )
    seo_in_progress = (
        db.query(func.count(SeoPage.id))
        .filter(SeoPage.tenant_id == tid, SeoPage.status.in_(["outline", "draft", "meta"]))
        .scalar()
        or 0
    )
    seo_review = (
        db.query(func.count(SeoPage.id)).filter(SeoPage.tenant_id == tid, SeoPage.status == "review").scalar() or 0
    )
    seo_ready = (
        db.query(func.count(SeoPage.id)).filter(SeoPage.tenant_id == tid, SeoPage.status == "ready").scalar() or 0
    )
    open_wo = (
        db.query(func.count(WorkOrder.id))
        .filter(WorkOrder.tenant_id == tid, WorkOrder.status.in_(["open", "claimed", "in_progress", "blocked"]))
        .scalar()
        or 0
    )
    inquiries = db.query(func.count(Inquiry.id)).filter(Inquiry.tenant_id == tid).scalar() or 0
    qualified = (
        db.query(func.count(Inquiry.id)).filter(Inquiry.tenant_id == tid, Inquiry.quality == "qualified").scalar()
        or 0
    )
    geo_prompts = db.query(func.count(GeoPrompt.id)).filter(GeoPrompt.tenant_id == tid).scalar() or 0
    geo_untested = (
        db.query(func.count(GeoObservation.id))
        .filter(GeoObservation.tenant_id == tid, GeoObservation.status == "untested")
        .scalar()
        or 0
    )
    geo_recorded = (
        db.query(func.count(GeoObservation.id))
        .filter(GeoObservation.tenant_id == tid, GeoObservation.status != "untested")
        .scalar()
        or 0
    )
    geo_assets_draft = (
        db.query(func.count(GeoAsset.id)).filter(GeoAsset.tenant_id == tid, GeoAsset.status == "draft").scalar() or 0
    )
    geo_tickets_open = (
        db.query(func.count(GeoTicket.id))
        .filter(GeoTicket.tenant_id == tid, GeoTicket.status.in_(["open", "in_progress", "verify", "reopened"]))
        .scalar()
        or 0
    )
    geo_evidence_results = (
        db.query(func.count(GeoSampleResult.id)).filter(GeoSampleResult.tenant_id == tid).scalar() or 0
    )
    recent_geo_runs = (
        db.query(GeoSampleRun)
        .options(selectinload(GeoSampleRun.results))
        .filter(GeoSampleRun.tenant_id == tid)
        .order_by(GeoSampleRun.started_at.desc())
        .limit(12)
        .all()
    )
    latest_geo_batch, _previous_geo = pick_sample_batches(recent_geo_runs)
    geo_latest_sampled, geo_latest_mentioned, _owned, _third = summarize_runs(latest_geo_batch)
    geo_watch_due = len(due_watch_prompts(db, tid))
    onsite_pages = db.query(func.count(SitePage.id)).filter(SitePage.tenant_id == tid).scalar() or 0
    onsite_open_low = (
        db.query(func.count(OnsiteIssue.id))
        .filter(OnsiteIssue.tenant_id == tid, OnsiteIssue.severity == "low", OnsiteIssue.status.in_(OPENISH))
        .scalar()
        or 0
    )
    onsite_open_high = (
        db.query(func.count(OnsiteIssue.id))
        .filter(OnsiteIssue.tenant_id == tid, OnsiteIssue.severity == "high", OnsiteIssue.status.in_(OPENISH))
        .scalar()
        or 0
    )
    onsite_open_critical = (
        db.query(func.count(OnsiteIssue.id))
        .filter(
            OnsiteIssue.tenant_id == tid,
            OnsiteIssue.severity == "critical",
            OnsiteIssue.status.in_(OPENISH),
        )
        .scalar()
        or 0
    )
    offsite_gaps = db.query(func.count(BacklinkGap.id)).filter(BacklinkGap.tenant_id == tid).scalar() or 0
    links_unverified = (
        db.query(func.count(BacklinkGap.id))
        .filter(BacklinkGap.tenant_id == tid, BacklinkGap.verify_status == "unverified")
        .scalar()
        or 0
    )
    offsite_outreach_open = (
        db.query(func.count(OutreachItem.id))
        .filter(OutreachItem.tenant_id == tid, OutreachItem.status.in_(["todo", "sent_manual"]))
        .scalar()
        or 0
    )
    distribution_jobs = db.query(func.count(DistributionJob.id)).filter(DistributionJob.tenant_id == tid).scalar() or 0
    return DashboardSummary(
        tenant_name=tenant.name if tenant else "",
        markets_count=markets,
        priority_markets=priority,
        seo_in_progress=seo_in_progress,
        seo_pending_review=seo_review,
        seo_ready=seo_ready,
        open_work_orders=open_wo,
        inquiries_total=inquiries,
        qualified_inquiries=qualified,
        geo_prompts=geo_prompts,
        geo_untested=geo_untested,
        geo_recorded=geo_recorded,
        geo_assets_draft=geo_assets_draft,
        geo_tickets_open=geo_tickets_open,
        geo_evidence_results=geo_evidence_results,
        geo_latest_sampled=geo_latest_sampled,
        geo_latest_mentioned=geo_latest_mentioned,
        geo_watch_due=geo_watch_due,
        onsite_pages=onsite_pages,
        onsite_open_low=onsite_open_low,
        onsite_open_high=onsite_open_high,
        onsite_open_critical=onsite_open_critical,
        offsite_gaps=offsite_gaps,
        offsite_outreach_open=offsite_outreach_open,
        links_unverified=links_unverified,
        distribution_jobs=distribution_jobs,
        llm_status=status_label(),
    )


def _diagnostic_status(summary: DashboardSummary, site_origin: str) -> str:
    if not site_origin:
        return "待登记官网"
    if summary.onsite_pages == 0 and summary.geo_prompts == 0:
        return "待启动诊断"
    if summary.onsite_open_critical or summary.geo_tickets_open:
        return "诊断处理中"
    return "诊断可复核"


def _issue_tone(issue: OnsiteIssue) -> str:
    if issue.severity == "critical":
        return "red"
    if issue.severity == "high" or issue.risk == "high":
        return "amber"
    return "green"


def _chain_health(count: int, blocked: int = 0) -> tuple[str, str]:
    if blocked:
        return "有阻塞", "red"
    if count:
        return "待处理", "amber"
    return "正常", "green"


def _parse_perf_date(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _filter_performance_rows(rows: list[SeoPerformanceRow], days: int) -> list[SeoPerformanceRow]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    dated: list[SeoPerformanceRow] = []
    undated: list[SeoPerformanceRow] = []
    for row in rows:
        parsed = _parse_perf_date(row.date)
        if parsed is None:
            undated.append(row)
        elif parsed >= cutoff:
            dated.append(row)
    return dated if dated else undated


def _weighted_position(rows: list[SeoPerformanceRow]) -> float | None:
    total = 0
    weighted = 0.0
    for row in rows:
        if row.position is None:
            continue
        weight = row.impressions or 1
        weighted += row.position * weight
        total += weight
    return round(weighted / total, 2) if total else None


def _bucket(key: str, rows: list[SeoPerformanceRow]) -> WorkbenchSeoBucket:
    clicks = sum(row.clicks for row in rows)
    impressions = sum(row.impressions for row in rows)
    return WorkbenchSeoBucket(
        key=key or "未标注",
        clicks=clicks,
        impressions=impressions,
        ctr=round(clicks / impressions * 100, 2) if impressions else None,
        position=_weighted_position(rows),
    )


def _top_buckets(rows: list[SeoPerformanceRow], attr: str, limit: int | None = 5) -> list[WorkbenchSeoBucket]:
    grouped: dict[str, list[SeoPerformanceRow]] = defaultdict(list)
    for row in rows:
        grouped[getattr(row, attr) or "未标注"].append(row)
    buckets = sorted(
        (_bucket(key, values) for key, values in grouped.items()),
        key=lambda item: (item.impressions, item.clicks),
        reverse=True,
    )
    return buckets[:limit] if limit is not None else buckets


def _seo_performance_for(user: User, db: Session, days: int) -> WorkbenchSeoPerformance:
    tid = user.tenant_id
    rows = db.query(SeoPerformanceRow).filter(SeoPerformanceRow.tenant_id == tid).all()
    rows = _filter_performance_rows(rows, days)
    clicks = sum(row.clicks for row in rows)
    impressions = sum(row.impressions for row in rows)
    indexed_pages = (
        db.query(func.count(SitePage.id)).filter(SitePage.tenant_id == tid, SitePage.index_status.in_(["indexed", "已收录"])).scalar()
        or 0
    )
    pending_index = (
        db.query(func.count(SitePage.id)).filter(SitePage.tenant_id == tid, SitePage.index_status.in_(["untested", "unknown", "需 GSC"])).scalar()
        or 0
    )
    backlink_domains = db.query(func.count(BacklinkGap.id)).filter(BacklinkGap.tenant_id == tid).scalar() or 0
    unverified_backlinks = (
        db.query(func.count(BacklinkGap.id)).filter(BacklinkGap.tenant_id == tid, BacklinkGap.verify_status == "unverified").scalar()
        or 0
    )
    latest_speed = (
        db.query(PageSpeedAudit)
        .filter(PageSpeedAudit.tenant_id == tid)
        .order_by(PageSpeedAudit.audited_at.desc())
        .first()
    )
    serp_runs = (
        db.query(SerpRun)
        .filter(SerpRun.tenant_id == tid)
        .order_by(SerpRun.created_at.desc())
        .limit(50)
        .all()
    )
    ok_serp = [row for row in serp_runs if row.status == "ok"]
    own_positions = [row.own_best_position for row in ok_serp if row.own_best_position is not None]
    keyword_positions = [item.position for item in _top_buckets(rows, "query", limit=None)]
    return WorkbenchSeoPerformance(
        days=days,
        data_status="已导入" if rows else "未导入",
        total_clicks=clicks,
        total_impressions=impressions,
        avg_ctr=round(clicks / impressions * 100, 2) if impressions else None,
        avg_position=_weighted_position(rows),
        indexed_pages=indexed_pages,
        index_pending_pages=pending_index,
        backlink_domains=backlink_domains,
        unverified_backlinks=unverified_backlinks,
        authority_status="未接入第三方权重",
        pagespeed_status="已测速" if latest_speed else "未测速",
        latest_speed_score=latest_speed.performance_score if latest_speed else None,
        serp_status="已查询" if ok_serp else "未查询",
        serp_runs=len(serp_runs),
        serp_own_visible_runs=sum(1 for row in ok_serp if row.own_best_position is not None),
        serp_competitor_visible_runs=sum(1 for row in ok_serp if row.competitor_best_position is not None),
        serp_avg_own_position=round(sum(own_positions) / len(own_positions), 2) if own_positions else None,
        keyword_rank_distribution=rank_distribution(keyword_positions),
        serp_rank_distribution=rank_distribution([row.own_best_position for row in ok_serp]),
        top_countries=_top_buckets(rows, "country"),
        top_keywords=_top_buckets(rows, "query"),
        top_pages=_top_buckets(rows, "page_url"),
    )


@router.get("/summary", response_model=DashboardSummary)
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DashboardSummary:
    return _summary_for(user, db)


@router.get("/customer-brief", response_model=CustomerBriefOut)
def customer_brief(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CustomerBriefOut:
    return build_customer_brief(user, db)


@router.get("/customer-brief.pdf")
def customer_brief_pdf(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    brief = build_customer_brief(user, db)
    date = brief.generated_at.strftime("%Y-%m-%d")
    return pdf_response(title=brief.title, markdown_text=brief.markdown, filename=f"本周客户说明-{date}.pdf")


@router.get("/workbench", response_model=WorkbenchOut)
def workbench(
    days: int = Query(default=28, ge=7, le=180),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkbenchOut:
    days = 7 if days <= 7 else 28 if days <= 28 else 90 if days <= 90 else 180
    summary = _summary_for(user, db)
    seo_performance = _seo_performance_for(user, db, days)
    tenant = db.get(Tenant, user.tenant_id)
    site_origin = tenant.site_origin if tenant else ""

    issues = (
        db.query(OnsiteIssue)
        .join(SitePage, SitePage.id == OnsiteIssue.page_id)
        .filter(OnsiteIssue.tenant_id == user.tenant_id, OnsiteIssue.status.in_(OPENISH))
        .all()
    )
    issues = sorted(issues, key=lambda i: (ISSUE_RANK.get(i.severity, 9), ISSUE_RANK.get(i.risk, 9), i.created_at))
    seo_items = [
        WorkbenchItem(
            id=i.id,
            title=i.title,
            subtitle=i.page.path if i.page else "站内页面",
            href=f"/onsite/{i.page_id}",
            status="需要人审" if i.risk == "high" else "可先落工作区",
            tone=_issue_tone(i),
            meta=f"{i.severity.upper()} / {i.category}",
            action_label="处理 SEO 问题",
        )
        for i in issues[:5]
    ]

    tickets = (
        db.query(GeoTicket)
        .join(GeoPrompt, GeoPrompt.id == GeoTicket.prompt_id)
        .filter(GeoTicket.tenant_id == user.tenant_id, GeoTicket.status.in_(["open", "in_progress", "verify", "reopened"]))
        .order_by(GeoTicket.updated_at.desc())
        .limit(5)
        .all()
    )
    geo_items = [
        WorkbenchItem(
            id=t.id,
            title=t.title,
            subtitle=t.prompt.prompt_text if t.prompt else "买家问题",
            href="/geo",
            status="待复查" if t.status == "verify" else "待处理",
            tone="red" if t.status == "reopened" else "amber",
            meta=t.diagnosis,
            action_label="去复查",
        )
        for t in tickets
    ]

    signals = (
        db.query(DemandSignal)
        .join(Market, Market.id == DemandSignal.market_id)
        .filter(
            DemandSignal.tenant_id == user.tenant_id,
            DemandSignal.source != "target_archived",
            Market.status != "paused",
        )
        .order_by(DemandSignal.created_at.desc())
        .limit(4)
        .all()
    )
    recent_signals = [
        WorkbenchItem(
            id=s.id,
            title=s.theme,
            subtitle=f"{s.market.name if s.market else '市场'} / {s.locale}",
            href=f"/insights/{s.market_id}",
            status="待投喂" if s.source == "manual" else s.source,
            tone="blue",
            meta=f"强度 {s.intensity}",
            action_label="查看信号",
        )
        for s in signals
    ]

    fetched_pages = (
        db.query(func.count(SitePage.id))
        .filter(
            SitePage.tenant_id == user.tenant_id,
            or_(SitePage.crawl_status == "ok", SitePage.fetched_at.isnot(None)),
        )
        .scalar()
        or 0
    )

    week_rows = load_weekly_onsite_issues(db, user.tenant_id)
    week_out = decorate_weekly_issues(db, user.tenant_id, week_rows)
    pin = weekly_pin_state(db, user.tenant_id)
    latest_by, previous_by = prompt_batch_rows(db, user.tenant_id)
    last_by = last_sampled_at_by_prompt(db, user.tenant_id)
    geo_questions: list[WorkbenchItem] = []
    cite_published = cite_sent = cite_draft = 0
    for prompt in (
        db.query(GeoPrompt)
        .filter(GeoPrompt.tenant_id == user.tenant_id)
        .order_by(GeoPrompt.created_at.desc())
        .limit(8)
        .all()
    ):
        note = prompt_compare_note_for(prompt.id, latest_by, previous_by)
        points = prompt_trend_points(db, user.tenant_id, prompt.id)
        watched = watch_state(last_by.get(prompt.id))
        stage = cite_stage(prompt)
        if stage == "published":
            cite_published += 1
        elif stage == "sent":
            cite_sent += 1
        else:
            cite_draft += 1
        if stage == "published":
            status, tone = "客户已贴，可再测", "green"
        elif stage == "sent":
            status, tone = "资产已发，等客户贴", "blue"
        elif last_by.get(prompt.id) is None:
            status, tone = "还没抽查", "amber"
        elif watched["due"]:
            status, tone = "到期该复测", "amber"
        elif "仍没有提到" in note or note.startswith("这一次没有提到"):
            status, tone = "没提到", "amber"
        elif "这次提到了" in note or note.startswith("这一次提到了") or "这次也提到了" in note:
            status, tone = "提到了", "green"
        else:
            status, tone = "已抽查", "default"
        source = recorded_from_label(getattr(prompt, "recorded_from", "") or "")
        extra = (getattr(prompt, "source_note", "") or "").strip()
        geo_questions.append(
            WorkbenchItem(
                id=prompt.id,
                title=prompt.prompt_text,
                subtitle=f"{source}{(' · ' + extra) if extra else ''}",
                href="/geo",
                status=status,
                tone=tone,
                meta=f"{note} {cite_stage_label(stage)}".strip(),
                trend=trend_note(points),
                action_label="去作战室",
            )
        )

    trust_map = trust_map_for_tenant(db, user.tenant_id, tenant)
    source_tone = {"owned": "green", "marketplace": "amber", "competitor": "red", "other": "blue"}
    geo_trust_sources = [
        WorkbenchItem(
            id=f"src-{row['host']}",
            title=row["host"],
            subtitle=row["kind_label"],
            href="/geo",
            status=f"{row['hits']} 次",
            tone=source_tone.get(row["kind"], "default"),
            meta=row.get("sample_prompt") or "",
            action_label="去作战室",
        )
        for row in trust_map["sources"]
    ]
    geo_competitors = [
        WorkbenchItem(
            id=f"comp-{row['name']}",
            title=row["name"],
            subtitle="选题里已记" if row["registered"] else "抽查里出现",
            href="/geo",
            status=f"{row['hits']} 次",
            tone="red" if row["registered"] else "amber",
            meta=row.get("sample_prompt") or "",
            action_label="去作战室",
        )
        for row in trust_map["competitors"]
    ]

    weekly_onsite: list[WorkbenchItem] = []
    for item in week_out:
        if item.sent_to_customer:
            status, tone = "已发给客户", "blue"
        elif (item.retest_result or "").startswith("打开过该页"):
            status, tone = "打开过，还没过", "amber"
        else:
            status, tone = "待发给客户", "default"
        weekly_onsite.append(
            WorkbenchItem(
                id=item.id,
                title=item.title,
                subtitle=item.page_path or "站内页面",
                href="/onsite",
                status=status,
                tone=tone,
                meta=(item.customer_note or item.retest_result or "").strip(),
                action_label="去站内",
            )
        )

    next_actions: list[WorkbenchItem] = []
    if summary.geo_watch_due:
        next_actions.append(
            WorkbenchItem(
                id="geo-watch-due",
                title=f"常驻复测：{summary.geo_watch_due} 句到期",
                subtitle="同一批已记问句该再抽了。没有原句不会编。不保证这次被提到。",
                href="/geo",
                status="到期该复测",
                tone="amber",
                action_label="去作战室",
            )
        )
    if weekly_onsite:
        next_actions.append(
            WorkbenchItem(
                id="weekly-three",
                title="这周给客户改三处",
                subtitle="；".join(item.subtitle for item in weekly_onsite),
                href="/onsite",
                status="已钉住" if pin.get("issue_ids") else "待钉住",
                tone="amber",
                action_label="去站内",
            )
        )
    if cite_published:
        next_actions.append(
            WorkbenchItem(
                id="cite-retest",
                title=f"同一问再测：{cite_published} 句客户已贴上",
                subtitle="只记有没有变化。不保证这次被提到。我们不代改。",
                href="/geo",
                status="可再测",
                tone="green",
                action_label="去作战室",
            )
        )
    elif cite_sent:
        next_actions.append(
            WorkbenchItem(
                id="cite-wait",
                title="等客户贴上可引用资产",
                subtitle="已把英文段发给客户。他们贴完再记页地址，同一问再测。我们不代改。",
                href="/geo",
                status="等客户贴",
                tone="blue",
                action_label="去作战室",
            )
        )
    elif cite_draft:
        pack_ok = fact_pack_ready(load_fact_pack(db, tenant), tenant)
        next_actions.append(
            WorkbenchItem(
                id="cite-send" if pack_ok else "cite-fact-pack",
                title="把英文段发给客户" if pack_ok else "先补 Fact Pack 再出草稿",
                subtitle="草稿只写已记事实。客户自己贴。我们不代改。" if pack_ok else FACT_PACK_BLOCK,
                href="/geo",
                status="草稿待发" if pack_ok else "缺 Fact Pack",
                tone="amber",
                action_label="去作战室",
            )
        )
    if not site_origin:
        next_actions.append(
            WorkbenchItem(
                id="set-origin",
                title="先登记客户官网",
                subtitle="网站检查需要网址，系统只查看已登记页面。",
                href="/onsite",
                status="待配置",
                tone="amber",
                action_label="去登记",
            )
        )
    elif summary.onsite_pages and fetched_pages == 0:
        next_actions.append(
            WorkbenchItem(
                id="fetch-site",
                title="先查看客户网页",
                subtitle="页面已登记，但还没打开看过。先查看再写改法。",
                href="/onsite",
                status="待查看",
                tone="amber",
                action_label="去查看",
            )
        )
    elif summary.onsite_pages and (summary.onsite_open_critical or summary.onsite_open_high):
        next_actions.append(
            WorkbenchItem(
                id="seo-critical",
                title="优先处理紧急网站问题",
                subtitle=f"紧急 {summary.onsite_open_critical} / 优先 {summary.onsite_open_high}",
                href="/onsite",
                status="需确认",
                tone="red" if summary.onsite_open_critical else "amber",
                action_label="去处理",
            )
        )
    if summary.geo_latest_sampled:
        sampled = summary.geo_latest_sampled
        mentioned = summary.geo_latest_mentioned
        if mentioned == 0:
            mention_bit = "都没有提到我们。"
        elif mentioned == sampled:
            mention_bit = "都提到了品牌。"
        else:
            mention_bit = f"其中 {mentioned} 条提到品牌。"
        next_actions.append(
            WorkbenchItem(
                id="geo-sampling",
                title="看这一轮 AI 搜索抽查",
                subtitle=f"联网搜索写了 {sampled} 条记录，{mention_bit}ChatGPT 等引擎还没打开。",
                href="/geo",
                status="已抽查",
                tone="default",
                action_label="去查看",
            )
        )
    elif summary.geo_prompts:
        next_actions.append(
            WorkbenchItem(
                id="geo-sampling",
                title="联网抽查买家问题",
                subtitle=f"{summary.geo_prompts} 个买家问题还没抽查。",
                href="/geo",
                status="尚未检查",
                tone="amber",
                action_label="去检查",
            )
        )
    if summary.geo_tickets_open:
        next_actions.append(
            WorkbenchItem(
                id="geo-ticket",
                title="复核 AI 搜索待处理项",
                subtitle=f"{summary.geo_tickets_open} 个 AI 搜索待处理项未关闭。",
                href="/geo",
                status="待复查",
                tone="amber",
                action_label="去复查",
            )
        )
    if not next_actions:
        next_actions.append(
            WorkbenchItem(
                id="diagnosis-ready",
                title="查看搜索数据并安排下一轮复查",
                subtitle="按展示、点击、点开率和打开速度判断下一批优先项。",
                href="/onsite",
                status="可复盘",
                tone="green",
                action_label="进入检查",
            )
        )

    seo_health, seo_tone = _chain_health(summary.onsite_open_critical + summary.onsite_open_high)
    geo_health, geo_tone = _chain_health(
        summary.geo_tickets_open + (0 if summary.geo_latest_sampled else summary.geo_prompts)
    )
    chains = [
        WorkbenchChain(
            key="seo",
            title="网站检查",
            href="/onsite",
            primary=summary.onsite_open_critical + summary.onsite_open_high,
            secondary=f"{summary.onsite_pages} 个页面 / 常规 {summary.onsite_open_low}",
            health=seo_health,
            tone=seo_tone,
            action_label="进入检查",
        ),
        WorkbenchChain(
            key="geo",
            title="AI 搜索可见度",
            href="/geo",
            primary=summary.geo_tickets_open,
            secondary=(
                f"{summary.geo_prompts} 个买家问题 / 最近抽查 {summary.geo_latest_sampled} 条，提到 {summary.geo_latest_mentioned}"
                if summary.geo_latest_sampled
                else f"{summary.geo_prompts} 个买家问题 / 还没联网抽查"
            ),
            health=geo_health,
            tone=geo_tone,
            action_label="进入检查",
        ),
    ]

    return WorkbenchOut(
        summary=summary,
        site_origin=site_origin or "",
        diagnostic_status=_diagnostic_status(summary, site_origin or ""),
        seo_performance=seo_performance,
        next_actions=next_actions[:6],
        seo_items=seo_items,
        geo_items=geo_items,
        recent_signals=recent_signals,
        chains=chains,
        weekly_onsite=weekly_onsite,
        weekly_pinned=bool(pin.get("issue_ids")),
        weekly_can_restore=bool(dropped_restore_id(db, user.tenant_id)),
        geo_questions=geo_questions,
        geo_trust_sources=geo_trust_sources,
        geo_competitors=geo_competitors,
        geo_trust_note=" ".join(
            part for part in (str(trust_map.get("note") or ""), str(trust_map.get("compare_note") or "")) if part
        ),
        deferred_modules=[
            WorkbenchItem(
                id="sem",
                title="SEM 投放",
                subtitle="广告账户、预算、关键词与线索归因后续接入。",
                href="/home",
                status="延后开发",
                tone="default",
                meta="不进入当前诊断闭环",
                action_label="暂不开放",
            ),
            WorkbenchItem(
                id="social",
                title="新媒体推广",
                subtitle="社媒内容日历、渠道发布与互动跟进后续接入。",
                href="/home",
                status="延后开发",
                tone="default",
                meta="不做假数据占位",
                action_label="暂不开放",
            ),
        ],
    )
