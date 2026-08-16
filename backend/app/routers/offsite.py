from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from sqlalchemy.orm import Session, selectinload

from app.ai_engine import assist_offsite_gap
from app.auth import get_current_user
from app.database import get_db
from app.models import BacklinkGap, OutreachItem, PlatformAccount, PlatformConnector, SourcePlatform, User
from app.schemas import (
    AiAssistOut,
    AiStepIn,
    BacklinkGapCreate,
    BacklinkGapOut,
    BacklinkGapUpdate,
    LinkCheckerOut,
    OutreachCreate,
    OutreachOut,
    PlatformAccountCreate,
    PlatformAccountOut,
    PlatformConnectorCreate,
    PlatformConnectorOut,
    SourcePlatformCreate,
    SourcePlatformOut,
    SourcePlatformSeedOut,
)

router = APIRouter(prefix="/api/offsite", tags=["offsite"])

GAP_STATUSES = {
    "identified",
    "outreach",
    "replied",
    "converted_to_task",
    "in_progress",
    "needs_retest",
    "won",
    "lost",
    "skipped",
    "blocked",
    "closed",
    "ignored",
}
OUTREACH_STATUSES = {"todo", "sent_manual", "replied", "closed"}
VERIFY_STATUSES = {"unverified", "valid", "dead", "spam"}
KINDS = {"inbound", "competitor"}
PRIORITIES = {"P0", "P1", "P2", "P3"}
SUBMISSION_MODES = {"manual_login", "email_outreach", "form_public", "paid_placement", "api_none"}
ACCOUNT_STATUSES = {"active", "needs_2fa", "locked", "expired", "banned", "retired"}
AUTH_METHODS = {"password_vault", "sso", "oauth", "api_key_vault", "manual_only"}

B2B_PLATFORM_SEEDS = [
    {
        "platform_key": "thomasnet",
        "name": "ThomasNet",
        "domain": "thomasnet.com",
        "source_type": "directory",
        "regions": "US, North America",
        "industry_tags": "industrial, manufacturing, supplier discovery",
        "base_url": "https://www.thomasnet.com/",
        "listing_model": "directory_profile",
        "submission_mode": "manual_login",
        "risk_level": "medium",
        "notes": "北美工业采购目录。适合供应商档案认领、品类补全、官网和认证信息一致性维护；不做自动登录提交。",
    },
    {
        "platform_key": "globalspec",
        "name": "GlobalSpec / Engineering360",
        "domain": "globalspec.com",
        "source_type": "directory",
        "regions": "US, Global",
        "industry_tags": "engineering, components, specifications",
        "base_url": "https://www.globalspec.com/",
        "listing_model": "directory_profile",
        "submission_mode": "manual_login",
        "risk_level": "medium",
        "notes": "工程和技术产品检索源。优先核对供应商、规格、品类和官网链接。",
    },
    {
        "platform_key": "industrynet",
        "name": "IndustryNet",
        "domain": "industrynet.com",
        "source_type": "directory",
        "regions": "US, North America",
        "industry_tags": "industrial suppliers, RFQ",
        "base_url": "https://www.industrynet.com/",
        "listing_model": "directory_profile",
        "submission_mode": "manual_login",
        "risk_level": "medium",
        "notes": "北美工业供应商发现源。适合 profile_create/profile_update，提交结果必须回填 result_url。",
    },
    {
        "platform_key": "kompass",
        "name": "Kompass",
        "domain": "kompass.com",
        "source_type": "directory",
        "regions": "Global, EU",
        "industry_tags": "global b2b, company directory",
        "base_url": "https://www.kompass.com/",
        "listing_model": "directory_profile",
        "submission_mode": "manual_login",
        "risk_level": "medium",
        "notes": "全球 B2B 公司目录。适合出口企业多语种档案和品类描述核对。",
    },
    {
        "platform_key": "europages",
        "name": "Europages",
        "domain": "europages.com",
        "source_type": "marketplace",
        "regions": "EU, Global",
        "industry_tags": "europe b2b, exporter",
        "base_url": "https://www.europages.com/",
        "listing_model": "marketplace",
        "submission_mode": "manual_login",
        "risk_level": "medium",
        "notes": "欧洲 B2B 平台。适合 profile_update、product_listing，多语种内容必须人工终审。",
    },
    {
        "platform_key": "mfg",
        "name": "MFG.com",
        "domain": "mfg.com",
        "source_type": "marketplace",
        "regions": "US, Global",
        "industry_tags": "custom manufacturing, RFQ, machining",
        "base_url": "https://www.mfg.com/",
        "listing_model": "marketplace",
        "submission_mode": "manual_login",
        "risk_level": "medium",
        "notes": "定制制造和 RFQ 平台。更偏获客与能力露出，不把提交视为 SEO 提升保证。",
    },
    {
        "platform_key": "engineering_media",
        "name": "Engineering / Industrial Media",
        "domain": "engineering.com",
        "source_type": "media",
        "regions": "US, Global",
        "industry_tags": "media, listicle, PR, roundup",
        "base_url": "https://www.engineering.com/",
        "listing_model": "media",
        "submission_mode": "email_outreach",
        "risk_level": "high",
        "notes": "行业媒体、榜单、测评和 PR 入口的代表资源。只生成 pitch/媒体包草稿，必须人工发送和终审。",
    },
    {
        "platform_key": "distributor_pages",
        "name": "Distributor / Partner Pages",
        "domain": "",
        "source_type": "distributor",
        "regions": "Target markets",
        "industry_tags": "dealer, distributor, partner, reseller",
        "base_url": "",
        "listing_model": "distributor",
        "submission_mode": "email_outreach",
        "risk_level": "low",
        "notes": "客户真实分销商、代理商、合作伙伴页面。重点是品牌名、官网链接、型号和描述一致性。",
    },
]


