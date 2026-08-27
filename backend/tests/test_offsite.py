from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import GeoPrompt, GeoTicket, OnsiteIssue, SeoPerformanceRow, SerpRun, SitePage

from tests.conftest import auth_header


def test_offsite_gap_and_outreach(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    gap = client.post(
        "/api/offsite/gaps",
        headers=headers,
        json={
            "title": "Reddit 竞品讨论机会",
            "competitor_name": "August Home",
            "referring_domain": "reddit.com",
            "priority": "P1",
            "owner_hint": "站外执行",
            "acceptance_criteria": "记录 result_url 并完成核验",
            "recommended_action": "判断是否可参与讨论或补充第三方资料",
            "retest_method": "复查页面是否可访问、是否提及客户",
            "notes": "公开讨论记下的缺口",
        },
    )
    assert gap.status_code == 201
    assert gap.json()["domain_metric"] == "untested"
    assert gap.json()["status"] == "identified"
    assert gap.json()["verify_status"] == "unverified"
    assert gap.json()["kind"] == "competitor"
    assert gap.json()["title"] == "Reddit 竞品讨论机会"
    assert gap.json()["priority"] == "P1"
    assert gap.json()["owner_hint"] == "站外执行"
    assert gap.json()["acceptance_criteria"] == "记录 result_url 并完成核验"
    gap_id = gap.json()["id"]

    verified = client.patch(
        f"/api/offsite/gaps/{gap_id}",
        headers=headers,
        json={"verify_status": "valid", "notes": "人工点开有效"},
    )
    assert verified.status_code == 200
    assert verified.json()["verify_status"] == "valid"
    assert verified.json()["last_checked_at"] is not None

    inbound = client.post(
        "/api/offsite/gaps",
        headers=headers,
        json={
            "competitor_name": "—",
            "referring_domain": "partner.example",
            "kind": "inbound",
            "link_url": "https://partner.example/lock",
        },
    )
    assert inbound.json()["kind"] == "inbound"
    assert inbound.json()["verify_status"] == "unverified"

    listed = client.get("/api/offsite/gaps", headers=headers)
    assert any(g["id"] == gap_id for g in listed.json())

    item = client.post(
        f"/api/offsite/gaps/{gap_id}/outreach",
        headers=headers,
        json={"contact": "mod@example.com", "channel": "email"},
    )
    assert item.status_code == 201
    assert item.json()["status"] == "todo"

    refreshed = client.get("/api/offsite/gaps", headers=headers).json()
    row = next(g for g in refreshed if g["id"] == gap_id)
    assert row["status"] == "outreach"
    assert row["outreach"][0]["contact"] == "mod@example.com"

    updated = client.patch(f"/api/offsite/outreach/{item.json()['id']}?status=sent_manual", headers=headers)
    assert updated.json()["status"] == "sent_manual"

    checker = client.get("/api/offsite/checker", headers=headers).json()
    assert checker["domain_metric"] == "未测"
    assert "Ahrefs" in checker["note"] or "指数" in checker["note"]
    assert "unverified" in checker["counts"]
    assert checker["counts"]["valid"] >= 1
    assert "share_of_voice" not in checker
    assert "domain_rating" not in checker


def test_workbench_fact_pack_is_first_until_ready(client: TestClient, demo_user, db: Session) -> None:
    from app.models import FactPack, Tenant

    headers = auth_header(client)
    empty = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    assert empty["summary"]["fact_pack_ready"] is False
    assert empty["next_actions"][0]["id"] == "fact-pack"
    assert empty["next_actions"][0]["href"] == "/offsite?tab=content"
    assert "不要编规格" in empty["next_actions"][0]["subtitle"]

    tenant = db.get(Tenant, demo_user.tenant_id)
    assert tenant is not None
    tenant.site_origin = "https://www.snipers.com.cn"
    db.add(
        FactPack(
            tenant_id=demo_user.tenant_id,
            website="https://www.snipers.com.cn",
            approved_boilerplate_en="SNIPERS supplies industrial fasteners for export buyers.",
        )
    )
    db.commit()
    draft = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    assert draft["summary"]["fact_pack_ready"] is False
    assert draft["summary"]["fact_pack_status"] == "draft"
    assert draft["next_actions"][0]["id"] == "fact-pack-approve"
    assert draft["next_actions"][0]["action_label"] == "去核对"
    assert "没有客户确认过的英文不要批" in draft["next_actions"][0]["subtitle"]

    pack = db.query(FactPack).filter(FactPack.tenant_id == demo_user.tenant_id).one()
    pack.status = "approved"
    pack.legal_name = "SNIPERS Fastener Co., Ltd."
    pack.brand_names = "SNIPERS"
    db.commit()
    ready = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    assert ready["summary"]["fact_pack_ready"] is True
    assert ready["summary"]["fact_pack_status"] == "ready"
    assert all(item["id"] not in {"fact-pack", "fact-pack-approve"} for item in ready["next_actions"])


def test_fact_pack_content_asset_approval_and_distribution_gate(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    fact = client.post(
        "/api/offsite/fact-packs",
        headers=headers,
        json={
            "name": "Pump Exporter Facts",
            "legal_name": "Example Pump Co., Ltd.",
            "brand_names": "ExamplePump",
            "website": "https://example.com",
            "product_categories_en": "industrial pumps, centrifugal pumps",
            "certifications": "ISO 9001",
            "banned_claims": "world leader, FDA approved",
            "approved_boilerplate_en": "ExamplePump manufactures industrial pump systems for export buyers.",
        },
    )
    assert fact.status_code == 201, fact.text
    fact_id = fact.json()["id"]

    blocked_generate = client.post(
        "/api/offsite/content-assets/generate",
        headers=headers,
        json={"fact_pack_id": fact_id, "asset_type": "company_blurb"},
    )
    assert blocked_generate.status_code == 400

    approved_fact = client.post(
        f"/api/offsite/fact-packs/{fact_id}/approve",
        headers=headers,
        json={"confirmed": True, "note": "客户确认"},
    )
    assert approved_fact.status_code == 200, approved_fact.text
    assert approved_fact.json()["status"] == "approved"

    draft = client.post(
        "/api/offsite/content-assets/generate",
        headers=headers,
        json={"fact_pack_id": fact_id, "asset_type": "company_blurb", "title": "Directory company blurb"},
    )
    assert draft.status_code == 201, draft.text
    asset_id = draft.json()["id"]
    assert draft.json()["status"] == "draft"
    assert "ExamplePump" in draft.json()["body_md"]

    job_denied = client.post(
        "/api/distribution/jobs",
        headers=headers,
        json={
            "content_asset_id": asset_id,
            "title": "Submit directory profile",
            "target_url": "https://example.com",
            "provider_key": "directory",
        },
    )
    assert job_denied.status_code == 400

    reviewed = client.post(f"/api/offsite/content-assets/{asset_id}/ai-review", headers=headers)
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["asset"]["ai_review_status"] == "pass"

    approved_asset = client.post(
        f"/api/offsite/content-assets/{asset_id}/approve",
        headers=headers,
        json={"confirmed": True, "note": "人工终审通过"},
    )
    assert approved_asset.status_code == 200, approved_asset.text
    assert approved_asset.json()["status"] == "human_approved"

    job = client.post(
        "/api/distribution/jobs",
        headers=headers,
        json={
            "content_asset_id": asset_id,
            "title": "Submit directory profile",
            "target_url": "https://example.com",
            "provider_key": "directory",
        },
    )
    assert job.status_code == 201, job.text
    assert job.json()["content_asset_id"] == asset_id
    assert "ExamplePump" in job.json()["payload_summary"]


def test_content_asset_review_blocks_need_input_and_banned_claim(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    fact = client.post(
        "/api/offsite/fact-packs",
        headers=headers,
        json={
            "legal_name": "Example Co.",
            "brand_names": "ExampleBrand",
            "website": "https://example.com",
            "product_categories_en": "industrial sensors",
            "banned_claims": "world leader",
        },
    ).json()
    approved = client.post(f"/api/offsite/fact-packs/{fact['id']}/approve", headers=headers, json={"confirmed": True})
    assert approved.status_code == 200, approved.text
    asset = client.post(
        "/api/offsite/content-assets",
        headers=headers,
        json={
            "fact_pack_id": fact["id"],
            "asset_type": "company_blurb",
            "title": "Unsafe blurb",
            "body_md": "ExampleBrand is the world leader in industrial sensors. [NEED_INPUT: certification]",
        },
    )
    assert asset.status_code == 201, asset.text
    reviewed = client.post(f"/api/offsite/content-assets/{asset.json()['id']}/ai-review", headers=headers)
    assert reviewed.status_code == 200, reviewed.text
    findings = "\n".join(reviewed.json()["findings"])
    assert "NEED_INPUT" in findings
    assert "world leader" in findings
    denied = client.post(
        f"/api/offsite/content-assets/{asset.json()['id']}/approve",
        headers=headers,
        json={"confirmed": True},
    )
    assert denied.status_code == 400


def test_generate_offsite_opportunities_from_existing_signals(
    client: TestClient,
    db: Session,
    demo_user,
) -> None:
    headers = auth_header(client)
    page = SitePage(
        tenant_id=demo_user.tenant_id,
        path="/products/pumps",
        locale="en",
        title="Pumps",
        final_url="https://example.com/products/pumps",
    )
    db.add(page)
    db.flush()
    db.add(
        OnsiteIssue(
            tenant_id=demo_user.tenant_id,
            page_id=page.id,
            category="content",
            title="产品参数和应用场景不足",
            detail="页面缺少 B2B 买家需要的公开参数和应用场景。",
            priority="P1",
        )
    )
    prompt = GeoPrompt(
        tenant_id=demo_user.tenant_id,
        prompt_text="best industrial pump suppliers for chemical plants",
        locale="en",
    )
    db.add(prompt)
    db.flush()
    db.add(
        GeoTicket(
            tenant_id=demo_user.tenant_id,
            prompt_id=prompt.id,
            title="AI 答案未引用客户品牌",
            diagnosis="not_mentioned",
            priority="P1",
        )
    )
    db.add(
        SeoPerformanceRow(
            tenant_id=demo_user.tenant_id,
            source="gsc",
            query="industrial pump supplier",
            page_url="https://example.com/products/pumps",
            impressions=240,
            clicks=3,
            position=32.4,
            country="US",
        )
    )
    db.add(
        SerpRun(
            tenant_id=demo_user.tenant_id,
            status="ok",
            keyword="chemical pump manufacturer",
            own_best_position=None,
            third_party_count=5,
            country="US",
        )
    )
    db.commit()

    generated = client.post("/api/offsite/gaps/generate-from-signals", headers=headers)
    assert generated.status_code == 200, generated.text
    body = generated.json()
    assert body["created"] == 4
    assert body["from_geo"] == 1
    assert body["from_onsite"] == 1
    assert body["from_seo"] == 2
    issue_types = {item["issue_type"] for item in body["gaps"]}
    assert {"geo_citation_gap", "onsite_content_gap", "seo_keyword_gap", "serp_visibility_gap"} <= issue_types
    assert all(item["acceptance_criteria"] for item in body["gaps"])
    assert all(item["retest_method"] for item in body["gaps"])

    repeated = client.post("/api/offsite/gaps/generate-from-signals", headers=headers)
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["created"] == 0
    assert repeated.json()["skipped"] == 4
