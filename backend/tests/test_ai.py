from fastapi.testclient import TestClient

from tests.conftest import auth_header


def test_app_boots_and_ai_unconfigured(client: TestClient, demo_user) -> None:
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["llm"] == "未配置"

    headers = auth_header(client)
    status = client.get("/api/ai/status", headers=headers)
    assert status.status_code == 200
    body = status.json()
    assert body["configured"] is False
    assert body["status"] == "未配置"
    assert body["env_var"] == "LLM_API_KEY"


def test_onsite_ai_does_not_fake_when_unconfigured(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    page = client.post(
        "/api/onsite/pages",
        headers=headers,
        json={"path": "/en-us/ai", "locale": "en-US", "title": "AI page"},
    ).json()
    analyzed = client.post(f"/api/onsite/pages/{page['id']}/analyze", headers=headers)
    assert analyzed.status_code == 200
    assert analyzed.json()["ai_status"] == "未配置"
    detail = client.get(f"/api/onsite/pages/{page['id']}", headers=headers).json()
    assert all(i["proposed_change"] == "" for i in detail["issues"])
    assert all(i["ai_status"] == "未配置" for i in detail["issues"])
    assert all("未配置" in (i["evidence"] or "") for i in detail["issues"])
    assert all(i["ai_diagnosis"] == "" for i in detail["issues"])

    issue_id = detail["issues"][0]["id"]
    before_desc = detail["meta_description"]
    assist = client.post(
        f"/api/onsite/issues/{issue_id}/ai",
        headers=headers,
        json={"step": "all"},
    )
    assert assist.status_code == 200
    assert assist.json()["status"] == "未配置"
    assert assist.json()["applied_draft"] is False
    assert assist.json()["draft"] == ""
    after = client.get(f"/api/onsite/pages/{page['id']}", headers=headers).json()
    assert after["meta_description"] == before_desc


def test_onsite_ai_analyze_does_not_write_drafts(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    page = client.post(
        "/api/onsite/pages",
        headers=headers,
        json={"path": "/en-us/recheck", "locale": "en-US", "title": "Recheck"},
    ).json()
    client.post(f"/api/onsite/pages/{page['id']}/analyze", headers=headers)
    before = client.get(f"/api/onsite/pages/{page['id']}", headers=headers).json()
    assert before["issues"]
    res = client.post("/api/onsite/ai", headers=headers, json={"step": "analyze", "limit": 5})
    assert res.status_code == 200, res.text
    assert "只重新检查" in res.json()["detail"]
    after = client.get(f"/api/onsite/pages/{page['id']}", headers=headers).json()
    assert all(i["proposed_change"] == "" for i in after["issues"])


def test_geo_ai_untested_or_unconfigured_not_invented(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    prompt = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={"prompt_text": "best lock", "locale": "en-US"},
    ).json()
    res = client.post(f"/api/geo/prompts/{prompt['id']}/ai", headers=headers, json={"step": "analyze"})
    assert res.status_code == 200
    assert res.json()["status"] in {"未配置", "未测"}
    assert res.json()["diagnosis"] in {"", "untested"}
    refreshed = client.get("/api/geo/prompts", headers=headers).json()
    row = next(p for p in refreshed if p["id"] == prompt["id"])
    assert row["diagnosis"] == "untested"
    assert row["cite_rate"] == "未测"


def test_offsite_ai_unconfigured_no_ahrefs(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    gap = client.post(
        "/api/offsite/gaps",
        headers=headers,
        json={"competitor_name": "—", "referring_domain": "example.com", "kind": "inbound"},
    ).json()
    res = client.post(f"/api/offsite/gaps/{gap['id']}/ai", headers=headers, json={"step": "evidence"})
    assert res.status_code == 200
    assert res.json()["status"] == "未配置"
    assert "Ahrefs" in res.json()["evidence"] or "未配置" in res.json()["detail"]
