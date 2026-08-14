from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.geo_helpers import (
    CHECKLIST_DEFS,
    CHECK_STATUSES,
    DIAGNOSES,
    ENGINES,
    ENGINE_LABELS,
    OBS_STATUSES,
    TICKET_STATUSES,
    build_llms_txt,
    engine_region,
    ensure_engine_slots,
)
from app.models import (
    DemandSignal,
    GeoAsset,
    GeoChecklistItem,
    GeoObservation,
    GeoPrompt,
    GeoTicket,
    SeoPage,
    Tenant,
    User,
)
from app.risk import require_confirm
from app.schemas import (
    ConfirmReadyIn,
    GeoAssetOut,
    GeoAssetUpdate,
    GeoChecklistItemOut,
    GeoChecklistItemUpdate,
    GeoDiagnosisIn,
    GeoObservationOut,
    GeoObservationUpdate,
    GeoPromptCreate,
    GeoPromptOut,
    GeoSummary,
    GeoTicketCreate,
    GeoTicketOut,
    GeoTicketVerifyIn,
)

router = APIRouter(prefix="/api/geo", tags=["geo"])


def _obs_out(o: GeoObservation) -> GeoObservationOut:
    return GeoObservationOut(
        id=o.id,
        prompt_id=o.prompt_id,
        engine=o.engine,
        engine_label=ENGINE_LABELS.get(o.engine, o.engine),
        region=engine_region(o.engine),
        status=o.status,
        notes=o.notes,
        observed_at=o.observed_at,
    )


def _prompt_out(row: GeoPrompt) -> GeoPromptOut:
    diagnosis = row.diagnosis or "untested"
    return GeoPromptOut(
        id=row.id,
        prompt_text=row.prompt_text,
        locale=row.locale,
        market_id=row.market_id,
        seo_page_id=row.seo_page_id,
        demand_signal_id=row.demand_signal_id,
        diagnosis=diagnosis,
        diagnosis_label=DIAGNOSES.get(diagnosis, diagnosis),
        created_at=row.created_at,
        observations=[_obs_out(o) for o in row.observations],
        cite_rate="未测",
        absorption_rate="未测",
    )


def _ticket_out(row: GeoTicket) -> GeoTicketOut:
    return GeoTicketOut(
        id=row.id,
        prompt_id=row.prompt_id,
        title=row.title,
        diagnosis=row.diagnosis,
        diagnosis_label=DIAGNOSES.get(row.diagnosis, row.diagnosis),
        rationale=row.rationale,
        acceptance_criteria=row.acceptance_criteria,
        status=row.status,
        verified_note=row.verified_note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _create_untested_slots(db: Session, user: User, prompt: GeoPrompt) -> None:
    for engine in ENGINES:
        db.add(
            GeoObservation(
                tenant_id=user.tenant_id,
                prompt_id=prompt.id,
                engine=engine,
                status="untested",
            )
        )


def _load_prompt(db: Session, prompt_id: str) -> GeoPrompt:
    return (
        db.query(GeoPrompt)
        .options(selectinload(GeoPrompt.observations))
        .filter(GeoPrompt.id == prompt_id)
        .one()
    )


@router.get("/summary", response_model=GeoSummary)
def geo_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GeoSummary:
    tid = user.tenant_id
    prompts = db.query(func.count(GeoPrompt.id)).filter(GeoPrompt.tenant_id == tid).scalar() or 0
    untested = (
        db.query(func.count(GeoObservation.id))
        .filter(GeoObservation.tenant_id == tid, GeoObservation.status == "untested")
        .scalar()
        or 0
    )
    recorded = (
        db.query(func.count(GeoObservation.id))
        .filter(GeoObservation.tenant_id == tid, GeoObservation.status != "untested")
        .scalar()
        or 0
    )
    check_untested = (
        db.query(func.count(GeoChecklistItem.id))
        .filter(GeoChecklistItem.tenant_id == tid, GeoChecklistItem.status == "untested")
        .scalar()
        or 0
    )
    assets_draft = (
        db.query(func.count(GeoAsset.id)).filter(GeoAsset.tenant_id == tid, GeoAsset.status == "draft").scalar() or 0
    )
    tickets_open = (
        db.query(func.count(GeoTicket.id))
        .filter(GeoTicket.tenant_id == tid, GeoTicket.status.in_(["open", "in_progress", "verify", "reopened"]))
        .scalar()
        or 0
    )
    return GeoSummary(
        prompts=prompts,
        untested=untested,
        recorded=recorded,
        checklist_untested=check_untested,
        assets_draft=assets_draft,
        tickets_open=tickets_open,
        cite_rate="未测",
    )


@router.get("/prompts", response_model=list[GeoPromptOut])
def list_prompts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GeoPromptOut]:
    rows = (
        db.query(GeoPrompt)
        .options(selectinload(GeoPrompt.observations))
        .filter(GeoPrompt.tenant_id == user.tenant_id)
        .order_by(GeoPrompt.created_at.desc())
        .all()
    )
    dirty = False
    for row in rows:
        existing = {o.engine for o in row.observations}
        if any(engine not in existing for engine in ENGINES):
            ensure_engine_slots(db, user.tenant_id, row)
            dirty = True
    if dirty:
        db.commit()
        rows = (
            db.query(GeoPrompt)
            .options(selectinload(GeoPrompt.observations))
            .filter(GeoPrompt.tenant_id == user.tenant_id)
            .order_by(GeoPrompt.created_at.desc())
            .all()
        )
    return [_prompt_out(r) for r in rows]


