from fastapi.testclient import TestClient

from tests.conftest import auth_header


def test_reserved_new_market_path_is_not_an_id(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    res = client.get("/api/markets/new", headers=headers)
    assert res.status_code == 404


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

    patched = client.patch(
        f"/api/markets/{market_id}",
        headers=headers,
        json={"status": "watching", "opportunity_score": 55},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "watching"
    assert patched.json()["opportunity_score"] == 55

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


def test_project_targets_partial_update_keeps_keywords_and_competitors(
    client: TestClient, demo_user
) -> None:
    headers = auth_header(client)
    first = client.put(
        "/api/project-targets",
        headers=headers,
        json={
            "markets": [
                {
                    "name": "美国",
                    "country_code": "US",
                    "primary_locale": "en-US",
                    "status": "priority",
                }
            ],
            "keywords": [{"theme": "smart lock for renters", "locale": "en-US"}],
            "competitors": [{"name": "Acme Locks", "website": "https://acmelocks.com"}],
        },
    )
    assert first.status_code == 200
    assert first.json()["keyword_count"] == 1
    assert first.json()["competitor_count"] == 1

    # Submitting an update that only touches markets must not wipe the
    # keywords/competitors that weren't part of this request.
    second = client.put(
        "/api/project-targets",
        headers=headers,
        json={
            "markets": [
                {
                    "name": "美国",
                    "country_code": "US",
                    "primary_locale": "en-US",
                    "status": "watching",
                }
            ],
        },
    )
    assert second.status_code == 200
    assert second.json()["keyword_count"] == 1
    assert second.json()["competitor_count"] == 1


def test_insight_feeds_three_chains(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    market = client.post(
        "/api/markets",
        headers=headers,
        json={"name": "美国", "region": "北美", "country_code": "US", "primary_locale": "en-US"},
    ).json()
    signal = client.post(
        f"/api/markets/{market['id']}/demand-signals",
        headers=headers,
        json={"theme": "apartment smart lock", "locale": "en-US"},
    ).json()

    onsite = client.post(f"/api/demand-signals/{signal['id']}/open-onsite", headers=headers)
    assert onsite.status_code == 201
    assert onsite.json()["chain"] == "onsite"
    page = client.get(f"/api/onsite/pages/{onsite.json()['created_id']}", headers=headers)
    assert page.status_code == 200
    assert page.json()["index_status"] == "untested"
    assert any("apartment smart lock" in i["title"] for i in page.json()["issues"])

    geo = client.post(f"/api/demand-signals/{signal['id']}/open-geo-ticket", headers=headers)
    assert geo.status_code == 201
    tickets = client.get("/api/geo/tickets", headers=headers).json()
    assert any(t["id"] == geo.json()["created_id"] for t in tickets)
    prompts = client.get("/api/geo/prompts", headers=headers).json()
    assert any(len(p["observations"]) == 8 for p in prompts)

    link = client.post(f"/api/demand-signals/{signal['id']}/open-link-followup", headers=headers)
    assert link.status_code == 201
    gaps = client.get("/api/offsite/gaps", headers=headers).json()
    row = next(g for g in gaps if g["id"] == link.json()["created_id"])
    assert row["kind"] == "inbound"
    assert row["verify_status"] == "unverified"
    assert row["domain_metric"] == "untested"
