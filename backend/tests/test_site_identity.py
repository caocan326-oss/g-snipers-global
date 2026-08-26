from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sqlalchemy import select

from app.models import GeoAsset, GeoPrompt, GeoTicket, Tenant
from app.seed import seed
from app.site_identity import adopt_live_site, is_lock_leftover_text
from tests.conftest import auth_header


def test_lock_leftover_matches_chinese_lock_not_bare_license() -> None:
    assert is_lock_leftover_text("智能锁许可")
    assert is_lock_leftover_text("买家问「智能锁许可」时没提到我们")
    assert is_lock_leftover_text("How do renters install a smart lock?")
    assert not is_lock_leftover_text("export license for fasteners")
    assert not is_lock_leftover_text("许可")


def test_snipers_drops_lock_prompts_and_keeps_own_cite(demo_user, db: Session) -> None:
    tenant = db.get(Tenant, demo_user.tenant_id)
    assert tenant is not None
    tenant.site_origin = "https://www.snipers.com.cn"
    tenant.name = "SNIPERS"
    lock = GeoPrompt(tenant_id=tenant.id, prompt_text="智能锁许可", locale="zh-CN")
    keep = GeoPrompt(tenant_id=tenant.id, prompt_text="best industrial fastener exporter", locale="en-US")
    db.add_all([lock, keep])
    db.flush()
    db.add(GeoTicket(tenant_id=tenant.id, prompt_id=lock.id, title="买家问「智能锁许可」时没提到我们", status="open"))
    asset = db.query(GeoAsset).filter(GeoAsset.tenant_id == tenant.id, GeoAsset.kind == "cite_checklist").first()
    if asset is None:
        asset = GeoAsset(tenant_id=tenant.id, kind="cite_checklist", title="可供引用的材料", body="https://www.snipers.com.cn/")
        db.add(asset)
    else:
        asset.body = "Official page: https://www.snipers.com.cn/"
    db.commit()

    note = adopt_live_site(db, tenant)
    db.commit()
    texts = [row.prompt_text for row in db.query(GeoPrompt).filter(GeoPrompt.tenant_id == tenant.id).all()]
    assert "智能锁许可" not in texts
    assert "best industrial fastener exporter" in texts
    titles = [row.title for row in db.query(GeoTicket).filter(GeoTicket.tenant_id == tenant.id).all()]
    assert not any("智能锁" in title for title in titles)
    db.refresh(asset)
    assert "snipers.com.cn" in (asset.body or "")
    assert "门锁" in note


def test_customer_brief_on_snipers_omits_lock_geo(client: TestClient, demo_user, db: Session) -> None:
    tenant = db.get(Tenant, demo_user.tenant_id)
    assert tenant is not None
    tenant.site_origin = "https://www.snipers.com.cn"
    tenant.name = "SNIPERS"
    prompt = GeoPrompt(tenant_id=tenant.id, prompt_text="智能锁许可", locale="zh-CN")
    db.add(prompt)
    db.flush()
    db.add(GeoTicket(tenant_id=tenant.id, prompt_id=prompt.id, title="买家问「智能锁许可」时没提到我们", status="open"))
    db.commit()

    headers = auth_header(client)
    brief = client.get("/api/dashboard/customer-brief", headers=headers)
    assert brief.status_code == 200, brief.text
    body = brief.json()
    assert "智能锁" not in body["markdown"]
    assert all("智能锁" not in item for item in body["this_week"])


def test_seed_does_not_reinject_lock_onto_named_snipers(db: Session) -> None:
    seed(db)
    tenant = db.scalar(select(Tenant).where(Tenant.name == "演示客户 · 智能门锁出海"))
    assert tenant is not None
    tenant.name = "SNIPERS"
    tenant.site_origin = "https://www.snipers.com.cn"
    db.add(GeoPrompt(tenant_id=tenant.id, prompt_text="智能锁许可", locale="zh-CN"))
    db.commit()
    seed(db)
    texts = [row.prompt_text for row in db.query(GeoPrompt).filter(GeoPrompt.tenant_id == tenant.id).all()]
    assert not any("智能锁" in text or "smart lock" in text.lower() or "スマートロック" in text for text in texts)
    titles = [row.title for row in db.query(GeoTicket).filter(GeoTicket.tenant_id == tenant.id).all()]
    assert not any("智能锁" in title for title in titles)
