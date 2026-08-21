from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, user_out, verify_password
from app.config import settings
from app.database import get_db
from app.login_guard import locked_until, record_failure, record_success
from app.models import Tenant, User
from app.schemas import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = body.email.lower()
    if locked_until(email) is not None:
        raise HTTPException(status_code=429, detail="失败次数过多，请 15 分钟后再试。")
    if not settings.demo_login_enabled and email == settings.demo_am_email.lower():
        raise HTTPException(status_code=401, detail="演示账号已关闭，请用管理员账号登录")
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(body.password, user.hashed_password):
        until = record_failure(email)
        if until is not None:
            raise HTTPException(status_code=429, detail="失败次数过多，请 15 分钟后再试。")
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    record_success(email)
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserOut:
    tenant = db.get(Tenant, user.tenant_id)
    return UserOut(**user_out(user, tenant))
