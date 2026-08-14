from fastapi.testclient import TestClient

from tests.conftest import auth_header


def test_market_crud_and_brief(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    created = client.post(
        "/api/markets",
        headers=headers,
        json={
            "name": "英国",
            "region": "欧洲",
            "country_code": "GB",
            "primary_locale": "en-GB",
            "status": "priority",
            "opportunity_score": 70,
        },
    )
    assert created.status_code == 201
    market_id = created.json()["id"]

    listed = client.get("/api/markets", headers=headers)
    assert listed.status_code == 200
    assert any(m["id"] == market_id for m in listed.json())

    brief = client.put(
        f"/api/markets/{market_id}/brief",
        headers=headers,
        json={
            "summary": "先做英文指南",
            "opportunities": "安装类内容",
            "risks": "认证",
            "recommended_actions": "开 SEO 选题",
        },
    )
    assert brief.status_code == 200
    assert brief.json()["summary"] == "先做英文指南"

    detail = client.get(f"/api/markets/{market_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["brief"]["summary"] == "先做英文指南"


def test_demand_signal_creates_seo_page(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    market = client.post(
        "/api/markets",
        headers=headers,
        json={
            "name": "美国",
            "region": "北美",
            "country_code": "US",
            "primary_locale": "en-US",
        },
    ).json()
    signal = client.post(
        f"/api/markets/{market['id']}/demand-signals",
        headers=headers,
        json={"theme": "smart lock for renters", "locale": "en-US", "intensity": 4},
    )
    assert signal.status_code == 201
    page = client.post(
        f"/api/demand-signals/{signal.json()['id']}/create-seo-page",
        headers=headers,
    )
    assert page.status_code == 201
    assert page.json()["target_keyword"] == "smart lock for renters"
    assert page.json()["status"] == "idea"
    assert page.json()["market_id"] == market["id"]
