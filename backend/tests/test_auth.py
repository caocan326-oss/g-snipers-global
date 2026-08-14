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
