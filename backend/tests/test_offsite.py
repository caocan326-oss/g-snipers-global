from fastapi.testclient import TestClient

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
