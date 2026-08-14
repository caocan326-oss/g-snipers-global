from fastapi.testclient import TestClient

from tests.conftest import auth_header


def _create_page(client: TestClient, headers: dict) -> str:
    res = client.post(
        "/api/seo-pages",
        headers=headers,
        json={"title": "Renter guide", "target_keyword": "smart lock installation", "locale": "en-US"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def test_outline_draft_meta_and_confirm_gate(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    page_id = _create_page(client, headers)

    outline = client.post(f"/api/seo-pages/{page_id}/generate-outline", headers=headers)
    assert outline.status_code == 200
    assert outline.json()["status"] == "outline"
    assert "smart lock installation" in outline.json()["outline"]

    draft = client.post(f"/api/seo-pages/{page_id}/generate-draft", headers=headers)
    assert draft.status_code == 200
    assert draft.json()["status"] == "draft"
    assert draft.json()["draft_body"]

    meta = client.post(f"/api/seo-pages/{page_id}/generate-meta", headers=headers)
    assert meta.status_code == 200
    assert meta.json()["meta_title"]
    assert len(meta.json()["meta_description"]) <= 160

    denied = client.post(f"/api/seo-pages/{page_id}/mark-ready", headers=headers, json={"confirmed": False})
    assert denied.status_code == 400

    patch_ready = client.patch(f"/api/seo-pages/{page_id}", headers=headers, json={"status": "ready"})
    assert patch_ready.status_code == 400

    review = client.post(f"/api/seo-pages/{page_id}/submit-review", headers=headers)
    assert review.status_code == 200
    assert review.json()["status"] == "review"

    still_denied = client.post(f"/api/seo-pages/{page_id}/mark-ready", headers=headers, json={"confirmed": False})
    assert still_denied.status_code == 400

    ready = client.post(
        f"/api/seo-pages/{page_id}/mark-ready",
        headers=headers,
        json={"confirmed": True, "note": "AM reviewed"},
    )
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


def test_list_filter_by_status(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    _create_page(client, headers)
    listed = client.get("/api/seo-pages", headers=headers, params={"status": "idea"})
    assert listed.status_code == 200
    assert len(listed.json()) == 1
