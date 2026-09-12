from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    capabilities: Mapped[list["UserCapability"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserCapability(Base):
    __tablename__ = "user_capability"
    __table_args__ = (UniqueConstraint("user_id", "capability", name="uq_user_capability"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    capability: Mapped[str] = mapped_column(String(64), nullable=False)

    user: Mapped["User"] = relationship(back_populates="capabilities")
