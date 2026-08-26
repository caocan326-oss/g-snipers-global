"""Onsite customer-facing short notes. Propose only; we never edit the live site."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from app.models import OnsiteIssue, SitePage

ONSITE_CUSTOMER_CLOSE = "我们不代改官网。改完告诉我，我再打开该页核对。"
WEEKLY_ONSITE_LIMIT = 3
_CLOSED = {"verified", "wont_fix"}
_SEV_RANK = {"critical": 0, "high": 1, "low": 2}
_STATUS_RANK = {"open": 0, "drafted": 1, "confirmed": 2, "draft_applied": 3}

_INTERNAL_CODE = re.compile(r"GEO-[A-Z]+-\d+\s*")


def _guidance(category: str) -> dict[str, str]:
    # Lazy import: avoid cycle with routers.onsite.common → onsite_loop.
    from app.routers.onsite.constants import CATEGORY_GUIDANCE

    return CATEGORY_GUIDANCE.get(category, CATEGORY_GUIDANCE["content"])


def _plain_titles() -> dict[str, str]:
    from app.routers.onsite.constants import ISSUE_PLAIN_TITLES

    return ISSUE_PLAIN_TITLES


def plain_issue_title(title: str) -> str:
    mapped = _plain_titles().get(title, title)
    mapped = _INTERNAL_CODE.sub("", mapped).strip() or mapped
    if re.search(r"schema|json-ld", mapped, re.I):
        return "页面缺少给搜索看的说明"
    return mapped


def page_label(page: SitePage | None) -> str:
    if page is None:
        return "还没有对应页"
    label = (page.title or page.meta_title or page.path or "未命名页面").strip()
    path = (page.path or "/").strip() or "/"
    return f"{label}（{path}）"


def page_url(page: SitePage | None, site_origin: str = "") -> str:
    if page is not None and (page.final_url or "").strip():
        return (page.final_url or "").strip()
    origin = (site_origin or "").rstrip("/")
    path = (page.path if page else "/") or "/"
    if not path.startswith("/"):
        path = f"/{path}"
    if origin:
        return f"{origin}{path}"
    return path


def _ask_line(issue: OnsiteIssue) -> str:
    drafted = (issue.proposed_change or "").strip()
    if drafted:
        return drafted
    return (_guidance(issue.category).get("action") or "按页面问题补齐内容，人工确认后再上线。").strip()


def issue_customer_note(
    issue: OnsiteIssue,
    page: SitePage | None = None,
    site_origin: str = "",
) -> str:
    page = page if page is not None else getattr(issue, "page", None)
    label = page_label(page)
    url = page_url(page, site_origin)
    title = plain_issue_title(issue.title or "")
    ask = _ask_line(issue)
    lines = [f"请改这一页：{label}"]
    if url:
        lines.append(url)
    if title:
        lines.append(f"问题：{title}")
    lines.append(f"请做：{ask}")
    retest = (
        (issue.retest_method or "").strip()
        or _guidance(issue.category).get("retest")
        or "改完后重新打开该页核对。"
    )
    lines.append(retest)
    lines.append(ONSITE_CUSTOMER_CLOSE)
    return "\n".join(lines)


def issue_customer_paste(
    issue: OnsiteIssue,
    page: SitePage | None = None,
    site_origin: str = "",
) -> str:
    return issue_customer_note(issue, page, site_origin)


def weekly_onsite_picks(issues: list[OnsiteIssue], *, limit: int = WEEKLY_ONSITE_LIMIT) -> list[OnsiteIssue]:
    """At most three pages. Prefer critical/high. One issue per page. No live-site edits."""
    active = [issue for issue in issues if (issue.status or "") not in _CLOSED]
    urgent = [issue for issue in active if (issue.severity or "low") in {"critical", "high"}]
    pool = urgent or active

    def sort_key(issue: OnsiteIssue) -> tuple[int, int, str, str]:
        created = (issue.created_at or datetime.min.replace(tzinfo=timezone.utc)).isoformat()
        return (
            _SEV_RANK.get(issue.severity or "low", 3),
            _STATUS_RANK.get(issue.status or "", 9),
            created,
            issue.id or "",
        )

    picked: list[OnsiteIssue] = []
    seen_pages: set[str] = set()
    for issue in sorted(pool, key=sort_key):
        page_id = (issue.page_id or "").strip()
        if not page_id or page_id in seen_pages:
            continue
        seen_pages.add(page_id)
        picked.append(issue)
        if len(picked) >= limit:
            break
    return picked


def weekly_onsite_paste(tenant_name: str, notes: list[str]) -> str:
    name = (tenant_name or "客户").strip() or "客户"
    usable = [note.strip() for note in notes if note.strip()]
    if not usable:
        return f"{name} 这周还没有要改的站内三处。\n\n{ONSITE_CUSTOMER_CLOSE}"
    numbered = "\n\n".join(f"{index}. {note}" for index, note in enumerate(usable, 1))
    return f"{name} 这周请改这几处：\n\n{numbered}\n\n{ONSITE_CUSTOMER_CLOSE}"


def looks_like_http_url(url: str) -> bool:
    parsed = urlparse((url or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
