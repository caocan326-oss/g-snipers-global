from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import PlatformAccount, PlatformConnector, SourcePlatform, User
from app.official_apis import OFFICIAL_APIS, OfficialApi
from app.schemas import (
    OfficialApiOut,
    OfficialApiSeedOut,
    PlatformAccountCreate,
    PlatformAccountOut,
    PlatformConnectorCreate,
    PlatformConnectorOut,
    SourcePlatformCreate,
    SourcePlatformOut,
    SourcePlatformSeedOut,
)

from . import router
from .common import _account_out, _connector_out, _platform_out
from .constants import ACCOUNT_STATUSES, AUTH_METHODS, SUBMISSION_MODES
from .seeds import B2B_PLATFORM_SEEDS


@router.get("/platforms", response_model=list[SourcePlatformOut])
def list_platforms(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[SourcePlatformOut]:
    rows = (
        db.query(SourcePlatform)
        .options(selectinload(SourcePlatform.accounts), selectinload(SourcePlatform.connectors))
        .filter(SourcePlatform.tenant_id == user.tenant_id)
        .order_by(SourcePlatform.status, SourcePlatform.name)
        .all()
    )
    return [_platform_out(row) for row in rows]


@router.post("/platforms", response_model=SourcePlatformOut, status_code=201)
def create_platform(
    body: SourcePlatformCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SourcePlatformOut:
    if body.submission_mode not in SUBMISSION_MODES:
        raise HTTPException(status_code=400, detail="无效提交方式")
    row = SourcePlatform(tenant_id=user.tenant_id, **body.model_dump())
    db.add(row)
    db.commit()
    row = (
        db.query(SourcePlatform)
        .options(selectinload(SourcePlatform.accounts), selectinload(SourcePlatform.connectors))
        .filter(SourcePlatform.id == row.id)
        .one()
    )
    return _platform_out(row)


@router.post("/platforms/seed-b2b", response_model=SourcePlatformSeedOut)
def seed_b2b_platforms(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SourcePlatformSeedOut:
    created = 0
    skipped = 0
    for item in B2B_PLATFORM_SEEDS:
        exists = (
            db.query(SourcePlatform)
            .filter(SourcePlatform.tenant_id == user.tenant_id, SourcePlatform.platform_key == item["platform_key"])
            .first()
        )
        if exists:
            skipped += 1
            continue
        db.add(
            SourcePlatform(
                tenant_id=user.tenant_id,
                has_official_api=item["platform_key"] in OFFICIAL_APIS,
                status="active",
                **item,
            )
        )
        created += 1
    db.commit()
    rows = (
        db.query(SourcePlatform)
        .options(selectinload(SourcePlatform.accounts), selectinload(SourcePlatform.connectors))
        .filter(SourcePlatform.tenant_id == user.tenant_id)
        .order_by(SourcePlatform.status, SourcePlatform.name)
        .all()
    )
    return SourcePlatformSeedOut(created=created, skipped=skipped, platforms=[_platform_out(row) for row in rows])


def _api_out(spec: OfficialApi) -> OfficialApiOut:
    return OfficialApiOut(
        platform_key=spec.platform_key,
        label=spec.label,
        compose_url=spec.compose_url,
        docs_url=spec.docs_url,
        api_endpoint=spec.api_endpoint,
        http_method=spec.http_method,
        auth_mode=spec.auth_mode,
        env_hint=spec.env_hint,
        note=spec.note,
    )


@router.get("/official-apis", response_model=list[OfficialApiOut])
def list_official_apis(user: User = Depends(get_current_user)) -> list[OfficialApiOut]:
    return [_api_out(spec) for spec in OFFICIAL_APIS.values()]


@router.post("/platforms/seed-official-apis", response_model=OfficialApiSeedOut)
def seed_official_apis(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> OfficialApiSeedOut:
    created = 0
    updated = 0
    for spec in OFFICIAL_APIS.values():
        platform = (
            db.query(SourcePlatform)
            .filter(SourcePlatform.tenant_id == user.tenant_id, SourcePlatform.platform_key == spec.platform_key)
            .first()
        )
        if platform is None:
            continue
        if not platform.has_official_api:
            platform.has_official_api = True
            updated += 1
        exists = (
            db.query(PlatformConnector)
            .filter(
                PlatformConnector.tenant_id == user.tenant_id,
                PlatformConnector.platform_id == platform.id,
                PlatformConnector.provider_key == spec.platform_key,
            )
            .first()
        )
        if exists:
            exists.auth_mode = spec.auth_mode
            exists.capabilities = "customer_post"
            exists.status = "customer_api"
            exists.notes = spec.note
            updated += 1
            continue
        db.add(
            PlatformConnector(
                tenant_id=user.tenant_id,
                platform_id=platform.id,
                provider_key=spec.platform_key,
                auth_mode=spec.auth_mode,
                capabilities="customer_post",
                status="customer_api",
                env_var=spec.env_hint,
                notes=spec.note,
            )
        )
        created += 1
    db.commit()
    return OfficialApiSeedOut(created=created, updated=updated, apis=[_api_out(spec) for spec in OFFICIAL_APIS.values()])


@router.get("/accounts", response_model=list[PlatformAccountOut])
def list_accounts(
    platform_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PlatformAccountOut]:
    q = db.query(PlatformAccount).options(selectinload(PlatformAccount.platform)).filter(PlatformAccount.tenant_id == user.tenant_id)
    if platform_id:
        q = q.filter(PlatformAccount.platform_id == platform_id)
    return [_account_out(row) for row in q.order_by(PlatformAccount.status, PlatformAccount.label).all()]


@router.post("/accounts", response_model=PlatformAccountOut, status_code=201)
def create_account(
    body: PlatformAccountCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlatformAccountOut:
    platform = db.get(SourcePlatform, body.platform_id)
    if platform is None or platform.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="平台不存在")
    if body.auth_method not in AUTH_METHODS:
        raise HTTPException(status_code=400, detail="无效授权方式")
    if body.status not in ACCOUNT_STATUSES:
        raise HTTPException(status_code=400, detail="无效账号状态")
    if body.auth_method in {"password_vault", "api_key_vault"} and not body.vault_ref.strip():
        raise HTTPException(status_code=400, detail="密码或 API Key 必须只保存 vault_ref")
    row = PlatformAccount(tenant_id=user.tenant_id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _account_out(row)


@router.get("/connectors", response_model=list[PlatformConnectorOut])
def list_connectors(
    platform_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PlatformConnectorOut]:
    q = db.query(PlatformConnector).options(selectinload(PlatformConnector.platform)).filter(PlatformConnector.tenant_id == user.tenant_id)
    if platform_id:
        q = q.filter(PlatformConnector.platform_id == platform_id)
    return [_connector_out(row) for row in q.order_by(PlatformConnector.status, PlatformConnector.provider_key).all()]


@router.post("/connectors", response_model=PlatformConnectorOut, status_code=201)
def create_connector(
    body: PlatformConnectorCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlatformConnectorOut:
    platform = db.get(SourcePlatform, body.platform_id)
    if platform is None or platform.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="平台不存在")
    row = PlatformConnector(tenant_id=user.tenant_id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _connector_out(row)
