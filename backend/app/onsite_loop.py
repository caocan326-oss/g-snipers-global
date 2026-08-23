"""Onsite customer-facing short notes. Propose only; we never edit the live site."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.models import OnsiteIssue, SitePage

ONSITE_CUSTOMER_CLOSE = "我们不代改官网。改完告诉我，我再打开该页核对。"

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
    return "\n".join(lines)


def issue_customer_paste(
    issue: OnsiteIssue,
    page: SitePage | None = None,
    site_origin: str = "",
) -> str:
    note = issue_customer_note(issue, page, site_origin)
    return "\n\n".join(part for part in (note, ONSITE_CUSTOMER_CLOSE) if part)


def looks_like_http_url(url: str) -> bool:
    parsed = urlparse((url or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
