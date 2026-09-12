from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Order(Base):
    __tablename__ = "order"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_order_idempotency_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_reference: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    supplier: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
