from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import OnsiteIssue, SitePage, User
from app.risk import HIGH, LOW, RISKS, default_risk, require_confirm
from app.schemas import (
    ConfirmReadyIn,
    OnsiteIssueCreate,
    OnsiteIssueOut,
    SitePageCreate,
    SitePageDetailOut,
    SitePageOut,
    SitePageUpdate,
)

router = APIRouter(prefix="/api/onsite", tags=["onsite"])

CATEGORIES = {"tdk", "heading", "internal_link", "schema", "index", "crawl"}
ISSUE_STATUSES = {"open", "draft_applied", "confirmed", "wont_fix"}


def _page_out(db: Session, page: SitePage) -> SitePageOut:
    open_count = (
        db.query(func.count(OnsiteIssue.id))
        .filter(OnsiteIssue.page_id == page.id, OnsiteIssue.status.in_(["open", "draft_applied"]))
        .scalar()
        or 0
    )
    return SitePageOut(
        id=page.id,
        path=page.path,
        locale=page.locale,
        title=page.title,
        market_id=page.market_id,
        seo_page_id=page.seo_page_id,
        meta_title=page.meta_title,
        meta_description=page.meta_description,
        meta_keywords=page.meta_keywords,
        headings=page.headings,
        internal_links=page.internal_links,
        structured_data=page.structured_data,
        index_status=page.index_status,
        crawl_status=page.crawl_status,
        notes=page.notes,
        open_issue_count=open_count,
    )


def _owned_page(db: Session, user: User, page_id: str) -> SitePage:
    page = db.get(SitePage, page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    return page


@router.get("/pages", response_model=list[SitePageOut])
def list_pages(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[SitePageOut]:
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).order_by(SitePage.path).all()
    return [_page_out(db, p) for p in pages]


@router.post("/pages", response_model=SitePageOut, status_code=201)
def create_page(
    body: SitePageCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SitePageOut:
    page = SitePage(
        tenant_id=user.tenant_id,
        index_status="untested",
        crawl_status="untested",
        **body.model_dump(),
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    return _page_out(db, page)


@router.get("/pages/{page_id}", response_model=SitePageDetailOut)
def get_page(
    page_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SitePageDetailOut:
    page = (
        db.query(SitePage)
        .options(selectinload(SitePage.issues))
        .filter(SitePage.id == page_id, SitePage.tenant_id == user.tenant_id)
        .first()
    )
    if page is None:
        raise HTTPException(status_code=404, detail="页面不存在")
    base = _page_out(db, page)
    return SitePageDetailOut(
        **base.model_dump(),
        issues=[OnsiteIssueOut.model_validate(i, from_attributes=True) for i in page.issues],
    )


@router.patch("/pages/{page_id}", response_model=SitePageOut)
def update_page(
    page_id: str,
    body: SitePageUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SitePageOut:
    page = _owned_page(db, user, page_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(page, key, value)
    db.commit()
    db.refresh(page)
    return _page_out(db, page)


@router.post("/pages/{page_id}/issues", response_model=OnsiteIssueOut, status_code=201)
def create_issue(
    page_id: str,
    body: OnsiteIssueCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssue:
    page = _owned_page(db, user, page_id)
    if body.category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="无效问题类型")
    risk = body.risk or default_risk(body.category)
    if risk not in RISKS:
        raise HTTPException(status_code=400, detail="无效风险等级")
    row = OnsiteIssue(
        tenant_id=user.tenant_id,
        page_id=page.id,
        category=body.category,
        title=body.title,
        detail=body.detail,
        proposed_change=body.proposed_change,
        risk=risk,
        status="open",
        metric_status="untested",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/issues/{issue_id}/apply-draft", response_model=OnsiteIssueOut)
def apply_draft(
    issue_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssue:
    row = db.get(OnsiteIssue, issue_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    if row.risk != LOW:
        raise HTTPException(status_code=400, detail="高风险任务不能自动落草稿，请走人工确认")
    row.status = "draft_applied"
    db.commit()
    db.refresh(row)
    return row


@router.post("/issues/{issue_id}/confirm-apply", response_model=OnsiteIssueOut)
def confirm_apply(
    issue_id: str,
    body: ConfirmReadyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssue:
    require_confirm(body.confirmed, action="应用到线上站点")
    row = db.get(OnsiteIssue, issue_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    if row.risk != HIGH:
        raise HTTPException(status_code=400, detail="低风险任务请用工作区落草稿，无需线上确认")
    row.status = "confirmed"
    db.commit()
    db.refresh(row)
    return row
