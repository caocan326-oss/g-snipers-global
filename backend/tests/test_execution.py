from fastapi.testclient import TestClient

from tests.conftest import auth_header


def test_execution_board_aggregates_open_issues_and_filters_closed(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    page = client.post(
        "/api/onsite/pages",
        headers=headers,
        json={"path": "/en-us/products", "locale": "en-US", "title": "Products"},
    )
    assert page.status_code == 201, page.text
    issue = client.post(
        f"/api/onsite/pages/{page.json()['id']}/issues",
        headers=headers,
        json={
            "category": "tdk",
            "title": "Title 缺少核心词",
            "priority": "P1",
            "owner_hint": "内容运营",
            "acceptance_criteria": "重新抓取后 Title 包含核心词。",
            "retest_method": "重新抓取页面并检查 title。",
        },
    )
    assert issue.status_code == 201, issue.text
    issue_id = issue.json()["id"]

    gap = client.post(
        "/api/offsite/gaps",
        headers=headers,
        json={
            "title": "行业目录缺少品牌资料",
            "competitor_name": "Competitor",
            "referring_domain": "industry.example",
            "priority": "P2",
        },
    )
    assert gap.status_code == 201, gap.text

    board = client.get("/api/execution/items", headers=headers)
    assert board.status_code == 200, board.text
    modules = {item["source_module"] for item in board.json()["items"]}
    assert {"seo", "offsite"}.issubset(modules)
    seo_item = next(item for item in board.json()["items"] if item["id"] == issue_id)
    assert seo_item["priority"] == "P1"
    assert seo_item["owner_hint"] == "内容运营"

    closed = client.post(
        f"/api/onsite/issues/{issue_id}/wont-fix",
        headers=headers,
        json={"note": "本轮不处理"},
    )
    assert closed.status_code == 200, closed.text
    refreshed = client.get("/api/execution/items", headers=headers).json()
    assert all(item["id"] != issue_id for item in refreshed["items"])
