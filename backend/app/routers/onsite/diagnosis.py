import hashlib
from collections import defaultdict
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import (
    Competitor,
    DemandSignal,
    Market,
    OnsiteIssue,
    PageSpeedAudit,
    SeoPage,
    SeoPerformanceImport,
    SeoPerformanceRow,
    SerpResult,
    SerpRun,
    SitePage,
    Tenant,
    User,
)
from app.onsite_analyzer import rank_distribution
from app.onsite_fetch import normalize_origin
from app.schemas import (
    PageSpeedAuditOut,
    PageSpeedRunIn,
    SeoPerformanceBucketOut,
    SeoPerformanceImportOut,
    SeoPerformanceSummaryOut,
    SerpResultOut,
    SerpRunBatchOut,
    SerpRunIn,
    SerpRunOut,
    SerpSummaryOut,
)

from . import router
from .common import _parse_float, _tenant
from .constants import BRIGHTDATA_SERP_INPUT_URL, PAGESPEED_ENDPOINT
from .integrations import _finish_data_sync, _integration_value


def _weighted_position(rows: list[SeoPerformanceRow]) -> float | None:
    weighted = 0.0
    total = 0
    for row in rows:
        if row.position is None:
            continue
        weight = row.impressions or 1
        weighted += row.position * weight
        total += weight
    return round(weighted / total, 2) if total else None


def _performance_bucket(key: str, rows: list[SeoPerformanceRow]) -> SeoPerformanceBucketOut:
    clicks = sum(r.clicks for r in rows)
    impressions = sum(r.impressions for r in rows)
    ctr = round(clicks / impressions * 100, 2) if impressions else None
    return SeoPerformanceBucketOut(
        key=key or "未标注",
        clicks=clicks,
        impressions=impressions,
        ctr=ctr,
        position=_weighted_position(rows),
    )


def _top_buckets(rows: list[SeoPerformanceRow], attr: str, limit: int = 8) -> list[SeoPerformanceBucketOut]:
    grouped: dict[str, list[SeoPerformanceRow]] = defaultdict(list)
    for row in rows:
        grouped[getattr(row, attr) or "未标注"].append(row)
    buckets = [_performance_bucket(key, values) for key, values in grouped.items()]
    return sorted(buckets, key=lambda item: (item.impressions, item.clicks), reverse=True)[:limit]


def _latest_speed_audits(db: Session, tenant_id: str, limit: int = 8) -> list[PageSpeedAudit]:
    return (
        db.query(PageSpeedAudit)
        .filter(PageSpeedAudit.tenant_id == tenant_id)
        .order_by(PageSpeedAudit.audited_at.desc())
        .limit(limit)
        .all()
    )


def _performance_summary(db: Session, user: User) -> SeoPerformanceSummaryOut:
    rows = db.query(SeoPerformanceRow).filter(SeoPerformanceRow.tenant_id == user.tenant_id).all()
    imports = (
        db.query(SeoPerformanceImport)
        .filter(SeoPerformanceImport.tenant_id == user.tenant_id)
        .order_by(SeoPerformanceImport.imported_at.desc())
        .limit(10)
        .all()
    )
    speed = _latest_speed_audits(db, user.tenant_id)
    gsc_rows = [row for row in rows if row.source in {"gsc_csv", "gsc_api"}]
    bing_rows = [row for row in rows if row.source == "bing_csv"]
    total_clicks = sum(row.clicks for row in rows)
    total_impressions = sum(row.impressions for row in rows)
    keyword_buckets = _top_buckets(rows, "query", limit=200)
    return SeoPerformanceSummaryOut(
        gsc_status="已导入" if gsc_rows else "未导入",
        bing_status="已导入" if bing_rows else "未导入",
        pagespeed_status="已测速" if speed else "未测速",
        total_clicks=total_clicks,
        total_impressions=total_impressions,
        avg_ctr=round(total_clicks / total_impressions * 100, 2) if total_impressions else None,
        avg_position=_weighted_position(rows),
        keyword_rank_distribution=rank_distribution([item.position for item in keyword_buckets]),
        by_country=_top_buckets(rows, "country"),
        by_query=keyword_buckets[:8],
        by_page=_top_buckets(rows, "page_url"),
        speed_latest=[PageSpeedAuditOut(**audit.__dict__) for audit in speed],
        imports=[SeoPerformanceImportOut(**item.__dict__) for item in imports],
        serp=_serp_summary(db, user),
    )


