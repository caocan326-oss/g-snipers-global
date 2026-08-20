import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.onsite_fetch import OriginError, normalize_origin, origin_host
from app.models import (
    AiRun,
    BacklinkGap,
    Competitor,
    ContentAsset,
    CrawlSession,
    DataSyncRun,
    DemandSignal,
    DistributionAttempt,
    DistributionJob,
    FactPack,
    GeoAsset,
    GeoChecklistItem,
    GeoObservation,
    GeoPrompt,
    GeoSampleResult,
    GeoSampleRun,
    GeoTicket,
    GscConnection,
    GscSyncRun,
    IndexNowSubmission,
    Inquiry,
    InsightBrief,
    Market,
    OnsiteIssue,
    OutreachItem,
    PageSpeedAudit,
    PlatformAccount,
    PlatformConnector,
    PublishConfirmation,
    SeoPage,
    SeoPerformanceImport,
    SeoPerformanceRow,
    SerpResult,
    SerpRun,
    SiteArchive,
    SitePage,
    SourcePlatform,
    Tenant,
    User,
    WorkOrder,
)


SNAPSHOT_MODELS = [
    Market,
    DemandSignal,
    Competitor,
    InsightBrief,
    SeoPage,
    WorkOrder,
    Inquiry,
    GeoAsset,
    GeoPrompt,
    GeoObservation,
    GeoTicket,
    GeoSampleRun,
    GeoSampleResult,
    GeoChecklistItem,
    SitePage,
    OnsiteIssue,
    CrawlSession,
    SeoPerformanceImport,
    SeoPerformanceRow,
    PageSpeedAudit,
    SerpRun,
    SerpResult,
    DataSyncRun,
    IndexNowSubmission,
    SourcePlatform,
    PlatformAccount,
    PlatformConnector,
    FactPack,
    ContentAsset,
    BacklinkGap,
    OutreachItem,
    DistributionJob,
    DistributionAttempt,
    AiRun,
    PublishConfirmation,
]

CLEAR_ONLY_MODELS = [GscSyncRun, GscConnection]
DELETE_MODELS = list(reversed(SNAPSHOT_MODELS)) + CLEAR_ONLY_MODELS


