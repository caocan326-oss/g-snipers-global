"""Drop demo leftover pages once a tenant has a real crawl."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import OnsiteIssue, SitePage

DEMO_LEFTOVER_PATHS = frozenset(
    {
        "/en-us/smart-lock-installation-renters",
        "/en-us/smart-lock-compatibility",
        "/ja-jp/chintai-smart-lock",
        "/de-de/smart-lock-dsgvo",
        "/en-us/",
        "/qa-test-page",
    }
)
QA_TITLES = frozenset({"QA Test Page"})


def is_live_page(page: SitePage) -> bool:
    return page.http_status is not None


def is_leftover_page(page: SitePage) -> bool:
    if page.path in DEMO_LEFTOVER_PATHS:
        return True
    if (page.title or "").strip() in QA_TITLES:
        return True
    return (page.discovery_source or "") == "seed"


def purge_demo_leftover_pages(db: Session, tenant_id: str) -> int:
    pages = db.query(SitePage).filter(SitePage.tenant_id == tenant_id).all()
    if not any(is_live_page(page) for page in pages):
        return 0
    dropped = 0
    for page in pages:
        if is_leftover_page(page):
            db.delete(page)
            dropped += 1
    return dropped


def close_untested_index_findings(db: Session, tenant_id: str) -> int:
    """GSC 已接上时，不再把「收录未测」挂成待处理紧急项。"""
    now = datetime.now(timezone.utc)
    closed = 0
    rows = (
        db.query(OnsiteIssue)
        .filter(
            OnsiteIssue.tenant_id == tenant_id,
            OnsiteIssue.category == "index",
            ~OnsiteIssue.status.in_(("verified", "wont_fix")),
        )
        .all()
    )
    for issue in rows:
        title = issue.title or ""
        if "noindex" in title.lower() or "不要收录" in title:
            continue
        if "未测" not in title and "GSC" not in title and "谷歌" not in title:
            continue
        issue.status = "wont_fix"
        issue.closed_at = now
        issue.severity = "low"
        note = "本轮不改：已接 Search Console 网域，但还不能按 URL 对收录。不把未测写成紧急。"
        issue.evidence = ((issue.evidence or "").rstrip() + "\n" + note).strip()
        closed += 1
    return closed
