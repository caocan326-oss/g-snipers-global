"""Onsite customer-facing short notes. Propose only; we never edit the live site."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models import IntegrationSetting, OnsiteIssue, SitePage

ONSITE_CUSTOMER_CLOSE = "我们不代改官网。改完告诉我，我再打开该页核对。"
WEEKLY_RECHECK_OPENED = "打开过该页"
WEEKLY_RECHECK_PASS = "打开过该页。这一条现在对得上。不是我们改的。还在这三处。我们不代改。"
WEEKLY_RECHECK_FAIL = "打开过该页。问题还在。还在这三处。我们不代改。"
TEMPLATE_LIMIT_MARK = "受模板限制"
TEMPLATE_LIMIT_REASON = "受模板限制。后台改不了，要等有主题文件权限的人改。不是客户没理。我们不代改。"
WEEKLY_PIN_KEY = "onsite_weekly_pin"
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


def weekly_recheck_kind(result: str) -> str:
    text = (result or "").strip()
    if "这一条现在对得上" in text:
        return "pass"
    if "问题还在" in text:
        return "fail"
    if text.startswith(WEEKLY_RECHECK_OPENED):
        return "viewed"
    return ""


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


def is_template_limited(issue: OnsiteIssue) -> bool:
    return (issue.blocked_reason or "").startswith(TEMPLATE_LIMIT_MARK)


def weekly_pin_state(db: Session, tenant_id: str) -> dict:
    empty = {"issue_ids": [], "sent_ids": [], "last_dropped_id": "", "last_dropped_sent": False}
    row = (
        db.query(IntegrationSetting)
        .filter(IntegrationSetting.tenant_id == tenant_id, IntegrationSetting.key == WEEKLY_PIN_KEY)
        .first()
    )
    if row is None or not (row.value or "").strip():
        return empty
    try:
        raw = json.loads(row.value)
    except json.JSONDecodeError:
        return empty
    issue_ids = [str(item) for item in (raw.get("issue_ids") or []) if str(item).strip()]
    sent_ids = [str(item) for item in (raw.get("sent_ids") or []) if str(item).strip()]
    return {
        "issue_ids": issue_ids[:WEEKLY_ONSITE_LIMIT],
        "sent_ids": sent_ids,
        "last_dropped_id": str(raw.get("last_dropped_id") or "").strip(),
        "last_dropped_sent": bool(raw.get("last_dropped_sent")),
    }


def save_weekly_pin(
    db: Session,
    tenant_id: str,
    *,
    issue_ids: list[str],
    sent_ids: list[str] | None = None,
    last_dropped_id: str | None = None,
    last_dropped_sent: bool | None = None,
) -> dict:
    prev = weekly_pin_state(db, tenant_id)
    clean_ids = [item for item in issue_ids if item][:WEEKLY_ONSITE_LIMIT]
    keep_sent = [item for item in (sent_ids if sent_ids is not None else prev["sent_ids"]) if item in clean_ids]
    dropped = prev.get("last_dropped_id") or "" if last_dropped_id is None else last_dropped_id
    dropped_sent = prev.get("last_dropped_sent") if last_dropped_sent is None else last_dropped_sent
    payload = {
        "issue_ids": clean_ids,
        "sent_ids": keep_sent,
        "last_dropped_id": dropped or "",
        "last_dropped_sent": bool(dropped_sent),
    }
    row = (
        db.query(IntegrationSetting)
        .filter(IntegrationSetting.tenant_id == tenant_id, IntegrationSetting.key == WEEKLY_PIN_KEY)
        .first()
    )
    blob = json.dumps(payload, ensure_ascii=False)
    if row is None:
        db.add(IntegrationSetting(tenant_id=tenant_id, key=WEEKLY_PIN_KEY, value=blob))
    else:
        row.value = blob
    return payload


def dropped_restore_id(db: Session, tenant_id: str) -> str:
    pin = weekly_pin_state(db, tenant_id)
    dropped_id = str(pin.get("last_dropped_id") or "").strip()
    if dropped_id:
        row = db.get(OnsiteIssue, dropped_id)
        if row is not None and row.tenant_id == tenant_id:
            return dropped_id
    fallback = (
        db.query(OnsiteIssue)
        .filter(
            OnsiteIssue.tenant_id == tenant_id,
            OnsiteIssue.status == "verified",
            OnsiteIssue.retest_result.startswith("打开过该页。这一条现在对得上"),
        )
        .order_by(OnsiteIssue.last_checked_at.desc())
        .first()
    )
    return fallback.id if fallback is not None else ""


def clear_weekly_pin(db: Session, tenant_id: str) -> None:
    db.query(IntegrationSetting).filter(
        IntegrationSetting.tenant_id == tenant_id, IntegrationSetting.key == WEEKLY_PIN_KEY
    ).delete(synchronize_session=False)


def weekly_onsite_picks(
    issues: list[OnsiteIssue],
    *,
    pinned_ids: list[str] | None = None,
    limit: int = WEEKLY_ONSITE_LIMIT,
) -> list[OnsiteIssue]:
    """At most three pages. Only critical/high, unless pinned. One issue per page. Pins stay put."""
    active = [
        issue
        for issue in issues
        if (issue.status or "") not in _CLOSED and not is_template_limited(issue)
    ]
    urgent = [issue for issue in active if (issue.severity or "low") in {"critical", "high"}]
    pool = urgent
    by_id = {issue.id: issue for issue in active}

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
    for issue_id in pinned_ids or []:
        issue = by_id.get(issue_id)
        if issue is None:
            continue
        page_id = (issue.page_id or "").strip()
        if not page_id or page_id in seen_pages:
            continue
        seen_pages.add(page_id)
        picked.append(issue)
        if len(picked) >= limit:
            return picked
    for issue in sorted(pool, key=sort_key):
        if issue in picked:
            continue
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
