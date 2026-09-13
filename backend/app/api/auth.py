from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.jwt_session import create_access_token
from app.auth.passwords import verify_password
from app.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.services.users import get_user_by_email, user_capability_set

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SignInBody(BaseModel):
    email: str
    password: str


@router.post("/sign-in")
def sign_in(body: SignInBody, response: Response, db: Session = Depends(get_db)):
    user = get_user_by_email(db, body.email)
    if not user or not verify_password(user.password_hash, body.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive")
    token = create_access_token(user.id, user.email, user.is_admin)
    settings = get_settings()
    response.set_cookie(
        key=settings.jwt_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.jwt_max_age_seconds,
    )
    return {"ok": True}


@router.post("/sign-out")
def sign_out(response: Response):
    settings = get_settings()
    response.delete_cookie(settings.jwt_cookie_name)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    caps = sorted(user_capability_set(db, user.id))
    if user.is_admin:
        from app.capabilities import ALL_CAPABILITIES

        caps = sorted(ALL_CAPABILITIES)
    return {
        "id": user.id,
        "email": user.email,
        "is_admin": user.is_admin,
        "capabilities": caps,
    }
