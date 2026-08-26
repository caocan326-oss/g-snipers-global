"""Keep the live customer name/prompts from being overwritten by the lock demo seed."""

from __future__ import annotations

from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models import (
    BacklinkGap,
    DemandSignal,
    DistributionJob,
    GeoAsset,
    GeoObservation,
    GeoPrompt,
    GeoSampleResult,
    GeoTicket,
    OutreachItem,
    Tenant,
)
from app.onsite_fetch import OriginError, normalize_origin, origin_host

DEMO_TENANT_NAME = "演示客户 · 智能门锁出海"
SNIPERS_HOSTS = {"snipers.com.cn", "www.snipers.com.cn"}
LOCK_PROMPT_MARKERS = (
    "smart lock",
    "スマートロック",
    "renters install",
    "賃貸でスマートロック",
    "智能锁",
    "智能门锁",
)
LOCK_KEYWORD_EXACT = {"smart lock for renters", "賃貸", "スマートロック", "許可"}
LOCK_GAP_MARKERS = ("smarthome-weekly.example", "old-blog.example", "renters-lock")
LOCK_GAP_COMPETITORS = {"august home", "level lock", "qrio", "nuki"}
LOCK_ASSET_MARKERS = (
    "智能门锁",
    "演示客户",
    "smart lock",
    "renters",
    "賃貸",
    "スマートロック",
    "snipers.com.cn",
)


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


def is_lock_leftover_text(text: str) -> bool:
    blob = (text or "").lower()
    return bool(blob) and any(marker.lower() in blob for marker in LOCK_PROMPT_MARKERS)


def is_buyer_question(text: str) -> bool:
    """A recorded buyer sentence, not a 1–3 word keyword and not a lock leftover."""
    raw = (text or "").strip()
    if not raw or is_lock_leftover_text(raw):
        return False
    if "?" in raw or "？" in raw:
        return True
    if len(raw.split()) >= 6:
        return True
    starters = ("怎么", "什么", "哪家", "哪些", "如何", "有没有", "能不能", "是否")
    return len(raw) >= 8 and any(mark in raw for mark in starters)


def _purge_lock_prompt(db: Session, prompt: GeoPrompt) -> None:
    db.query(GeoSampleResult).filter(GeoSampleResult.prompt_id == prompt.id).delete(synchronize_session=False)
    db.query(GeoObservation).filter(GeoObservation.prompt_id == prompt.id).delete(synchronize_session=False)
    db.query(GeoTicket).filter(GeoTicket.prompt_id == prompt.id).delete(synchronize_session=False)
    db.delete(prompt)


def adopt_live_site(db: Session, tenant: Tenant) -> str:
    """Rename the demo lock tenant and archive lock leftover prompts/keywords."""
    if not tenant.site_origin:
        return ""
    if tenant.name == DEMO_TENANT_NAME and is_snipers_host(tenant.site_origin):
        return ""
    notes: list[str] = []
    next_name = name_from_origin(tenant.site_origin)
    if tenant.name == DEMO_TENANT_NAME and next_name:
        tenant.name = next_name
        notes.append(f"客户名改为 {next_name}")

    archived = 0
    for row in db.query(DemandSignal).filter(DemandSignal.tenant_id == tenant.id).all():
        theme = (row.theme or "").strip().lower()
        if theme in LOCK_KEYWORD_EXACT or is_lock_leftover_text(theme):
            row.source = "target_archived"
            archived += 1
    if archived:
        notes.append(f"已归档 {archived} 条门锁搜索词")

    prompts = db.query(GeoPrompt).filter(GeoPrompt.tenant_id == tenant.id).all()
    removed = 0
    for prompt in prompts:
        if is_lock_leftover_text(prompt.prompt_text or ""):
            _purge_lock_prompt(db, prompt)
            removed += 1
    if removed:
        notes.append(f"已去掉 {removed} 条门锁买家问题")

    tickets_removed = 0
    for ticket in db.query(GeoTicket).filter(GeoTicket.tenant_id == tenant.id).all():
        blob = " ".join([ticket.title or "", ticket.recommended_action or "", ticket.rationale or ""])
        if is_lock_leftover_text(blob):
            prompt = db.get(GeoPrompt, ticket.prompt_id) if ticket.prompt_id else None
            if prompt is not None:
                _purge_lock_prompt(db, prompt)
            else:
                db.delete(ticket)
            tickets_removed += 1
    if tickets_removed:
        notes.append(f"已去掉 {tickets_removed} 条门锁待处理项")

    gaps = 0
    for gap in db.query(BacklinkGap).filter(BacklinkGap.tenant_id == tenant.id).all():
        host = (gap.referring_domain or "").lower()
        blob = " ".join([host, gap.link_url or "", gap.title or "", gap.competitor_name or ""]).lower()
        demo_host = host.endswith(".example") or any(marker in blob for marker in LOCK_GAP_MARKERS)
        demo_brand = (gap.competitor_name or "").strip().lower() in LOCK_GAP_COMPETITORS
        if demo_host or demo_brand:
            db.query(OutreachItem).filter(OutreachItem.gap_id == gap.id).delete(synchronize_session=False)
            for job in db.query(DistributionJob).filter(DistributionJob.gap_id == gap.id).all():
                job.gap_id = None
            db.delete(gap)
            gaps += 1
    if gaps:
        notes.append(f"已去掉 {gaps} 条门锁/演示站外示例")

    if not is_snipers_host(tenant.site_origin):
        assets_cleared = 0
        for asset in db.query(GeoAsset).filter(GeoAsset.tenant_id == tenant.id).all():
            blob = f"{asset.title}\n{asset.body}".lower()
            if any(marker.lower() in blob for marker in LOCK_ASSET_MARKERS):
                asset.body = ""
                if asset.kind == "cite_checklist":
                    asset.title = "可供引用的材料"
                elif asset.kind == "llms_txt":
                    asset.title = "llms.txt 草稿"
                asset.status = "draft"
                assets_cleared += 1
        if assets_cleared:
            notes.append(f"已清空 {assets_cleared} 份门锁/演示引用材料")

    return "；".join(notes)
