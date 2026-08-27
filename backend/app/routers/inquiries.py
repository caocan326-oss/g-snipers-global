from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import GeoPrompt, Inquiry, User
from app.schemas import InquiryCreate, InquiryOut, InquiryPatch

router = APIRouter(prefix="/api/inquiries", tags=["inquiries"])

QUALITIES = {"unreviewed", "qualified", "disqualified"}


def _prompt_for_tenant(db: Session, tenant_id: str, prompt_id: str | None) -> GeoPrompt | None:
    if not prompt_id:
        return None
    prompt = db.get(GeoPrompt, prompt_id)
    if prompt is None or prompt.tenant_id != tenant_id:
        raise HTTPException(status_code=400, detail="只能挂本户已记的买家问句。不要编。")
    return prompt


def _inquiry_out(row: Inquiry, db: Session) -> InquiryOut:
    prompt = db.get(GeoPrompt, row.related_prompt_id) if row.related_prompt_id else None
    text = prompt.prompt_text if prompt and prompt.tenant_id == row.tenant_id else ""
    return InquiryOut(
        id=row.id,
        source=row.source,
        contact=row.contact,
        quality=row.quality,
        related_seo_page_id=row.related_seo_page_id,
        related_work_order_id=row.related_work_order_id,
        related_market_id=row.related_market_id,
        related_prompt_id=row.related_prompt_id,
        related_prompt_text=text,
        notes=row.notes,
        created_at=row.created_at,
    )


@router.get("", response_model=list[InquiryOut])
def list_inquiries(
    quality: str | None = None,
    source: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InquiryOut]:
    q = db.query(Inquiry).filter(Inquiry.tenant_id == user.tenant_id)
    if quality:
        q = q.filter(Inquiry.quality == quality)
    if source:
        q = q.filter(Inquiry.source == source)
    return [_inquiry_out(row, db) for row in q.order_by(Inquiry.created_at.desc()).all()]


@router.post("", response_model=InquiryOut, status_code=201)
def create_inquiry(
    body: InquiryCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InquiryOut:
    if body.quality not in QUALITIES:
        raise HTTPException(status_code=400, detail="无效质量标记")
    _prompt_for_tenant(db, user.tenant_id, body.related_prompt_id)
    payload = body.model_dump()
    row = Inquiry(tenant_id=user.tenant_id, **payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _inquiry_out(row, db)


@router.get("/{inquiry_id}", response_model=InquiryOut)
def get_inquiry(
    inquiry_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InquiryOut:
    row = db.get(Inquiry, inquiry_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="询盘不存在")
    return _inquiry_out(row, db)


@router.patch("/{inquiry_id}", response_model=InquiryOut)
def update_inquiry(
    inquiry_id: str,
    body: InquiryPatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InquiryOut:
    row = db.get(Inquiry, inquiry_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="询盘不存在")
    payload = body.model_dump(exclude_unset=True)
    if "quality" in payload and payload["quality"] not in QUALITIES:
        raise HTTPException(status_code=400, detail="无效质量标记")
    if "related_prompt_id" in payload:
        _prompt_for_tenant(db, user.tenant_id, payload["related_prompt_id"])
    for key, value in payload.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return _inquiry_out(row, db)
