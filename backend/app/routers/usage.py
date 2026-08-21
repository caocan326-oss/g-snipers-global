from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import Tenant, User
from app.schemas import UsageBoardOut, UsageMeterOut, UsageQuotaPatch, UsageTenantOut, UsageTodayOut
from app.usage import set_quota, tenant_usage, usage_day

router = APIRouter(prefix="/api/usage", tags=["usage"])


def _meters(db: Session, tenant_id: str) -> list[UsageMeterOut]:
    return [UsageMeterOut(**item.__dict__) for item in tenant_usage(db, tenant_id)]


@router.get("/today", response_model=UsageTodayOut)
def usage_today(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UsageTodayOut:
    tenant = db.get(Tenant, user.tenant_id)
    return UsageTodayOut(
        day=usage_day(),
        tenant_id=user.tenant_id,
        tenant_name=tenant.name if tenant else "",
        meters=_meters(db, user.tenant_id),
    )


@router.get("/board", response_model=UsageBoardOut)
def usage_board(admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> UsageBoardOut:
    del admin
    tenants = db.query(Tenant).order_by(Tenant.created_at.desc()).all()
    return UsageBoardOut(
        day=usage_day(),
        tenants=[
            UsageTenantOut(
                tenant_id=tenant.id,
                tenant_name=tenant.name,
                site_origin=tenant.site_origin or "",
                meters=_meters(db, tenant.id),
            )
            for tenant in tenants
        ],
    )


@router.patch("/quota", response_model=UsageMeterOut)
def patch_usage_quota(
    body: UsageQuotaPatch,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UsageMeterOut:
    tenant = db.get(Tenant, body.tenant_id)
    if tenant is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="没有这家客户。")
    row = set_quota(db, body.tenant_id, body.meter, body.daily_limit, admin.id)
    db.commit()
    return UsageMeterOut(**row.__dict__)
