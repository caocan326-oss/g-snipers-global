from fastapi.testclient import TestClient

from app.usage import METERS, record
from tests.conftest import auth_header
from tests.test_ops_backup import _admin


def _meter(body: dict, key: str) -> dict:
    return next(row for row in body["meters"] if row["key"] == key)


def _set_limit(client: TestClient, tenant_id: str, meter: str, daily_limit: int) -> None:
    admin = auth_header(client, email="admin@demo.gsnipers.com", password="admin1234")
    res = client.patch(
        "/api/usage/quota",
        headers=admin,
        json={"tenant_id": tenant_id, "meter": meter, "daily_limit": daily_limit},
    )
    assert res.status_code == 200, res.text


def test_account_manager_can_see_own_usage_but_not_board(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    today = client.get("/api/usage/today", headers=headers)
    assert today.status_code == 200, today.text
    body = today.json()
    assert body["tenant_name"] == "测试租户"
    keys = {row["key"] for row in body["meters"]}
    assert keys == {item["key"] for item in METERS}
    assert all(row["used"] == 0 for row in body["meters"])
    assert client.get("/api/usage/board", headers=headers).status_code == 403
    assert client.patch(
        "/api/usage/quota",
        headers=headers,
        json={"tenant_id": demo_user.tenant_id, "meter": "serp", "daily_limit": 3},
    ).status_code == 403


def test_admin_sets_per_tenant_daily_limit(client: TestClient, demo_user, db) -> None:
    _admin(db)
    headers = auth_header(client, email="admin@demo.gsnipers.com", password="admin1234")
    board = client.get("/api/usage/board", headers=headers)
    assert board.status_code == 200, board.text
    tenant = next(row for row in board.json()["tenants"] if row["tenant_id"] == demo_user.tenant_id)
    serp = next(row for row in tenant["meters"] if row["key"] == "serp")
    assert serp["limit"] == 15

    patched = client.patch(
        "/api/usage/quota",
        headers=headers,
        json={"tenant_id": demo_user.tenant_id, "meter": "serp", "daily_limit": 3},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["limit"] == 3
    assert patched.json()["remaining"] == 3

    today = client.get("/api/usage/today", headers=auth_header(client)).json()
    assert _meter(today, "serp")["limit"] == 3
    assert {row["key"] for row in today["meters"]} == {item["key"] for item in METERS}


def test_geo_sample_stops_when_daily_limit_is_zero(client: TestClient, demo_user, db) -> None:
    _admin(db)
    admin_headers = auth_header(client, email="admin@demo.gsnipers.com", password="admin1234")
    client.patch(
        "/api/usage/quota",
        headers=admin_headers,
        json={"tenant_id": demo_user.tenant_id, "meter": "llm", "daily_limit": 0},
    )
    headers = auth_header(client)
    prompt = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={"prompt_text": "Best industrial valve suppliers", "locale": "en-US"},
    ).json()
    run = client.post(
        "/api/geo/sample-runs/auto",
        headers=headers,
        json={"prompt_ids": [prompt["id"]], "trials": 1, "limit": 1, "provider": "deepseek"},
    )
    assert run.status_code == 429, run.text
    assert "改法与分析" in run.json()["detail"]
    assert "已用 0/0" in run.json()["detail"]


def test_serp_stops_when_daily_limit_is_zero(client: TestClient, demo_user, db, monkeypatch) -> None:
    from app.config import settings

    _admin(db)
    _set_limit(client, demo_user.tenant_id, "serp", 0)
    monkeypatch.setattr(settings, "brightdata_dataset_api_key", "dataset-key")
    monkeypatch.setattr(settings, "brightdata_serp_zone", "serp_api1")

    called = {"n": 0}

    def boom(*args, **kwargs):
        called["n"] += 1
        raise AssertionError("配额用完后不该再打 Bright Data")

    monkeypatch.setattr("app.routers.onsite.diagnosis._fetch_brightdata_serp", boom)
    res = client.post(
        "/api/onsite/serp/run",
        headers=auth_header(client),
        json={"keywords": ["industrial pump"], "country": "US", "locale": "en-US", "device": "desktop", "limit": 5},
    )
    assert res.status_code == 429, res.text
    assert "关键词排名" in res.json()["detail"]
    assert called["n"] == 0


def test_pagespeed_stops_when_daily_limit_is_zero(client: TestClient, demo_user, db, monkeypatch) -> None:
    import app.routers.onsite.diagnosis as diagnosis

    _admin(db)
    _set_limit(client, demo_user.tenant_id, "pagespeed", 0)
    headers = auth_header(client)
    client.patch("/api/onsite/settings", headers=headers, json={"site_origin": "https://example.com"})
    monkeypatch.setattr(diagnosis, "_run_pagespeed", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("配额用完后不该再测速")))
    res = client.post("/api/onsite/performance/pagespeed", headers=headers, json={"urls": [], "limit": 1})
    assert res.status_code == 429, res.text
    assert "测速" in res.json()["detail"]


