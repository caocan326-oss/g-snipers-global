from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import ContentAsset, PlatformAccount, PlatformConnector, SourcePlatform, Tenant, User
from app.offsite_profile import check_public_profile
from app.official_apis import OFFICIAL_APIS, OfficialApi, official_api_for, official_api_payload
from app.schemas import (
    CheckProfileIn,
    MarkOwnApiIn,
    OfficialApiOut,
    ProfileCheckOut,
    OfficialApiSeedOut,
    OfficialPayloadOut,
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


@router.post("/platforms/{platform_id}/check-profile", response_model=ProfileCheckOut)
def check_platform_profile(
    platform_id: str,
    body: CheckProfileIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileCheckOut:
    platform = db.get(SourcePlatform, platform_id)
    if platform is None or platform.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="平台不存在")
    tenant = db.get(Tenant, user.tenant_id)
    profile_url = (body.profile_url or "").strip()
    if not profile_url:
        _store_profile_reject(platform, "先填这家客户的公开主页 URL。我们不猜、不注册、不代登。")
        db.commit()
        raise HTTPException(status_code=400, detail=platform.profile_note)
    try:
        result = check_public_profile(
            profile_url=profile_url,
            site_origin=(tenant.site_origin if tenant else "") or "",
            brand=(tenant.name if tenant else "") or "",
            platform_name=platform.name or "",
        )
    except ValueError as exc:
        _store_profile_reject(platform, str(exc))
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    platform.profile_url = result["profile_url"]
    platform.profile_http_status = result["http_status"]
    platform.profile_is_live = result["is_live"]
    platform.profile_site_found = result["site_found"]
    platform.profile_checked_at = datetime.now(timezone.utc)
    platform.profile_note = result["note"]
    db.commit()
    return ProfileCheckOut(platform_id=platform.id, **result)


def _store_profile_reject(platform: SourcePlatform, detail: str) -> None:
    platform.profile_url = ""
    platform.profile_http_status = None
    platform.profile_is_live = False
    platform.profile_site_found = False
    platform.profile_checked_at = datetime.now(timezone.utc)
    platform.profile_note = detail


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


@router.get("/platforms/{platform_id}/official-payload", response_model=OfficialPayloadOut)
def platform_official_payload(
    platform_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OfficialPayloadOut:
    platform = db.get(SourcePlatform, platform_id)
    if platform is None or platform.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="平台不存在")
    spec = official_api_for(platform.platform_key)
    if spec is None:
        raise HTTPException(status_code=400, detail="这个渠道还没有挂客户自己的官方接口。请打开官方发帖页，或登记客户自己的接口。")
    tenant = db.get(Tenant, user.tenant_id)
    assets = db.query(ContentAsset).filter(ContentAsset.tenant_id == user.tenant_id).all()
    asset = next((row for row in assets if platform.name in (row.title or "") and (row.body_md or "").strip()), None)
    body = asset.body_md if asset else ""
    title = asset.title if asset else f"在 {platform.name} 发一篇"
    target = (tenant.site_origin if tenant else "") or ""
    payload = official_api_payload(platform_key=platform.platform_key, title=title, body=body, target_url=target)
    return OfficialPayloadOut(sent=False, **payload)


@router.post("/platforms/{platform_id}/mark-own-api", response_model=PlatformConnectorOut)
def mark_own_api(
    platform_id: str,
    body: MarkOwnApiIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlatformConnectorOut:
    if not body.confirmed:
        raise HTTPException(status_code=400, detail="登记客户已自备接口需要确认。我们不代发、不收他们的钥匙。")
    platform = db.get(SourcePlatform, platform_id)
    if platform is None or platform.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="平台不存在")
    spec = official_api_for(platform.platform_key)
    note = "客户说已自备接口。我们不代发、不存他们的钥匙。"
    row = (
        db.query(PlatformConnector)
        .filter(PlatformConnector.tenant_id == user.tenant_id, PlatformConnector.platform_id == platform.id)
        .first()
    )
    if row is None:
        row = PlatformConnector(
            tenant_id=user.tenant_id,
            platform_id=platform.id,
            provider_key=platform.platform_key or "customer_api",
            auth_mode=spec.auth_mode if spec else "api",
            capabilities="customer_post",
            status="customer_own",
            env_var=spec.env_hint if spec else "",
            notes=note,
        )
        db.add(row)
    else:
        row.status = "customer_own"
        row.capabilities = "customer_post"
        row.notes = note
        row.env_var = spec.env_hint if spec else row.env_var
    db.commit()
    db.refresh(row)
    row.platform = platform
    return _connector_out(row)


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
