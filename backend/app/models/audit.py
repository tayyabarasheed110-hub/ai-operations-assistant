from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    tool: Mapped[str] = mapped_column(String(128), nullable=False)
    arguments_json: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str] = mapped_column(String(64), nullable=False)
    thread_id: Mapped[int | None] = mapped_column(ForeignKey("thread.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