def test_grounded_batch_stops_when_bocha_limit_is_zero(client: TestClient, demo_user, db, monkeypatch) -> None:
    from app import geo_providers

    _admin(db)
    _set_limit(client, demo_user.tenant_id, "bocha", 0)
    headers = auth_header(client)
    prompt = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={"prompt_text": "How do renters install a smart lock?", "locale": "en-US"},
    ).json()
    monkeypatch.setattr(geo_providers.settings, "bocha_api_key", "test-bocha")
    monkeypatch.setattr(geo_providers.settings, "dashscope_api_key", "test-dashscope")
    called = {"n": 0}

    def boom(*args, **kwargs):
        called["n"] += 1
        raise AssertionError("配额用完后不该再抽查")

    monkeypatch.setattr("app.routers.geo.sample_with_provider", boom)
    res = client.post(
        "/api/geo/sample-runs/auto-grounded",
        headers=headers,
        json={"prompt_ids": [prompt["id"]], "trials": 1, "limit": 1},
    )
    assert res.status_code == 429, res.text
    assert "博查" in res.json()["detail"]
    assert called["n"] == 0


def test_pagespeed_counts_used_after_success(client: TestClient, demo_user, monkeypatch) -> None:
    import app.routers.onsite.diagnosis as diagnosis
    from app.config import settings

    headers = auth_header(client)
    client.patch("/api/onsite/settings", headers=headers, json={"site_origin": "https://example.com"})
    monkeypatch.setattr(settings, "google_relay_url", "https://g-snipers-google-relay.example.workers.dev")
    monkeypatch.setattr(settings, "google_relay_key", "relay-secret")
    monkeypatch.setattr(
        diagnosis.google_relay,
        "request",
        lambda *args, **kwargs: __import__("httpx").Response(
            200,
            json={
                "lighthouseResult": {
                    "categories": {"performance": {"score": 0.8}, "seo": {"score": 0.8}, "accessibility": {"score": 0.8}, "best-practices": {"score": 0.8}},
                    "audits": {},
                }
            },
        ),
    )
    res = client.post("/api/onsite/performance/pagespeed", headers=headers, json={"urls": [], "limit": 1})
    assert res.status_code == 200, res.text
    today = client.get("/api/usage/today", headers=headers).json()
    pagespeed = _meter(today, "pagespeed")
    assert pagespeed["used"] == 1
    assert pagespeed["remaining"] == pagespeed["limit"] - 1


def test_record_drops_remaining_for_each_meter(demo_user, db) -> None:
    for item in METERS:
        snap = record(db, demo_user.tenant_id, item["key"], 2)
        assert snap.used == 2
        assert snap.remaining == item["default_daily"] - 2
    db.commit()


def _fake_httpx_client(response):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            return response

    return FakeClient


