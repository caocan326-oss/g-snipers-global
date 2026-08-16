from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai_engine import assist_geo_ticket
from app.auth import get_current_user
from app.database import get_db
from app.geo_helpers import DIAGNOSES, TICKET_STATUSES
from app.models import GeoPrompt, GeoTicket, User
from app.risk import require_confirm
from app.schemas import AiAssistOut, AiStepIn, GeoTicketCreate, GeoTicketOut, GeoTicketVerifyIn

from . import router
from .common import _ticket_out


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
