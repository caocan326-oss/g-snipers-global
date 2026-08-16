from fastapi.testclient import TestClient

from tests.conftest import auth_header


def test_providers_unconfigured_and_send_gates(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
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

    final_gap = client.get("/api/offsite/gaps", headers=headers).json()
    row = next(g for g in final_gap if g["id"] == gap_id)
    assert row["status"] == "won"
    assert row["verify_status"] == "valid"
    assert row["result_url"] == "https://www.thomasnet.com/profile/example"
    assert "页面已上线" in row["evidence"]
