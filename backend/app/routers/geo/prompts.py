from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.ai_engine import assist_geo_prompt
from app.auth import get_current_user
from app.database import get_db
from app.geo_helpers import DIAGNOSES, ENGINES, OBS_STATUSES, ensure_engine_slots
from app.geo_providers import provider_statuses
from app.models import (
    DemandSignal,
    GeoAsset,
    GeoChecklistItem,
    GeoObservation,
    GeoPrompt,
    GeoSampleResult,
    GeoSampleRun,
    GeoTicket,
    Market,
    SeoPage,
    Tenant,
    User,
)
from app.schemas import (
    AiAssistOut,
    AiStepIn,
    GeoDiagnosisIn,
    GeoObservationOut,
    GeoObservationUpdate,
    GeoPromptCreate,
    GeoPromptOut,
    GeoProviderStatusListOut,
    GeoProviderStatusOut,
    GeoSeedOut,
    GeoSummary,
)

from . import router
from .common import (
    _create_untested_slots,
    _evidence_tier,
    _load_prompt,
    _obs_out,
    _prompt_key,
    _prompt_out,
    _prompt_pack_candidates,
    _rate,
)
from .constants import PROMPT_TYPES, RECORDED_OBS


@router.get("/providers/status", response_model=GeoProviderStatusListOut)
def geo_provider_status(user: User = Depends(get_current_user)) -> GeoProviderStatusListOut:
    return GeoProviderStatusListOut(
        providers=[GeoProviderStatusOut(**row.__dict__) for row in provider_statuses()]
    )