COUNT_LABELS = {
    "markets": "目标国家",
    "demand_signals": "关键词",
    "competitors": "竞品",
    "site_pages": "抓取页面",
    "onsite_issues": "SEO 问题",
    "geo_prompts": "GEO 问句",
    "geo_sample_runs": "GEO 采样",
    "seo_performance_rows": "搜索表现记录",
    "pagespeed_audits": "测速记录",
    "serp_runs": "关键词排名查询",
    "backlink_gaps": "站外渠道",
    "distribution_jobs": "站外执行任务",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return {"__datetime__": value.isoformat()}
    return value


def _from_json_value(value: Any) -> Any:
    if isinstance(value, dict) and "__datetime__" in value:
        raw = value["__datetime__"]
        if not raw:
            return None
        return datetime.fromisoformat(raw)
    return value


def _row_to_dict(row: object) -> dict[str, Any]:
    return {column.name: _json_value(getattr(row, column.name)) for column in row.__table__.columns}


def _rows_for(db: Session, tenant_id: str, model: type) -> list[dict[str, Any]]:
    return [_row_to_dict(row) for row in db.query(model).filter(model.tenant_id == tenant_id).all()]


def snapshot_counts(snapshot: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    return {table: len(rows) for table, rows in snapshot.items()}


def readable_counts(counts: dict[str, int]) -> dict[str, int]:
    return {COUNT_LABELS.get(key, key): value for key, value in counts.items() if value}


def site_host_changed(old_origin: str | None, new_origin: str | None) -> bool:
    """True only when both origins resolve to a different host.

    Host-only comparison so a scheme/path/query edit on the same site
    doesn't trigger a data wipe. This is the single source of truth for
    "did the site change" — every endpoint that can update site_origin
    must go through it instead of re-deriving its own comparison.
    """
    old_host = origin_host(normalize_origin(old_origin)) if old_origin else ""
    new_host = origin_host(normalize_origin(new_origin)) if new_origin else ""
    return bool(old_host and new_host and old_host != new_host)


class SiteSwitchError(ValueError):
    pass


def latest_archive_for_origin(db: Session, tenant_id: str, origin: str | None) -> SiteArchive | None:
    if not origin:
        return None
    try:
        host = origin_host(normalize_origin(origin))
    except OriginError:
        return None
    archives = (
        db.query(SiteArchive)
        .filter(SiteArchive.tenant_id == tenant_id)
        .order_by(SiteArchive.archived_at.desc())
        .all()
    )
    for archive in archives:
        try:
            if origin_host(normalize_origin(archive.site_origin)) == host:
                return archive
        except OriginError:
            continue
    return None


def prepare_site_switch(
    db: Session,
    user: User,
    *,
    old_origin: str | None,
    new_origin: str | None,
    confirm: bool,
) -> dict[str, Any]:
    """Archive current site when the host changes. Reuse the latest matching archive."""
    if not new_origin or not site_host_changed(old_origin, new_origin):
        return {"changed": False, "restored": False, "note": ""}
    if not confirm:
        raise SiteSwitchError(
            f"更换官网会归档当前工作台（{old_origin or '未设置'} → {new_origin}）。确认后才会切换；若该官网查过，会恢复历史数据，不会再造空站。"
        )
    archive_current_context(db, user, note=f"切换到 {new_origin} 前自动归档")
    existing = latest_archive_for_origin(db, user.tenant_id, new_origin)
    if existing:
        restore_archive_context(db, user, existing)
        return {
            "changed": True,
            "restored": True,
            "note": f"已恢复历史网站 {existing.site_origin}。刚才的网站已归档，可在历史网站里查看。",
        }
    reset_current_context(db, user)
    return {
        "changed": True,
        "restored": False,
        "note": f"已切换到 {new_origin}。原网站已归档，可在历史网站里恢复。",
    }


def archive_and_reset_if_site_changed(
    db: Session,
    user: User,
    *,
    old_origin: str | None,
    new_origin: str | None,
) -> bool:
    """Archive + reset tenant data iff the site host actually changed."""
    changed = site_host_changed(old_origin, new_origin)
    if changed:
        archive_current_context(db, user, note=f"切换到 {new_origin} 前自动归档")
        reset_current_context(db, user)
    return changed


def archive_current_context(db: Session, user: User, *, note: str = "") -> SiteArchive | None:
    tenant = db.get(Tenant, user.tenant_id)
    site_origin = (tenant.site_origin if tenant else "").strip()
    if not site_origin:
        return None
    snapshot = {model.__tablename__: _rows_for(db, user.tenant_id, model) for model in SNAPSHOT_MODELS}
    counts = snapshot_counts(snapshot)
    if not any(counts.values()):
        return None
    archive = SiteArchive(
        tenant_id=user.tenant_id,
        site_origin=site_origin,
        snapshot_json=json.dumps(snapshot, ensure_ascii=False),
        counts_json=json.dumps(counts, ensure_ascii=False),
        note=note,
        archived_by=user.id,
    )
    db.add(archive)
    db.flush()
    return archive


def reset_current_context(db: Session, user: User) -> None:
    for model in DELETE_MODELS:
        db.query(model).filter(model.tenant_id == user.tenant_id).delete(synchronize_session=False)
    db.flush()


def restore_archive_context(db: Session, user: User, archive: SiteArchive) -> None:
    snapshot = json.loads(archive.snapshot_json or "{}")
    reset_current_context(db, user)
    for model in SNAPSHOT_MODELS:
        rows = snapshot.get(model.__tablename__, [])
        for row in rows:
            values = {key: _from_json_value(value) for key, value in row.items()}
            values["tenant_id"] = user.tenant_id
            db.add(model(**values))
        if rows:
            db.flush()
    tenant = db.get(Tenant, user.tenant_id)
    if tenant:
        tenant.site_origin = archive.site_origin
    archive.restored_at = _now()
    db.flush()
