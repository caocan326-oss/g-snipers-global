from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.ai_engine import assist_offsite_gap
from app.auth import get_current_user
from app.database import get_db
from app.models import BacklinkGap, OutreachItem, User
from app.schemas import (
    AiAssistOut,
    AiStepIn,
    BacklinkGapCreate,
    BacklinkGapOut,
    BacklinkGapUpdate,
    LinkCheckerOut,
    OutreachCreate,
    OutreachOut,
)

from . import router
from .common import _gap_out
from .constants import GAP_STATUSES, KINDS, OUTREACH_STATUSES, PRIORITIES, VERIFY_STATUSES


@router.get("/gaps", response_model=list[BacklinkGapOut])
def list_gaps(
    status: str | None = None,
    verify_status: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BacklinkGapOut]:
    q = (
        db.query(BacklinkGap)
        .options(selectinload(BacklinkGap.outreach))
        .filter(BacklinkGap.tenant_id == user.tenant_id)
    )
    if status:
        q = q.filter(BacklinkGap.status == status)
    if verify_status:
        q = q.filter(BacklinkGap.verify_status == verify_status)
    return [_gap_out(r) for r in q.order_by(BacklinkGap.created_at.desc()).all()]


@router.get("/checker", response_model=LinkCheckerOut)
def link_checker(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> LinkCheckerOut:
    rows = (
        db.query(BacklinkGap)
        .options(selectinload(BacklinkGap.outreach))
        .filter(BacklinkGap.tenant_id == user.tenant_id)
        .order_by(BacklinkGap.created_at.desc())
        .all()
    )
    counts = {key: 0 for key in VERIFY_STATUSES}
    for row in rows:
        key = row.verify_status if row.verify_status in counts else "unverified"
        counts[key] += 1
    return LinkCheckerOut(counts=counts, domain_metric="未测", links=[_gap_out(r) for r in rows])


@router.post("/gaps", response_model=BacklinkGapOut, status_code=201)
def create_gap(
    body: BacklinkGapCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BacklinkGapOut:
    if body.kind not in KINDS:
        raise HTTPException(status_code=400, detail="无效链接类型")
    if body.priority not in PRIORITIES:
        raise HTTPException(status_code=400, detail="无效优先级")
    payload = body.model_dump()
    if not payload.get("title"):
        payload["title"] = f"{body.referring_domain} · {('我方已覆盖' if body.kind == 'inbound' else '待处理曝光渠道')}"
    if not payload.get("acceptance_criteria"):
        payload["acceptance_criteria"] = "记录结果页面 URL，并完成结果页面核验。"
    if not payload.get("retest_method"):
        payload["retest_method"] = "复查 result_url 是否可访问、是否提及客户、是否链接到目标页。"
    row = BacklinkGap(
        tenant_id=user.tenant_id,
        domain_metric="untested",
        status="identified",
        verify_status="unverified",
        **payload,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    row.outreach = []
    return _gap_out(row)


@router.patch("/gaps/{gap_id}", response_model=BacklinkGapOut)
def update_gap(
    gap_id: str,
    status: str | None = None,
    body: BacklinkGapUpdate = BacklinkGapUpdate(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BacklinkGapOut:
    row = db.get(BacklinkGap, gap_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="缺口不存在")
    payload = body.model_dump(exclude_unset=True)
    next_status = status or payload.get("status")
    if next_status:
        if next_status not in GAP_STATUSES:
            raise HTTPException(status_code=400, detail="无效缺口状态")
        row.status = next_status
        row.closed_at = datetime.now(timezone.utc) if next_status in {"closed", "ignored", "won"} else None
    if "verify_status" in payload:
        if payload["verify_status"] not in VERIFY_STATUSES:
            raise HTTPException(status_code=400, detail="无效核验状态")
        row.verify_status = payload["verify_status"]
        row.last_checked_at = datetime.now(timezone.utc)
    if "notes" in payload:
        row.notes = payload["notes"]
    if "link_url" in payload:
        row.link_url = payload["link_url"]
    if "kind" in payload:
        if payload["kind"] not in KINDS:
            raise HTTPException(status_code=400, detail="无效链接类型")
        row.kind = payload["kind"]
    if "priority" in payload:
        if payload["priority"] not in PRIORITIES:
            raise HTTPException(status_code=400, detail="无效优先级")
        row.priority = payload["priority"]
    for field in (
        "title",
        "issue_type",
        "source",
        "source_platform_id",
        "owner_hint",
        "acceptance_criteria",
        "recommended_action",
        "retest_method",
        "retest_result",
        "result_url",
        "blocked_reason",
    ):
        if field in payload:
            setattr(row, field, payload[field] or "")
    db.commit()
    row = (
        db.query(BacklinkGap)
        .options(selectinload(BacklinkGap.outreach))
        .filter(BacklinkGap.id == gap_id)
        .one()
    )
    return _gap_out(row)


@router.post("/gaps/{gap_id}/outreach", response_model=OutreachOut, status_code=201)
def create_outreach(
    gap_id: str,
    body: OutreachCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OutreachItem:
    gap = db.get(BacklinkGap, gap_id)
    if gap is None or gap.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="缺口不存在")
    row = OutreachItem(
        tenant_id=user.tenant_id,
        gap_id=gap.id,
        status="todo",
        **body.model_dump(),
    )
    db.add(row)
    if gap.status == "identified":
        gap.status = "outreach"
    db.commit()
    db.refresh(row)
    return row


@router.patch("/outreach/{item_id}", response_model=OutreachOut)
def update_outreach(
    item_id: str,
    status: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OutreachItem:
    if status not in OUTREACH_STATUSES:
        raise HTTPException(status_code=400, detail="无效外联状态")
    if status == "sent_manual":
        # Manual outreach only — no auto-blast endpoint exists.
        pass
    row = db.get(OutreachItem, item_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="外联不存在")
    row.status = status
    db.commit()
    db.refresh(row)
    return row


@router.post("/gaps/{gap_id}/ai", response_model=AiAssistOut)
def ai_gap(
    gap_id: str,
    body: AiStepIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiAssistOut:
    row = db.get(BacklinkGap, gap_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="链接不存在")
    payload = assist_offsite_gap(db, row, step=body.step or "evidence")
    db.commit()
    return AiAssistOut(**payload)
