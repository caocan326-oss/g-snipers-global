"""One customer-facing weekly brief. Counts only; no invented ranks."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.models import GeoTicket, Inquiry, OnsiteIssue, SeoPerformanceRow, SerpRun, SitePage, Tenant, User
from app.routers.geo.prompts import geo_summary
from app.routers.onsite.common import (
    _active_issue,
    _issue_sort_key,
    _page_short,
    _plain_title,
    _severity_label,
)
from app.schemas import CustomerBriefOut, CustomerBriefSection


def _display_rate(value: str | None) -> str:
    if not value or value == "未测":
        return "尚未检查"
    return value


def _headline(
    *,
    site_origin: str,
    pages: int,
    critical: int,
    high: int,
    geo_untested: int,
    geo_recorded: int,
    mention_rate: str,
    cite_rate: str,
) -> str:
    if not site_origin:
        return "还没登记官网。这一周先记下客户网站，再查看网页和 AI 搜索。"
    if not pages:
        return "官网已登记，但还没查看网页。先把页面看一遍，再写改法。"
    if critical:
        extra = f"另外，AI 搜索还有 {geo_untested} 条尚未检查。" if geo_untested else "AI 搜索已有记录，尚未检查的不要写成结论。"
        return f"这一周先处理 {critical} 个紧急网站问题。{extra}"
    if high:
        geo_bit = f"AI 搜索还有 {geo_untested} 条尚未检查。" if geo_untested else "AI 搜索已有记录。"
        return f"没有紧急问题，还有 {high} 个优先网站问题要跟。{geo_bit}"
    if geo_untested:
        return f"网站紧急问题不多。这一周先补齐 {geo_untested} 条尚未检查的 AI 搜索。"
    if geo_recorded:
        return (
            f"已有 {geo_recorded} 条 AI 搜索记录。品牌被提到 {_display_rate(mention_rate)}，"
            f"给出官网 {_display_rate(cite_rate)}。尚未核对的不要写成已被推荐。"
        )
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
    priority_issues = sorted(active, key=_issue_sort_key)[:3]
    waiting = [issue for issue in active if issue.status in {"confirmed", "draft_applied"}]

    geo = geo_summary(user, db)
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

    untested: list[str] = []
    if not site_origin:
        untested.append("客户官网尚未登记。")
    if site_origin and not pages:
        untested.append("还没有查看网页，不能写网站结论。")
    if not serp_ok:
        untested.append("目标词在谷歌前排还没查过。")
    if not impressions:
        untested.append("谷歌搜索表现还没有可用数据。")
    if geo.untested:
        untested.append(f"AI 搜索还有 {geo.untested} 条尚未检查，不能写成已经被提到或给出了官网。")
    if geo.prompts and not geo.recorded:
        untested.append("买家问题已生成，但还没有检查记录。")
    if not geo.prompts:
        untested.append("还没有买家问题，AI 搜索这一块只能写尚未开始。")
    if _display_rate(geo.verified_citation_rate) == "尚未检查":
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
    if geo.untested:
        findability.append(f"AI 搜索还有 {geo.untested} 条尚未检查，不能写成已经被提到。")
    if tickets:
        findability.append(tickets[0].title)
    if not findability:
        findability.append("这一轮还没有足够记录，说明里只能写尚未检查。")

    this_week: list[str] = []
    if not site_origin:
        this_week.append("登记客户官网。")
    elif not pages:
        this_week.append("查看已登记网站的页面。")
    for issue in priority_issues:
        this_week.append(f"{_severity_label(issue.severity)}：{_plain_title(issue.title)}（{_page_short(issue.page)}）")
    if not this_week:
        this_week.append("对照已有记录，整理给客户的说明，并安排下一轮复查。")
    this_week = this_week[:3]

    retest: list[str] = []
    if waiting:
        retest.append(f"有 {len(waiting)} 处已经改过，需要再打开页面核对还在不在。")
    elif priority_issues:
        retest.append("这几处改完后，再抓一次对应页面核对。系统不会自己改官网。")
    else:
        retest.append("这一轮还没有要复查的改动。")

    inquiry_items = [
        f"这个月记到 {inquiry_count} 条。",
        "软件不会自动抓邮箱。客户来问之后，由客户经理登记。",
    ]

    headline = _headline(
        site_origin=site_origin,
        pages=len(pages),
        critical=len(critical),
        high=len(high),
        geo_untested=geo.untested,
        geo_recorded=geo.recorded,
        mention_rate=geo.mention_rate,
        cite_rate=geo.cite_rate,
    )

    sections = [
        CustomerBriefSection(key="findability", title="哪些地方让老外搜不到我", items=findability),
        CustomerBriefSection(key="this_week", title="这周技术改哪三处", items=this_week),
        CustomerBriefSection(key="retest", title="改完你再看一次", items=retest),
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
    lines += [
        "## 写法提醒",
        "",
        "- 尚未检查的不按 0 计算，也不编造排名或推荐。",
        "- 提到品牌不等于给出了官网；给出官网不等于已被稳定推荐。",
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
        sections=sections,
    )
