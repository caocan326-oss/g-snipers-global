from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import BacklinkGap, DistributionAttempt, DistributionJob, User
from app.providers import all_providers, get_provider
from app.risk import require_confirm
from app.schemas import (
    ConfirmReadyIn,
    DistributionJobCreate,
    DistributionJobOut,
    DistributionJobUpdate,
    DistributionSubmitResultIn,
    ProviderOut,
    SendResultOut,
)

router = APIRouter(prefix="/api/distribution", tags=["distribution"])

JOB_STATUSES = {"draft", "ready", "in_progress", "submitted", "verifying", "done", "blocked", "blocked_unconfigured", "cancelled", "sent"}
VERIFY_STATUSES = {"pending", "live", "failed", "unknown"}
TASK_TYPES = {
    "profile_create",
    "profile_update",
    "brand_fix",
    "product_listing",
    "listicle_pitch",
    "guest_or_pr",
    "distributor_align",
    "link_claim",
    "monitor_only",
}


def _job_out(row: DistributionJob) -> DistributionJobOut:
    return DistributionJobOut.model_validate(row, from_attributes=True)


@router.get("/providers", response_model=list[ProviderOut])
def list_providers() -> list[ProviderOut]:
    return [
        ProviderOut(
            key=p.key,
            label=p.label,
            configured=p.configured(),
            status="已配置" if p.configured() else "未配置",
            env_var=p.env_var,
        )
        for p in all_providers()
    ]


@router.get("/jobs", response_model=list[DistributionJobOut])
def list_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[DistributionJob]:
    return (
        db.query(DistributionJob)
        .filter(DistributionJob.tenant_id == user.tenant_id)
        .order_by(DistributionJob.created_at.desc())
        .all()
    )


@router.post("/jobs", response_model=DistributionJobOut, status_code=201)
def create_job(
    body: DistributionJobCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DistributionJob:
    if get_provider(body.provider_key) is None:
        raise HTTPException(status_code=400, detail="未知分发渠道")
    if body.task_type not in TASK_TYPES:
        raise HTTPException(status_code=400, detail="无效任务类型")
    gap = None
    if body.gap_id:
        gap = db.get(BacklinkGap, body.gap_id)
        if gap is None or gap.tenant_id != user.tenant_id:
            raise HTTPException(status_code=404, detail="站外机会不存在")
    row = DistributionJob(
        tenant_id=user.tenant_id,
        status="draft",
        last_result="未发送",
        **body.model_dump(),
    )
    db.add(row)
    if gap:
        gap.status = "converted_to_task"
        if not gap.owner_hint and body.owner_hint:
            gap.owner_hint = body.owner_hint
        if not gap.recommended_action:
            gap.recommended_action = f"按 {body.task_type} 创建分发任务：{body.title}"
    db.commit()
    db.refresh(row)
    return row


@router.patch("/jobs/{job_id}", response_model=DistributionJobOut)
def update_job(
    job_id: str,
    body: DistributionJobUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DistributionJob:
    job = db.get(DistributionJob, job_id)
    if job is None or job.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="分发任务不存在")
    payload = body.model_dump(exclude_unset=True)
    if "status" in payload and payload["status"]:
        if payload["status"] not in JOB_STATUSES:
            raise HTTPException(status_code=400, detail="无效任务状态")
        job.status = payload["status"]
    if "verify_status" in payload and payload["verify_status"]:
        if payload["verify_status"] not in VERIFY_STATUSES:
            raise HTTPException(status_code=400, detail="无效核验状态")
        job.verify_status = payload["verify_status"]
    for field in ("owner_hint", "result_url", "blocked_reason", "payload_summary"):
        if field in payload:
            setattr(job, field, payload[field] or "")
    if job.gap_id:
        gap = db.get(BacklinkGap, job.gap_id)
        if gap and gap.tenant_id == user.tenant_id:
            _sync_gap_from_job(gap, job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/jobs/{job_id}/submit-result", response_model=DistributionJobOut)
def submit_result(
    job_id: str,
    body: DistributionSubmitResultIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DistributionJob:
    if body.verify_status not in VERIFY_STATUSES:
        raise HTTPException(status_code=400, detail="无效核验状态")
    job = db.get(DistributionJob, job_id)
    if job is None or job.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="分发任务不存在")
    job.result_url = body.result_url
    job.verify_status = body.verify_status
    job.status = "verifying" if body.verify_status == "pending" else "done" if body.verify_status == "live" else "submitted"
    job.last_result = "已提交结果"
    job.last_detail = body.evidence or f"Result URL: {body.result_url}"
    job.last_checked_at = datetime.now(timezone.utc)
    if job.gap_id:
        gap = db.get(BacklinkGap, job.gap_id)
        if gap and gap.tenant_id == user.tenant_id:
            _sync_gap_from_job(gap, job, evidence=body.evidence)
    db.commit()
    db.refresh(job)
    return job


@router.post("/jobs/{job_id}/send", response_model=SendResultOut)
def send_job(
    job_id: str,
    body: ConfirmReadyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SendResultOut:
    require_confirm(body.confirmed, action="向外链渠道发送")
    job = db.get(DistributionJob, job_id)
    if job is None or job.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="分发任务不存在")
    provider = get_provider(job.provider_key)
    if provider is None:
        raise HTTPException(status_code=400, detail="未知分发渠道")

    result = provider.send(title=job.title, target_url=job.target_url, payload_summary=job.payload_summary)
    attempt = DistributionAttempt(
        tenant_id=user.tenant_id,
        job_id=job.id,
        confirmed=True,
        sent=result.sent,
        result=result.status,
        detail=result.detail,
    )
    db.add(attempt)
    job.last_result = result.status
    job.last_detail = result.detail
    if result.sent:
        job.status = "sent"
    elif result.status == "未配置":
        job.status = "blocked_unconfigured"
    else:
        job.status = "blocked"
    if job.gap_id:
        gap = db.get(BacklinkGap, job.gap_id)
        if gap and gap.tenant_id == user.tenant_id:
            _sync_gap_from_job(gap, job)
    db.commit()
    db.refresh(job)
    return SendResultOut(
        sent=result.sent,
        provider_status=result.status,
        detail=result.detail,
        job=_job_out(job),
    )


def _sync_gap_from_job(gap: BacklinkGap, job: DistributionJob, *, evidence: str = "") -> None:
    if job.result_url:
        gap.result_url = job.result_url
        gap.link_url = job.result_url
    if job.verify_status == "live":
        gap.verify_status = "valid"
        gap.status = "won"
        gap.closed_at = datetime.now(timezone.utc)
    elif job.verify_status == "failed":
        gap.verify_status = "dead"
        gap.status = "needs_retest"
    elif job.status in {"submitted", "verifying", "sent"}:
        gap.status = "needs_retest"
    elif job.status in {"blocked", "blocked_unconfigured"}:
        gap.status = "blocked"
        gap.blocked_reason = job.blocked_reason or job.last_detail or "分发任务受阻"
    elif job.status in {"ready", "in_progress"}:
        gap.status = "in_progress"
    if job.owner_hint and not gap.owner_hint:
        gap.owner_hint = job.owner_hint
    if job.result_url and not gap.retest_method:
        gap.retest_method = "复查 result_url 是否可访问、是否提及客户、是否链接到目标页。"
    if evidence:
        gap.evidence = "\n".join(part for part in [gap.evidence, evidence] if part)
    gap.last_checked_at = datetime.now(timezone.utc)
