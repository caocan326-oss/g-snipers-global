from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.content_templates import generate_draft, generate_meta, generate_outline
from app.database import get_db
from app.models import Market, PublishConfirmation, SeoPage, User
from app.schemas import ConfirmReadyIn, SeoPageCreate, SeoPageOut, SeoPageUpdate

router = APIRouter(prefix="/api/seo-pages", tags=["seo"])

SEO_STATUSES = {"idea", "outline", "draft", "meta", "review", "ready"}


def _owned_page(db: Session, user: User, page_id: str) -> SeoPage:
    page = db.get(SeoPage, page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="选题不存在")
    return page


@router.get("", response_model=list[SeoPageOut])
def list_pages(
    status: str | None = None,
    locale: str | None = None,
    market_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SeoPage]:
    q = db.query(SeoPage).filter(SeoPage.tenant_id == user.tenant_id)
    if status:
        q = q.filter(SeoPage.status == status)
    if locale:
        q = q.filter(SeoPage.locale == locale)
    if market_id:
        q = q.filter(SeoPage.market_id == market_id)
    return q.order_by(SeoPage.updated_at.desc()).all()


@router.post("", response_model=SeoPageOut, status_code=201)
def create_page(
    body: SeoPageCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SeoPage:
    if body.market_id:
        market = db.get(Market, body.market_id)
        if market is None or market.tenant_id != user.tenant_id:
            raise HTTPException(status_code=400, detail="市场不存在")
    page = SeoPage(
        tenant_id=user.tenant_id,
        created_by=user.id,
        status="idea",
        **body.model_dump(),
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


@router.get("/{page_id}", response_model=SeoPageOut)
def get_page(
    page_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SeoPage:
    return _owned_page(db, user, page_id)


@router.patch("/{page_id}", response_model=SeoPageOut)
def update_page(
    page_id: str,
    body: SeoPageUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SeoPage:
    page = _owned_page(db, user, page_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("status") == "ready":
        raise HTTPException(status_code=400, detail="标记可交付必须走人工确认接口")
    if "status" in data and data["status"] not in SEO_STATUSES - {"ready"}:
        raise HTTPException(status_code=400, detail="无效状态")
    for key, value in data.items():
        setattr(page, key, value)
    db.commit()
    db.refresh(page)
    return page


@router.post("/{page_id}/generate-outline", response_model=SeoPageOut)
def make_outline(
    page_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SeoPage:
    page = _owned_page(db, user, page_id)
    page.outline = generate_outline(page.target_keyword, page.locale)
    page.status = "outline"
    db.commit()
    db.refresh(page)
    return page


@router.post("/{page_id}/generate-draft", response_model=SeoPageOut)
def make_draft(
    page_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SeoPage:
    page = _owned_page(db, user, page_id)
    outline = page.outline or generate_outline(page.target_keyword, page.locale)
    if not page.outline:
        page.outline = outline
    page.draft_body = generate_draft(page.target_keyword, page.locale, outline)
    page.status = "draft"
    db.commit()
    db.refresh(page)
    return page


@router.post("/{page_id}/generate-meta", response_model=SeoPageOut)
def make_meta(
    page_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SeoPage:
    page = _owned_page(db, user, page_id)
    title, desc = generate_meta(page.target_keyword, page.locale, page.title)
    page.meta_title = title
    page.meta_description = desc
    page.status = "meta"
    db.commit()
    db.refresh(page)
    return page


@router.post("/{page_id}/submit-review", response_model=SeoPageOut)
def submit_review(
    page_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SeoPage:
    page = _owned_page(db, user, page_id)
    if not page.outline or not page.draft_body or not page.meta_title:
        raise HTTPException(status_code=400, detail="提交审核前需完成大纲、正文与 Meta")
    page.status = "review"
    db.commit()
    db.refresh(page)
    return page


@router.post("/{page_id}/mark-ready", response_model=SeoPageOut)
def mark_ready(
    page_id: str,
    body: ConfirmReadyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SeoPage:
    page = _owned_page(db, user, page_id)
    if not body.confirmed:
        raise HTTPException(status_code=400, detail="需要客户经理人工确认后才能标记可交付")
    if page.status != "review":
        raise HTTPException(status_code=400, detail="仅审核中的选题可确认可交付")
    db.add(
        PublishConfirmation(
            tenant_id=user.tenant_id,
            seo_page_id=page.id,
            confirmed_by=user.id,
            confirmed=True,
            note=body.note,
        )
    )
    page.status = "ready"
    db.commit()
    db.refresh(page)
    return page
