from fastapi.testclient import TestClient

from app.main import UNEXPECTED_FAILURE, app


def test_unhandled_error_is_chinese_not_internal_server_error() -> None:
    @app.get("/api/_test_boom")
    def _boom() -> None:
        raise RuntimeError("database is locked")

    try:
        with TestClient(app, raise_server_exceptions=False) as raw:
            res = raw.get("/api/_test_boom")
        assert res.status_code == 500
        assert res.json()["detail"] == UNEXPECTED_FAILURE
        assert "Internal Server Error" not in res.text
        assert "locked" not in res.json()["detail"]
    finally:
        app.router.routes[:] = [route for route in app.router.routes if getattr(route, "path", None) != "/api/_test_boom"]


def test_known_http_error_stays_chinese(client: TestClient) -> None:
    empty = client.post("/api/auth/login", json={"email": "", "password": ""})
    assert empty.status_code == 400
    assert empty.json()["detail"] == "请填写邮箱和密码。"
