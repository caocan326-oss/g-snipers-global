from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import CrawlSession, OnsiteIssue, SitePage, User
from app.onsite_analyzer import parse_internal_paths
from app.onsite_fetch import (
    OriginError,
    allowed_hosts_from_origin,
    apply_observation,
    build_fetch_url,
    fetch_many,
    fetch_site,
    fetch_url,
    load_robots,
    make_client,
    normalize_origin,
    origin_host,
    registered_targets,
)
from app.risk import severity_to_risk
from app.site_context import archive_and_reset_if_site_changed
from app.schemas import (
    CrawlOrSeedOut,
    CrawlSessionOut,
    CrawlSiteIn,
    FetchPageResultOut,
    FetchRegisteredOut,
    SiteOriginIn,
    SiteSettingsOut,
)

from . import router
from .common import (
    _analyze_one,
    _crawl_session_out,
    _owned_page,
    _require_origin,
    _tenant,
)
from .constants import OPENISH


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
        next_origin = normalize_origin(body.site_origin)
    except OriginError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    archive_and_reset_if_site_changed(db, user, old_origin=tenant.site_origin, new_origin=next_origin)
    tenant.site_origin = next_origin
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


@router.post("/crawl-site", response_model=CrawlSessionOut)
def crawl_site(
    body: CrawlSiteIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CrawlSessionOut:
    """Discover sitemap/internal links and crawl a bounded set of same-host pages."""
    tenant = _tenant(db, user)
    origin = _require_origin(tenant)
    session = CrawlSession(
        tenant_id=user.tenant_id,
        origin=origin,
        mode="site",
        max_urls=body.max_urls,
        max_depth=body.max_depth,
        status="running",
        note="站点诊断抓取运行中。",
    )
    db.add(session)
    db.flush()
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()
    rows = fetch_site(origin, pages, max_urls=body.max_urls, max_depth=body.max_depth)
    fetched = failed = created = verified = robots_blocked = needs_js_count = 0
    known_by_path = {p.path: p for p in db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()}
    for target, snap in rows:
        path = urlparse(snap.final_url or target.url).path or "/"
        page = target.page or known_by_path.get(path)
        if page is None:
            page = SitePage(
                tenant_id=user.tenant_id,
                path=path,
                locale="und",
                title=path.rsplit("/", 1)[-1] or "/",
                index_status="untested",
                crawl_status="untested",
                discovery_source=target.source,
                is_in_sitemap="yes" if target.in_sitemap else "no",
                notes="由站点抓取自动发现。收录仍未测。",
            )
            db.add(page)
            db.flush()
            known_by_path[path] = page
        page.discovery_source = target.source or page.discovery_source or "internal_link"
        page.is_in_sitemap = "yes" if target.in_sitemap else (page.is_in_sitemap or "no")
        apply_observation(page, snap)
        if snap.usable:
            fetched += 1
            c, _s, v = _analyze_one(db, user, page)
            created += c
            verified += v
        else:
            failed += 1
        if snap.crawl_status == "robots_disallow":
            robots_blocked += 1
        if snap.needs_js:
            needs_js_count += 1
    site_created, site_refreshed = _reconcile_site_patterns(
        db, user, db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()
    )
    created += site_created
    session.status = "finished"
    session.discovered = len(rows)
    session.fetched = fetched
    session.failed = failed
    session.created = created
    session.verified = verified
    session.robots_blocked = robots_blocked
    session.needs_js = needs_js_count
    session.finished_at = datetime.now(timezone.utc)
    session.note = (
        f"已完成站点诊断抓取：发现 {len(rows)} 个 URL，成功 {fetched}，失败 {failed}，"
        f"新增问题 {created}，刷新站点级问题 {site_refreshed}，验收 {verified}。AI 不参与抓取事实。"
    )
    db.commit()
    db.refresh(session)
    return _crawl_session_out(session)


@router.get("/crawl-sessions", response_model=list[CrawlSessionOut])
def list_crawl_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CrawlSessionOut]:
    rows = (
        db.query(CrawlSession)
        .filter(CrawlSession.tenant_id == user.tenant_id)
        .order_by(CrawlSession.started_at.desc())
        .limit(10)
        .all()
    )
    return [_crawl_session_out(row) for row in rows]


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
                fetch_mode=snap.fetch_mode,
                render_status=snap.render_status,
                error=snap.error,
                verified=verified,
                created=created,
            )
        ],
        ai_status="skipped",
    )


