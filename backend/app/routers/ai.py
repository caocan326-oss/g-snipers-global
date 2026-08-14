from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.llm import gateway_info
from app.models import AiRun, User
from app.schemas import AiStatusOut

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/status", response_model=AiStatusOut)
def ai_status() -> AiStatusOut:
    return AiStatusOut(**gateway_info())


@router.get("/runs")
def list_runs(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = (
        db.query(AiRun)
        .filter(AiRun.tenant_id == user.tenant_id)
        .order_by(AiRun.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": r.id,
            "chain": r.chain,
            "step": r.step,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "status": r.status,
            "evidence": r.evidence,
            "detail": r.detail,
        }
        for r in rows
    ]
