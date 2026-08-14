from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.ai_engine import assist_onsite_issue
from app.llm import UNCONFIGURED, configured
from app.models import OnsiteIssue, SeoPage, SitePage, Tenant, User
from app.onsite_analyzer import parse_internal_paths, reconcile_issues
from app.onsite_fetch import (
    OriginError,
    allowed_hosts_from_origin,
    apply_observation,
    build_fetch_url,
    fetch_many,
    fetch_url,
    load_robots,
    make_client,
    normalize_origin,
    origin_host,
    registered_targets,
)
from app.risk import RISKS, SEVERITIES, default_severity, needs_confirm, require_confirm, severity_to_risk
from app.schemas import (
    AiAssistOut,
    AiStepIn,
    AnalyzeOut,
    ConfirmReadyIn,
    ContentBriefOut,
    CrawlOrSeedOut,
    FetchPageResultOut,
    FetchRegisteredOut,
    OnsiteBoardOut,
    OnsiteDraftIn,
    OnsiteIssueCreate,
    OnsiteIssueOut,
    SiteOriginIn,
    SitePageCreate,
    SitePageDetailOut,
    SitePageOut,
    SitePageUpdate,
    SiteSettingsOut,
)

router = APIRouter(prefix="/api/onsite", tags=["onsite"])

CATEGORIES = {"tdk", "heading", "internal_link", "schema", "index", "crawl", "canonical"}
ISSUE_STATUSES = {"open", "drafted", "draft_applied", "confirmed", "verified", "wont_fix"}
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
        ai_status=row.ai_status or "untested",
        ai_diagnosis=row.ai_diagnosis or "",
        ai_review=row.ai_review or "",
        ai_review_verdict=row.ai_review_verdict or "untested",
        evidence=row.evidence or "",
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
        fetched_at=page.fetched_at,
        final_url=page.final_url or "",
        http_status=page.http_status,
        needs_js=bool(page.needs_js),
        html_lang=page.html_lang or "",
        hreflang=page.hreflang or "",
        viewport=page.viewport or "",
        json_ld_types=page.json_ld_types or "",
        crawl_error=page.crawl_error or "",
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
        note="只从已登记页的内链扩清单。线上回抓请用「抓这一站」。不跑 GSC。",
    )


@router.get("/settings", response_model=SiteSettingsOut)
def get_site_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SiteSettingsOut:
    tenant = _tenant(db, user)
    return SiteSettingsOut(site_origin=tenant.site_origin or "")


