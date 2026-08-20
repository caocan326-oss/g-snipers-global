from collections import Counter
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import CrawlSession, OnsiteIssue, SitePage, Tenant, User
from app.onsite_analyzer import reconcile_issues
from app.onsite_fetch import OriginError, normalize_origin
from app.risk import needs_confirm
from app.schemas import CrawlSessionOut, OnsiteIssueOut, SitePageOut

from .constants import (
    AI_BATCH_DEFAULT_LIMIT,
    AI_BATCH_MAX_LIMIT,
    CATEGORY_GUIDANCE,
    CATEGORY_LABELS,
    CRAWL_LABELS,
    CSV_ALIASES,
    OPENISH,
    SEVERITY_LABELS,
    SEVERITY_RANK,
)


def _url_depth(path: str) -> int:
    return len([part for part in (path or "/").split("/") if part])


def _page_type(page: SitePage) -> str:
    text = f"{page.path} {page.title} {page.meta_title}".lower()
    if (page.path or "/").strip() in {"", "/"}:
        return "home"
    if any(token in text for token in ("product", "products", "sku", "model")):
        return "product"
    if any(token in text for token in ("solution", "application", "industry")):
        return "solution"
    if any(token in text for token in ("case", "project")):
        return "case"
    if any(token in text for token in ("blog", "article", "news")):
        return "article"
    if any(token in text for token in ("contact", "inquiry", "quote")):
        return "contact"
    return "other"


def _priority_hint(page: SitePage) -> str:
    page_type = _page_type(page)
    if page_type in {"home", "product", "solution"}:
        return "P1"
    if page.is_in_sitemap == "yes" or page_type in {"case", "contact"}:
        return "P2"
    return "P3"


def _ai_batch_limit(limit: int | None) -> int:
    if limit is None:
        return AI_BATCH_DEFAULT_LIMIT
    return max(1, min(limit, AI_BATCH_MAX_LIMIT))


def _issue_needs_ai(issue: OnsiteIssue) -> bool:
    return not (issue.proposed_change or "").strip()


def _issue_priority_key(issue: OnsiteIssue) -> tuple[int, int, str]:
    has_draft = 1 if (issue.proposed_change or "").strip() else 0
    created = (issue.created_at or datetime.now(timezone.utc)).isoformat()
    return (has_draft, SEVERITY_RANK.get(issue.severity or "low", 3), created)


def _ai_issue_candidates(db: Session, user: User) -> list[OnsiteIssue]:
    rows = (
        db.query(OnsiteIssue)
        .filter(OnsiteIssue.tenant_id == user.tenant_id, OnsiteIssue.status.in_(["open", "drafted"]))
        .all()
    )
    rows.sort(key=_issue_priority_key)
    return rows


def _issue_out(row: OnsiteIssue, page: SitePage | None = None) -> OnsiteIssueOut:
    p = page or row.page
    guidance = CATEGORY_GUIDANCE.get(
        row.category,
        {
            "impact": "影响页面可被搜索引擎和 AI 系统稳定理解。",
            "action": "结合诊断证据补充处理方案，人工确认后执行。",
            "retest": "执行后重新抓取页面并比对观察层。",
            "owner": "客户经理 / 执行人",
        },
    )
    review_required = needs_confirm(row.severity or "low", row.risk)
    return OnsiteIssueOut(
        id=row.id,
        page_id=row.page_id,
        page_path=p.path if p else "",
        page_title=p.title if p else "",
        category=row.category,
        title=row.title,
        detail=row.detail,
        proposed_change=row.proposed_change,
        severity=row.severity or "low",
        risk=row.risk,
        priority=row.priority or {"critical": "P0", "high": "P1", "low": "P2"}.get(row.severity or "low", "P2"),
        status=row.status,
        metric_status=row.metric_status,
        ai_status=row.ai_status or "untested",
        ai_diagnosis=row.ai_diagnosis or "",
        ai_review=row.ai_review or "",
        ai_review_verdict=row.ai_review_verdict or "untested",
        evidence=row.evidence or "",
        impact=guidance["impact"],
        acceptance_criteria=row.acceptance_criteria or "按处理方案上线后，重新抓取页面并确认该问题不再出现。",
        recommended_action=row.recommended_action or guidance["action"],
        review_required=review_required,
        retest_method=row.retest_method or guidance["retest"],
        retest_result=row.retest_result or "",
        result_url=row.result_url or "",
        blocked_reason=row.blocked_reason or "",
        owner_hint=row.owner_hint or (guidance["owner"] if review_required else "内容运营 / 客户经理"),
        last_checked_at=row.last_checked_at,
        closed_at=row.closed_at,
    )