@router.get("/summary", response_model=GeoSummary)
def geo_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GeoSummary:
    tid = user.tenant_id
    observations = db.query(GeoObservation).filter(GeoObservation.tenant_id == tid).all()
    recorded_rows = [o for o in observations if o.status in RECORDED_OBS]
    mentioned_rows = [o for o in recorded_rows if _evidence_tier(o) in {"mentioned", "cited", "verified"}]
    cited_rows = [o for o in recorded_rows if _evidence_tier(o) in {"cited", "verified"}]
    verified_rows = [o for o in recorded_rows if _evidence_tier(o) == "verified"]
    competitor_rows = [o for o in recorded_rows if (o.competitor_mentions or "").strip()]
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
    sample_runs = db.query(func.count(GeoSampleRun.id)).filter(GeoSampleRun.tenant_id == tid).scalar() or 0
    evidence_results = db.query(func.count(GeoSampleResult.id)).filter(GeoSampleResult.tenant_id == tid).scalar() or 0
    latest_run = (
        db.query(GeoSampleRun)
        .filter(GeoSampleRun.tenant_id == tid)
        .order_by(GeoSampleRun.started_at.desc())
        .first()
    )
    return GeoSummary(
        prompts=prompts,
        untested=untested,
        recorded=recorded,
        checklist_untested=check_untested,
        assets_draft=assets_draft,
        tickets_open=tickets_open,
        mention_rate=_rate(len(mentioned_rows), len(recorded_rows)),
        cite_rate=_rate(len(cited_rows), len(recorded_rows)),
        verified_citation_rate=_rate(len(verified_rows), len(recorded_rows)),
        competitor_rate=_rate(len(competitor_rows), len(recorded_rows)),
        absorption_rate=_rate(len(mentioned_rows), len(recorded_rows)),
        competitor_mentions=len(competitor_rows),
        sample_runs=sample_runs,
        evidence_results=evidence_results,
        latest_run_id=latest_run.id if latest_run else None,
        latest_run_at=latest_run.started_at if latest_run else None,
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
    if body.prompt_type not in PROMPT_TYPES:
        raise HTTPException(status_code=400, detail="无效问句类型")
    row = GeoPrompt(tenant_id=user.tenant_id, diagnosis="untested", **body.model_dump())
    db.add(row)
    db.flush()
    _create_untested_slots(db, user, row)
    db.commit()
    return _prompt_out(_load_prompt(db, row.id))


@router.post("/prompt-panel/seed", response_model=GeoSeedOut)
def seed_prompt_panel(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GeoSeedOut:
    existing = {
        _prompt_key(p.prompt_text, p.locale)
        for p in db.query(GeoPrompt).filter(GeoPrompt.tenant_id == user.tenant_id).all()
    }
    created = skipped = 0
    candidates: list[dict[str, str | None]] = []
    tenant = db.get(Tenant, user.tenant_id)
    seo_pages = db.query(SeoPage).filter(SeoPage.tenant_id == user.tenant_id).order_by(SeoPage.created_at.desc()).limit(12).all()
    for page in seo_pages:
        keyword = (page.target_keyword or page.title or "").strip()
        if not keyword:
            continue
        market = db.get(Market, page.market_id) if page.market_id else None
        candidates.extend(
            _prompt_pack_candidates(
                db,
                user,
                tenant=tenant,
                market=market,
                keyword=keyword,
                locale=page.locale,
                seo_page_id=page.id,
                limit_per_source=20,
            )
        )
    signals = (
        db.query(DemandSignal)
        .filter(
            DemandSignal.tenant_id == user.tenant_id,
            DemandSignal.source != "target_archived",
        )
        .order_by(DemandSignal.created_at.desc())
        .limit(12)
        .all()
    )
    for signal in signals:
        theme = (signal.theme or "").strip()
        if not theme:
            continue
        market = db.get(Market, signal.market_id) if signal.market_id else None
        candidates.extend(
            _prompt_pack_candidates(
                db,
                user,
                tenant=tenant,
                market=market,
                keyword=theme,
                locale=signal.locale,
                demand_signal_id=signal.id,
                limit_per_source=20,
            )
        )
    if not candidates:
        total = db.query(func.count(GeoPrompt.id)).filter(GeoPrompt.tenant_id == user.tenant_id).scalar() or 0
        return GeoSeedOut(created=0, skipped=0, prompts=total, note="没有可生成问句的 SEO 目标。请先在首页配置目标关键词，或在 SEO 选题里登记 target keyword。")
    for item in candidates:
        key = _prompt_key(str(item["prompt_text"]), str(item["locale"]))
        if key in existing:
            skipped += 1
            continue
        row = GeoPrompt(tenant_id=user.tenant_id, diagnosis="untested", **item)
        db.add(row)
        db.flush()
        _create_untested_slots(db, user, row)
        existing.add(key)
        created += 1
        if created >= 20:
            break
    db.commit()
    total = db.query(func.count(GeoPrompt.id)).filter(GeoPrompt.tenant_id == user.tenant_id).scalar() or 0
    note = "已按出口 B2B GEO 观测包生成 branded/category/competitor/task 问句。"
    if created == 0 and skipped > 0:
        note = "这些 SEO 目标已经生成过问句，本次没有新增。"
    return GeoSeedOut(created=created, skipped=skipped, prompts=total, note=note)


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
    if body.surface is not None:
        row.surface = body.surface
    if body.sample_type is not None:
        row.sample_type = body.sample_type
    if body.response_excerpt is not None:
        row.response_excerpt = body.response_excerpt
    if body.citation_urls is not None:
        row.citation_urls = body.citation_urls
    if body.brand_mentions is not None:
        row.brand_mentions = body.brand_mentions
    if body.competitor_mentions is not None:
        row.competitor_mentions = body.competitor_mentions
    if body.interpretation_note is not None:
        row.interpretation_note = body.interpretation_note
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


@router.post("/prompts/{prompt_id}/ai", response_model=AiAssistOut)
def ai_prompt(
    prompt_id: str,
    body: AiStepIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiAssistOut:
    row = (
        db.query(GeoPrompt)
        .options(selectinload(GeoPrompt.observations))
        .filter(GeoPrompt.id == prompt_id, GeoPrompt.tenant_id == user.tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="问句不存在")
    payload = assist_geo_prompt(db, row, step=body.step)
    db.commit()
    return AiAssistOut(**payload)
