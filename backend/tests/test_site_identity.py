from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sqlalchemy import select

from app.models import GeoAsset, GeoPrompt, GeoTicket, Inquiry, Tenant
from app.seed import seed
from app.site_identity import (
    adopt_live_site,
    is_buyer_question,
    is_lock_asset_text,
    is_lock_inquiry_text,
    is_lock_leftover_text,
)
from tests.conftest import auth_header


def test_lock_leftover_matches_chinese_lock_not_bare_license() -> None:
    assert is_lock_leftover_text("智能锁许可")
    assert is_lock_leftover_text("买家问「智能锁许可」时没提到我们")
    assert is_lock_leftover_text("How do renters install a smart lock?")
    assert not is_lock_leftover_text("export license for fasteners")
    assert not is_lock_leftover_text("许可")
    assert is_buyer_question("Which industrial pump supplier is reliable for export?")
    assert is_buyer_question("哪家紧固件出口商能供货？")
    assert not is_buyer_question("industrial pump supplier")
    assert not is_buyer_question("智能锁许可")
    assert is_lock_inquiry_text("alex@example.com / 加州物业经理", "询问多门锁批量安装，来自英文指南预览页（演示）。")
    assert is_lock_inquiry_text("采购", "智能门锁询价")
    assert not is_lock_inquiry_text("buyer@factory.com", "询盘紧固件出口许可")
    assert not is_lock_inquiry_text("采购", "批量安装")


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


def test_snipers_drops_lock_demo_inquiry_keeps_real_one(demo_user, db: Session) -> None:
    tenant = db.get(Tenant, demo_user.tenant_id)
    assert tenant is not None
    tenant.site_origin = "https://www.snipers.com.cn"
    tenant.name = "SNIPERS"
    db.add_all(
        [
            Inquiry(
                tenant_id=tenant.id,
                source="organic_en",
                contact="alex@example.com / 加州物业经理",
                quality="qualified",
                notes="询问多门锁批量安装，来自英文指南预览页（演示）。",
            ),
            Inquiry(
                tenant_id=tenant.id,
                source="email",
                contact="buyer@factory.com",
                quality="unreviewed",
                notes="询盘紧固件出口许可",
            ),
        ]
    )
    db.commit()

    note = adopt_live_site(db, tenant)
    db.commit()
    contacts = [row.contact for row in db.query(Inquiry).filter(Inquiry.tenant_id == tenant.id).all()]
    assert contacts == ["buyer@factory.com"]
    assert "演示询盘" in note


def test_snipers_inquiry_list_purges_lock_demo(client: TestClient, demo_user, db: Session) -> None:
    tenant = db.get(Tenant, demo_user.tenant_id)
    assert tenant is not None
    tenant.site_origin = "https://www.snipers.com.cn"
    tenant.name = "SNIPERS"
    db.add(
        Inquiry(
            tenant_id=tenant.id,
            source="organic_en",
            contact="alex@example.com / 加州物业经理",
            quality="qualified",
            notes="询问多门锁批量安装，来自英文指南预览页（演示）。",
        )
    )
    db.commit()

    listed = client.get("/api/inquiries", headers=auth_header(client))
    assert listed.status_code == 200, listed.text
    assert listed.json() == []
    workbench = client.get("/api/dashboard/workbench?days=28", headers=auth_header(client)).json()
    assert workbench["summary"]["inquiries_month"] == 0
    assert workbench["summary"]["inquiries_month_unlinked"] == 0
    assert all(item["id"] != "inquiry-link" for item in workbench["next_actions"])


def test_snipers_clears_lock_llms_and_keeps_own_cite(demo_user, db: Session) -> None:
    tenant = db.get(Tenant, demo_user.tenant_id)
    assert tenant is not None
    tenant.site_origin = "https://www.snipers.com.cn"
    tenant.name = "SNIPERS"
    llms = db.query(GeoAsset).filter(GeoAsset.tenant_id == tenant.id, GeoAsset.kind == "llms_txt").first()
    if llms is None:
        llms = GeoAsset(tenant_id=tenant.id, kind="llms_txt", title="llms.txt 草稿", status="draft")
        db.add(llms)
    llms.body = "\n".join(
        [
            "# 演示客户 · 智能门锁出海",
            "- [Smart lock installation for renters](/en-US/smart-lock)",
            "- [賃貸でスマートロック](/ja-JP/chintai)",
            "- [Smart lock DSGVO](/de-DE/dsgvo)",
        ]
    )
    cite = db.query(GeoAsset).filter(GeoAsset.tenant_id == tenant.id, GeoAsset.kind == "cite_checklist").first()
    if cite is None:
        cite = GeoAsset(tenant_id=tenant.id, kind="cite_checklist", title="可供引用的材料", status="draft")
        db.add(cite)
    cite.body = "Official page: https://www.snipers.com.cn/"
    db.commit()

    assert is_lock_asset_text(llms.body, keep_snipers_cite=True)
    assert not is_lock_asset_text(cite.body, keep_snipers_cite=True)

    note = adopt_live_site(db, tenant)
    db.commit()
    db.refresh(llms)
    db.refresh(cite)
    assert "智能门锁" not in (llms.body or "")
    assert "smart lock" not in (llms.body or "").lower()
    assert "スマートロック" not in (llms.body or "")
    assert "门锁演示稿已清掉" in (llms.body or "")
    assert "snipers.com.cn" in (cite.body or "")
    assert "引用材料" in note


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
    contacts = [row.contact for row in db.query(Inquiry).filter(Inquiry.tenant_id == tenant.id).all()]
    assert not any("alex@example.com" in contact or "加州物业" in contact for contact in contacts)