def _platform_out(row: SourcePlatform) -> SourcePlatformOut:
    return SourcePlatformOut(
        id=row.id,
        platform_key=row.platform_key,
        name=row.name,
        domain=row.domain,
        source_type=row.source_type,
        regions=row.regions,
        industry_tags=row.industry_tags,
        base_url=row.base_url,
        listing_model=row.listing_model,
        submission_mode=row.submission_mode,
        has_official_api=row.has_official_api,
        risk_level=row.risk_level,
        status=row.status,
        notes=row.notes,
        accounts_count=len(row.accounts),
        connectors_count=len(row.connectors),
    )


def _account_out(row: PlatformAccount) -> PlatformAccountOut:
    return PlatformAccountOut(
        id=row.id,
        platform_id=row.platform_id,
        platform_name=row.platform.name if row.platform else "",
        label=row.label,
        login_identifier=row.login_identifier,
        auth_method=row.auth_method,
        vault_ref=row.vault_ref,
        owner_hint=row.owner_hint,
        scope=row.scope,
        status=row.status,
        risk_level=row.risk_level,
        regions_allowed=row.regions_allowed,
        notes=row.notes,
        last_verified_at=row.last_verified_at,
        last_used_at=row.last_used_at,
    )


def _connector_out(row: PlatformConnector) -> PlatformConnectorOut:
    return PlatformConnectorOut(
        id=row.id,
        platform_id=row.platform_id,
        platform_name=row.platform.name if row.platform else "",
        provider_key=row.provider_key,
        auth_mode=row.auth_mode,
        capabilities=row.capabilities,
        status=row.status,
        env_var=row.env_var,
        notes=row.notes,
        last_verified_at=row.last_verified_at,
    )


def _gap_out(row: BacklinkGap) -> BacklinkGapOut:
    return BacklinkGapOut(
        id=row.id,
        title=row.title or "",
        issue_type=row.issue_type or "competitor_gap",
        source=row.source or "manual",
        source_platform_id=row.source_platform_id or "",
        competitor_name=row.competitor_name,
        referring_domain=row.referring_domain,
        competitor_url=row.competitor_url,
        link_url=row.link_url,
        kind=row.kind or "competitor",
        priority=row.priority or "P2",
        verify_status=row.verify_status or "unverified",
        market_id=row.market_id,
        our_presence=row.our_presence,
        domain_metric=row.domain_metric,
        status=row.status,
        owner_hint=row.owner_hint or "",
        acceptance_criteria=row.acceptance_criteria or "",
        recommended_action=row.recommended_action or "",
        retest_method=row.retest_method or "",
        retest_result=row.retest_result or "",
        result_url=row.result_url or "",
        blocked_reason=row.blocked_reason or "",
        notes=row.notes,
        ai_status=row.ai_status or "untested",
        ai_review=row.ai_review or "",
        evidence=row.evidence or "",
        last_checked_at=row.last_checked_at,
        closed_at=row.closed_at,
        outreach=[OutreachOut.model_validate(o, from_attributes=True) for o in row.outreach],
    )


@router.get("/gaps", response_model=list[BacklinkGapOut])
def list_gaps(
    status: str | None = None,
    verify_status: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BacklinkGapOut]:
    q = (
        db.query(BacklinkGap)
        .options(selectinload(BacklinkGap.outreach))
        .filter(BacklinkGap.tenant_id == user.tenant_id)
    )
    if status:
        q = q.filter(BacklinkGap.status == status)
    if verify_status:
        q = q.filter(BacklinkGap.verify_status == verify_status)
    return [_gap_out(r) for r in q.order_by(BacklinkGap.created_at.desc()).all()]


