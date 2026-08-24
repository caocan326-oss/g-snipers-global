from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.ai_engine import assist_geo_ticket
from app.auth import get_current_user
from app.database import get_db
from app.geo_helpers import DIAGNOSES, TICKET_STATUSES
from app.geo_loop import (
    HANDOFFS,
    latest_prompt_rows,
    prompt_sample_tally,
    reconcile_open_ticket_status,
    refresh_open_tickets_from_samples,
    set_ticket_handoff,
    set_ticket_offsite_url,
    ticket_handoff,
    ticket_live_url,
)
from app.models import GeoPrompt, GeoTicket, Tenant, User
from app.risk import require_confirm
from app.schemas import (
    AiAssistOut,
    AiStepIn,
    GeoTicketCreate,
    GeoTicketHandoffIn,
    GeoTicketOffsiteIn,
    GeoTicketOut,
    GeoTicketVerifyIn,
)
from app.site_identity import adopt_live_site

from . import router
from .common import _ticket_out


@router.get("/tickets", response_model=list[GeoTicketOut])
def list_tickets(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[GeoTicketOut]:
    tenant = db.get(Tenant, user.tenant_id)
    cleaned = adopt_live_site(db, tenant) if tenant is not None else ""
    refreshed = refresh_open_tickets_from_samples(db, user.tenant_id) or reconcile_open_ticket_status(db, user.tenant_id)
    if cleaned or refreshed:
        db.commit()
    by_prompt = latest_prompt_rows(db, user.tenant_id)
    rows = (
        db.query(GeoTicket)
        .options(selectinload(GeoTicket.prompt))
        .filter(GeoTicket.tenant_id == user.tenant_id)
        .order_by(GeoTicket.created_at.desc())
        .all()
    )
    return [
        _ticket_out(
            r,
            sample_note=prompt_sample_tally(by_prompt.get(r.prompt_id, []), r.prompt),
        )
        for r in rows
    ]


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
        priority=body.priority,
        owner_hint=body.owner_hint,
        recommended_action=body.recommended_action,
        retest_method=body.retest_method,
        status="open",
    )
    db.add(row)
    if prompt.diagnosis == "untested" and body.diagnosis != "untested":
        prompt.diagnosis = body.diagnosis
    db.commit()
    db.refresh(row)
    return _ticket_out(row)


@router.post("/tickets/{ticket_id}/handoff", response_model=GeoTicketOut)
def mark_ticket_handoff(
    ticket_id: str,
    body: GeoTicketHandoffIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoTicketOut:
    if body.handoff not in HANDOFFS:
        raise HTTPException(status_code=400, detail="无效进度。只能记：已写改法、已发给客户、客户已上线。")
    row = db.get(GeoTicket, ticket_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="整改项不存在")
    try:
        set_ticket_handoff(row, body.handoff, live_url=body.result_url or "")
    except ValueError as exc:
        if str(exc) == "live_url":
            raise HTTPException(
                status_code=400,
                detail="请先填写客户已上线的页或帖地址（http/https）。没有地址不能记第三档，也不能再测。",
            ) from exc
        raise
    if body.note:
        row.verified_note = body.note
    row.last_checked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _ticket_out(row)


@router.post("/tickets/{ticket_id}/offsite", response_model=GeoTicketOut)
def mark_ticket_offsite(
    ticket_id: str,
    body: GeoTicketOffsiteIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoTicketOut:
    row = db.get(GeoTicket, ticket_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="整改项不存在")
    try:
        set_ticket_offsite_url(row, body.post_url or "")
    except ValueError as exc:
        if str(exc) == "offsite_url":
            raise HTTPException(
                status_code=400,
                detail="请先填写已发出的帖子地址（http/https）。我们不代发，只记下客户自己发完的链接。",
            ) from exc
        raise
    row.last_checked_at = datetime.now(timezone.utc)
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
    require_confirm(body.confirmed, action="验收 GEO 整改项")
    row = db.get(GeoTicket, ticket_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="整改项不存在")
    if ticket_handoff(row) != "live" or not ticket_live_url(row):
        raise HTTPException(
            status_code=400,
            detail="还没到验收：先记下客户页或帖的地址，再测同一问。工作台打勾不算官网已改。",
        )
    row.status = "done"
    row.verified_note = body.note or "客户经理已按验收标准人工复核。"
    row.closed_at = datetime.now(timezone.utc)
    row.last_checked_at = datetime.now(timezone.utc)
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
        raise HTTPException(status_code=404, detail="整改项不存在")
    if row.status not in TICKET_STATUSES:
        raise HTTPException(status_code=400, detail="无效整改项状态")
    row.status = "reopened"
    row.closed_at = None
    if body.note:
        row.verified_note = body.note
    db.commit()
    db.refresh(row)
    return _ticket_out(row)


@router.post("/tickets/{ticket_id}/ai", response_model=AiAssistOut)
def ai_ticket(
    ticket_id: str,
    body: AiStepIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiAssistOut:
    row = db.get(GeoTicket, ticket_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="整改项不存在")
    payload = assist_geo_ticket(db, row, step=body.step or "review")
    db.commit()
    return AiAssistOut(**payload)
