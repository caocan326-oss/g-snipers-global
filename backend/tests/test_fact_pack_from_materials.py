from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.fact_pack_from_materials import extract_fact_fields
from app.models import Tenant
from tests.conftest import auth_header


def test_extract_uses_only_pasted_facts() -> None:
    extracted = extract_fact_fields(
        "\n".join(
            [
                "SNIPERS Fastener Co., Ltd. supplies industrial fasteners for export buyers.",
                "Official website https://www.snipers.com.cn",
                "Contact sales@snipers.com.cn",
                "ISO 9001. 闽ICP备123456号.",
                "Public size: M8 grade 8.8 bolts.",
            ]
        ),
        site_origin="https://www.other.example",
    )
    assert extracted["legal_name"].startswith("SNIPERS Fastener")
    assert "SNIPERS" in extracted["brand_names"]
    assert extracted["website"] == "https://www.snipers.com.cn"
    assert "fastener" in extracted["product_categories_en"]
    assert "ISO 9001" in extracted["certifications"]
    assert "ICP" not in extracted["certifications"]
    assert "TUV" not in extracted["certifications"]
    assert "sales@snipers.com.cn" in extracted["contact_public"]
    assert "supplies industrial fasteners" in extracted["approved_boilerplate_en"]
    assert "Xiamen" not in extracted["approved_boilerplate_en"]
    assert "M8" in extracted["key_specs"]
    assert any("备案" in note for note in extracted["notes"])
    assert "备案/闽ICP（不是认证）" in extracted["omitted"]


def test_extract_chinese_only_does_not_invent_english() -> None:
    extracted = extract_fact_fields("我们是紧固件出口工厂，总部在厦门成都，有认证。请联系我们。")
    assert extracted["approved_boilerplate_en"] == ""
    assert extracted["certifications"] == ""
    assert extracted["key_specs"] == ""
    assert any("中文" in note for note in extracted["notes"])


def test_extract_rejects_lock_demo_copy() -> None:
    try:
        extract_fact_fields("How do renters install a smart lock? 智能门锁批量安装。")
    except ValueError as exc:
        assert "门锁" in str(exc)
    else:
        raise AssertionError("lock leftover should be rejected")
    try:
        extract_fact_fields("智能门锁适合租客安装")
    except ValueError as exc:
        assert "门锁" in str(exc)
        assert "太短" not in str(exc)
    else:
        raise AssertionError("short lock leftover should say 门锁, not 太短")


def test_from_materials_saves_draft_not_approved(client: TestClient, demo_user, db: Session) -> None:
    tenant = db.get(Tenant, demo_user.tenant_id)
    assert tenant is not None
    tenant.site_origin = "https://www.snipers.com.cn"
    tenant.name = "SNIPERS"
    db.commit()
    headers = auth_header(client)
    created = client.post(
        "/api/offsite/fact-packs/from-materials",
        headers=headers,
        json={
            "source_text": (
                "SNIPERS Fastener Co., Ltd. supplies industrial fasteners for export buyers. "
                "Website https://www.snipers.com.cn"
            )
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["fact_pack"]["status"] == "draft"
    assert "supplies industrial fasteners" in body["fact_pack"]["approved_boilerplate_en"]
    assert body["fact_pack"]["website"] == "https://www.snipers.com.cn"
    blocked = client.post(
        "/api/offsite/content-assets/generate",
        headers=headers,
        json={"fact_pack_id": body["fact_pack"]["id"], "asset_type": "company_blurb"},
    )
    assert blocked.status_code == 400
    assert "未批准" in blocked.json()["detail"]
    workbench = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    assert workbench["summary"]["fact_pack_ready"] is False
    assert workbench["summary"]["fact_pack_status"] == "draft"
    assert workbench["next_actions"][0]["id"] == "fact-pack-approve"
    prompt = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={
            "prompt_text": "Which factory can export industrial fasteners to the US?",
            "locale": "en-US",
            "recorded_from": "sales",
        },
    )
    assert prompt.status_code == 201, prompt.text
    assert "不能出对外草稿" in prompt.json()["page_draft"]


def test_from_materials_rejects_short_or_lock(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    short = client.post(
        "/api/offsite/fact-packs/from-materials",
        headers=headers,
        json={"source_text": "太短"},
    )
    assert short.status_code == 400
    lock = client.post(
        "/api/offsite/fact-packs/from-materials",
        headers=headers,
        json={"source_text": "智能门锁适合租客安装"},
    )
    assert lock.status_code == 400
    assert "门锁" in lock.json()["detail"]
    assert "太短" not in lock.json()["detail"]
