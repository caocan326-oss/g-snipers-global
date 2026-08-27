"""One customer-facing weekly brief. Counts only; no invented ranks."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.models import GeoPrompt, GeoTicket, Inquiry, OnsiteIssue, SeoPerformanceRow, SerpRun, SitePage, Tenant, User
from app.geo_loop import (
    FACT_PACK_BLOCK,
    cite_pack_for_prompt,
    cite_paste_for_prompt,
    cite_published_url,
    cite_stage,
    cite_stage_label,
    last_sampled_at_by_prompt,
    prompt_batch_rows,
    prompt_compare_note_for,
    prompt_trend_points,
    recorded_from_label,
    trend_note,
    watch_state,
    reconcile_open_ticket_status,
    refresh_open_tickets_from_samples,
    ticket_customer_note,
    ticket_handoff,
    ticket_live_url,
    ticket_offsite_ask,
    trust_map_for_tenant,
    weekly_paste,
)
from app.onsite_loop import issue_customer_note, weekly_pin_state
from app.routers.geo.prompts import geo_summary
from app.routers.onsite.common import (
    _active_issue,
    _page_short,
    _plain_title,
    _severity_label,
    load_weekly_onsite_issues,
)
from app.schemas import CustomerBriefOut, CustomerBriefSection


def _display_rate(value: str | None) -> str:
    if not value or value == "未测":
        return "尚未检查"
    return value


def _geo_plain(geo) -> tuple[str, str]:
    """客户说明只写买家问题和抽查结果，不写 8 个引擎空位。"""
    engines = "ChatGPT、Perplexity 等引擎还没逐个打开。"
    if getattr(geo, "latest_sampled", 0):
        n = geo.latest_sampled
        split = (getattr(geo, "latest_mention_split", "") or "").strip()
        if geo.latest_mentioned == 0 and geo.latest_owned == 0:
            core = f"联网搜索写了 {n} 条记录，都没有提到我们，也没有给出官网。"
        elif geo.latest_mentioned and geo.latest_owned == 0:
            core = f"联网搜索写了 {n} 条记录，其中 {geo.latest_mentioned} 条提到品牌，没有给出官网。"
        elif geo.latest_owned:
            verified = (getattr(geo, "verified_citation_rate", None) or "").strip()
            if verified and verified not in {"未测", "尚未检查"} and not verified.startswith("0"):
                core = f"联网搜索写了 {n} 条记录，其中 {geo.latest_owned} 条给出了疑似官网；已核对比例 {verified}。"
            else:
                core = f"联网搜索写了 {n} 条记录，其中 {geo.latest_owned} 条给出了疑似官网，还要人工打开核对，不能写成已经确认。"
        else:
            core = f"联网搜索写了 {n} 条记录。"
        extra = ""
        if split:
            extra = split
        elif geo.latest_third_party and geo.latest_owned == 0:
            extra = f"搜到 {geo.latest_third_party} 个外来网址，不能写成给出了官网。"
        if geo.latest_third_party and geo.latest_owned == 0 and split:
            extra = f"{split}搜到 {geo.latest_third_party} 个外来网址，不能写成给出了官网。"
        compare = getattr(geo, "compare_note", "") or ""
        bound = "这一轮是联网搜索源（如 Tavily / 博查），不是 ChatGPT 本人。"
        return core, " ".join(part for part in (core, extra, compare, bound, engines) if part)
    if geo.prompts:
        core = f"{geo.prompts} 个买家问题还没联网抽查。"
        return core, f"{core}{engines}引擎空位不算这一周的缺口。"
    return "", "还没有买家问题，AI 搜索这一块只能写尚未开始。"


def _headline(
    *,
    site_origin: str,
    pages: int,
    critical: int,
    high: int,
    geo_core: str,
    geo_sampled: int,
    geo_prompts: int,
) -> str:
    if not site_origin:
        return "还没登记官网。这一周先记下客户网站，再查看网页和 AI 搜索。"
    if not pages:
        return "官网已登记，但还没查看网页。先把页面看一遍，再写改法。"
    if critical:
        extra = f"另外，{geo_core}" if geo_core else "AI 搜索已有记录，尚未检查的不要写成结论。"
        return f"这一周先处理 {critical} 个紧急网站问题。{extra}"
    if high:
        geo_bit = geo_core or "AI 搜索已有记录。"
        return f"没有紧急问题，还有 {high} 个优先网站问题要跟。{geo_bit}"
    if geo_sampled:
        return f"{geo_core} ChatGPT、Perplexity 等引擎还没逐个打开。"
    if geo_prompts:
        return f"网站紧急问题不多。这一周先联网抽查 {geo_prompts} 个买家问题。"
    return "这一周可以把网站改法和 AI 搜索检查对一下，再写给客户。"


def _month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def build_customer_brief(user: User, db: Session) -> CustomerBriefOut:
    tenant = db.get(Tenant, user.tenant_id)
    site_origin = (tenant.site_origin if tenant else "") or ""
    generated = datetime.now(timezone.utc)
    title = f"本周客户说明 - {tenant.name if tenant else ''}".strip()

    pages = (
        db.query(SitePage)
        .filter(SitePage.tenant_id == user.tenant_id)
        .order_by(SitePage.path)
        .all()
    )
    issues = (
        db.query(OnsiteIssue)
        .options(selectinload(OnsiteIssue.page))
        .filter(OnsiteIssue.tenant_id == user.tenant_id)
        .order_by(OnsiteIssue.severity, OnsiteIssue.status, OnsiteIssue.created_at)
        .all()
    )
    active = [issue for issue in issues if _active_issue(issue)]
    critical = [issue for issue in active if issue.severity == "critical"]
    high = [issue for issue in active if issue.severity == "high"]
    priority_issues = load_weekly_onsite_issues(db, user.tenant_id)
    waiting = [issue for issue in active if issue.status in {"confirmed", "draft_applied"}]

    geo = geo_summary(user, db)
    if refresh_open_tickets_from_samples(db, user.tenant_id) or reconcile_open_ticket_status(db, user.tenant_id):
        db.commit()
    tickets = (
        db.query(GeoTicket)
        .options(selectinload(GeoTicket.prompt))
        .filter(
            GeoTicket.tenant_id == user.tenant_id,
            GeoTicket.status.in_(["open", "in_progress", "verify", "reopened"]),
        )
        .order_by(GeoTicket.updated_at.desc())
        .limit(5)
        .all()
    )
    serp_ok = (
        db.query(SerpRun)
        .filter(SerpRun.tenant_id == user.tenant_id, SerpRun.status == "ok")
        .all()
    )
    impressions = (
        db.query(func.coalesce(func.sum(SeoPerformanceRow.impressions), 0))
        .filter(SeoPerformanceRow.tenant_id == user.tenant_id)
        .scalar()
        or 0
    )
    clicks = (
        db.query(func.coalesce(func.sum(SeoPerformanceRow.clicks), 0))
        .filter(SeoPerformanceRow.tenant_id == user.tenant_id)
        .scalar()
        or 0
    )
    inquiry_count = (
        db.query(func.count(Inquiry.id))
        .filter(Inquiry.tenant_id == user.tenant_id, Inquiry.created_at >= _month_start(generated))
        .scalar()
        or 0
    )

    geo_core, geo_find = _geo_plain(geo)

    untested: list[str] = []
    if not site_origin:
        untested.append("客户官网尚未登记。")
    if site_origin and not pages:
        untested.append("还没有查看网页，不能写网站结论。")
    if not serp_ok:
        untested.append("目标词在谷歌前排还没查过。")
    if not impressions:
        untested.append("谷歌搜索表现还没有可用数据。")
    if geo_find:
        untested.append(geo_find)
    elif not geo.prompts:
        untested.append("还没有买家问题，AI 搜索这一块只能写尚未开始。")
    if not geo.latest_sampled and _display_rate(geo.verified_citation_rate) == "尚未检查":
        untested.append("官网来源尚未核对。提到品牌不等于给出了官网。")
    if not untested:
        untested.append("这一轮该查的都有记录。没核对过的来源仍不要写成已推荐。")

    findability: list[str] = []
    if not site_origin:
        findability.append("还没登记官网，谈不上老外搜不搜得到。")
    elif not pages:
        findability.append("官网已登记，但还没查看网页，不能写搜索结论。")
    if serp_ok:
        own = sum(1 for row in serp_ok if row.own_best_position is not None)
        competitors = sum(1 for row in serp_ok if row.competitor_best_position is not None)
        findability.append(f"目标词里，我方出现 {own} 次，竞品出现 {competitors} 次。")
    elif site_origin:
        findability.append("目标词在谷歌前排还没查过，这一项标尚未检查。")
    if impressions:
        findability.append(f"最近导入的搜索数据：曝光 {int(impressions)}，点击 {int(clicks)}。")
    elif site_origin:
        findability.append("谷歌搜索表现还没有可用数据，不能写成已经有曝光。")
    discovery = [
        issue
        for issue in critical
        if issue.category in {"index", "canonical", "crawl"} or "noindex" in (issue.title or "")
    ]
    for issue in discovery[:3]:
        findability.append(f"{_plain_title(issue.title)}（{_page_short(issue.page)}）")
    if geo_find:
        findability.append(geo_find)
    if tickets:
        findability.append(tickets[0].title)
    if not findability:
        findability.append("这一轮还没有足够记录，说明里只能写尚未检查。")

    this_week: list[str] = []
    if not site_origin:
        this_week.append("登记客户官网。")
    elif not pages:
        this_week.append("查看已登记网站的页面。")
    geo_lines: list[str] = []
    for ticket in tickets[:1]:
        note = ticket_customer_note(ticket, ticket.prompt)
        ask = ticket_offsite_ask(ticket, ticket.prompt)
        block = f"{ticket.title}\n{note}".strip() if note else ticket.title
        if ask:
            block = f"{block}\n{ask}"
        geo_lines.append(block)
    for issue in priority_issues:
        note = issue_customer_note(issue, issue.page, site_origin)
        this_week.append(f"{_severity_label(issue.severity)}\n{note}".strip() if note else _plain_title(issue.title))
    this_week.extend(geo_lines[:1])
    if not this_week:
        this_week.append("对照已有记录，整理给客户的说明，并安排下一轮复查。")

    retest: list[str] = []
    geo_waiting = [ticket for ticket in tickets if ticket_handoff(ticket) in {"drafted", "sent"}]
    geo_live = [ticket for ticket in tickets if ticket_handoff(ticket) == "live"]
    if geo_waiting:
        retest.append("AI 搜索改法还在工作台或已发给客户。客户页没上线、帖没发出前不要再测。工作台打勾不是官网已改。")
    if geo_live:
        live_urls = [ticket_live_url(ticket) for ticket in geo_live if ticket_live_url(ticket)]
        if live_urls:
            retest.append(
                f"客户登记了上线地址：{live_urls[0]}。"
                "用同一买家问题再抽查一次。只记变化，不承诺这次会提到。登记地址不是我们打开核对过的证明。"
            )
        else:
            retest.append("有项标了客户已上线，但没有页或帖地址。先补链接再测。工作台打勾不是官网已改。")
    if waiting:
        retest.append(
            f"工作台记了 {len(waiting)} 处「已改 / 人工上线」，还要再打开页面核对。"
            "这只是工作台打勾，不是客户官网已经改完的证明。"
        )
    elif priority_issues:
        sent_ids = set(weekly_pin_state(db, user.tenant_id).get("sent_ids") or [])
        if any(issue.id in sent_ids for issue in priority_issues):
            retest.append("这周这几处已发给客户。他们改完再打开对应页核对。工作台打勾不是官网已改。我们不代改。")
        else:
            retest.append("客户改完这几处后，再抓一次对应页面核对。我们不改客户官网。")
    compare_note = getattr(geo, "compare_note", "") or ""
    if compare_note:
        retest.append(compare_note)
    elif geo.latest_sampled:
        retest.append("客户改完对应页或发出帖后，用同一买家问题再抽查一次。只记有没有变化，不承诺这次会提到。")
    if not retest:
        retest.append("这一轮还没有要复查的改动。")

    inquiry_items = [
        f"这个月记到 {inquiry_count} 条。",
        "软件不会自动抓邮箱。客户来问之后，由客户经理登记。",
    ]

    buyer_prompts = (
        db.query(GeoPrompt)
        .filter(GeoPrompt.tenant_id == user.tenant_id)
        .order_by(GeoPrompt.created_at.desc())
        .limit(8)
        .all()
    )
    pending_paste: list[str] = []
    if not buyer_prompts:
        buyer_kpi = [
            "还没有买家原句。先从销售、询盘、展会或客户自己说的记下来。",
            "没有原句不会编。不保证这次被提到。",
        ]
        cite_assets = ["没有原句，没有可引用资产。不会编英文段。客户自己贴。我们不代改。"]
    else:
        latest_by, previous_by = prompt_batch_rows(db, user.tenant_id)
        last_by = last_sampled_at_by_prompt(db, user.tenant_id)
        buyer_kpi = []
        due = 0
        for prompt in buyer_prompts:
            note = prompt_compare_note_for(prompt.id, latest_by, previous_by)
            source = recorded_from_label(getattr(prompt, "recorded_from", "") or "")
            extra = (getattr(prompt, "source_note", "") or "").strip()
            history = trend_note(prompt_trend_points(db, user.tenant_id, prompt.id))
            watched = watch_state(last_by.get(prompt.id))
            if watched["due"]:
                due += 1
            buyer_kpi.append(
                f"{prompt.prompt_text}（{source}{(' · ' + extra) if extra else ''}）{note}{history}{watched['note']}"
            )
        if due:
            buyer_kpi.append(f"{due} 句到期该复测。常驻监控只抽已记原句，不编问句。")
        buyer_kpi.append("抽查是联网搜索源，不是 ChatGPT 本人。不保证这次被提到。没有 Fact Pack 不出对外草稿。我们不代改。")

    if not buyer_prompts:
        cite_assets = ["没有原句，没有可引用资产。不会编英文段。客户自己贴。我们不代改。"]
    else:
        cite_assets = []
        pack_blocked = False
        for prompt in buyer_prompts:
            pack = cite_pack_for_prompt(db, tenant, prompt)
            stage = cite_stage(prompt)
            url = cite_published_url(prompt)
            extra = f" {url}" if url else ""
            cite_assets.append(f"{prompt.prompt_text}：{cite_stage_label(stage)}{extra}")
            if stage in {"draft", "sent"}:
                paste = cite_paste_for_prompt(pack, prompt)
                if paste == FACT_PACK_BLOCK:
                    pack_blocked = True
                else:
                    pending_paste.append(paste)
        if pack_blocked:
            pending_paste.insert(0, FACT_PACK_BLOCK)
            cite_assets.append(FACT_PACK_BLOCK)
        else:
            cite_assets.append("只写已记事实，缺的标 NEED_INPUT。客户自己贴。我们不代改。不保证这次被提到。")

    trust = trust_map_for_tenant(db, user.tenant_id, tenant)
    if trust["empty"]:
        trust_items = [trust["note"], "不会编来源，不编竞品。不保证这次被提到。"]
    else:
        trust_items = [trust["note"]]
        for row in trust["sources"][:8]:
            trust_items.append(f"{row['host']} · {row['kind_label']} · {row['hits']} 次")
        for row in trust["competitors"][:8]:
            mark = "已记竞品" if row["registered"] else "抽查出现"
            trust_items.append(f"{row['name']} · {mark} · {row['hits']} 次")
        if trust.get("compare_note"):
            trust_items.append(trust["compare_note"])
        for row in (trust.get("prompts") or [])[:4]:
            if row.get("compare"):
                trust_items.append(f"{row['prompt_text']}：{row['compare']}")
        trust_items.append("只记抽查里出现的来源和名字。不是我们编的竞品名单。不保证这次被提到。")

    headline = _headline(
        site_origin=site_origin,
        pages=len(pages),
        critical=len(critical),
        high=len(high),
        geo_core=geo_core,
        geo_sampled=geo.latest_sampled,
        geo_prompts=geo.prompts,
    )

    sections = [
        CustomerBriefSection(key="findability", title="哪些地方让老外搜不到我", items=findability),
        CustomerBriefSection(key="buyer_kpi", title="AI 可见度作战室：这些问句有没有动", items=buyer_kpi),
        CustomerBriefSection(key="cite_assets", title="请客户自己贴的英文段", items=cite_assets),
        CustomerBriefSection(key="trust_map", title="AI 引用了谁、提到了谁", items=trust_items),
        CustomerBriefSection(key="this_week", title="这周带给客户改的三处", items=this_week),
        CustomerBriefSection(key="retest", title="客户改完你再看一次", items=retest),
        CustomerBriefSection(key="inquiries", title="这个月有几个老外来问过", body=f"这个月记到 {inquiry_count} 条。", items=inquiry_items),
    ]

    lines = [
        f"# {title}",
        "",
        headline,
        "",
        f"- 客户网站：{site_origin or '尚未登记'}",
        f"- 说明时间：{generated.strftime('%Y-%m-%d %H:%M')} UTC",
        "",
    ]
    for section in sections:
        lines += [f"## {section.title}", ""]
        if section.body:
            lines += [section.body, ""]
        for item in section.items:
            lines.append(f"- {item}")
        lines.append("")
    paste_text = weekly_paste(tenant.name if tenant else "", this_week)
    if pending_paste:
        paste_text = paste_text + "\n\n" + "\n\n".join(pending_paste)
    lines += [
        "## 发给客户的短稿",
        "",
        paste_text,
        "",
        "## 写法提醒",
        "",
        "- 尚未检查的不按 0 计算，也不编造排名或推荐。",
        "- 提到品牌不等于给出了官网；给出官网不等于已被稳定推荐。",
        "- 做了页或发了帖之后，用同一问再抽查。仍没提到就写仍没提到，不要写成已经推荐。",
        "- 客户说明只写这一次已经看到的事实。",
        "",
    ]

    return CustomerBriefOut(
        title=title,
        headline=headline,
        markdown="\n".join(lines),
        generated_at=generated,
        untested=untested,
        this_week=this_week,
        paste_text=paste_text,
        sections=sections,
    )
