from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.jwt_session import decode_access_token
from app.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.services.users import get_user_by_id


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    settings = get_settings()
    token = request.cookies.get(settings.jwt_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    user_id = int(payload["sub"])
    user = get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return user
