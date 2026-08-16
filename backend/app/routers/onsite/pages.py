from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import OnsiteIssue, SeoPage, SitePage, User
from app.risk import needs_confirm
from app.schemas import (
    ContentBriefOut,
    OnsiteBoardOut,
    OnsiteIssueOut,
    SitePageCreate,
    SitePageDetailOut,
    SitePageOut,
    SitePageUpdate,
)

from . import router
from .constants import BOARD_ACTIONABLE, ISSUE_STATUSES
from .common import _issue_out, _owned_page, _page_out


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
        issues=[_issue_out(i, page) for i in page.issues],
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


@router.get("/board", response_model=OnsiteBoardOut)
def issue_board(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> OnsiteBoardOut:
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()
    analyzed = sum(1 for p in pages if p.analyzed_at)
    rows = (
        db.query(OnsiteIssue)
        .options(selectinload(OnsiteIssue.page))
        .filter(OnsiteIssue.tenant_id == user.tenant_id, OnsiteIssue.status.in_(list(BOARD_ACTIONABLE)))
        .all()
    )
    groups: dict[str, list[OnsiteIssueOut]] = {"critical": [], "high": [], "low": []}
    status_counts = {status: 0 for status in ISSUE_STATUSES}
    workflow_counts = {
        "needs_draft": 0,
        "needs_review": 0,
        "ready_to_execute": 0,
        "waiting_retest": 0,
        "verified": 0,
        "wont_fix": 0,
    }
    all_status_rows = db.query(OnsiteIssue).filter(OnsiteIssue.tenant_id == user.tenant_id).all()
    for row in all_status_rows:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1
        if row.status == "open" and not (row.proposed_change or "").strip():
            workflow_counts["needs_draft"] += 1
        if row.status == "drafted":
            workflow_counts["ready_to_execute"] += 1
            if needs_confirm(row.severity or "low", row.risk):
                workflow_counts["needs_review"] += 1
        if row.status in {"draft_applied", "confirmed"}:
            workflow_counts["waiting_retest"] += 1
        if row.status == "verified":
            workflow_counts["verified"] += 1
        if row.status == "wont_fix":
            workflow_counts["wont_fix"] += 1
    for row in rows:
        sev = row.severity if row.severity in groups else "low"
        groups[sev].append(_issue_out(row))
    return OnsiteBoardOut(
        pages=len(pages),
        analyzed_pages=analyzed,
        counts={k: len(v) for k, v in groups.items()},
        status_counts=status_counts,
        workflow_counts=workflow_counts,
        groups=groups,
    )


@router.get("/briefs", response_model=list[ContentBriefOut])
def content_briefs(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ContentBriefOut]:
    pages = db.query(SeoPage).filter(SeoPage.tenant_id == user.tenant_id).order_by(SeoPage.updated_at.desc()).all()
    return [
        ContentBriefOut(
            id=p.id,
            title=p.title,
            target_keyword=p.target_keyword,
            locale=p.locale,
            status=p.status,
            serp_features="未测",
        )
        for p in pages
    ]