def _owned_issue(db: Session, user: User, issue_id: str) -> OnsiteIssue:
    row = db.get(OnsiteIssue, issue_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    return row


def _page_out(db: Session, page: SitePage) -> SitePageOut:
    open_count = (
        db.query(func.count(OnsiteIssue.id))
        .filter(OnsiteIssue.page_id == page.id, OnsiteIssue.status.in_(list(OPENISH)))
        .scalar()
        or 0
    )
    return SitePageOut(
        id=page.id,
        path=page.path,
        locale=page.locale,
        title=page.title,
        market_id=page.market_id,
        seo_page_id=page.seo_page_id,
        meta_title=page.meta_title,
        meta_description=page.meta_description,
        meta_keywords=page.meta_keywords,
        headings=page.headings,
        internal_links=page.internal_links,
        structured_data=page.structured_data,
        canonical=page.canonical or "",
        index_status=page.index_status,
        crawl_status=page.crawl_status,
        fetched_at=page.fetched_at,
        final_url=page.final_url or "",
        http_status=page.http_status,
        content_type=page.content_type or "",
        ttfb_ms=page.ttfb_ms,
        redirect_count=page.redirect_count or 0,
        html_bytes=page.html_bytes or 0,
        body_hash=page.body_hash or "",
        needs_js=bool(page.needs_js),
        fetch_mode=page.fetch_mode or "http",
        render_status=page.render_status or "not_needed",
        render_final_url=page.render_final_url or "",
        render_word_count=page.render_word_count or 0,
        html_lang=page.html_lang or "",
        hreflang=page.hreflang or "",
        viewport=page.viewport or "",
        json_ld_types=page.json_ld_types or "",
        crawl_error=page.crawl_error or "",
        discovery_source=page.discovery_source or "manual",
        is_in_sitemap=page.is_in_sitemap or "untested",
        meta_robots=page.meta_robots or "",
        x_robots_tag=page.x_robots_tag or "",
        word_count=page.word_count or 0,
        image_count=page.image_count or 0,
        images_missing_alt=page.images_missing_alt or 0,
        external_link_count=page.external_link_count or 0,
        page_type=_page_type(page),
        url_depth=_url_depth(page.path),
        priority_hint=_priority_hint(page),
        notes=page.notes,
        open_issue_count=open_count,
        analyzed_at=page.analyzed_at,
    )


def _owned_page(db: Session, user: User, page_id: str) -> SitePage:
    page = db.get(SitePage, page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    return page


def _crawl_session_out(row: CrawlSession) -> CrawlSessionOut:
    return CrawlSessionOut(
        id=row.id,
        origin=row.origin,
        mode=row.mode,
        max_urls=row.max_urls,
        max_depth=row.max_depth,
        status=row.status,
        discovered=row.discovered,
        fetched=row.fetched,
        failed=row.failed,
        created=row.created,
        verified=row.verified,
        robots_blocked=row.robots_blocked,
        needs_js=row.needs_js,
        note=row.note,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


def _status_name(status: str) -> str:
    return {
        "open": "待写改法",
        "drafted": "改法已写，待上线",
        "draft_applied": "已交给执行",
        "confirmed": "已修改，待复查",
        "verified": "复查通过",
        "wont_fix": "本轮不改",
    }.get(status, status)


def _active_issue(issue: OnsiteIssue) -> bool:
    return issue.status not in {"verified", "wont_fix"}


def _severity_label(severity: str) -> str:
    return SEVERITY_LABELS.get(severity, severity or "一般")


def _category_label(category: str) -> str:
    return CATEGORY_LABELS.get(category, category or "其他")


def _page_label(page: SitePage | None) -> str:
    if page is None:
        return "页面未找到"
    label = page.title or page.meta_title or page.path
    return f"{label}（{page.path}）"


def _crawl_label(status: str | None) -> str:
    return CRAWL_LABELS.get(status or "untested", status or "未抓取")


def _sitemap_label(value: str | None) -> str:
    return {"yes": "在 sitemap 中", "no": "不在 sitemap 中", "untested": "未确认"}.get(value or "untested", value or "未确认")


def _issue_impact(issue: OnsiteIssue) -> str:
    return CATEGORY_GUIDANCE.get(issue.category, CATEGORY_GUIDANCE["content"])["impact"]


def _issue_action(issue: OnsiteIssue) -> str:
    if (issue.proposed_change or "").strip():
        return issue.proposed_change or ""
    return CATEGORY_GUIDANCE.get(issue.category, CATEGORY_GUIDANCE["content"])["action"]


def _issue_owner(issue: OnsiteIssue) -> str:
    return CATEGORY_GUIDANCE.get(issue.category, CATEGORY_GUIDANCE["content"])["owner"]


def _issue_retest(issue: OnsiteIssue) -> str:
    return CATEGORY_GUIDANCE.get(issue.category, CATEGORY_GUIDANCE["content"])["retest"]


def _issue_sort_key(issue: OnsiteIssue) -> tuple[int, int, str]:
    status_rank = {"open": 0, "drafted": 1, "confirmed": 2, "draft_applied": 3, "verified": 4, "wont_fix": 5}
    created = (issue.created_at or datetime.now(timezone.utc)).isoformat()
    return (SEVERITY_RANK.get(issue.severity or "low", 3), status_rank.get(issue.status, 9), created)


def _issue_group_rows(issues: list[OnsiteIssue]) -> list[tuple[tuple[str, str, str], int]]:
    counter: Counter[tuple[str, str, str]] = Counter()
    for issue in issues:
        if _active_issue(issue):
            counter[(issue.severity or "low", issue.category or "content", issue.title or "未命名问题")] += 1
    return sorted(counter.items(), key=lambda row: (SEVERITY_RANK.get(row[0][0], 3), -row[1], row[0][2]))


def _csv_value(row: dict[str, str], field: str) -> str:
    aliases = CSV_ALIASES[field]
    for key, value in row.items():
        normalized = key.strip().lower().lstrip("﻿")
        if normalized in aliases:
            return (value or "").strip()
    return ""


def _parse_int(value: str) -> int:
    cleaned = value.replace(",", "").strip()
    if not cleaned:
        return 0
    try:
        return int(float(cleaned))
    except ValueError:
        return 0


def _parse_float(value: str) -> float | None:
    cleaned = value.replace(",", "").replace("%", "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _tenant(db: Session, user: User) -> Tenant:
    tenant = db.get(Tenant, user.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="租户不存在")
    return tenant


def _require_origin(tenant: Tenant) -> str:
    try:
        return normalize_origin(tenant.site_origin or "")
    except OriginError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _page_issues(db: Session, page_id: str) -> list[OnsiteIssue]:
    return db.query(OnsiteIssue).filter(OnsiteIssue.page_id == page_id).all()


def _analyze_one(db: Session, user: User, page: SitePage) -> tuple[int, int, int]:
    created, skipped, verified = reconcile_issues(
        db, tenant_id=user.tenant_id, page=page, issues=_page_issues(db, page.id)
    )
    db.flush()
    return created, skipped, verified
