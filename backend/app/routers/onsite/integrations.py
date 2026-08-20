import csv
from datetime import datetime, timedelta, timezone
from io import StringIO
from urllib.parse import quote, urlencode, urlparse

import httpx
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app import google_relay
from app.models import (
    DataSyncRun,
    GscConnection,
    GscSyncRun,
    IndexNowSubmission,
    IntegrationSetting,
    SeoPerformanceImport,
    SeoPerformanceRow,
    Tenant,
    User,
)
from app.onsite_fetch import build_fetch_url, normalize_origin, origin_host
from app.schemas import (
    BingStatusOut,
    DataSyncRunDueIn,
    DataSyncRunDueOut,
    DataSyncRunOut,
    DataSyncStatusOut,
    GscAuthUrlOut,
    GscConnectIn,
    GscStatusOut,
    GscSyncIn,
    GscSyncOut,
    IndexNowStatusOut,
    IndexNowSubmitIn,
    IndexNowSubmitOut,
    IntegrationFieldOut,
    IntegrationSettingsIn,
    IntegrationSettingsOut,
    SeoPerformanceImportIn,
    SeoPerformanceImportOut,
)

import app.routers.onsite as _onsite_pkg

from . import router
from .common import _csv_value, _parse_float, _parse_int, _tenant
from .constants import (
    GSC_AUTH_ENDPOINT,
    GSC_SCOPE,
    GSC_SEARCH_ANALYTICS_ENDPOINT,
    GSC_TOKEN_ENDPOINT,
    INDEXNOW_ENDPOINT,
    INTEGRATION_FIELDS,
    PERFORMANCE_SOURCE_LABELS,
)


def _gsc_redirect_uri(db: Session, tenant_id: str) -> str:
    return _integration_value(db, tenant_id, "gsc_oauth_redirect_uri") or f"{settings.frontend_origin.rstrip('/')}/onsite"


def _gsc_configured(db: Session, tenant_id: str) -> bool:
    return bool(
        _integration_value(db, tenant_id, "gsc_oauth_client_id")
        and _integration_value(db, tenant_id, "gsc_oauth_client_secret")
    )


def _gsc_connection(db: Session, tenant_id: str) -> GscConnection | None:
    return db.query(GscConnection).filter(GscConnection.tenant_id == tenant_id).first()


def _gsc_status(db: Session, user: User) -> GscStatusOut:
    conn = _gsc_connection(db, user.tenant_id)
    configured = _gsc_configured(db, user.tenant_id)
    connected = bool(conn and conn.status == "connected" and conn.refresh_token)
    note = "已连接，可同步 Google Search Console 数据。" if connected else "需要客户授权 Google Search Console。"
    if not configured:
        note = "服务器未配置 GSC OAuth Client ID / Secret。"
    elif not google_relay.configured():
        note = f"{note} 服务端未配 Google 中转（GOOGLE_RELAY_URL / GOOGLE_RELAY_KEY）。北京同步会直连 Google 并失败。"
    else:
        note = f"{note} 换 token 与同步走 Cloudflare Worker，不直连 Google。"
    return GscStatusOut(
        configured=configured,
        connected=connected,
        relay_configured=google_relay.configured(),
        status=conn.status if conn else "disconnected",
        site_url=conn.site_url if conn else "",
        last_sync_at=conn.last_sync_at if conn else None,
        last_error=conn.last_error if conn else "",
        redirect_uri=_gsc_redirect_uri(db, user.tenant_id),
        note=note,
    )


def _gsc_site_url(tenant: Tenant, raw: str) -> str:
    text = (raw or "").strip() or tenant.site_origin or ""
    if not text:
        raise HTTPException(status_code=400, detail="请先设置客户官网或填写 GSC property URL。")
    if text.startswith("sc-domain:"):
        return text
    origin = normalize_origin(text)
    return origin.rstrip("/") + "/"


