"""Create one customer tenant + AM + official site. Internal use only. No public signup."""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.database import SessionLocal
from app.models import Tenant, User
from app.onsite_fetch import OriginError, normalize_origin


def provision_customer(
    db: Session,
    *,
    name: str,
    email: str,
    password: str,
    site_origin: str,
    industry: str = "",
    am_name: str = "",
) -> dict[str, str]:
    tenant_name = (name or "").strip()
    am_email = (email or "").strip().lower()
    if not tenant_name:
        raise ValueError("请填写客户名称")
    if not am_email or "@" not in am_email:
        raise ValueError("请填写客户经理邮箱")
    if len(password or "") < 8:
        raise ValueError("密码至少 8 位")
    origin = normalize_origin(site_origin)

    if db.scalar(select(User).where(User.email == am_email)):
        raise ValueError(f"邮箱已存在：{am_email}")
    existing = db.scalar(select(Tenant).where(Tenant.name == tenant_name))
    if existing:
        raise ValueError(f"客户名称已存在：{tenant_name}")

    tenant = Tenant(name=tenant_name, industry=(industry or "").strip() or None, site_origin=origin)
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=am_email,
        hashed_password=hash_password(password),
        name=(am_name or "").strip() or "客户经理",
        role="account_manager",
    )
    db.add(user)
    db.flush()
    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "user_id": user.id,
        "email": user.email,
        "site_origin": tenant.site_origin,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="内部开户：建租户、建客户经理、挂官网。不要做成公开注册。")
    parser.add_argument("--name", required=True, help="客户名称，例如：某某锁具")
    parser.add_argument("--email", required=True, help="客户经理登录邮箱")
    parser.add_argument("--password", required=True, help="登录密码，至少 8 位。不要写进仓库。")
    parser.add_argument("--site", required=True, help="客户官网，例如 https://www.example.com")
    parser.add_argument("--industry", default="", help="行业，可选")
    parser.add_argument("--am-name", default="", help="客户经理显示名，可选")
    args = parser.parse_args(argv)

    db = SessionLocal()
    try:
        created = provision_customer(
            db,
            name=args.name,
            email=args.email,
            password=args.password,
            site_origin=args.site,
            industry=args.industry,
            am_name=args.am_name,
        )
        db.commit()
    except (ValueError, OriginError) as exc:
        db.rollback()
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        db.close()

    print("已开户（内部）。")
    for key in ("tenant_name", "email", "site_origin", "tenant_id", "user_id"):
        print(f"{key}: {created[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