@router.get("/checker", response_model=LinkCheckerOut)
def link_checker(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> LinkCheckerOut:
    rows = (
        db.query(BacklinkGap)
        .options(selectinload(BacklinkGap.outreach))
        .filter(BacklinkGap.tenant_id == user.tenant_id)
        .order_by(BacklinkGap.created_at.desc())
        .all()
    )
    counts = {key: 0 for key in VERIFY_STATUSES}
    for row in rows:
        key = row.verify_status if row.verify_status in counts else "unverified"
        counts[key] += 1
    return LinkCheckerOut(counts=counts, domain_metric="未测", links=[_gap_out(r) for r in rows])


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
        db.add(SourcePlatform(tenant_id=user.tenant_id, has_official_api=False, status="active", **item))
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


@router.post("/gaps", response_model=BacklinkGapOut, status_code=201)
def create_gap(
    body: BacklinkGapCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BacklinkGapOut:
    if body.kind not in KINDS:
        raise HTTPException(status_code=400, detail="无效链接类型")
    if body.priority not in PRIORITIES:
        raise HTTPException(status_code=400, detail="无效优先级")
    payload = body.model_dump()
    if not payload.get("title"):
        payload["title"] = f"{body.referring_domain} · {('我方曝光' if body.kind == 'inbound' else '竞品机会')}"
    if not payload.get("acceptance_criteria"):
        payload["acceptance_criteria"] = "记录 result_url，并完成 Placement 核验。"
    if not payload.get("retest_method"):
        payload["retest_method"] = "复查 result_url 是否可访问、是否提及客户、是否链接到目标页。"
    row = BacklinkGap(
        tenant_id=user.tenant_id,
        domain_metric="untested",
        status="identified",
        verify_status="unverified",
        **payload,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    row.outreach = []
    return _gap_out(row)


@router.patch("/gaps/{gap_id}", response_model=BacklinkGapOut)
def update_gap(
    gap_id: str,
    status: str | None = None,
    body: BacklinkGapUpdate = BacklinkGapUpdate(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BacklinkGapOut:
    row = db.get(BacklinkGap, gap_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="缺口不存在")
    payload = body.model_dump(exclude_unset=True)
    next_status = status or payload.get("status")
    if next_status:
        if next_status not in GAP_STATUSES:
            raise HTTPException(status_code=400, detail="无效缺口状态")
        row.status = next_status
        row.closed_at = datetime.now(timezone.utc) if next_status in {"closed", "ignored", "won"} else None
    if "verify_status" in payload:
        if payload["verify_status"] not in VERIFY_STATUSES:
            raise HTTPException(status_code=400, detail="无效核验状态")
        row.verify_status = payload["verify_status"]
        row.last_checked_at = datetime.now(timezone.utc)
    if "notes" in payload:
        row.notes = payload["notes"]
    if "link_url" in payload:
        row.link_url = payload["link_url"]
    if "kind" in payload:
        if payload["kind"] not in KINDS:
            raise HTTPException(status_code=400, detail="无效链接类型")
        row.kind = payload["kind"]
    if "priority" in payload:
        if payload["priority"] not in PRIORITIES:
            raise HTTPException(status_code=400, detail="无效优先级")
        row.priority = payload["priority"]
    for field in (
        "title",
        "issue_type",
        "source",
        "source_platform_id",
        "owner_hint",
        "acceptance_criteria",
        "recommended_action",
        "retest_method",
        "retest_result",
        "result_url",
        "blocked_reason",
    ):
        if field in payload:
            setattr(row, field, payload[field] or "")
    db.commit()
    row = (
        db.query(BacklinkGap)
        .options(selectinload(BacklinkGap.outreach))
        .filter(BacklinkGap.id == gap_id)
        .one()
    )
    return _gap_out(row)


@router.post("/gaps/{gap_id}/outreach", response_model=OutreachOut, status_code=201)
def create_outreach(
    gap_id: str,
    body: OutreachCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OutreachItem:
    gap = db.get(BacklinkGap, gap_id)
    if gap is None or gap.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="缺口不存在")
    row = OutreachItem(
        tenant_id=user.tenant_id,
        gap_id=gap.id,
        status="todo",
        **body.model_dump(),
    )
    db.add(row)
    if gap.status == "identified":
        gap.status = "outreach"
    db.commit()
    db.refresh(row)
    return row


@router.patch("/outreach/{item_id}", response_model=OutreachOut)
def update_outreach(
    item_id: str,
    status: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OutreachItem:
    if status not in OUTREACH_STATUSES:
        raise HTTPException(status_code=400, detail="无效外联状态")
    if status == "sent_manual":
        # Manual outreach only — no auto-blast endpoint exists.
        pass
    row = db.get(OutreachItem, item_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="外联不存在")
    row.status = status
    db.commit()
    db.refresh(row)
    return row


@router.post("/gaps/{gap_id}/ai", response_model=AiAssistOut)
def ai_gap(
    gap_id: str,
    body: AiStepIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiAssistOut:
    row = db.get(BacklinkGap, gap_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="链接不存在")
    payload = assist_offsite_gap(db, row, step=body.step or "evidence")
    db.commit()
    return AiAssistOut(**payload)
