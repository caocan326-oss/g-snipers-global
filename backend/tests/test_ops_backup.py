from pathlib import Path

from fastapi.testclient import TestClient

from app.auth import hash_password
from app.config import settings
from app.models import Tenant, User
from tests.conftest import auth_header


def _admin(db) -> User:
    tenant = db.get(Tenant, db.query(User).first().tenant_id) if db.query(User).first() else None
    if tenant is None:
        tenant = Tenant(name="管理租户", industry="test")
        db.add(tenant)
        db.flush()
    user = User(
        tenant_id=tenant.id,
        email="admin@demo.gsnipers.com",
        hashed_password=hash_password("admin1234"),
        name="管理员",
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_account_manager_cannot_export_backup(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    assert client.get("/api/ops/backup", headers=headers).status_code == 403
    assert client.post("/api/ops/backup", headers=headers).status_code == 403


def test_admin_can_export_and_download_backup(client: TestClient, demo_user, db, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "backup_local_dir", str(tmp_path))
    monkeypatch.setattr(settings, "backup_schedule_enabled", False)
    monkeypatch.setattr(settings, "backup_offsite_kind", "none")
    _admin(db)
    headers = auth_header(client, email="admin@demo.gsnipers.com", password="admin1234")

    status = client.get("/api/ops/backup", headers=headers)
    assert status.status_code == 200, status.text
    body = status.json()
    assert body["schedule_enabled"] is False
    assert body["offsite_configured"] is False

    created = client.post("/api/ops/backup", headers=headers)
    assert created.status_code == 200, created.text
    filename = created.json()["filename"]
    assert filename.startswith("gsnipers-db-")
    assert created.json()["offsite"] == "skipped"

    listed = client.get("/api/ops/backup", headers=headers).json()
    assert listed["latest"]["filename"] == filename

    download = client.get(f"/api/ops/backup/{filename}", headers=headers)
    assert download.status_code == 200, download.text
    assert download.content[:2] == b"\x1f\x8b"
