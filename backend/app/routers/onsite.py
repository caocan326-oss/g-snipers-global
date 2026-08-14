from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.geo_helpers import apply_proposed_change
from app.models import OnsiteIssue, SeoPage, SitePage, User
from app.onsite_analyzer import analyze_page, parse_internal_paths
from app.risk import RISKS, SEVERITIES, default_severity, needs_confirm, require_confirm, severity_to_risk
from app.schemas import (
    AnalyzeOut,
    ConfirmReadyIn,
    ContentBriefOut,
    CrawlOrSeedOut,
    OnsiteBoardOut,
    OnsiteDraftIn,
    OnsiteIssueCreate,
    OnsiteIssueOut,
    SitePageCreate,
    SitePageDetailOut,
    SitePageOut,
    SitePageUpdate,
)

router = APIRouter(prefix="/api/onsite", tags=["onsite"])

CATEGORIES = {"tdk", "heading", "internal_link", "schema", "index", "crawl", "canonical"}
ISSUE_STATUSES = {"open", "drafted", "draft_applied", "confirmed", "wont_fix"}
OPENISH = {"open", "drafted", "draft_applied"}


def _issue_out(row: OnsiteIssue, page: SitePage | None = None) -> OnsiteIssueOut:
    p = page or row.page
    return OnsiteIssueOut(
        id=row.id,
        page_id=row.page_id,
        page_path=p.path if p else "",
        page_title=p.title if p else "",
        category=row.category,
        title=row.title,
        detail=row.detail,
        proposed_change=row.proposed_change,
        severity=row.severity or "low",
        risk=row.risk,
        status=row.status,
        metric_status=row.metric_status,
    )


