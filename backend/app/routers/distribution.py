from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import DistributionAttempt, DistributionJob, User
from app.providers import all_providers, get_provider
from app.risk import require_confirm
from app.schemas import ConfirmReadyIn, DistributionJobCreate, DistributionJobOut, ProviderOut, SendResultOut

router = APIRouter(prefix="/api/distribution", tags=["distribution"])


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
    row = DistributionJob(
        tenant_id=user.tenant_id,
        status="draft",
        last_result="未发送",
        **body.model_dump(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


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
    db.commit()
    db.refresh(job)
    return SendResultOut(
        sent=result.sent,
        provider_status=result.status,
        detail=result.detail,
        job=_job_out(job),
    )
