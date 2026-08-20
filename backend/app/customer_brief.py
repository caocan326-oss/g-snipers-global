"""One customer-facing weekly brief. Counts only; no invented ranks."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session, selectinload

from app.models import GeoTicket, OnsiteIssue, SitePage, Tenant, User
from app.routers.geo.prompts import geo_summary
from app.routers.onsite.common import (
    _active_issue,
    _category_label,
    _issue_sort_key,
    _page_label,
    _severity_label,
    _status_name,
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
    low = [issue for issue in active if issue.severity == "low"]
    priority_issues = sorted(active, key=_issue_sort_key)[:5]

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

    untested: list[str] = []
    if not site_origin:
        untested.append("客户官网尚未登记。")
    if site_origin and not pages:
        untested.append("还没有查看网页，不能写网站结论。")
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

    this_week: list[str] = []
    if not site_origin:
        this_week.append("登记客户官网。")
    elif not pages:
        this_week.append("查看已登记网站的页面。")
    if critical:
        this_week.append(f"先处理 {len(critical)} 个紧急网站问题。")
    elif high:
        this_week.append(f"跟进 {len(high)} 个优先网站问题。")
    if geo.untested:
        this_week.append(f"补齐 {geo.untested} 条尚未检查的 AI 搜索。")
    if tickets:
        this_week.append(f"复查 {len(tickets)} 个 AI 搜索待处理项。")
    if not this_week:
        this_week.append("对照已有记录，整理给客户的说明，并安排下一轮复查。")

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

    onsite_items = [
        f"{_severity_label(issue.severity)} · {_category_label(issue.category)} · {issue.title}（{_page_label(issue.page)}，{_status_name(issue.status)}）"
        for issue in priority_issues
    ]
    if not onsite_items:
        onsite_items = ["这一轮没有未关闭的网站问题，或还没查看网页。"]

    geo_items = [
        f"{ticket.title}（{ticket.prompt.prompt_text if ticket.prompt else '买家问题'}）"
        for ticket in tickets
    ]
    if not geo_items:
        if geo.recorded:
            geo_items = ["已有检查记录，这一轮还没有未关闭的待处理项。"]
        else:
            geo_items = ["还没有可写入说明的 AI 搜索记录。"]

    sections = [
        CustomerBriefSection(key="this_week", title="这一周先做", items=this_week),
        CustomerBriefSection(
            key="onsite",
            title="网站检查",
            body=(
                f"已查看 {len(pages)} 个页面，待处理 {len(active)} 个问题，"
                f"其中紧急 {len(critical)} 个、优先 {len(high)} 个、常规 {len(low)} 个。"
            ),
            items=onsite_items,
        ),
        CustomerBriefSection(
            key="geo",
            title="AI 搜索可见度",
            body=(
                f"买家问题 {geo.prompts} 个，已有记录 {geo.recorded} 条，尚未检查 {geo.untested} 条。"
                f"品牌被提到 {_display_rate(geo.mention_rate)}，给出官网 {_display_rate(geo.cite_rate)}，"
                f"来源核对 {_display_rate(geo.verified_citation_rate)}。"
            ),
            items=geo_items,
        ),
        CustomerBriefSection(key="untested", title="还没查到的", items=untested),
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
