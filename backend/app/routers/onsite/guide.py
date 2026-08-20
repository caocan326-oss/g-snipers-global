from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.onsite_guide import guide_payload
from app.schemas import OnsiteGuideOut

from . import router


@router.get("/guide", response_model=OnsiteGuideOut)
def get_onsite_guide(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> OnsiteGuideOut:
    """Fast next-step. Narrative is a template; call /guide/voice for the LLM line."""
    return OnsiteGuideOut(**guide_payload(db, user, voice=False))


@router.post("/guide/voice", response_model=OnsiteGuideOut)
def voice_onsite_guide(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> OnsiteGuideOut:
    """Rephrase the same counts. Missing LLM key keeps the template and 未配置."""
    return OnsiteGuideOut(**guide_payload(db, user, voice=True))