def _serp_configured(db: Session, tenant_id: str) -> bool:
    return bool(
        _integration_value(db, tenant_id, "brightdata_dataset_api_key")
        and _integration_value(db, tenant_id, "brightdata_serp_dataset_id")
    )


def _domain(url: str) -> str:
    host = (urlparse(url if "://" in url else f"https://{url}").hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _same_or_subdomain(domain: str, root: str) -> bool:
    d = _domain(domain)
    r = _domain(root)
    return bool(d and r and (d == r or d.endswith("." + r)))


def _competitor_domains(db: Session, tenant_id: str) -> set[str]:
    rows = db.query(Competitor).filter(Competitor.tenant_id == tenant_id).all()
    domains = {_domain(row.website or "") for row in rows if row.website}
    return {item for item in domains if item}


def _ownership(url: str, own_domain: str, competitors: set[str]) -> str:
    domain = _domain(url)
    if own_domain and _same_or_subdomain(domain, own_domain):
        return "owned"
    if any(_same_or_subdomain(domain, comp) for comp in competitors):
        return "competitor"
    return "third_party"


def _extract_organic_results(data: object, limit: int) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []

    def candidates_from(node: object) -> list[object]:
        if isinstance(node, list):
            return node
        if not isinstance(node, dict):
            return []
        candidates = (
            node.get("organic")
            or node.get("organic_results")
            or node.get("organic_results_100")
            or node.get("results")
            or node.get("items")
            or []
        )
        if isinstance(candidates, dict):
            candidates = candidates.get("items") or candidates.get("results") or []
        return candidates if isinstance(candidates, list) else []

    top_level = data if isinstance(data, list) else [data]
    candidates: list[object] = []
    for item in top_level:
        if isinstance(item, dict):
            candidates.extend(candidates_from(item))
            if isinstance(item.get("result"), (dict, list)):
                candidates.extend(candidates_from(item.get("result")))
            if isinstance(item.get("data"), (dict, list)):
                candidates.extend(candidates_from(item.get("data")))
        else:
            candidates.extend(candidates_from(item))

    if not isinstance(candidates, list):
        return rows
    for idx, item in enumerate(candidates, start=1):
        if not isinstance(item, dict):
            continue
        url = str(item.get("link") or item.get("url") or item.get("href") or item.get("displayed_link") or "").strip()
        if not url:
            continue
        position_raw = item.get("position") or item.get("rank") or idx
        try:
            position = int(position_raw)
        except (TypeError, ValueError):
            position = idx
        rows.append(
            {
                "position": position,
                "title": str(item.get("title") or "").strip(),
                "url": url,
                "snippet": str(item.get("snippet") or item.get("description") or item.get("text") or "").strip(),
                "result_type": str(item.get("type") or "organic").strip() or "organic",
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _fetch_brightdata_serp(
    db: Session,
    tenant_id: str,
    keyword: str,
    *,
    country: str,
    locale: str,
    device: str,
    limit: int,
) -> list[dict[str, str | int]]:
    language = locale.split("-", 1)[0].lower() if locale else ""
    payload = {
        "input": [
            {
                "url": BRIGHTDATA_SERP_INPUT_URL,
                "keyword": keyword,
                "language": language,
                "uule": "",
                "brd_mobile": "1" if device == "mobile" else "",
                "tbs": "",
                "tbm": "",
                "nfpr": "",
                "index": "",
            }
        ],
        "limit_per_input": limit,
    }
    params = {
        "dataset_id": _integration_value(db, tenant_id, "brightdata_serp_dataset_id"),
        "notify": "false",
        "include_errors": "true",
    }
    headers = {
        "Authorization": f"Bearer {_integration_value(db, tenant_id, 'brightdata_dataset_api_key')}",
        "Content-Type": "application/json",
    }
    endpoint = _integration_value(db, tenant_id, "brightdata_serp_endpoint") or "https://api.brightdata.com/datasets/v3/scrape"
    with httpx.Client(timeout=90, headers=headers) as client:
        response = client.post(endpoint, params=params, json=payload)
        response.raise_for_status()
        data = response.json()
    return _extract_organic_results(data, limit)


def _serp_run_out(run: SerpRun, results: list[SerpResult] | None = None) -> SerpRunOut:
    return SerpRunOut(
        id=run.id,
        provider=run.provider,
        keyword=run.keyword,
        country=run.country,
        locale=run.locale,
        device=run.device,
        status=run.status,
        own_domain=run.own_domain,
        own_best_position=run.own_best_position,
        competitor_best_position=run.competitor_best_position,
        result_count=run.result_count,
        third_party_count=run.third_party_count,
        error=run.error,
        created_at=run.created_at,
        results=[SerpResultOut(**item.__dict__) for item in (results or [])],
    )


def _serp_summary(db: Session, user: User) -> SerpSummaryOut:
    runs = (
        db.query(SerpRun)
        .filter(SerpRun.tenant_id == user.tenant_id)
        .order_by(SerpRun.created_at.desc())
        .limit(20)
        .all()
    )
    latest = runs[:6]
    ok_runs = [row for row in runs if row.status == "ok"]
    own_positions = [row.own_best_position for row in ok_runs if row.own_best_position is not None]
    third_party_rows = (
        db.query(SerpResult.domain, func.count(SerpResult.id))
        .filter(SerpResult.tenant_id == user.tenant_id, SerpResult.ownership == "third_party")
        .group_by(SerpResult.domain)
        .order_by(func.count(SerpResult.id).desc())
        .limit(8)
        .all()
    )
    return SerpSummaryOut(
        configured=_serp_configured(db, user.tenant_id),
        status="已配置" if _serp_configured(db, user.tenant_id) else "未配置",
        total_runs=len(runs),
        own_visible_runs=sum(1 for row in ok_runs if row.own_best_position is not None),
        competitor_visible_runs=sum(1 for row in ok_runs if row.competitor_best_position is not None),
        avg_own_position=round(sum(own_positions) / len(own_positions), 2) if own_positions else None,
        rank_distribution=rank_distribution([row.own_best_position for row in ok_runs]),
        latest_runs=[_serp_run_out(row) for row in latest],
        top_third_party_domains=[{"domain": domain or "未知域名", "count": int(count)} for domain, count in third_party_rows],
    )


def _target_serp_keywords(db: Session, user: User, requested: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in requested:
        text = raw.strip()
        if text and text.lower() not in seen:
            seen.add(text.lower())
            out.append(text)
    if not out:
        signals = (
            db.query(DemandSignal)
            .filter(
                DemandSignal.tenant_id == user.tenant_id,
                DemandSignal.source != "target_archived",
            )
            .order_by(DemandSignal.intensity.desc(), DemandSignal.created_at.desc())
            .limit(limit)
            .all()
        )
        for row in signals:
            text = (row.theme or "").strip()
            if text and text.lower() not in seen:
                seen.add(text.lower())
                out.append(text)
    if not out:
        seo_pages = (
            db.query(SeoPage)
            .filter(SeoPage.tenant_id == user.tenant_id)
            .order_by(SeoPage.updated_at.desc())
            .limit(limit)
            .all()
        )
        for row in seo_pages:
            text = (row.target_keyword or "").strip()
            if text and text.lower() not in seen:
                seen.add(text.lower())
                out.append(text)
    return out[:limit]


def _run_one_serp(db: Session, user: User, keyword: str, *, country: str, locale: str, device: str, limit: int) -> SerpRun:
    tenant = _tenant(db, user)
    own_domain = _domain(tenant.site_origin or "")
    competitors = _competitor_domains(db, user.tenant_id)
    config_hash = hashlib.sha256(f"brightdata|{keyword}|{country}|{locale}|{device}|{limit}|{own_domain}|{','.join(sorted(competitors))}".encode()).hexdigest()
    run = SerpRun(
        tenant_id=user.tenant_id,
        provider="brightdata",
        keyword=keyword,
        country=country,
        locale=locale,
        device=device,
        status="running",
        own_domain=own_domain,
        config_hash=config_hash,
        created_by=user.id,
    )
    db.add(run)
    db.flush()
    try:
        rows = _fetch_brightdata_serp(db, user.tenant_id, keyword, country=country, locale=locale, device=device, limit=limit)
        own_positions: list[int] = []
        competitor_positions: list[int] = []
        third_party_count = 0
        for item in rows:
            url = str(item["url"])
            ownership = _ownership(url, own_domain, competitors)
            position = int(item["position"])
            if ownership == "owned":
                own_positions.append(position)
            elif ownership == "competitor":
                competitor_positions.append(position)
            else:
                third_party_count += 1
            db.add(
                SerpResult(
                    tenant_id=user.tenant_id,
                    run_id=run.id,
                    position=position,
                    title=str(item["title"])[:500],
                    url=url[:1000],
                    domain=_domain(url)[:255],
                    snippet=str(item["snippet"]),
                    result_type=str(item["result_type"])[:40],
                    ownership=ownership,
                )
            )
        run.status = "ok"
        run.result_count = len(rows)
        run.third_party_count = third_party_count
        run.own_best_position = min(own_positions) if own_positions else None
        run.competitor_best_position = min(competitor_positions) if competitor_positions else None
    except Exception as exc:
        run.status = "error"
        run.error = f"Bright Data SERP 查询失败：{exc}"[:1000]
    return run


def _page_performance(rows: list[SeoPerformanceRow], page: SitePage | None) -> SeoPerformanceBucketOut | None:
    if not page:
        return None
    path = page.path or "/"
    matched = []
    for row in rows:
        parsed = urlparse(row.page_url)
        candidate_path = parsed.path if parsed.scheme else row.page_url
        if candidate_path == path or row.page_url.endswith(path):
            matched.append(row)
    return _performance_bucket(path, matched) if matched else None


def _score_text(score: int | None) -> str:
    return str(score) if score is not None else "未得分"


def _pagespeed_targets(tenant: Tenant, pages: list[SitePage], requested: list[str], limit: int) -> list[str]:
    origin = normalize_origin(tenant.site_origin or "")
    seen: set[str] = set()
    urls: list[str] = []
    for raw in requested:
        candidate = raw.strip()
        if not candidate:
            continue
        url = candidate if urlparse(candidate).scheme else urljoin(origin, candidate)
        if url not in seen:
            urls.append(url)
            seen.add(url)
    if not urls:
        for path in ["/"] + [page.path for page in pages]:
            url = urljoin(origin, path)
            if url not in seen:
                urls.append(url)
                seen.add(url)
            if len(urls) >= limit:
                break
    return urls[:limit]


def _extract_pagespeed_score(category: dict) -> int | None:
    score = category.get("score")
    if score is None:
        return None
    try:
        return int(round(float(score) * 100))
    except (TypeError, ValueError):
        return None


def _audit_numeric(audits: dict, key: str) -> int | None:
    value = (audits.get(key) or {}).get("numericValue")
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _run_pagespeed(db: Session, tenant_id: str, url: str, strategy: str) -> dict:
    params = {"url": url, "strategy": strategy, "category": ["performance", "seo", "accessibility", "best-practices"]}
    pagespeed_key = _integration_value(db, tenant_id, "pagespeed_api_key") or settings.pagespeed_api_key
    if pagespeed_key:
        params["key"] = pagespeed_key
    with httpx.Client(timeout=45) as client:
        response = client.get(PAGESPEED_ENDPOINT, params=params)
        response.raise_for_status()
        data = response.json()
    lighthouse = data.get("lighthouseResult") or {}
    categories = lighthouse.get("categories") or {}
    audits = lighthouse.get("audits") or {}
    return {
        "performance_score": _extract_pagespeed_score(categories.get("performance") or {}),
        "seo_score": _extract_pagespeed_score(categories.get("seo") or {}),
        "accessibility_score": _extract_pagespeed_score(categories.get("accessibility") or {}),
        "best_practices_score": _extract_pagespeed_score(categories.get("best-practices") or {}),
        "lcp_ms": _audit_numeric(audits, "largest-contentful-paint"),
        "inp_ms": _audit_numeric(audits, "interaction-to-next-paint") or _audit_numeric(audits, "max-potential-fid"),
        "cls": _parse_float(str((audits.get("cumulative-layout-shift") or {}).get("numericValue", ""))),
        "detail": "PageSpeed Insights 在线测速完成。",
    }


def _diagnosis_targets(db: Session, user: User) -> dict[str, list]:
    markets = (
        db.query(Market)
        .filter(Market.tenant_id == user.tenant_id)
        .order_by(Market.opportunity_score.desc(), Market.created_at.desc())
        .all()
    )
    status_rank = {"priority": 0, "watching": 1, "paused": 2}
    markets.sort(key=lambda m: (status_rank.get(m.status, 9), -(m.opportunity_score or 0), m.name))
    seo_pages = (
        db.query(SeoPage)
        .filter(SeoPage.tenant_id == user.tenant_id)
        .order_by(SeoPage.updated_at.desc())
        .all()
    )
    signals = (
        db.query(DemandSignal)
        .filter(
            DemandSignal.tenant_id == user.tenant_id,
            DemandSignal.source != "target_archived",
        )
        .order_by(DemandSignal.intensity.desc(), DemandSignal.created_at.desc())
        .all()
    )
    market_by_id = {m.id: m for m in markets}
    keyword_rows: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for page in seo_pages:
        key = (page.target_keyword.strip().lower(), page.locale)
        if not page.target_keyword.strip() or key in seen:
            continue
        market = market_by_id.get(page.market_id or "")
        keyword_rows.append((page.target_keyword, page.locale, market.name if market else "未绑定市场", page.status))
        seen.add(key)
    for signal in signals:
        key = (signal.theme.strip().lower(), signal.locale)
        if not signal.theme.strip() or key in seen:
            continue
        market = market_by_id.get(signal.market_id)
        keyword_rows.append((signal.theme, signal.locale, market.name if market else "未绑定市场", f"需求强度 {signal.intensity}"))
        seen.add(key)
    target_markets = [m for m in markets if m.status == "priority"] or markets
    return {
        "markets": target_markets[:8],
        "keywords": keyword_rows[:20],
        "seo_pages": seo_pages,
        "market_by_id": market_by_id,
    }


def _issue_target_market(issue: OnsiteIssue, page: SitePage | None, market_by_id: dict[str, Market]) -> str:
    market_id = page.market_id if page else None
    market = market_by_id.get(market_id or "")
    return f"{market.name}（{market.country_code}）" if market else "未绑定目标国家"


def _issue_target_keyword(issue: OnsiteIssue, page: SitePage | None, seo_by_id: dict[str, SeoPage]) -> str:
    seo = seo_by_id.get((page.seo_page_id if page else "") or "")
    return seo.target_keyword if seo else "未绑定目标关键词"


@router.get("/performance", response_model=SeoPerformanceSummaryOut)
def seo_performance(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SeoPerformanceSummaryOut:
    return _performance_summary(db, user)


@router.get("/serp/status", response_model=SerpSummaryOut)
def serp_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SerpSummaryOut:
    return _serp_summary(db, user)


@router.post("/serp/run", response_model=SerpRunBatchOut)
def run_serp(
    body: SerpRunIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SerpRunBatchOut:
    if not _serp_configured(db, user.tenant_id):
        return SerpRunBatchOut(
            status="未配置",
            configured=False,
            note="服务器未配置 Bright Data Dataset SERP API。请配置 BRIGHTDATA_DATASET_API_KEY / BRIGHTDATA_SERP_DATASET_ID。",
        )
    keywords = _target_serp_keywords(db, user, body.keywords, limit=min(5, body.limit))
    if not keywords:
        raise HTTPException(status_code=400, detail="没有可查询的关键词。请先在首页配置客户 SEO 目标关键词。")
    runs: list[SerpRun] = []
    for keyword in keywords:
        runs.append(_run_one_serp(db, user, keyword, country=body.country, locale=body.locale, device=body.device, limit=body.limit))
    failed = sum(1 for row in runs if row.status == "error")
    _finish_data_sync(
        db,
        user,
        source="serp",
        mode="manual",
        status="error" if failed == len(runs) else "ok",
        rows_imported=sum(row.result_count for row in runs),
        note=f"Bright Data SERP 查询 {len(runs)} 个关键词，失败 {failed} 个。",
    )
    db.commit()
    for row in runs:
        db.refresh(row)
    return SerpRunBatchOut(
        status="ok" if failed == 0 else "partial",
        configured=True,
        ran=len(runs),
        failed=failed,
        note=f"SERP 查询完成：关键词 {len(runs)} 个，失败 {failed} 个。",
        runs=[_serp_run_out(row) for row in runs],
    )


@router.post("/performance/pagespeed", response_model=list[PageSpeedAuditOut])
def run_pagespeed_audits(
    body: PageSpeedRunIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PageSpeedAuditOut]:
    tenant = _tenant(db, user)
    if not tenant.site_origin:
        raise HTTPException(status_code=400, detail="请先设置客户官网，再运行测速。")
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).order_by(SitePage.path).all()
    urls = _pagespeed_targets(tenant, pages, body.urls, body.limit)
    strategies = [s for s in body.strategies if s in {"mobile", "desktop"}] or ["mobile"]
    audits: list[PageSpeedAudit] = []
    for url in urls:
        for strategy in strategies:
            try:
                metrics = _run_pagespeed(db, user.tenant_id, url, strategy)
                audit = PageSpeedAudit(tenant_id=user.tenant_id, url=url, strategy=strategy, status="ok", **metrics)
            except Exception as exc:
                audit = PageSpeedAudit(
                    tenant_id=user.tenant_id,
                    url=url,
                    strategy=strategy,
                    status="error",
                    detail=f"PageSpeed Insights 测速失败：{exc}",
                )
            db.add(audit)
            audits.append(audit)
    db.commit()
    for audit in audits:
        db.refresh(audit)
    return [PageSpeedAuditOut(**audit.__dict__) for audit in audits]
