from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.config import get_settings


def create_access_token(user_id: int, email: str, is_admin: bool) -> str:
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "email": email,
        "is_admin": is_admin,
        "exp": datetime.now(UTC) + timedelta(seconds=settings.jwt_max_age_seconds),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError:
        return None
