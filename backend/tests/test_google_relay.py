import httpx

from app import google_relay
from app.config import settings


def test_request_goes_direct_when_relay_unconfigured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "google_relay_url", "")
    monkeypatch.setattr(settings, "google_relay_key", "")
    seen: dict[str, str] = {}

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def request(self, method, url, headers=None, data=None, json=None):
            seen["method"] = method
            seen["url"] = url
            seen["auth"] = (headers or {}).get("Authorization", "")
            return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(google_relay.httpx, "Client", FakeClient)
    res = google_relay.request(
        "POST",
        "https://oauth2.googleapis.com/token",
        headers={"Authorization": "Bearer t"},
        data={"grant_type": "refresh_token"},
    )
    assert res.status_code == 200
    assert seen["url"] == "https://oauth2.googleapis.com/token"
    assert seen["auth"] == "Bearer t"


def test_request_uses_worker_when_relay_configured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "google_relay_url", "https://g-snipers-google-relay.example.workers.dev")
    monkeypatch.setattr(settings, "google_relay_key", "relay-secret")
    seen: dict[str, object] = {}

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def request(self, method, url, headers=None, data=None, json=None):
            seen["url"] = url
            seen["headers"] = headers
            seen["json"] = json
            return httpx.Response(200, json={"rows": []})

    monkeypatch.setattr(google_relay.httpx, "Client", FakeClient)
    res = google_relay.request(
        "POST",
        "https://searchconsole.googleapis.com/webmasters/v3/sites/https%3A%2F%2Fexample.com%2F/searchAnalytics/query",
        headers={"Authorization": "Bearer t"},
        json={"startDate": "2026-08-01"},
    )
    assert res.status_code == 200
    assert seen["url"] == "https://g-snipers-google-relay.example.workers.dev/"
    headers = seen["headers"]
    assert headers["x-relay-key"] == "relay-secret"
    assert str(headers["x-relay-target"]).startswith("https://searchconsole.googleapis.com/")
    assert headers["Authorization"] == "Bearer t"


def test_request_rejects_non_google_host() -> None:
    try:
        google_relay.request("GET", "https://example.com/")
        raise AssertionError("expected refuse")
    except ValueError as exc:
        assert "refuses" in str(exc)
