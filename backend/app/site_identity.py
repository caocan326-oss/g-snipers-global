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
    Inquiry,
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
LOCK_INQUIRY_MARKERS = (
    "alex@example.com",
    "加州物业经理",
    "多门锁",
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


def is_lock_inquiry_text(*parts: str) -> bool:
    """Seed leftover from the lock demo (alex@example.com / 多门锁), not a real lead."""
    blob = " ".join(part or "" for part in parts)
    if is_lock_leftover_text(blob):
        return True
    lower = blob.lower()
    return bool(lower) and any(marker.lower() in lower for marker in LOCK_INQUIRY_MARKERS)


def is_lock_asset_text(text: str, *, keep_snipers_cite: bool = False) -> bool:
    """Lock-demo cite/llms copy. SNIPERS own cite that only mentions snipers.com.cn is kept."""
    blob = (text or "").lower()
    if not blob:
        return False
    markers = LOCK_ASSET_MARKERS
    if keep_snipers_cite:
        markers = tuple(item for item in markers if item != "snipers.com.cn")
    return any(marker.lower() in blob for marker in markers)


def honest_empty_llms(tenant_name: str) -> str:
    name = (tenant_name or "").strip() or "客户"
    return (
        f"# {name}\n\n"
        "> 这是给客户经理改稿的 llms.txt 草稿，不是已发布文件，也不能证明任何模型引用了本站。\n\n"
        "## Pages\n"
        "- （门锁演示稿已清掉。没有已记页面可写。不要编。）\n"
    )


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


def is_recordable_question(text: str) -> bool:
    """Hand-written record: a sentence, not a one-word keyword."""
    raw = (text or "").strip()
    if not raw:
        return False
    if is_buyer_question(raw):
        return True
    return len(raw.split()) >= 3


def _purge_lock_prompt(db: Session, prompt: GeoPrompt) -> None:
    db.query(Inquiry).filter(Inquiry.related_prompt_id == prompt.id).update(
        {Inquiry.related_prompt_id: None}, synchronize_session=False
    )
    db.query(GeoSampleResult).filter(GeoSampleResult.prompt_id == prompt.id).delete(synchronize_session=False)
    db.query(GeoObservation).filter(GeoObservation.prompt_id == prompt.id).delete(synchronize_session=False)
    db.query(GeoTicket).filter(GeoTicket.prompt_id == prompt.id).delete(synchronize_session=False)
    db.delete(prompt)


def adopt_live_site(db: Session, tenant: Tenant) -> str:
    """Rename the demo lock tenant and drop lock leftover prompts/keywords/inquiries."""
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

    inquiries_removed = 0
    for row in db.query(Inquiry).filter(Inquiry.tenant_id == tenant.id).all():
        if is_lock_inquiry_text(row.contact or "", row.notes or ""):
            db.delete(row)
            inquiries_removed += 1
    if inquiries_removed:
        notes.append(f"已去掉 {inquiries_removed} 条门锁演示询盘")

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

    assets_cleared = 0
    on_snipers = is_snipers_host(tenant.site_origin)
    for asset in db.query(GeoAsset).filter(GeoAsset.tenant_id == tenant.id).all():
        blob = f"{asset.title}\n{asset.body}"
        if not is_lock_asset_text(blob, keep_snipers_cite=on_snipers):
            continue
        if asset.kind == "cite_checklist":
            asset.title = "可供引用的材料"
            asset.body = ""
        elif asset.kind == "llms_txt":
            asset.title = "llms.txt 草稿"
            asset.body = honest_empty_llms(tenant.name)
        else:
            asset.body = ""
        asset.status = "draft"
        assets_cleared += 1
    if assets_cleared:
        notes.append(f"已清空 {assets_cleared} 份门锁/演示引用材料")

    return "；".join(notes)
