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
    workspace = client.get(f"/api/onsite/pages/{page_id}", headers=headers).json()
    assert workspace["meta_description"] == ""
    assert drafted.json()["proposed_change"] == "加长"

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
    assert confirmed.json()["status"] in {"confirmed", "verified"}
    after_high = client.get(f"/api/onsite/pages/{page_id}", headers=headers).json()
    assert after_high["structured_data"] == ""
    assert confirmed.json()["proposed_change"] == "JSON-LD"


def test_analyze_does_not_apply_and_board_groups_severity(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    page = client.post(
        "/api/onsite/pages",
        headers=headers,
        json={"path": "/en-us/empty", "locale": "en-US", "title": "Empty"},
    ).json()
    page_id = page["id"]
    before = client.get(f"/api/onsite/pages/{page_id}", headers=headers).json()
    assert before["meta_description"] == ""
    assert before["structured_data"] == ""
    assert before["index_status"] == "untested"

    analyzed = client.post(f"/api/onsite/pages/{page_id}/analyze", headers=headers)
    assert analyzed.status_code == 200
    assert analyzed.json()["created"] >= 3
    assert "未改" in analyzed.json()["note"] or analyzed.json()["pages"] == 1

    after_analyze = client.get(f"/api/onsite/pages/{page_id}", headers=headers).json()
    assert after_analyze["meta_description"] == ""
    assert after_analyze["structured_data"] == ""
    assert after_analyze["index_status"] == "untested"
    assert any(i["category"] == "canonical" for i in after_analyze["issues"])
    assert all(i["status"] == "open" for i in after_analyze["issues"])
    assert all(i["proposed_change"] == "" for i in after_analyze["issues"])

    empty_apply = next(i for i in after_analyze["issues"] if i["severity"] == "low")
    denied = client.post(f"/api/onsite/issues/{empty_apply['id']}/apply-draft", headers=headers)
    assert denied.status_code == 400

    drafted = client.patch(
        f"/api/onsite/issues/{empty_apply['id']}/draft",
        headers=headers,
        json={"proposed_change": "工作区描述草稿"},
    )
    assert drafted.json()["status"] == "drafted"
    still = client.get(f"/api/onsite/pages/{page_id}", headers=headers).json()
    assert still["meta_description"] == ""

    applied = client.post(f"/api/onsite/issues/{empty_apply['id']}/apply-draft", headers=headers)
    assert applied.json()["status"] == "draft_applied"
    assert applied.json()["proposed_change"] == "工作区描述草稿"
    assert client.get(f"/api/onsite/pages/{page_id}", headers=headers).json()["meta_description"] == ""

    board = client.get("/api/onsite/board", headers=headers).json()
    assert "critical" in board["groups"]
    assert board["counts"]["critical"] + board["counts"]["high"] + board["counts"]["low"] >= 1
    assert all(i["metric_status"] == "untested" for i in board["groups"]["critical"])

    briefs = client.get("/api/onsite/briefs", headers=headers).json()
    assert isinstance(briefs, list)
    if briefs:
        assert briefs[0]["serp_features"] == "未测"


def test_crawl_or_seed_from_internal_links(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    client.post(
        "/api/onsite/pages",
        headers=headers,
        json={
            "path": "/en-us/home",
            "locale": "en-US",
            "title": "Home",
            "internal_links": "/en-us/new-from-seed\nhttps://example.com/out",
        },
    )
    result = client.post("/api/onsite/crawl-or-seed", headers=headers)
    assert result.status_code == 200
    assert result.json()["seeded"] >= 1
    pages = client.get("/api/onsite/pages", headers=headers).json()
    assert any(p["path"] == "/en-us/new-from-seed" for p in pages)
    seeded = next(p for p in pages if p["path"] == "/en-us/new-from-seed")
    assert seeded["index_status"] == "untested"