def _page_out(db: Session, page: SitePage) -> SitePageOut:
    open_count = (
        db.query(func.count(OnsiteIssue.id))
        .filter(OnsiteIssue.page_id == page.id, OnsiteIssue.status.in_(list(OPENISH)))
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
        canonical=page.canonical or "",
        index_status=page.index_status,
        crawl_status=page.crawl_status,
        notes=page.notes,
        open_issue_count=open_count,
        analyzed_at=page.analyzed_at,
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
        .filter(OnsiteIssue.tenant_id == user.tenant_id, OnsiteIssue.status.in_(["open", "drafted"]))
        .all()
    )
    groups: dict[str, list[OnsiteIssueOut]] = {"critical": [], "high": [], "low": []}
    for row in rows:
        sev = row.severity if row.severity in groups else "low"
        groups[sev].append(_issue_out(row))
    return OnsiteBoardOut(
        pages=len(pages),
        analyzed_pages=analyzed,
        counts={k: len(v) for k, v in groups.items()},
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


@router.post("/crawl-or-seed", response_model=CrawlOrSeedOut)
def crawl_or_seed(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CrawlOrSeedOut:
    """Expand inventory from seeded internal links. No live HTTP, no GSC."""
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()
    known = {p.path for p in pages}
    seeded = 0
    for page in pages:
        for path in parse_internal_paths(page.internal_links):
            if path in known:
                continue
            db.add(
                SitePage(
                    tenant_id=user.tenant_id,
                    market_id=page.market_id,
                    path=path,
                    locale=page.locale,
                    title=path.rsplit("/", 1)[-1] or path,
                    index_status="untested",
                    crawl_status="untested",
                    notes="由工作区内链种子登记。未抓取线上，收录未测。",
                )
            )
            known.add(path)
            seeded += 1
    db.commit()
    total = db.query(func.count(SitePage.id)).filter(SitePage.tenant_id == user.tenant_id).scalar() or 0
    return CrawlOrSeedOut(
        seeded=seeded,
        pages=total,
        note="只从已登记页的内链扩清单，不请求客户站点，也不跑 GSC。",
    )


def _analyze_one(db: Session, user: User, page: SitePage) -> tuple[int, int]:
    existing = {
        (i.category, i.title)
        for i in db.query(OnsiteIssue).filter(
            OnsiteIssue.page_id == page.id,
            OnsiteIssue.status.in_(["open", "drafted", "draft_applied", "confirmed"]),
        )
    }
    created = 0
    skipped = 0
    for finding in analyze_page(page):
        key = (finding.category, finding.title)
        if key in existing:
            skipped += 1
            continue
        db.add(
            OnsiteIssue(
                tenant_id=user.tenant_id,
                page_id=page.id,
                category=finding.category,
                title=finding.title,
                detail=finding.detail,
                proposed_change="",
                severity=finding.severity,
                risk=severity_to_risk(finding.severity),
                status="open",
                metric_status=finding.metric_status,
            )
        )
        existing.add(key)
        created += 1
    page.analyzed_at = datetime.now(timezone.utc)
    return created, skipped


@router.post("/analyze", response_model=AnalyzeOut)
def analyze_inventory(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AnalyzeOut:
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()
    created = skipped = 0
    for page in pages:
        c, s = _analyze_one(db, user, page)
        created += c
        skipped += s
    db.commit()
    return AnalyzeOut(created=created, skipped=skipped, pages=len(pages))


@router.post("/pages/{page_id}/analyze", response_model=AnalyzeOut)
def analyze_one_page(
    page_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyzeOut:
    page = _owned_page(db, user, page_id)
    created, skipped = _analyze_one(db, user, page)
    db.commit()
    return AnalyzeOut(created=created, skipped=skipped, pages=1)


@router.post("/pages/{page_id}/issues", response_model=OnsiteIssueOut, status_code=201)
def create_issue(
    page_id: str,
    body: OnsiteIssueCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    page = _owned_page(db, user, page_id)
    if body.category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="无效问题类型")
    severity = body.severity or default_severity(body.category)
    if severity not in SEVERITIES:
        raise HTTPException(status_code=400, detail="无效严重级别")
    risk = body.risk or severity_to_risk(severity)
    if risk not in RISKS:
        raise HTTPException(status_code=400, detail="无效风险等级")
    row = OnsiteIssue(
        tenant_id=user.tenant_id,
        page_id=page.id,
        category=body.category,
        title=body.title,
        detail=body.detail,
        proposed_change=body.proposed_change,
        severity=severity,
        risk=risk,
        status="open",
        metric_status="untested",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _issue_out(row, page)


@router.patch("/issues/{issue_id}/draft", response_model=OnsiteIssueOut)
def write_change_draft(
    issue_id: str,
    body: OnsiteDraftIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    row = db.get(OnsiteIssue, issue_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not body.proposed_change.strip():
        raise HTTPException(status_code=400, detail="改稿草稿不能为空")
    row.proposed_change = body.proposed_change
    if row.status == "open":
        row.status = "drafted"
    db.commit()
    db.refresh(row)
    return _issue_out(row)


@router.post("/issues/{issue_id}/apply-draft", response_model=OnsiteIssueOut)
def apply_draft(
    issue_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    row = db.get(OnsiteIssue, issue_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    if needs_confirm(row.severity, row.risk):
        raise HTTPException(status_code=400, detail="高风险任务不能自动落草稿，请走人工确认")
    if not (row.proposed_change or "").strip():
        raise HTTPException(status_code=400, detail="请先写改稿草稿，分析与应用是两步")
    page = db.get(SitePage, row.page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    apply_proposed_change(page, row)
    row.status = "draft_applied"
    db.commit()
    db.refresh(row)
    return _issue_out(row, page)


@router.post("/issues/{issue_id}/confirm-apply", response_model=OnsiteIssueOut)
def confirm_apply(
    issue_id: str,
    body: ConfirmReadyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    require_confirm(body.confirmed, action="应用到线上站点")
    row = db.get(OnsiteIssue, issue_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not needs_confirm(row.severity, row.risk):
        raise HTTPException(status_code=400, detail="低风险任务请用工作区落草稿，无需线上确认")
    if not (row.proposed_change or "").strip():
        raise HTTPException(status_code=400, detail="请先写改稿草稿，分析与应用是两步")
    page = db.get(SitePage, row.page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    apply_proposed_change(page, row)
    row.status = "confirmed"
    db.commit()
    db.refresh(row)
    return _issue_out(row, page)