def _upsert_site_issue(
    db: Session,
    *,
    user: User,
    page: SitePage,
    category: str,
    title: str,
    detail: str,
    severity: str,
    proposed_change: str,
) -> tuple[int, int]:
    row = (
        db.query(OnsiteIssue)
        .filter(
            OnsiteIssue.tenant_id == user.tenant_id,
            OnsiteIssue.page_id == page.id,
            OnsiteIssue.category == category,
            OnsiteIssue.title == title,
        )
        .first()
    )
    if row is None:
        db.add(
            OnsiteIssue(
                tenant_id=user.tenant_id,
                page_id=page.id,
                category=category,
                title=title,
                detail=detail,
                proposed_change=proposed_change,
                severity=severity,
                risk=severity_to_risk(severity),
                status="open",
                metric_status="untested",
            )
        )
        return 1, 0
    if row.status in OPENISH:
        row.detail = detail
        row.severity = severity
        return 0, 1
    return 0, 0


def _reconcile_site_patterns(db: Session, user: User, pages: list[SitePage]) -> tuple[int, int]:
    created = refreshed = 0
    by_title: dict[str, list[SitePage]] = {}
    by_desc: dict[str, list[SitePage]] = {}
    inlinks: dict[str, int] = {p.path: 0 for p in pages}
    for page in pages:
        title = (page.meta_title or "").strip().lower()
        desc = (page.meta_description or "").strip().lower()
        if title:
            by_title.setdefault(title, []).append(page)
        if desc and len(desc) > 20:
            by_desc.setdefault(desc, []).append(page)
        for raw in parse_internal_paths(page.internal_links):
            if raw in inlinks:
                inlinks[raw] += 1

    def add(page: SitePage, category: str, title: str, detail: str, severity: str, proposed: str) -> None:
        nonlocal created, refreshed
        c, r = _upsert_site_issue(
            db,
            user=user,
            page=page,
            category=category,
            title=title,
            detail=detail,
            severity=severity,
            proposed_change=proposed,
        )
        created += c
        refreshed += r

    for title, rows in by_title.items():
        if len(rows) < 2:
            continue
        paths = ", ".join(p.path for p in rows[:8])
        for page in rows:
            add(
                page,
                "tdk",
                "Title 重复",
                f"当前 Title 与 {len(rows) - 1} 个页面重复：{paths}。",
                "high",
                "为不同产品/方案页面写唯一 Title，体现产品名、应用场景和目标市场。",
            )
    for desc, rows in by_desc.items():
        if len(rows) < 2:
            continue
        paths = ", ".join(p.path for p in rows[:8])
        for page in rows:
            add(
                page,
                "tdk",
                "Description 重复",
                f"当前 Description 与 {len(rows) - 1} 个页面重复：{paths}。",
                "low",
                "为每个核心页面写不同的描述，突出应用、参数、认证或询盘价值。",
            )
    for page in pages:
        if (page.path or "/") == "/":
            continue
        if page.is_in_sitemap == "yes" and inlinks.get(page.path, 0) == 0:
            add(
                page,
                "internal_link",
                "孤岛页面（sitemap 有但无内链入口）",
                "当前页面出现在 sitemap 中，但本次抓取未发现其他已抓页面链接到它。",
                "high",
                "从首页、产品分类页、相关文章或导航增加到该页面的可抓取内链。",
            )
        if page.is_in_sitemap != "yes" and inlinks.get(page.path, 0) > 0:
            add(
                page,
                "internal_link",
                "内链页面未进入 sitemap",
                "当前页面可从站内链接发现，但未确认出现在 sitemap 中。",
                "low",
                "确认该 URL 是否为正式页面；如是，加入 sitemap 并保持 canonical 一致。",
            )
    return created, refreshed


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
                fetch_mode=snap.fetch_mode,
                render_status=snap.render_status,
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
