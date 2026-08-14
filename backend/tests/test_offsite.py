from fastapi.testclient import TestClient

from tests.conftest import auth_header


def test_offsite_gap_and_outreach(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    gap = client.post(
        "/api/offsite/gaps",
        headers=headers,
        json={
            "competitor_name": "August Home",
            "referring_domain": "reddit.com",
            "notes": "公开讨论记下的缺口",
        },
    )
    assert gap.status_code == 201
    assert gap.json()["domain_metric"] == "untested"
    assert gap.json()["status"] == "identified"
    gap_id = gap.json()["id"]

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
