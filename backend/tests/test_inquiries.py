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
    assert listed.json()[0]["related_prompt_id"] is None
    assert listed.json()[0]["related_prompt_text"] == ""


def test_inquiry_attaches_recorded_prompt_only(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    prompt = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={"prompt_text": "什么获客软件比较好", "locale": "zh-CN", "recorded_from": "inquiry"},
    )
    assert prompt.status_code == 201, prompt.text
    created = client.post(
        "/api/inquiries",
        headers=headers,
        json={
            "source": "email",
            "contact": "buyer@example.com",
            "quality": "unreviewed",
            "related_prompt_id": prompt.json()["id"],
            "notes": "展会后邮件",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["related_prompt_id"] == prompt.json()["id"]
    assert created.json()["related_prompt_text"] == "什么获客软件比较好"

    denied = client.post(
        "/api/inquiries",
        headers=headers,
        json={
            "source": "email",
            "contact": "other@example.com",
            "related_prompt_id": "not-a-real-prompt",
        },
    )
    assert denied.status_code == 400
    assert "已记" in denied.json()["detail"]

    later = client.post(
        "/api/inquiries",
        headers=headers,
        json={"source": "email", "contact": "later@example.com"},
    ).json()
    attached = client.patch(
        f"/api/inquiries/{later['id']}",
        headers=headers,
        json={"related_prompt_id": prompt.json()["id"]},
    )
    assert attached.status_code == 200, attached.text
    assert attached.json()["related_prompt_text"] == "什么获客软件比较好"

    brief = client.get("/api/dashboard/customer-brief", headers=headers).json()
    inquiries = next(section for section in brief["sections"] if section["key"] == "inquiries")
    assert any("什么获客软件比较好" in item for item in inquiries["items"])
    assert any("不是证明" in item for item in inquiries["items"])
    assert "什么获客软件比较好" in brief["english_markdown"]
    assert "inquiry logged" in brief["english_markdown"]
    assert "not proof of an AI mention" in brief["english_markdown"]
