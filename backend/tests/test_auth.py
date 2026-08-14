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
