from sqlalchemy.orm import Session

from app.models.user import User, UserCapability


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def user_capability_set(db: Session, user_id: int) -> set[str]:
    rows = db.query(UserCapability.capability).filter(UserCapability.user_id == user_id).all()
    return {r[0] for r in rows}


def user_has_capability(db: Session, user_id: int, capability: str) -> bool:
    user = get_user_by_id(db, user_id)
    if not user or not user.is_active:
        return False
    if user.is_admin:
        return True
    return capability in user_capability_set(db, user_id)
