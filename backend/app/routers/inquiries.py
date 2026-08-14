from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Inquiry, User
from app.schemas import InquiryCreate, InquiryOut

router = APIRouter(prefix="/api/inquiries", tags=["inquiries"])

QUALITIES = {"unreviewed", "qualified", "disqualified"}


@router.get("", response_model=list[InquiryOut])
def list_inquiries(
    quality: str | None = None,
    source: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Inquiry]:
    q = db.query(Inquiry).filter(Inquiry.tenant_id == user.tenant_id)
    if quality:
        q = q.filter(Inquiry.quality == quality)
    if source:
        q = q.filter(Inquiry.source == source)
    return q.order_by(Inquiry.created_at.desc()).all()


@router.post("", response_model=InquiryOut, status_code=201)
def create_inquiry(
    body: InquiryCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Inquiry:
    if body.quality not in QUALITIES:
        raise HTTPException(status_code=400, detail="无效质量标记")
    row = Inquiry(tenant_id=user.tenant_id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{inquiry_id}", response_model=InquiryOut)
def get_inquiry(
    inquiry_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Inquiry:
    row = db.get(Inquiry, inquiry_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="询盘不存在")
    return row


@router.patch("/{inquiry_id}", response_model=InquiryOut)
def update_inquiry(
    inquiry_id: str,
    body: InquiryCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Inquiry:
    row = db.get(Inquiry, inquiry_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="询盘不存在")
    if body.quality not in QUALITIES:
        raise HTTPException(status_code=400, detail="无效质量标记")
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row
