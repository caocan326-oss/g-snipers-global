from fastapi.testclient import TestClient

from tests.conftest import auth_header


def test_work_order_create_claim_status(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    created = client.post(
        "/api/work-orders",
        headers=headers,
        json={
            "title": "写日语大纲",
            "type": "seo_outline",
            "acceptance_criteria": "覆盖管理组合",
        },
    )
    assert created.status_code == 201
    order_id = created.json()["id"]
    assert created.json()["status"] == "open"

    listed = client.get("/api/work-orders", headers=headers, params={"status": "open"})
    assert any(o["id"] == order_id for o in listed.json())

    claimed = client.post(f"/api/work-orders/{order_id}/claim", headers=headers)
    assert claimed.status_code == 200
    assert claimed.json()["status"] == "claimed"
    assert claimed.json()["assignee_id"] == demo_user.id

    progressed = client.post(
        f"/api/work-orders/{order_id}/status",
        headers=headers,
        json={"status": "in_progress"},
    )
    assert progressed.json()["status"] == "in_progress"

    done = client.post(f"/api/work-orders/{order_id}/status", headers=headers, json={"status": "done"})
    assert done.json()["status"] == "done"


def test_reject_ads_typed_work_order(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    res = client.post(
        "/api/work-orders",
        headers=headers,
        json={"title": "改预算", "type": "ads_setup"},
    )
    assert res.status_code == 400
