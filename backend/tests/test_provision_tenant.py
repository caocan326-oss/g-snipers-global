from app.models import Tenant, User
from app.provision_tenant import provision_customer


def test_provision_customer_creates_tenant_am_and_site(db) -> None:
    created = provision_customer(
        db,
        name="第二家出口客户",
        email="am@second.example",
        password="long-enough",
        site_origin="https://www.second.example",
        industry="五金",
        am_name="王经理",
    )
    db.commit()
    tenant = db.get(Tenant, created["tenant_id"])
    user = db.get(User, created["user_id"])
    assert tenant is not None
    assert tenant.site_origin == "https://www.second.example"
    assert user is not None
    assert user.email == "am@second.example"
    assert user.role == "account_manager"
    assert user.tenant_id == tenant.id


def test_provision_customer_rejects_duplicate_email(db, demo_user) -> None:
    try:
        provision_customer(
            db,
            name="另一家",
            email=demo_user.email,
            password="long-enough",
            site_origin="https://www.other.example",
        )
    except ValueError as exc:
        assert "已存在" in str(exc)
    else:
        raise AssertionError("expected duplicate email to fail")
