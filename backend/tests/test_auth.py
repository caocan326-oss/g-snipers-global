from fastapi.testclient import TestClient


def test_login_and_me(client: TestClient, demo_user) -> None:
    bad = client.post("/api/auth/login", json={"email": "am@demo.gsnipers.com", "password": "wrong"})
    assert bad.status_code == 401

    ok = client.post("/api/auth/login", json={"email": "am@demo.gsnipers.com", "password": "demo1234"})
    assert ok.status_code == 200
    token = ok.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "am@demo.gsnipers.com"
    assert me.json()["tenant_name"] == "测试租户"


def test_health(client: TestClient) -> None:
    assert client.get("/api/health").json()["status"] == "ok"


def test_dashboard_has_geo_counts_not_rates(client: TestClient, demo_user) -> None:
    token = client.post("/api/auth/login", json={"email": "am@demo.gsnipers.com", "password": "demo1234"}).json()[
        "access_token"
    ]
    res = client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert "geo_untested" in body
    assert "citation_rate" not in body
    assert "share_of_voice" not in body


def test_dashboard_workbench_prioritizes_seo_geo_diagnosis(client: TestClient, demo_user) -> None:
    token = client.post("/api/auth/login", json={"email": "am@demo.gsnipers.com", "password": "demo1234"}).json()[
        "access_token"
    ]
    headers = {"Authorization": f"Bearer {token}"}
    saved = client.patch("/api/onsite/settings", headers=headers, json={"site_origin": "https://www.example.com"})
    assert saved.status_code == 200, saved.text
    market = client.post(
        "/api/markets",
        headers=headers,
        json={"name": "美国", "region": "北美", "country_code": "US", "primary_locale": "en-US"},
    ).json()
    signal = client.post(
        f"/api/markets/{market['id']}/demand-signals",
        headers=headers,
        json={"theme": "smart lock for renters", "locale": "en-US", "intensity": 5},
    ).json()
    page = client.post(
        "/api/onsite/pages",
        headers=headers,
        json={"path": "/en-us/renters", "locale": "en-US", "title": "Renters"},
    ).json()
    client.post(
        f"/api/onsite/pages/{page['id']}/issues",
        headers=headers,
        json={"category": "schema", "title": "缺少 FAQ schema", "severity": "critical", "risk": "high"},
    )
    client.post(f"/api/demand-signals/{signal['id']}/open-geo-ticket", headers=headers)
    client.post(
        "/api/onsite/performance/import-csv",
        headers=headers,
        json={
            "source": "gsc_csv",
            "filename": "gsc.csv",
            "csv_text": "\n".join(
                [
                    "Date,Query,Page,Country,Clicks,Impressions,CTR,Position",
                    "2026-08-15,smart lock,https://example.com/en-us/renters,United States,8,200,4%,9",
                ]
            ),
        },
    )

    res = client.get("/api/dashboard/workbench?days=7", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["summary"]["onsite_open_critical"] == 1
    assert data["summary"]["geo_tickets_open"] == 1
    assert data["chains"][0]["title"] == "网站检查"
    assert all(chain["key"] != "insights" for chain in data["chains"])
    assert data["seo_performance"]["days"] == 7
    assert data["seo_performance"]["total_impressions"] == 200
    assert data["seo_performance"]["top_keywords"][0]["key"] == "smart lock"
    assert any(item["id"] == "fetch-site" for item in data["next_actions"])
    assert all(item["id"] != "seo-critical" for item in data["next_actions"])
    assert data["seo_items"][0]["href"] == f"/onsite/{page['id']}"
    assert data["recent_signals"][0]["href"] == f"/insights/{market['id']}"


def test_boot_does_not_require_google_ads_env(client: TestClient, monkeypatch) -> None:
    for key in (
        "GOOGLE_ADS_CLIENT_ID",
        "GOOGLE_ADS_CLIENT_SECRET",
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "GOOGLE_ADS_MCC_ID",
        "GOOGLE_ADS_REDIRECT_URI",
    ):
        monkeypatch.delenv(key, raising=False)
    assert client.get("/api/health").json()["status"] == "ok"
