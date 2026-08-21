from sqlalchemy import select

from app.models import SitePage, Tenant
from app.onsite_inventory import DEMO_LEFTOVER_PATHS, purge_demo_leftover_pages
from app.seed import seed


def test_seed_keeps_demo_pages_when_site_not_crawled(db) -> None:
    seed(db)
    tenant = db.scalar(select(Tenant).where(Tenant.name == "演示客户 · 智能门锁出海"))
    assert tenant is not None
    pages = db.query(SitePage).filter(SitePage.tenant_id == tenant.id).all()
    paths = {page.path for page in pages}
    assert paths == {
        "/en-us/smart-lock-installation-renters",
        "/en-us/smart-lock-compatibility",
        "/ja-jp/chintai-smart-lock",
        "/de-de/smart-lock-dsgvo",
        "/en-us/",
    }
    assert all(page.discovery_source == "seed" for page in pages)
    assert purge_demo_leftover_pages(db, tenant.id) == 0


def test_seed_drops_leftovers_once_a_live_page_exists(db) -> None:
    seed(db)
    tenant = db.scalar(select(Tenant).where(Tenant.name == "演示客户 · 智能门锁出海"))
    assert tenant is not None
    db.add(
        SitePage(
            tenant_id=tenant.id,
            path="/",
            locale="en-US",
            title="Home",
            crawl_status="ok",
            http_status=200,
            final_url="https://www.snipers.com.cn/",
            discovery_source="sitemap",
        )
    )
    db.commit()

    seed(db)
    paths = {page.path for page in db.query(SitePage).filter(SitePage.tenant_id == tenant.id).all()}
    assert "/" in paths
    assert not (paths & DEMO_LEFTOVER_PATHS)
