from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.ai_engine import assist_offsite_gap
from app.auth import get_current_user
from app.database import get_db
from app.models import BacklinkGap, OutreachItem, User
from app.schemas import (
    AiAssistOut,
    AiStepIn,
    BacklinkGapCreate,
    BacklinkGapOut,
    BacklinkGapUpdate,
    LinkCheckerOut,
    OutreachCreate,
    OutreachOut,
)

router = APIRouter(prefix="/api/offsite", tags=["offsite"])

GAP_STATUSES = {"identified", "outreach", "replied", "won", "lost", "skipped"}
OUTREACH_STATUSES = {"todo", "sent_manual", "replied", "closed"}
VERIFY_STATUSES = {"unverified", "valid", "dead", "spam"}
KINDS = {"inbound", "competitor"}


def _gap_out(row: BacklinkGap) -> BacklinkGapOut:
    return BacklinkGapOut(
        id=row.id,
        competitor_name=row.competitor_name,
        referring_domain=row.referring_domain,
        competitor_url=row.competitor_url,
        link_url=row.link_url,
        kind=row.kind or "competitor",
        verify_status=row.verify_status or "unverified",
        market_id=row.market_id,
        our_presence=row.our_presence,
        domain_metric=row.domain_metric,
        status=row.status,
        notes=row.notes,
        ai_status=row.ai_status or "untested",
        ai_review=row.ai_review or "",
        evidence=row.evidence or "",
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


@router.post("/gaps", response_model=BacklinkGapOut, status_code=201)
def create_gap(
    body: BacklinkGapCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BacklinkGapOut:
    if body.kind not in KINDS:
        raise HTTPException(status_code=400, detail="无效链接类型")
    row = BacklinkGap(
        tenant_id=user.tenant_id,
        domain_metric="untested",
        status="identified",
        verify_status="unverified",
        **body.model_dump(),
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
    if "verify_status" in payload:
        if payload["verify_status"] not in VERIFY_STATUSES:
            raise HTTPException(status_code=400, detail="无效核验状态")
        row.verify_status = payload["verify_status"]
    if "notes" in payload:
        row.notes = payload["notes"]
    if "link_url" in payload:
        row.link_url = payload["link_url"]
    if "kind" in payload:
        if payload["kind"] not in KINDS:
            raise HTTPException(status_code=400, detail="无效链接类型")
        row.kind = payload["kind"]
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
