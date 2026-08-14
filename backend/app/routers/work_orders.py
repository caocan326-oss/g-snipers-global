from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User, WorkOrder
from app.schemas import WorkOrderCreate, WorkOrderOut, WorkOrderStatusIn, WorkOrderUpdate

router = APIRouter(prefix="/api/work-orders", tags=["work-orders"])

TYPES = {"insight", "seo_outline", "seo_draft", "seo_meta", "other"}
STATUSES = {"open", "claimed", "in_progress", "done", "blocked"}


def _owned(db: Session, user: User, order_id: str) -> WorkOrder:
    row = db.get(WorkOrder, order_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="工单不存在")
    return row


@router.get("", response_model=list[WorkOrderOut])
def list_orders(
    status: str | None = None,
    type: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WorkOrder]:
    q = db.query(WorkOrder).filter(WorkOrder.tenant_id == user.tenant_id)
    if status:
        q = q.filter(WorkOrder.status == status)
    if type:
        q = q.filter(WorkOrder.type == type)
    return q.order_by(WorkOrder.created_at.desc()).all()


@router.post("", response_model=WorkOrderOut, status_code=201)
def create_order(
    body: WorkOrderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkOrder:
    if body.type not in TYPES:
        raise HTTPException(status_code=400, detail="无效工单类型")
    row = WorkOrder(tenant_id=user.tenant_id, status="open", **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{order_id}", response_model=WorkOrderOut)
def get_order(
    order_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkOrder:
    return _owned(db, user, order_id)


@router.patch("/{order_id}", response_model=WorkOrderOut)
def update_order(
    order_id: str,
    body: WorkOrderUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkOrder:
    row = _owned(db, user, order_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("type") and data["type"] not in TYPES:
        raise HTTPException(status_code=400, detail="无效工单类型")
    if data.get("status") and data["status"] not in STATUSES:
        raise HTTPException(status_code=400, detail="无效工单状态")
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@router.post("/{order_id}/claim", response_model=WorkOrderOut)
def claim_order(
    order_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkOrder:
    row = _owned(db, user, order_id)
    if row.status not in {"open", "blocked"}:
        raise HTTPException(status_code=400, detail="仅待领取或受阻工单可领取")
    row.assignee_id = user.id
    row.status = "claimed"
    db.commit()
    db.refresh(row)
    return row


@router.post("/{order_id}/status", response_model=WorkOrderOut)
def change_status(
    order_id: str,
    body: WorkOrderStatusIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkOrder:
    if body.status not in STATUSES:
        raise HTTPException(status_code=400, detail="无效工单状态")
    row = _owned(db, user, order_id)
    row.status = body.status
    if body.status == "claimed" and row.assignee_id is None:
        row.assignee_id = user.id
    db.commit()
    db.refresh(row)
    return row
