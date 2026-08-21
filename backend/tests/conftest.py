import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret")

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.database import Base, get_db
from app.login_guard import reset_login_guard
from app.main import app
from app.models import Tenant, User

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def _clear_login_guard() -> Generator[None, None, None]:
    reset_login_guard()
    yield
    reset_login_guard()


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    def _get_db() -> Generator[Session, None, None]:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def demo_user(db: Session) -> User:
    tenant = Tenant(name="测试租户", industry="test")
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email="am@demo.gsnipers.com",
        hashed_password=hash_password("demo1234"),
        name="测试经理",
        role="account_manager",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_header(client: TestClient, email: str = "am@demo.gsnipers.com", password: str = "demo1234") -> dict[str, str]:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