@router.post("/prompts", response_model=GeoPromptOut, status_code=201)
def create_prompt(
    body: GeoPromptCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoPromptOut:
    row = GeoPrompt(tenant_id=user.tenant_id, diagnosis="untested", **body.model_dump())
    db.add(row)
    db.flush()
    _create_untested_slots(db, user, row)
    db.commit()
    return _prompt_out(_load_prompt(db, row.id))


@router.patch("/prompts/{prompt_id}/diagnosis", response_model=GeoPromptOut)
def set_diagnosis(
    prompt_id: str,
    body: GeoDiagnosisIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoPromptOut:
    if body.diagnosis not in DIAGNOSES:
        raise HTTPException(status_code=400, detail="无效诊断层")
    row = db.get(GeoPrompt, prompt_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="问句不存在")
    row.diagnosis = body.diagnosis
    db.commit()
    return _prompt_out(_load_prompt(db, row.id))


@router.patch("/observations/{obs_id}", response_model=GeoObservationOut)
def record_observation(
    obs_id: str,
    body: GeoObservationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoObservationOut:
    if body.status not in OBS_STATUSES:
        raise HTTPException(status_code=400, detail="无效观测状态")
    row = db.get(GeoObservation, obs_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="观测不存在")
    row.status = body.status
    row.notes = body.notes
    if body.status == "untested":
        row.observed_at = None
        row.observed_by = None
    else:
        row.observed_at = datetime.now(timezone.utc)
        row.observed_by = user.id
    db.commit()
    db.refresh(row)
    return _obs_out(row)


@router.get("/tickets", response_model=list[GeoTicketOut])
def list_tickets(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[GeoTicketOut]:
    rows = (
        db.query(GeoTicket)
        .filter(GeoTicket.tenant_id == user.tenant_id)
        .order_by(GeoTicket.created_at.desc())
        .all()
    )
    return [_ticket_out(r) for r in rows]


@router.post("/tickets", response_model=GeoTicketOut, status_code=201)
def create_ticket(
    body: GeoTicketCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoTicketOut:
    prompt = db.get(GeoPrompt, body.prompt_id)
    if prompt is None or prompt.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="问句不存在")
    if body.diagnosis not in DIAGNOSES:
        raise HTTPException(status_code=400, detail="无效诊断层")
    row = GeoTicket(
        tenant_id=user.tenant_id,
        prompt_id=prompt.id,
        title=body.title,
        diagnosis=body.diagnosis,
        rationale=body.rationale,
        acceptance_criteria=body.acceptance_criteria,
        status="open",
    )
    db.add(row)
    if prompt.diagnosis == "untested" and body.diagnosis != "untested":
        prompt.diagnosis = body.diagnosis
    db.commit()
    db.refresh(row)
    return _ticket_out(row)


@router.post("/tickets/{ticket_id}/verify", response_model=GeoTicketOut)
def verify_ticket(
    ticket_id: str,
    body: GeoTicketVerifyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoTicketOut:
    require_confirm(body.confirmed, action="验收 GEO 工单")
    row = db.get(GeoTicket, ticket_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="工单不存在")
    row.status = "done"
    row.verified_note = body.note or "客户经理已按验收标准人工复核。"
    db.commit()
    db.refresh(row)
    return _ticket_out(row)


@router.post("/tickets/{ticket_id}/reopen", response_model=GeoTicketOut)
def reopen_ticket(
    ticket_id: str,
    body: GeoTicketVerifyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoTicketOut:
    row = db.get(GeoTicket, ticket_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="工单不存在")
    if row.status not in TICKET_STATUSES:
        raise HTTPException(status_code=400, detail="无效工单状态")
    row.status = "reopened"
    if body.note:
        row.verified_note = body.note
    db.commit()
    db.refresh(row)
    return _ticket_out(row)


@router.get("/assets", response_model=list[GeoAssetOut])
def list_assets(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[GeoAsset]:
    return db.query(GeoAsset).filter(GeoAsset.tenant_id == user.tenant_id).all()


@router.post("/assets/llms.txt/generate", response_model=GeoAssetOut)
def generate_llms_txt(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GeoAsset:
    tenant = db.get(Tenant, user.tenant_id)
    pages = db.query(SeoPage).filter(SeoPage.tenant_id == user.tenant_id).all()
    body = build_llms_txt(tenant, pages) if tenant else ""
    asset = db.query(GeoAsset).filter(GeoAsset.tenant_id == user.tenant_id, GeoAsset.kind == "llms_txt").first()
    if asset is None:
        asset = GeoAsset(tenant_id=user.tenant_id, kind="llms_txt", title="llms.txt 草稿")
        db.add(asset)
    asset.body = body
    asset.status = "draft"
    asset.updated_by = user.id
    db.commit()
    db.refresh(asset)
    return asset


@router.patch("/assets/{asset_id}", response_model=GeoAssetOut)
def update_asset(
    asset_id: str,
    body: GeoAssetUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoAsset:
    asset = db.get(GeoAsset, asset_id)
    if asset is None or asset.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="资产不存在")
    asset.body = body.body
    asset.status = "draft"
    asset.updated_by = user.id
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/assets/{asset_id}/mark-ready", response_model=GeoAssetOut)
def mark_asset_ready(
    asset_id: str,
    body: ConfirmReadyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoAsset:
    if not body.confirmed:
        raise HTTPException(status_code=400, detail="需要客户经理人工确认后才能标记可交付")
    asset = db.get(GeoAsset, asset_id)
    if asset is None or asset.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="资产不存在")
    if not asset.body.strip():
        raise HTTPException(status_code=400, detail="正文为空，不能标记可交付")
    asset.status = "ready"
    asset.updated_by = user.id
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/checklists/ensure", response_model=list[GeoChecklistItemOut])
def ensure_checklist(
    seo_page_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GeoChecklistItem]:
    page = db.get(SeoPage, seo_page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="选题不存在")
    existing = {
        i.item_key: i
        for i in db.query(GeoChecklistItem).filter(GeoChecklistItem.seo_page_id == seo_page_id).all()
    }
    for key, label in CHECKLIST_DEFS:
        if key not in existing:
            db.add(
                GeoChecklistItem(
                    tenant_id=user.tenant_id,
                    seo_page_id=seo_page_id,
                    item_key=key,
                    label=label,
                    status="untested",
                )
            )
    db.commit()
    return (
        db.query(GeoChecklistItem)
        .filter(GeoChecklistItem.seo_page_id == seo_page_id)
        .order_by(GeoChecklistItem.item_key)
        .all()
    )


@router.patch("/checklist-items/{item_id}", response_model=GeoChecklistItemOut)
def update_checklist_item(
    item_id: str,
    body: GeoChecklistItemUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoChecklistItem:
    if body.status not in CHECK_STATUSES:
        raise HTTPException(status_code=400, detail="无效清单状态")
    row = db.get(GeoChecklistItem, item_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="清单项不存在")
    row.status = body.status
    row.notes = body.notes
    db.commit()
    db.refresh(row)
    return row


@router.post("/from-demand-signal/{signal_id}", response_model=GeoPromptOut, status_code=201)
def prompt_from_signal(
    signal_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoPromptOut:
    signal = db.get(DemandSignal, signal_id)
    if signal is None or signal.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="需求信号不存在")
    row = GeoPrompt(
        tenant_id=user.tenant_id,
        market_id=signal.market_id,
        demand_signal_id=signal.id,
        prompt_text=signal.theme,
        locale=signal.locale,
        diagnosis="untested",
    )
    db.add(row)
    db.flush()
    _create_untested_slots(db, user, row)
    db.commit()
    return _prompt_out(_load_prompt(db, row.id))
