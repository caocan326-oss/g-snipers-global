"""Keep the live customer name/prompts from being overwritten by the lock demo seed."""

from __future__ import annotations

from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models import BacklinkGap, DemandSignal, GeoObservation, GeoPrompt, GeoTicket, Tenant
from app.onsite_fetch import OriginError, normalize_origin, origin_host

DEMO_TENANT_NAME = "演示客户 · 智能门锁出海"
SNIPERS_HOSTS = {"snipers.com.cn", "www.snipers.com.cn"}
LOCK_PROMPT_MARKERS = ("smart lock", "スマートロック", "renters install", "賃貸でスマートロック")
LOCK_KEYWORD_EXACT = {"smart lock for renters", "賃貸", "スマートロック", "許可"}
LOCK_GAP_MARKERS = ("smarthome-weekly.example", "renters-lock")


def host_of(origin: str | None) -> str:
    text = (origin or "").strip()
    if not text:
        return ""
    try:
        return origin_host(normalize_origin(text))
    except OriginError:
        try:
            return (urlparse(text if "://" in text else f"https://{text}").hostname or "").lower()
        except ValueError:
            return ""


def is_snipers_host(origin: str | None) -> bool:
    host = host_of(origin)
    return host in SNIPERS_HOSTS or host.endswith(".snipers.com.cn")


def name_from_origin(origin: str | None) -> str:
    host = host_of(origin).removeprefix("www.")
    if not host:
        return ""
    label = host.split(".")[0]
    return label.upper() if label.isalpha() and len(label) <= 12 else host


def adopt_live_site(db: Session, tenant: Tenant) -> str:
    """Rename the demo lock tenant and archive lock leftover prompts/keywords."""
    if not tenant.site_origin or is_snipers_host(tenant.site_origin):
        return ""
    notes: list[str] = []
    next_name = name_from_origin(tenant.site_origin)
    if tenant.name == DEMO_TENANT_NAME and next_name:
        tenant.name = next_name
        notes.append(f"客户名改为 {next_name}")

    archived = 0
    for row in db.query(DemandSignal).filter(DemandSignal.tenant_id == tenant.id).all():
        theme = (row.theme or "").strip().lower()
        if theme in LOCK_KEYWORD_EXACT or any(marker in theme for marker in ("smart lock", "スマートロック")):
            row.source = "target_archived"
            archived += 1
    if archived:
        notes.append(f"已归档 {archived} 条门锁搜索词")

    prompts = db.query(GeoPrompt).filter(GeoPrompt.tenant_id == tenant.id).all()
    removed = 0
    for prompt in prompts:
        text = (prompt.prompt_text or "").lower()
        if any(marker.lower() in text for marker in LOCK_PROMPT_MARKERS):
            db.query(GeoObservation).filter(GeoObservation.prompt_id == prompt.id).delete(synchronize_session=False)
            db.query(GeoTicket).filter(GeoTicket.prompt_id == prompt.id).delete(synchronize_session=False)
            db.delete(prompt)
            removed += 1
    if removed:
        notes.append(f"已去掉 {removed} 条门锁买家问题")

    gaps = 0
    for gap in db.query(BacklinkGap).filter(BacklinkGap.tenant_id == tenant.id).all():
        blob = " ".join([gap.referring_domain or "", gap.link_url or "", gap.title or ""]).lower()
        if any(marker in blob for marker in LOCK_GAP_MARKERS):
            db.delete(gap)
            gaps += 1
    if gaps:
        notes.append(f"已去掉 {gaps} 条门锁站外示例")
    return "；".join(notes)
