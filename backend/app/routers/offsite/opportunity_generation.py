from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import BacklinkGap, GeoTicket, OnsiteIssue, SeoPerformanceRow, SerpRun, SitePage, User
from app.schemas import OffsiteOpportunityGenerateOut

from . import router
from .common import _gap_out


CLOSED_STATUSES = {"closed", "ignored", "won", "skipped"}
CONTENT_CATEGORIES = {"content", "b2b", "inquiry", "schema"}


def _priority(value: str | None, fallback: str = "P2") -> str:
    return value if value in {"P0", "P1", "P2", "P3"} else fallback


def _dedupe_key(source: str, issue_type: str, title: str, url: str = "") -> str:
    return " | ".join([source.strip().lower(), issue_type.strip().lower(), title.strip().lower(), url.strip().lower()])


def _existing_keys(db: Session, tenant_id: str) -> set[str]:
    rows = (
        db.query(BacklinkGap.source, BacklinkGap.issue_type, BacklinkGap.title, BacklinkGap.link_url)
        .filter(BacklinkGap.tenant_id == tenant_id)
        .all()
    )
    return {_dedupe_key(source or "", issue_type or "", title or "", link_url or "") for source, issue_type, title, link_url in rows}


def _add_gap_if_new(
    db: Session,
    tenant_id: str,
    keys: set[str],
    *,
    title: str,
    issue_type: str,
    source: str,
    competitor_name: str,
    referring_domain: str,
    priority: str,
    recommended_action: str,
    acceptance_criteria: str,
    retest_method: str,
    notes: str,
    link_url: str = "",
    market_id: str | None = None,
) -> BacklinkGap | None:
    key = _dedupe_key(source, issue_type, title, link_url)
    if key in keys:
        return None
    row = BacklinkGap(
        tenant_id=tenant_id,
        market_id=market_id,
        title=title[:300],
        issue_type=issue_type,
        source=source,
        competitor_name=competitor_name[:200] or "客户官网",
        referring_domain=referring_domain[:300] or "unknown",
        link_url=link_url or None,
        kind="competitor",
        priority=priority,
        verify_status="unverified",
        our_presence="none",
        domain_metric="untested",
        status="identified",
        owner_hint="站外执行",
        acceptance_criteria=acceptance_criteria,
        recommended_action=recommended_action,
        retest_method=retest_method,
        notes=notes,
    )
    db.add(row)
    keys.add(key)
    return row


def _generate_from_geo(db: Session, user: User, keys: set[str], limit: int) -> tuple[list[BacklinkGap], int]:
    rows = (
        db.query(GeoTicket)
        .options(selectinload(GeoTicket.prompt))
        .filter(GeoTicket.tenant_id == user.tenant_id, ~GeoTicket.status.in_(CLOSED_STATUSES))
        .order_by(GeoTicket.created_at.desc())
        .limit(limit)
        .all()
    )
    created: list[BacklinkGap] = []
    skipped = 0
    for ticket in rows:
        prompt = ticket.prompt.prompt_text if ticket.prompt else ""
        row = _add_gap_if_new(
            db,
            user.tenant_id,
            keys,
            title=f"GEO 引用缺口：{ticket.title}",
            issue_type="geo_citation_gap",
            source="geo",
            competitor_name="AI 搜索引用源",
            referring_domain="ai-search-sources",
            priority=_priority(ticket.priority, "P1"),
            recommended_action=(
                "围绕该 AI 问答场景准备可被第三方引用的公司资料、产品说明或专家内容；优先选择行业目录、"
                "媒体、协会、榜单或高质量 B2B 平台。"
            ),
            acceptance_criteria="形成至少一个可访问的第三方结果页，并记录 result_url；后续 GEO 采样复测是否出现品牌提及或引用。",
            retest_method="重新运行对应 GEO 问句采样，检查品牌是否被提及、是否有第三方引用和引用来源质量。",
            notes=f"来自 GEO 问题：{prompt or ticket.rationale or ticket.diagnosis}",
        )
        if row:
            created.append(row)
        else:
            skipped += 1
    return created, skipped


def _generate_from_onsite(db: Session, user: User, keys: set[str], limit: int) -> tuple[list[BacklinkGap], int]:
    rows = (
        db.query(OnsiteIssue)
        .options(selectinload(OnsiteIssue.page))
        .filter(
            OnsiteIssue.tenant_id == user.tenant_id,
            ~OnsiteIssue.status.in_(CLOSED_STATUSES),
            or_(
                OnsiteIssue.category.in_(CONTENT_CATEGORIES),
                OnsiteIssue.title.ilike("%内容%"),
                OnsiteIssue.title.ilike("%询盘%"),
                OnsiteIssue.title.ilike("%B2B%"),
            ),
        )
        .order_by(OnsiteIssue.priority.asc(), OnsiteIssue.created_at.desc())
        .limit(limit)
        .all()
    )
    created: list[BacklinkGap] = []
    skipped = 0
    for issue in rows:
        page: SitePage | None = issue.page
        page_ref = page.final_url or page.path if page else ""
        row = _add_gap_if_new(
            db,
            user.tenant_id,
            keys,
            title=f"站内内容缺口可转站外素材：{issue.title}",
            issue_type="onsite_content_gap",
            source="onsite",
            competitor_name="客户官网",
            referring_domain="owned-content",
            priority=_priority(issue.priority, "P2"),
            recommended_action=(
                "先补齐官网页面的事实、参数、应用场景或询盘入口，再提炼成平台资料、FAQ、公司简介或投稿 pitch。"
            ),
            acceptance_criteria="官网内容完成修正；至少准备一份人工批准的对外材料，并绑定到后续站外执行任务。",
            retest_method="复测原站内 Issue 是否关闭；若已发布到第三方，再核验 result_url 和品牌/链接情况。",
            notes=f"来自站内诊断：{issue.detail or issue.proposed_change or page_ref}",
            link_url=page_ref,
        )
        if row:
            created.append(row)
        else:
            skipped += 1
    return created, skipped


