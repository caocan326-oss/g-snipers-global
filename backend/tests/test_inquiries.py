from fastapi.testclient import TestClient

from tests.conftest import auth_header


def test_inquiry_create_list_attach(client: TestClient, demo_user) -> None:
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
    page = client.post(
        "/api/seo-pages",
        headers=headers,
        json={
            "title": "Guide",
            "target_keyword": "smart lock",
            "locale": "en-US",
            "market_id": market["id"],
        },
    ).json()
    created = client.post(
        "/api/inquiries",
        headers=headers,
        json={
            "source": "organic_en",
            "contact": "buyer@example.com",
            "quality": "qualified",
            "related_market_id": market["id"],
            "related_seo_page_id": page["id"],
        },
    )
    assert created.status_code == 201
    listed = client.get("/api/inquiries", headers=headers, params={"quality": "qualified"})
    assert listed.status_code == 200
    assert listed.json()[0]["related_seo_page_id"] == page["id"]
