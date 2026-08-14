from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import BacklinkGap, OutreachItem, User
from app.schemas import BacklinkGapCreate, BacklinkGapOut, OutreachCreate, OutreachOut

router = APIRouter(prefix="/api/offsite", tags=["offsite"])

GAP_STATUSES = {"identified", "outreach", "replied", "won", "lost", "skipped"}
OUTREACH_STATUSES = {"todo", "sent_manual", "replied", "closed"}


def _gap_out(row: BacklinkGap) -> BacklinkGapOut:
    return BacklinkGapOut(
        id=row.id,
        competitor_name=row.competitor_name,
        referring_domain=row.referring_domain,
        competitor_url=row.competitor_url,
        market_id=row.market_id,
        our_presence=row.our_presence,
        domain_metric=row.domain_metric,
        status=row.status,
        notes=row.notes,
        outreach=[OutreachOut.model_validate(o, from_attributes=True) for o in row.outreach],
    )


@router.get("/gaps", response_model=list[BacklinkGapOut])
def list_gaps(
    status: str | None = None,
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
    return [_gap_out(r) for r in q.order_by(BacklinkGap.created_at.desc()).all()]


@router.post("/gaps", response_model=BacklinkGapOut, status_code=201)
def create_gap(
    body: BacklinkGapCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BacklinkGapOut:
    row = BacklinkGap(
        tenant_id=user.tenant_id,
        domain_metric="untested",
        status="identified",
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
    status: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BacklinkGapOut:
    if status not in GAP_STATUSES:
        raise HTTPException(status_code=400, detail="无效缺口状态")
    row = db.get(BacklinkGap, gap_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="缺口不存在")
    row.status = status
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