def test_record_current_survives_later_rollback(demo_user, db) -> None:
    from app.models import Tenant
    from app.usage import record_current, set_usage_tenant, used_today

    set_usage_tenant(demo_user.tenant_id, db)
    record_current("bocha", 1)
    tenant = db.get(Tenant, demo_user.tenant_id)
    tenant.name = "SHOULD_REVERT"
    db.rollback()
    db.expire_all()
    assert used_today(db, demo_user.tenant_id, "bocha") == 1
    assert db.get(Tenant, demo_user.tenant_id).name == "测试租户"


def test_bocha_counts_only_after_http_success(demo_user, db, monkeypatch) -> None:
    from app import geo_providers
    from app.usage import used_today

    monkeypatch.setattr(geo_providers.settings, "bocha_api_key", "test-key")

    class Fail:
        status_code = 500
        text = "nope"

    monkeypatch.setattr(geo_providers.httpx, "Client", _fake_httpx_client(Fail()))
    try:
        geo_providers._call_bocha("best lock", db=db, tenant_id=demo_user.tenant_id)
        raise AssertionError("博查失败时不该当成功")
    except geo_providers.GeoProviderError:
        pass
    assert used_today(db, demo_user.tenant_id, "bocha") == 0

    class Ok:
        status_code = 200

        def json(self):
            return {"data": {"webPages": {"value": [{"url": "https://a.example", "name": "A", "snippet": "s"}]}}}

    monkeypatch.setattr(geo_providers.httpx, "Client", _fake_httpx_client(Ok()))
    geo_providers._call_bocha("best lock", db=db, tenant_id=demo_user.tenant_id)
    db.rollback()
    db.expire_all()
    assert used_today(db, demo_user.tenant_id, "bocha") == 1


def test_bocha_without_tenant_does_not_count(demo_user, db, monkeypatch) -> None:
    from app import geo_providers
    from app.usage import used_today

    monkeypatch.setattr(geo_providers.settings, "bocha_api_key", "test-key")
    called = {"n": 0}

    class Probe:
        def __init__(self, *args, **kwargs):
            called["n"] += 1

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            raise AssertionError("没有租户时不该打博查")

    monkeypatch.setattr(geo_providers.httpx, "Client", Probe)
    try:
        geo_providers._call_bocha("best lock")
        raise AssertionError("缺少用量上下文时应失败")
    except geo_providers.GeoProviderError as exc:
        assert "用量" in str(exc)
    assert called["n"] == 0
    assert used_today(db, demo_user.tenant_id, "bocha") == 0


def test_llm_counts_only_after_http_success(demo_user, db, monkeypatch) -> None:
    from app import llm
    from app.usage import set_usage_tenant, used_today

    set_usage_tenant(demo_user.tenant_id, db)
    monkeypatch.setattr(llm.settings, "llm_api_key", "test-key")

    class Fail:
        status_code = 500
        text = "nope"

        def json(self):
            return {}

    monkeypatch.setattr(llm.httpx, "Client", _fake_httpx_client(Fail()))
    result = llm.complete(system="s", user="u")
    assert result.status == llm.ERROR
    assert used_today(db, demo_user.tenant_id, "llm") == 0

    class Ok:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "hello"}}]}

    monkeypatch.setattr(llm.httpx, "Client", _fake_httpx_client(Ok()))
    result = llm.complete(system="s", user="u")
    assert result.status == llm.OK
    db.rollback()
    db.expire_all()
    assert used_today(db, demo_user.tenant_id, "llm") == 1


def test_admin_cannot_set_quota_for_missing_tenant(client: TestClient, demo_user, db) -> None:
    _admin(db)
    headers = auth_header(client, email="admin@demo.gsnipers.com", password="admin1234")
    res = client.patch(
        "/api/usage/quota",
        headers=headers,
        json={"tenant_id": "missing-tenant", "meter": "serp", "daily_limit": 1},
    )
    assert res.status_code == 404
