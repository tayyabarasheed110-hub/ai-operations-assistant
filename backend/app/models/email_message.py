from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmailMessage(Base):
    __tablename__ = "email_message"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_email_idempotency_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sent_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
