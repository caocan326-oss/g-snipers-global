from sqlalchemy import select

from app.models import GeoAsset, GeoObservation, GeoPrompt, GeoTicket, OnsiteIssue, SitePage, Tenant
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


def test_seed_marks_untested_index_as_wont_fix(db) -> None:
    seed(db)
    tenant = db.scalar(select(Tenant).where(Tenant.name == "演示客户 · 智能门锁出海"))
    page = db.query(SitePage).filter(SitePage.tenant_id == tenant.id).first()
    db.add_all(
        [
            OnsiteIssue(
                tenant_id=tenant.id,
                page_id=page.id,
                category="index",
                title="收录状态未测（需 GSC）",
                severity="critical",
                status="open",
            ),
            OnsiteIssue(
                tenant_id=tenant.id,
                page_id=page.id,
                category="index",
                title="页面声明 noindex",
                severity="critical",
                status="open",
            ),
        ]
    )
    db.commit()

    seed(db)
    rows = {issue.title: issue.status for issue in db.query(OnsiteIssue).filter(OnsiteIssue.tenant_id == tenant.id).all()}
    assert rows["收录状态未测（需 GSC）"] == "wont_fix"
    assert rows["页面声明 noindex"] == "open"


def test_seed_does_not_duplicate_cite_checklist_when_prompts_missing(db) -> None:
    seed(db)
    tenant = db.scalar(select(Tenant).where(Tenant.name == "演示客户 · 智能门锁出海"))
    assert tenant is not None
    db.query(GeoObservation).filter(GeoObservation.tenant_id == tenant.id).delete()
    db.query(GeoTicket).filter(GeoTicket.tenant_id == tenant.id).delete()
    db.query(GeoPrompt).filter(GeoPrompt.tenant_id == tenant.id).delete()
    db.commit()
    seed(db)
    kinds = [row.kind for row in db.query(GeoAsset).filter(GeoAsset.tenant_id == tenant.id).all()]
    assert kinds.count("cite_checklist") == 1
    assert kinds.count("llms_txt") == 1
