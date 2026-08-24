from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import DistributionJob
from tests.conftest import auth_header


def test_providers_unconfigured_and_send_gates(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    anon = client.get("/api/distribution/providers")
    assert anon.status_code == 401
    providers = client.get("/api/distribution/providers", headers=headers)
    assert providers.status_code == 200
    assert len(providers.json()) == 3
    assert all(p["configured"] is False for p in providers.json())
    assert all(p["status"] == "未配置" for p in providers.json())

    job = client.post(
        "/api/distribution/jobs",
        headers=headers,
        json={
            "title": "提交指南",
            "target_url": "/en-us/demo",
            "provider_key": "directory",
            "payload_summary": "草稿",
        },
    )
    assert job.status_code == 201
    assert job.json()["last_result"] == "未发送"
    job_id = job.json()["id"]

    listed = client.get("/api/distribution/jobs", headers=headers)
    assert any(j["id"] == job_id for j in listed.json())

    no_confirm = client.post(
        f"/api/distribution/jobs/{job_id}/send",
        headers=headers,
        json={"confirmed": False},
    )
    assert no_confirm.status_code == 400

    blocked = client.post(
        f"/api/distribution/jobs/{job_id}/send",
        headers=headers,
        json={"confirmed": True},
    )
    assert blocked.status_code == 200
    body = blocked.json()
    assert body["sent"] is False
    assert body["provider_status"] == "未配置"
    assert body["job"]["status"] == "blocked_unconfigured"
    assert body["job"]["last_result"] == "未配置"


def test_unknown_provider_rejected(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    res = client.post(
        "/api/distribution/jobs",
        headers=headers,
        json={"title": "x", "target_url": "/", "provider_key": "ahrefs"},
    )
    assert res.status_code == 400


def test_distribution_task_writes_back_to_offsite_issue(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    gap = client.post(
        "/api/offsite/gaps",
        headers=headers,
        json={
            "title": "ThomasNet 供应商档案缺席",
            "competitor_name": "Competitor",
            "referring_domain": "thomasnet.com",
            "priority": "P1",
        },
    )
    assert gap.status_code == 201
    gap_id = gap.json()["id"]

    job = client.post(
        "/api/distribution/jobs",
        headers=headers,
        json={
            "gap_id": gap_id,
            "title": "提交 ThomasNet 供应商资料",
            "target_url": "https://example.com/en/products",
            "provider_key": "directory",
            "task_type": "profile_create",
            "payload_summary": "公司资料和产品页",
            "owner_hint": "站外执行",
        },
    )
    assert job.status_code == 201
    body = job.json()
    assert body["gap_id"] == gap_id
    assert body["task_type"] == "profile_create"

    saved = client.patch(
        f"/api/distribution/jobs/{body['id']}",
        headers=headers,
        json={"status": "ready", "owner_hint": "站外执行"},
    )
    assert saved.status_code == 200
    assert saved.json()["status"] == "ready"

    refreshed_gap = client.get("/api/offsite/gaps", headers=headers).json()
    row = next(g for g in refreshed_gap if g["id"] == gap_id)
    assert row["status"] == "in_progress"
    assert row["owner_hint"] == "站外执行"

    submitted = client.post(
        f"/api/distribution/jobs/{body['id']}/submit-result",
        headers=headers,
        json={
            "result_url": "https://www.thomasnet.com/profile/example",
            "verify_status": "live",
            "evidence": "人工提交后页面已上线",
        },
    )
    assert submitted.status_code == 200
    assert submitted.json()["result_url"] == "https://www.thomasnet.com/profile/example"
    assert submitted.json()["verify_status"] == "live"
    assert submitted.json()["last_result"] == "已回填结果链接"
    assert "已提交结果" not in (submitted.json()["last_result"] or "")
    assert "登记≠我们代发" in (submitted.json()["last_detail"] or "")

    final_gap = client.get("/api/offsite/gaps", headers=headers).json()
    row = next(g for g in final_gap if g["id"] == gap_id)
    assert row["status"] == "won"
    assert row["verify_status"] == "valid"
    assert row["result_url"] == "https://www.thomasnet.com/profile/example"
    assert "页面已上线" in row["evidence"]


def test_platform_account_connector_and_manual_login_block(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    platform = client.post(
        "/api/offsite/platforms",
        headers=headers,
        json={
            "platform_key": "thomasnet",
            "name": "ThomasNet",
            "domain": "thomasnet.com",
            "submission_mode": "manual_login",
        },
    )
    assert platform.status_code == 201, platform.text
    platform_id = platform.json()["id"]

    connector = client.post(
        "/api/offsite/connectors",
        headers=headers,
        json={
            "platform_id": platform_id,
            "provider_key": "manual_browser",
            "auth_mode": "manual",
            "capabilities": "draft_only,check_placement",
            "status": "manual_only",
        },
    )
    assert connector.status_code == 201

    blocked = client.post(
        "/api/distribution/jobs",
        headers=headers,
        json={
            "platform_id": platform_id,
            "title": "提交 ThomasNet",
            "target_url": "https://example.com",
            "provider_key": "directory",
        },
    )
    assert blocked.status_code == 201
    assert blocked.json()["status"] == "blocked"
    assert blocked.json()["last_result"] == "缺账号"
    assert "needs_account" in blocked.json()["blocked_reason"]

    account = client.post(
        "/api/offsite/accounts",
        headers=headers,
        json={
            "platform_id": platform_id,
            "label": "ThomasNet 主账号",
            "auth_method": "password_vault",
            "vault_ref": "vault://thomasnet/main",
            "owner_hint": "站外执行",
        },
    )
    assert account.status_code == 201, account.text
    account_id = account.json()["id"]

    ready = client.post(
        "/api/distribution/jobs",
        headers=headers,
        json={
            "platform_id": platform_id,
            "account_id": account_id,
            "title": "提交 ThomasNet with account",
            "target_url": "https://example.com",
            "provider_key": "directory",
        },
    )
    assert ready.status_code == 201
    assert ready.json()["status"] == "draft"

    platforms = client.get("/api/offsite/platforms", headers=headers).json()
    assert platforms[0]["accounts_count"] == 1
    assert platforms[0]["connectors_count"] == 1


def test_b2b_platform_seed_and_job_guide(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    seeded = client.post("/api/offsite/platforms/seed-b2b", headers=headers)
    assert seeded.status_code == 200, seeded.text
    assert seeded.json()["created"] >= 6
    assert any(row["platform_key"] == "thomasnet" for row in seeded.json()["platforms"])

    again = client.post("/api/offsite/platforms/seed-b2b", headers=headers)
    assert again.status_code == 200
    assert again.json()["created"] == 0
    assert again.json()["skipped"] >= seeded.json()["created"]

    platform = next(row for row in seeded.json()["platforms"] if row["platform_key"] == "engineering_media")
    job = client.post(
        "/api/distribution/jobs",
        headers=headers,
        json={
            "platform_id": platform["id"],
            "title": "媒体榜单 Pitch",
            "target_url": "https://example.com/en/products",
            "provider_key": "directory",
            "task_type": "listicle_pitch",
        },
    )
    assert job.status_code == 201, job.text
    guide = client.get(f"/api/distribution/jobs/{job.json()['id']}/guide", headers=headers)
    assert guide.status_code == 200, guide.text
    assert guide.json()["submission_mode"] == "email_outreach"
    assert any("pitch" in item.lower() for item in guide.json()["materials"])
    assert any("人工" in item for item in guide.json()["risk_notes"])


def test_placement_check_writes_back_to_offsite_issue(client: TestClient, demo_user, monkeypatch) -> None:
    headers = auth_header(client)
    gap = client.post(
        "/api/offsite/gaps",
        headers=headers,
        json={
            "title": "行业目录上线核验",
            "competitor_name": "Competitor",
            "referring_domain": "directory.example",
            "priority": "P1",
        },
    )
    assert gap.status_code == 201, gap.text
    job = client.post(
        "/api/distribution/jobs",
        headers=headers,
        json={
            "gap_id": gap.json()["id"],
            "title": "核验目录页",
            "target_url": "https://example.com/en/products",
            "provider_key": "directory",
            "task_type": "profile_update",
            "result_url": "https://directory.example/vendor",
        },
    )
    assert job.status_code == 201, job.text

    class FakeResponse:
        status_code = 200
        text = '<html><body>Example supplier <a href="https://example.com/en/products" rel="nofollow">official site</a></body></html>'

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url: str):
            assert url == "https://directory.example/vendor"
            return FakeResponse()

    from app.routers import distribution

    monkeypatch.setattr(distribution.httpx, "Client", FakeClient)
    checked = client.post(f"/api/distribution/jobs/{job.json()['id']}/check-placement", headers=headers)
    assert checked.status_code == 200, checked.text
    assert checked.json()["is_live"] is True
    assert checked.json()["target_link_found"] is True
    assert checked.json()["link_attr"] == "nofollow"

    jobs = client.get("/api/distribution/jobs", headers=headers).json()
    row = next(item for item in jobs if item["id"] == job.json()["id"])
    assert row["status"] == "done"
    assert row["verify_status"] == "live"

    gaps = client.get("/api/offsite/gaps", headers=headers).json()
    refreshed = next(item for item in gaps if item["id"] == gap.json()["id"])
    assert refreshed["status"] == "won"
    assert refreshed["verify_status"] == "valid"
    assert "结果页面核验" in refreshed["evidence"]


def test_official_apis_are_customer_owned_not_auto_sent(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    catalog = client.get("/api/offsite/official-apis", headers=headers)
    assert catalog.status_code == 200
    keys = {row["platform_key"] for row in catalog.json()}
    assert {"linkedin_company", "x_twitter", "facebook_page", "youtube_channel"} <= keys

    seeded = client.post("/api/offsite/platforms/seed-b2b", headers=headers)
    assert seeded.status_code == 200
    linkedin = next(row for row in seeded.json()["platforms"] if row["platform_key"] == "linkedin_company")
    assert linkedin["has_official_api"] is True
    assert linkedin["compose_url"].startswith("https://")
    assert linkedin["api_endpoint"].startswith("https://")

    wired = client.post("/api/offsite/platforms/seed-official-apis", headers=headers)
    assert wired.status_code == 200, wired.text
    assert wired.json()["created"] >= 1
    again = client.post("/api/offsite/platforms/seed-official-apis", headers=headers)
    assert again.status_code == 200
    assert again.json()["created"] == 0

    job = client.post(
        "/api/distribution/jobs",
        headers=headers,
        json={
            "platform_id": linkedin["id"],
            "title": "LinkedIn company update",
            "target_url": "https://www.snipers.com.cn/",
            "provider_key": "directory",
            "task_type": "social_post_plan",
            "payload_summary": "Smart lock for renters. https://www.snipers.com.cn/",
        },
    )
    assert job.status_code == 201, job.text
    payload = client.get(f"/api/distribution/jobs/{job.json()['id']}/official-payload", headers=headers)
    assert payload.status_code == 200, payload.text
    body = payload.json()
    assert body["sent"] is False
    assert body["compose_url"].startswith("https://")
    assert "api.linkedin.com" in body["api_endpoint"]
    assert body["customer_body"]["link"] == "https://www.snipers.com.cn/"
    assert "代登" not in body["note"] or "不代登" in body["note"]


def test_list_jobs_shows_fillback_note_on_old_451_detail(client: TestClient, demo_user, db: Session) -> None:
    headers = auth_header(client)
    created = client.post(
        "/api/distribution/jobs",
        headers=headers,
        json={
            "title": "在 LinkedIn Company Page 发一篇",
            "target_url": "https://www.ugreen.com/products/usa-65585",
            "provider_key": "directory",
            "task_type": "social_post_plan",
        },
    )
    assert created.status_code == 201
    job_id = created.json()["id"]

    row = db.get(DistributionJob, job_id)
    assert row is not None
    row.status = "submitted"
    row.result_url = "https://www.linkedin.com/feed/update/test-ugreen-100w"
    row.verify_status = "failed"
    row.last_detail = "URL 返回 HTTP 451，暂未通过存活核验。"
    db.commit()

    listed = client.get("/api/distribution/jobs", headers=headers)
    assert listed.status_code == 200
    out = next(item for item in listed.json() if item["id"] == job_id)
    assert out["last_detail"] == "URL 返回 HTTP 451，暂未通过存活核验。登记≠我们代发。"