@router.patch("/settings", response_model=SiteSettingsOut)
def update_site_settings(
    body: SiteOriginIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SiteSettingsOut:
    tenant = _tenant(db, user)
    try:
        tenant.site_origin = normalize_origin(body.site_origin)
    except OriginError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return SiteSettingsOut(site_origin=tenant.site_origin)


@router.post("/fetch-registered", response_model=FetchRegisteredOut)
def fetch_registered(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> FetchRegisteredOut:
    """HTTP GET already-registered pages only. Observation layer only. No GSC."""
    tenant = _tenant(db, user)
    origin = _require_origin(tenant)
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()
    targets = registered_targets(origin, pages)
    rows = fetch_many(targets, origin)
    fetched, failed, verified, created, results = _ingest_snapshots(db, user, rows)
    pages_after = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()
    db.commit()
    note = (
        f"只抓已登记页（含站点根），主机名必须是 {origin_host(origin)}。"
        "观察层已覆盖并按规则验收。改稿未动，本请求不跑 LLM。收录仍未测。"
    )
    return FetchRegisteredOut(
        origin=origin,
        fetched=fetched,
        failed=failed,
        verified=verified,
        created=created,
        pages=len(pages_after),
        note=note,
        results=results,
        ai_status="skipped",
    )


@router.post("/pages/{page_id}/fetch", response_model=FetchRegisteredOut)
def fetch_one_page(
    page_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FetchRegisteredOut:
    tenant = _tenant(db, user)
    origin = _require_origin(tenant)
    page = _owned_page(db, user, page_id)
    snap, created, verified = _fetch_one_registered(db, user, page, origin)
    db.commit()
    failed = 0 if snap.usable else 1
    fetched = 1 if snap.usable else 0
    note = "已回抓本页观察层并按规则验收。改稿未覆盖，本请求不跑 LLM。收录仍未测。"
    return FetchRegisteredOut(
        origin=origin,
        fetched=fetched,
        failed=failed,
        verified=verified,
        created=created,
        pages=1,
        note=note,
        results=[
            FetchPageResultOut(
                page_id=page.id,
                path=page.path,
                url=build_fetch_url(origin, page.path),
                crawl_status=snap.crawl_status,
                http_status=snap.http_status,
                final_url=snap.final_url,
                needs_js=snap.needs_js,
                error=snap.error,
                verified=verified,
                created=created,
            )
        ],
        ai_status="skipped",
    )


def _tenant(db: Session, user: User) -> Tenant:
    tenant = db.get(Tenant, user.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="租户不存在")
    return tenant


def _require_origin(tenant: Tenant) -> str:
    try:
        return normalize_origin(tenant.site_origin or "")
    except OriginError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _page_issues(db: Session, page_id: str) -> list[OnsiteIssue]:
    return db.query(OnsiteIssue).filter(OnsiteIssue.page_id == page_id).all()


def _analyze_one(db: Session, user: User, page: SitePage) -> tuple[int, int, int]:
    created, skipped, verified = reconcile_issues(
        db, tenant_id=user.tenant_id, page=page, issues=_page_issues(db, page.id)
    )
    db.flush()
    return created, skipped, verified


def _ensure_root_page(db: Session, user: User, path: str = "/") -> SitePage:
    page = (
        db.query(SitePage)
        .filter(SitePage.tenant_id == user.tenant_id, SitePage.path == path)
        .first()
    )
    if page is None:
        page = SitePage(
            tenant_id=user.tenant_id,
            path=path,
            locale="und",
            title=path or "/",
            index_status="untested",
            crawl_status="untested",
            notes="站点根。由抓取登记，未编收录。",
        )
        db.add(page)
        db.flush()
    return page


def _ingest_snapshots(
    db: Session,
    user: User,
    rows: list[tuple[str, SitePage | None, object]],
) -> tuple[int, int, int, int, list[FetchPageResultOut]]:
    fetched = failed = verified = created = 0
    results: list[FetchPageResultOut] = []
    for url, page, snap in rows:
        if page is None:
            path = "/"
            page = _ensure_root_page(db, user, path)
        apply_observation(page, snap)
        page_created = page_verified = 0
        if snap.usable:
            fetched += 1
            c, _s, v = _analyze_one(db, user, page)
            page_created, page_verified = c, v
            created += c
            verified += v
        else:
            failed += 1
        results.append(
            FetchPageResultOut(
                page_id=page.id,
                path=page.path,
                url=url,
                crawl_status=snap.crawl_status,
                http_status=snap.http_status,
                final_url=snap.final_url,
                needs_js=snap.needs_js,
                error=snap.error,
                verified=page_verified,
                created=page_created,
            )
        )
    return fetched, failed, verified, created, results


def _fetch_one_registered(db: Session, user: User, page: SitePage, origin: str):
    url = build_fetch_url(origin, page.path)
    with make_client() as client:
        robots = load_robots(origin, client)
        snap = fetch_url(url, allowed_hosts_from_origin(origin), client=client, robots=robots)
    apply_observation(page, snap)
    created = verified = 0
    if snap.usable:
        created, _skipped, verified = _analyze_one(db, user, page)
    return snap, created, verified


def _ai_after_analyze(db: Session, user: User, pages: list[SitePage]) -> str:
    issues = (
        db.query(OnsiteIssue)
        .filter(OnsiteIssue.tenant_id == user.tenant_id, OnsiteIssue.status.in_(["open", "drafted"]))
        .all()
    )
    by_id = {p.id: p for p in pages}
    for issue in issues:
        page = by_id.get(issue.page_id) or db.get(SitePage, issue.page_id)
        if page is None:
            continue
        assist_onsite_issue(db, issue, page, step="analyze")
    return UNCONFIGURED if not configured() else "ok"


@router.post("/analyze", response_model=AnalyzeOut)
def analyze_inventory(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AnalyzeOut:
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()
    created = skipped = verified = 0
    for page in pages:
        c, s, v = _analyze_one(db, user, page)
        created += c
        skipped += s
        verified += v
    ai_status = _ai_after_analyze(db, user, pages)
    db.commit()
    note = "分析只读当前观察，不改改稿，也不应用到线上。已满足的工单标为已验收。"
    if ai_status == UNCONFIGURED:
        note += " LLM 未配置，诊断/改稿未编造。"
    return AnalyzeOut(
        created=created, skipped=skipped, verified=verified, pages=len(pages), note=note, ai_status=ai_status
    )


@router.post("/pages/{page_id}/analyze", response_model=AnalyzeOut)
def analyze_one_page(
    page_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyzeOut:
    page = _owned_page(db, user, page_id)
    created, skipped, verified = _analyze_one(db, user, page)
    ai_status = _ai_after_analyze(db, user, [page])
    db.commit()
    note = "分析只读当前观察，不改改稿，也不应用到线上。已满足的工单标为已验收。"
    if ai_status == UNCONFIGURED:
        note += " LLM 未配置，诊断/改稿未编造。"
    return AnalyzeOut(
        created=created, skipped=skipped, verified=verified, pages=1, note=note, ai_status=ai_status
    )


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
    row.status = "confirmed"
    tenant = _tenant(db, user)
    if (tenant.site_origin or "").strip():
        try:
            origin = normalize_origin(tenant.site_origin)
            _fetch_one_registered(db, user, page, origin)
        except OriginError:
            pass
    db.commit()
    db.refresh(row)
    return _issue_out(row, page)


@router.post("/issues/{issue_id}/ai", response_model=AiAssistOut)
def ai_issue(
    issue_id: str,
    body: AiStepIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiAssistOut:
    row = db.get(OnsiteIssue, issue_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    page = db.get(SitePage, row.page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="页面不存在")
    payload = assist_onsite_issue(db, row, page, step=body.step)
    db.commit()
    return AiAssistOut(**payload)


@router.post("/ai", response_model=AiAssistOut)
def ai_onsite_engine(
    body: AiStepIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiAssistOut:
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()
    created = skipped = 0
    if body.step in {"analyze", "all"}:
        for page in pages:
            c, s, _v = _analyze_one(db, user, page)
            created += c
            skipped += s
    issues = (
        db.query(OnsiteIssue)
        .filter(OnsiteIssue.tenant_id == user.tenant_id, OnsiteIssue.status.in_(["open", "drafted"]))
        .all()
    )
    last: dict = {"status": UNCONFIGURED, "step": body.step, "detail": "没有待处理问题。"}
    by_id = {p.id: p for p in pages}
    for issue in issues:
        page = by_id.get(issue.page_id)
        if page is None:
            continue
        last = assist_onsite_issue(db, issue, page, step=body.step)
    db.commit()
    last["detail"] = (last.get("detail") or "") + f" 分析新建 {created}，跳过 {skipped}。"
    return AiAssistOut(**last)
