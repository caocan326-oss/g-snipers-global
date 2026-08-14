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
