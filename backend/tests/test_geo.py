from fastapi.testclient import TestClient

from tests.conftest import auth_header


def test_geo_prompt_slots_are_untested_not_zero(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    created = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={"prompt_text": "best smart lock for renters", "locale": "en-US"},
    )
    assert created.status_code == 201
    observations = created.json()["observations"]
    assert len(observations) == 4
    assert all(o["status"] == "untested" for o in observations)
    assert "citation_rate" not in created.json()
    assert "share_of_voice" not in created.json()

    summary = client.get("/api/geo/summary", headers=headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["prompts"] == 1
    assert body["untested"] == 4
    assert body["recorded"] == 0
    assert "citation_rate" not in body
    assert "percent" not in body


def test_record_observation_and_llms_asset_confirm(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    prompt = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={"prompt_text": "smart lock DSGVO", "locale": "de-DE"},
    ).json()
    obs_id = prompt["observations"][0]["id"]

    recorded = client.patch(
        f"/api/geo/observations/{obs_id}",
        headers=headers,
        json={"status": "mentioned", "notes": "客户经理手工抽查"},
    )
    assert recorded.status_code == 200
    assert recorded.json()["status"] == "mentioned"
    assert recorded.json()["observed_at"]

    summary = client.get("/api/geo/summary", headers=headers).json()
    assert summary["untested"] == 3
    assert summary["recorded"] == 1

    generated = client.post("/api/geo/assets/llms.txt/generate", headers=headers)
    assert generated.status_code == 200
    assert generated.json()["status"] == "draft"
    assert "不是已发布" in generated.json()["body"] or "llms.txt" in generated.json()["title"]

    denied = client.post(
        f"/api/geo/assets/{generated.json()['id']}/mark-ready",
        headers=headers,
        json={"confirmed": False},
    )
    assert denied.status_code == 400

    ready = client.post(
        f"/api/geo/assets/{generated.json()['id']}/mark-ready",
        headers=headers,
        json={"confirmed": True},
    )
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


def test_checklist_starts_untested(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    page = client.post(
        "/api/seo-pages",
        headers=headers,
        json={"title": "Guide", "target_keyword": "smart lock", "locale": "en-US"},
    ).json()
    items = client.post(
        f"/api/geo/checklists/ensure?seo_page_id={page['id']}",
        headers=headers,
    )
    assert items.status_code == 200
    assert len(items.json()) >= 5
    assert all(i["status"] == "untested" for i in items.json())

    patched = client.patch(
        f"/api/geo/checklist-items/{items.json()[0]['id']}",
        headers=headers,
        json={"status": "pass", "notes": "作者栏已写"},
    )
    assert patched.json()["status"] == "pass"


def test_demand_signal_feeds_geo_prompt(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    market = client.post(
        "/api/markets",
        headers=headers,
        json={"name": "美国", "region": "北美", "country_code": "US", "primary_locale": "en-US"},
    ).json()
    signal = client.post(
        f"/api/markets/{market['id']}/demand-signals",
        headers=headers,
        json={"theme": "renter smart lock", "locale": "en-US"},
    ).json()
    prompt = client.post(f"/api/geo/from-demand-signal/{signal['id']}", headers=headers)
    assert prompt.status_code == 201
    assert prompt.json()["prompt_text"] == "renter smart lock"
    assert all(o["status"] == "untested" for o in prompt.json()["observations"])