def _exchange_gsc_code(db: Session, user: User, code: str) -> dict:
    response = google_relay.request(
        "POST",
        GSC_TOKEN_ENDPOINT,
        data={
            "code": code,
            "client_id": _integration_value(db, user.tenant_id, "gsc_oauth_client_id"),
            "client_secret": _integration_value(db, user.tenant_id, "gsc_oauth_client_secret"),
            "redirect_uri": _gsc_redirect_uri(db, user.tenant_id),
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail=f"GSC 授权失败：{response.text[:500]}")
    return response.json()


def _refresh_gsc_token(db: Session, conn: GscConnection) -> str:
    if conn.access_token and conn.token_expires_at and conn.token_expires_at > datetime.now(timezone.utc) + timedelta(minutes=5):
        return conn.access_token
    if not conn.refresh_token:
        raise HTTPException(status_code=400, detail="GSC refresh token 缺失，请重新授权。")
    response = google_relay.request(
        "POST",
        GSC_TOKEN_ENDPOINT,
        data={
            "client_id": _integration_value(db, conn.tenant_id, "gsc_oauth_client_id"),
            "client_secret": _integration_value(db, conn.tenant_id, "gsc_oauth_client_secret"),
            "refresh_token": conn.refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    if response.status_code >= 400:
        conn.status = "error"
        conn.last_error = response.text[:1000]
        raise HTTPException(status_code=400, detail=f"GSC token 刷新失败：{response.text[:500]}")
    data = response.json()
    conn.access_token = data.get("access_token", "")
    expires_in = int(data.get("expires_in") or 3600)
    conn.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    conn.status = "connected"
    conn.last_error = ""
    return conn.access_token


def _gsc_date_range(days: int) -> tuple[str, str]:
    end = datetime.now(timezone.utc).date() - timedelta(days=2)
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def _finish_data_sync(
    db: Session,
    user: User,
    *,
    source: str,
    mode: str,
    status: str,
    rows_imported: int = 0,
    submitted: int = 0,
    note: str = "",
) -> DataSyncRun:
    row = DataSyncRun(
        tenant_id=user.tenant_id,
        source=source,
        mode=mode,
        status=status,
        rows_imported=rows_imported,
        submitted=submitted,
        note=note,
        finished_at=datetime.now(timezone.utc),
    )
    db.add(row)
    return row


def _integration_rows(db: Session | None, tenant_id: str) -> dict[str, IntegrationSetting]:
    if db is None:
        return {}
    rows = db.query(IntegrationSetting).filter(IntegrationSetting.tenant_id == tenant_id).all()
    return {row.key: row for row in rows}


def _integration_value(db: Session | None, tenant_id: str, key: str) -> str:
    if key not in INTEGRATION_FIELDS:
        return ""
    row = _integration_rows(db, tenant_id).get(key)
    if row and row.value.strip():
        return row.value.strip()
    fallback = getattr(settings, INTEGRATION_FIELDS[key][1], "")
    return (fallback or "").strip()


def _integration_source(db: Session | None, tenant_id: str, key: str) -> str:
    row = _integration_rows(db, tenant_id).get(key)
    if row and row.value.strip():
        return "database"
    if (getattr(settings, INTEGRATION_FIELDS[key][1], "") or "").strip():
        return "env"
    return "none"


def _mask_secret(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if len(text) <= 8:
        return "*" * len(text)
    return f"{text[:4]}...{text[-4:]}"


def _integration_settings_out(db: Session, tenant_id: str) -> IntegrationSettingsOut:
    fields = [
        IntegrationFieldOut(
            key=key,
            label=label,
            configured=bool(_integration_value(db, tenant_id, key)),
            masked_value=_mask_secret(_integration_value(db, tenant_id, key)),
            source=_integration_source(db, tenant_id, key),
        )
        for key, (label, _setting_attr) in INTEGRATION_FIELDS.items()
    ]
    return IntegrationSettingsOut(
        fields=fields,
        gsc_configured=bool(
            _integration_value(db, tenant_id, "gsc_oauth_client_id")
            and _integration_value(db, tenant_id, "gsc_oauth_client_secret")
        ),
        pagespeed_configured=bool(_integration_value(db, tenant_id, "pagespeed_api_key")),
        google_relay_configured=google_relay.configured(),
        ce17_configured=bool(
            _integration_value(db, tenant_id, "ce17_user")
            and _integration_value(db, tenant_id, "ce17_api_pwd")
        ),
        brightdata_serp_configured=bool(
            _integration_value(db, tenant_id, "brightdata_dataset_api_key")
            and _integration_value(db, tenant_id, "brightdata_serp_dataset_id")
        ),
    )


def _gsc_sync_due(conn: GscConnection) -> bool:
    if not conn.last_sync_at:
        return True
    last_sync = conn.last_sync_at
    if last_sync.tzinfo is None:
        last_sync = last_sync.replace(tzinfo=timezone.utc)
    interval = max(1, settings.gsc_auto_sync_min_interval_hours)
    return last_sync <= datetime.now(timezone.utc) - timedelta(hours=interval)


def _sync_gsc_rows(db: Session, user: User, conn: GscConnection, body: GscSyncIn, *, mode: str = "manual") -> GscSyncOut:
    token = _onsite_pkg._refresh_gsc_token(db, conn)
    date_start, date_end = _gsc_date_range(body.days)
    run = GscSyncRun(
        tenant_id=user.tenant_id,
        connection_id=conn.id,
        status="running",
        date_start=date_start,
        date_end=date_end,
        note="GSC Search Analytics 同步中。",
    )
    db.add(run)
    db.flush()
    url = GSC_SEARCH_ANALYTICS_ENDPOINT.format(site_url=quote(conn.site_url, safe=""))
    payload = {
        "startDate": date_start,
        "endDate": date_end,
        "dimensions": ["date", "query", "page", "country", "device"],
        "rowLimit": body.row_limit,
    }
    try:
        response = google_relay.request(
            "POST",
            url,
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=60,
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"GSC 同步失败：{response.text[:500]}")
        data = response.json()
        imported = SeoPerformanceImport(
            tenant_id=user.tenant_id,
            source="gsc_api",
            filename=f"GSC API {date_start}~{date_end}",
            imported_by=user.id,
            note=f"Google Search Console API 自动同步，property={conn.site_url}",
        )
        db.add(imported)
        db.flush()
        count = 0
        for row in data.get("rows") or []:
            keys = row.get("keys") or []
            if len(keys) < 5:
                continue
            impressions = _parse_int(str(row.get("impressions", "")))
            clicks = _parse_int(str(row.get("clicks", "")))
            db.add(
                SeoPerformanceRow(
                    tenant_id=user.tenant_id,
                    import_id=imported.id,
                    source="gsc_api",
                    date=str(keys[0]),
                    query=str(keys[1]),
                    page_url=str(keys[2]),
                    country=str(keys[3]),
                    device=str(keys[4]),
                    clicks=clicks,
                    impressions=impressions,
                    ctr=round(float(row.get("ctr") or 0) * 100, 4),
                    position=round(float(row.get("position") or 0), 2) if row.get("position") is not None else None,
                )
            )
            count += 1
        imported.rows_imported = count
        run.status = "ok"
        run.rows_imported = count
        run.note = "GSC Search Analytics 同步完成。"
        run.finished_at = datetime.now(timezone.utc)
        conn.status = "connected"
        conn.last_sync_at = run.finished_at
        conn.last_error = ""
        _finish_data_sync(
            db,
            user,
            source="gsc",
            mode=mode,
            status="ok",
            rows_imported=count,
            note=f"GSC Search Analytics {date_start}~{date_end}",
        )
        db.commit()
        return GscSyncOut(status="ok", rows_imported=count, date_start=date_start, date_end=date_end, note=run.note)
    except HTTPException as exc:
        run.status = "error"
        run.note = str(exc.detail)
        run.finished_at = datetime.now(timezone.utc)
        conn.status = "error"
        conn.last_error = str(exc.detail)
        _finish_data_sync(db, user, source="gsc", mode=mode, status="error", note=str(exc.detail))
        db.commit()
        raise


def _indexnow_key_location(tenant: Tenant) -> str:
    if settings.indexnow_key_location:
        return settings.indexnow_key_location
    origin = normalize_origin(tenant.site_origin or "")
    return f"{origin.rstrip('/')}/{settings.indexnow_key}.txt" if settings.indexnow_key else ""


def _indexnow_urls(tenant: Tenant, body: IndexNowSubmitIn) -> list[str]:
    origin = normalize_origin(tenant.site_origin or "")
    seen: set[str] = set()
    urls: list[str] = []
    for raw in [*body.urls, *body.paths]:
        item = raw.strip()
        if not item:
            continue
        url = item if urlparse(item).scheme else build_fetch_url(origin, item)
        if urlparse(url).hostname != urlparse(origin).hostname:
            continue
        if url not in seen:
            urls.append(url)
            seen.add(url)
    return urls[:10000]


@router.get("/integrations", response_model=IntegrationSettingsOut)
def get_integration_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> IntegrationSettingsOut:
    return _integration_settings_out(db, user.tenant_id)


@router.patch("/integrations", response_model=IntegrationSettingsOut)
def update_integration_settings(
    body: IntegrationSettingsIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IntegrationSettingsOut:
    existing = _integration_rows(db, user.tenant_id)
    for key in body.clear_keys:
        if key not in INTEGRATION_FIELDS:
            continue
        row = existing.get(key)
        if row:
            db.delete(row)

    values = body.model_dump(exclude={"clear_keys"}, exclude_none=True)
    for key, raw in values.items():
        if key not in INTEGRATION_FIELDS:
            continue
        value = str(raw or "").strip()
        if not value:
            continue
        row = existing.get(key)
        if row is None:
            row = IntegrationSetting(tenant_id=user.tenant_id, key=key)
            db.add(row)
        row.value = value
        row.updated_by = user.id

    db.commit()
    return _integration_settings_out(db, user.tenant_id)


@router.get("/gsc/status", response_model=GscStatusOut)
def gsc_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GscStatusOut:
    return _gsc_status(db, user)


@router.get("/gsc/auth-url", response_model=GscAuthUrlOut)
def gsc_auth_url(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GscAuthUrlOut:
    if not _gsc_configured(db, user.tenant_id):
        return GscAuthUrlOut(configured=False, redirect_uri=_gsc_redirect_uri(db, user.tenant_id), note="服务器未配置 GSC OAuth Client ID / Secret。")
    params = {
        "client_id": _integration_value(db, user.tenant_id, "gsc_oauth_client_id"),
        "redirect_uri": _gsc_redirect_uri(db, user.tenant_id),
        "response_type": "code",
        "scope": GSC_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": user.tenant_id,
    }
    note = "打开授权链接后，Google 会回到诊断页并带上 code。浏览器授权不走中转。"
    if not google_relay.configured():
        note += " 服务端未配 GOOGLE_RELAY_*，北京换 token / 同步仍会直连 Google。"
    return GscAuthUrlOut(
        configured=True,
        auth_url=f"{GSC_AUTH_ENDPOINT}?{urlencode(params)}",
        redirect_uri=_gsc_redirect_uri(db, user.tenant_id),
        note=note,
    )


@router.post("/gsc/connect", response_model=GscStatusOut)
def gsc_connect(
    body: GscConnectIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GscStatusOut:
    if not _gsc_configured(db, user.tenant_id):
        raise HTTPException(status_code=400, detail="服务器未配置 GSC OAuth Client ID / Secret。")
    tenant = _tenant(db, user)
    data = _onsite_pkg._exchange_gsc_code(db, user, body.code)
    conn = _gsc_connection(db, user.tenant_id)
    if conn is None:
        conn = GscConnection(tenant_id=user.tenant_id)
        db.add(conn)
    conn.site_url = _gsc_site_url(tenant, body.site_url)
    conn.status = "connected"
    conn.access_token = data.get("access_token", "")
    if data.get("refresh_token"):
        conn.refresh_token = data.get("refresh_token", "")
    conn.scopes = data.get("scope", GSC_SCOPE)
    expires_in = int(data.get("expires_in") or 3600)
    conn.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    conn.connected_by = user.id
    conn.last_error = ""
    db.commit()
    return _gsc_status(db, user)


@router.post("/gsc/sync", response_model=GscSyncOut)
def gsc_sync(
    body: GscSyncIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GscSyncOut:
    if not _gsc_configured(db, user.tenant_id):
        raise HTTPException(status_code=400, detail="服务器未配置 GSC OAuth Client ID / Secret。")
    conn = _gsc_connection(db, user.tenant_id)
    if conn is None or not conn.refresh_token:
        raise HTTPException(status_code=400, detail="尚未连接 Google Search Console。")
    return _sync_gsc_rows(db, user, conn, body)


@router.get("/data-sync/status", response_model=DataSyncStatusOut)
def data_sync_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DataSyncStatusOut:
    rows = (
        db.query(DataSyncRun)
        .filter(DataSyncRun.tenant_id == user.tenant_id)
        .order_by(DataSyncRun.started_at.desc())
        .limit(12)
        .all()
    )
    return DataSyncStatusOut(runs=[DataSyncRunOut(**row.__dict__) for row in rows])


@router.post("/data-sync/run-due", response_model=DataSyncRunDueOut)
def data_sync_run_due(
    body: DataSyncRunDueIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DataSyncRunDueOut:
    requested = set(body.sources or ["gsc"])
    if "gsc" not in requested:
        return DataSyncRunDueOut(status="skipped", skipped=1, note="本次没有请求可自动同步的数据源。")
    if not _gsc_configured(db, user.tenant_id):
        return DataSyncRunDueOut(status="skipped", skipped=1, note="GSC OAuth 未配置，无法执行自动同步。")
    conn = _gsc_connection(db, user.tenant_id)
    if conn is None or not conn.refresh_token:
        return DataSyncRunDueOut(status="skipped", skipped=1, note="尚未连接 Google Search Console。")
    if not body.force and not _gsc_sync_due(conn):
        return DataSyncRunDueOut(status="skipped", skipped=1, note="GSC 最近已同步，未达到自动同步间隔。")

    days = max(1, min(180, settings.gsc_auto_sync_days))
    result = _sync_gsc_rows(db, user, conn, GscSyncIn(days=days, row_limit=25000), mode="manual" if body.force else "scheduled")
    latest = (
        db.query(DataSyncRun)
        .filter(DataSyncRun.tenant_id == user.tenant_id, DataSyncRun.source == "gsc")
        .order_by(DataSyncRun.started_at.desc())
        .limit(1)
        .all()
    )
    return DataSyncRunDueOut(
        status="ok",
        ran=1,
        runs=[DataSyncRunOut(**row.__dict__) for row in latest],
        note=f"{result.note} {result.date_start} 至 {result.date_end}，导入 {result.rows_imported} 行。",
    )


@router.get("/bing/status", response_model=BingStatusOut)
def bing_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> BingStatusOut:
    configured = bool(settings.bing_webmaster_api_key)
    return BingStatusOut(
        configured=configured,
        status="configured" if configured else "unconfigured",
        note="Bing Webmaster API Key 已配置；下一步可接入具体站点数据同步。" if configured else "服务器未配置 Bing Webmaster API Key。本阶段不编造 Bing 数据。",
    )


@router.get("/indexnow/status", response_model=IndexNowStatusOut)
def indexnow_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> IndexNowStatusOut:
    tenant = _tenant(db, user)
    last = (
        db.query(IndexNowSubmission)
        .filter(IndexNowSubmission.tenant_id == user.tenant_id)
        .order_by(IndexNowSubmission.submitted_at.desc())
        .first()
    )
    host = origin_host(normalize_origin(tenant.site_origin)) if tenant.site_origin else ""
    configured = bool(settings.indexnow_key and tenant.site_origin)
    return IndexNowStatusOut(
        configured=configured,
        host=host,
        key_location=_indexnow_key_location(tenant) if configured else "",
        last_submitted_at=last.submitted_at if last else None,
        last_status=last.status if last else "",
        note="IndexNow 可提交 URL 更新通知；不保证抓取、收录或排名。" if configured else "请先配置 INDEXNOW_KEY 并设置客户官网。",
    )


@router.post("/indexnow/submit", response_model=IndexNowSubmitOut)
def indexnow_submit(
    body: IndexNowSubmitIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IndexNowSubmitOut:
    tenant = _tenant(db, user)
    if not settings.indexnow_key:
        raise HTTPException(status_code=400, detail="服务器未配置 INDEXNOW_KEY。")
    if not tenant.site_origin:
        raise HTTPException(status_code=400, detail="请先设置客户官网。")
    urls = _indexnow_urls(tenant, body)
    if not urls:
        raise HTTPException(status_code=400, detail="没有可提交的同域 URL。")
    host = origin_host(normalize_origin(tenant.site_origin))
    payload = {
        "host": host,
        "key": settings.indexnow_key,
        "keyLocation": _indexnow_key_location(tenant),
        "urlList": urls,
    }
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(INDEXNOW_ENDPOINT, json=payload)
        status = "submitted" if response.status_code in {200, 202} else "error"
        note = "IndexNow 已接收 URL 更新通知；这不保证收录或排名。" if status == "submitted" else f"IndexNow 返回异常：{response.text[:500]}"
    except httpx.HTTPError as exc:
        response = None
        status = "error"
        note = f"IndexNow 提交失败：{exc}"
    db.add(
        IndexNowSubmission(
            tenant_id=user.tenant_id,
            host=host,
            key_location=payload["keyLocation"],
            urls="\n".join(urls),
            status=status,
            http_status=response.status_code if response is not None else None,
            response_text=(response.text if response is not None else note)[:1000],
            submitted_by=user.id,
        )
    )
    _finish_data_sync(db, user, source="indexnow", mode="manual", status=status, submitted=len(urls), note=note)
    db.commit()
    return IndexNowSubmitOut(status=status, submitted=len(urls), http_status=response.status_code if response is not None else None, note=note)


@router.post("/performance/import-csv", response_model=SeoPerformanceImportOut, status_code=201)
def import_seo_performance_csv(
    body: SeoPerformanceImportIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SeoPerformanceImportOut:
    reader = csv.DictReader(StringIO(body.csv_text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV 没有表头，无法识别字段。")
    imported = SeoPerformanceImport(
        tenant_id=user.tenant_id,
        source=body.source,
        filename=body.filename or PERFORMANCE_SOURCE_LABELS.get(body.source, body.source),
        imported_by=user.id,
        note="已按中英文常见字段解析 clicks / impressions / CTR / position。",
    )
    db.add(imported)
    db.flush()
    count = 0
    for raw in reader:
        clicks = _parse_int(_csv_value(raw, "clicks"))
        impressions = _parse_int(_csv_value(raw, "impressions"))
        query = _csv_value(raw, "query")
        page_url = _csv_value(raw, "page_url")
        if not any([clicks, impressions, query, page_url]):
            continue
        db.add(
            SeoPerformanceRow(
                tenant_id=user.tenant_id,
                import_id=imported.id,
                source=body.source,
                date=_csv_value(raw, "date"),
                country=_csv_value(raw, "country"),
                device=_csv_value(raw, "device"),
                query=query,
                page_url=page_url,
                clicks=clicks,
                impressions=impressions,
                ctr=_parse_float(_csv_value(raw, "ctr")),
                position=_parse_float(_csv_value(raw, "position")),
            )
        )
        count += 1
    if count == 0:
        raise HTTPException(status_code=400, detail="没有识别到可导入的搜索表现数据。请确认 CSV 包含查询、页面、点击、曝光等字段。")
    imported.rows_imported = count
    db.commit()
    db.refresh(imported)
    return SeoPerformanceImportOut(**imported.__dict__)
