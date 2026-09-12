from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Thread(Base):
    __tablename__ = "thread"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), default="New conversation", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
