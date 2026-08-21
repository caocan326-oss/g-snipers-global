"""Drop demo leftover pages once a tenant has a real crawl."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import SitePage

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
