from fastapi.testclient import TestClient

from tests.conftest import auth_header


def test_onsite_page_and_risk_gates(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    page = client.post(
        "/api/onsite/pages",
        headers=headers,
        json={"path": "/en-us/demo", "locale": "en-US", "title": "Demo page"},
    )
    assert page.status_code == 201
    assert page.json()["index_status"] == "untested"
    assert page.json()["crawl_status"] == "untested"
    page_id = page.json()["id"]

    listed = client.get("/api/onsite/pages", headers=headers)
    assert any(p["id"] == page_id for p in listed.json())

    low = client.post(
        f"/api/onsite/pages/{page_id}/issues",
        headers=headers,
        json={"category": "tdk", "title": "描述过短", "proposed_change": "加长"},
    )
    assert low.status_code == 201
    assert low.json()["risk"] == "low"
    assert low.json()["metric_status"] == "untested"

    high = client.post(
        f"/api/onsite/pages/{page_id}/issues",
        headers=headers,
        json={"category": "schema", "title": "补 FAQ", "proposed_change": "JSON-LD"},
    )
    assert high.json()["risk"] == "high"

    denied_auto = client.post(f"/api/onsite/issues/{high.json()['id']}/apply-draft", headers=headers)
    assert denied_auto.status_code == 400

    drafted = client.post(f"/api/onsite/issues/{low.json()['id']}/apply-draft", headers=headers)
    assert drafted.json()["status"] == "draft_applied"

    denied_live = client.post(
        f"/api/onsite/issues/{high.json()['id']}/confirm-apply",
        headers=headers,
        json={"confirmed": False},
    )
    assert denied_live.status_code == 400

    confirmed = client.post(
        f"/api/onsite/issues/{high.json()['id']}/confirm-apply",
        headers=headers,
        json={"confirmed": True},
    )
    assert confirmed.json()["status"] == "confirmed"