def _generate_from_seo_performance(db: Session, user: User, keys: set[str], limit: int) -> tuple[list[BacklinkGap], int]:
    rows = (
        db.query(SeoPerformanceRow)
        .filter(
            SeoPerformanceRow.tenant_id == user.tenant_id,
            SeoPerformanceRow.query != "",
            SeoPerformanceRow.impressions > 0,
            or_(SeoPerformanceRow.position.is_(None), SeoPerformanceRow.position > 10),
        )
        .order_by(SeoPerformanceRow.impressions.desc(), SeoPerformanceRow.created_at.desc())
        .limit(limit)
        .all()
    )
    created: list[BacklinkGap] = []
    skipped = 0
    for row in rows:
        position = "未测" if row.position is None else f"{row.position:.1f}"
        priority = "P1" if row.impressions >= 100 and (row.position is None or row.position > 20) else "P2"
        gap = _add_gap_if_new(
            db,
            user.tenant_id,
            keys,
            title=f"SEO 关键词曝光弱：{row.query}",
            issue_type="seo_keyword_gap",
            source="seo",
            competitor_name="Google/Bing 搜索结果",
            referring_domain="google.com",
            priority=priority,
            recommended_action=(
                "围绕该关键词补官网内容和第三方曝光：优先选择行业目录、B2B 平台、榜单/测评页或媒体资料页，"
                "让搜索结果里出现更多可验证的品牌资料。"
            ),
            acceptance_criteria="明确目标页面和对外材料；至少创建一个站外执行任务或说明本周期暂不处理原因。",
            retest_method="重新导入 GSC/Bing 或 SERP 数据，对比 Top 10/30/50 覆盖和点击、曝光、平均排名变化。",
            notes=f"来自 SEO 表现数据：曝光 {row.impressions}，点击 {row.clicks}，平均排名 {position}，国家 {row.country or '未分国家'}。",
            link_url=row.page_url,
        )
        if gap:
            created.append(gap)
        else:
            skipped += 1
    return created, skipped


def _generate_from_serp(db: Session, user: User, keys: set[str], limit: int) -> tuple[list[BacklinkGap], int]:
    rows = (
        db.query(SerpRun)
        .filter(
            SerpRun.tenant_id == user.tenant_id,
            SerpRun.status == "ok",
            SerpRun.keyword != "",
            or_(SerpRun.own_best_position.is_(None), SerpRun.own_best_position > 10),
        )
        .order_by(SerpRun.created_at.desc())
        .limit(limit)
        .all()
    )
    created: list[BacklinkGap] = []
    skipped = 0
    for run in rows:
        own_position = "未进入前 10" if run.own_best_position is None else f"第 {run.own_best_position} 位"
        gap = _add_gap_if_new(
            db,
            user.tenant_id,
            keys,
            title=f"SERP 可见度缺口：{run.keyword}",
            issue_type="serp_visibility_gap",
            source="seo",
            competitor_name="Google SERP",
            referring_domain="google.com",
            priority="P1" if run.third_party_count >= 3 else "P2",
            recommended_action="查看当前前 10 中的第三方页面类型，选择可进入的目录、榜单、媒体或 B2B 平台推进资料覆盖。",
            acceptance_criteria="记录目标第三方平台或页面，并创建对应执行任务；若不适合执行，写明不做原因。",
            retest_method="重新查询同一关键词 SERP，观察自有页面与第三方品牌资料在 Top 10/30/50 的覆盖变化。",
            notes=f"来自 SERP 查询：我方最佳位置 {own_position}，第三方结果 {run.third_party_count} 个，国家 {run.country or '未指定'}。",
        )
        if gap:
            created.append(gap)
        else:
            skipped += 1
    return created, skipped


@router.post("/gaps/generate-from-signals", response_model=OffsiteOpportunityGenerateOut)
def generate_opportunities_from_signals(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OffsiteOpportunityGenerateOut:
    keys = _existing_keys(db, user.tenant_id)
    geo_created, geo_skipped = _generate_from_geo(db, user, keys, 8)
    onsite_created, onsite_skipped = _generate_from_onsite(db, user, keys, 8)
    seo_perf_created, seo_perf_skipped = _generate_from_seo_performance(db, user, keys, 8)
    serp_created, serp_skipped = _generate_from_serp(db, user, keys, 8)
    created_rows = geo_created + onsite_created + seo_perf_created + serp_created
    db.commit()
    for row in created_rows:
        db.refresh(row)
        row.outreach = []
    return OffsiteOpportunityGenerateOut(
        created=len(created_rows),
        skipped=geo_skipped + onsite_skipped + seo_perf_skipped + serp_skipped,
        from_geo=len(geo_created),
        from_onsite=len(onsite_created),
        from_seo=len(seo_perf_created) + len(serp_created),
        note=(
            "已把 GEO、SEO 表现和站内内容类问题转成站外可执行机会。"
            if created_rows
            else "没有发现新的可转化站外机会；已有机会不会重复创建。"
        ),
        gaps=[_gap_out(row) for row in created_rows],
    )
