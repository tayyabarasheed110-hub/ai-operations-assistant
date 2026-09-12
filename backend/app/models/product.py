from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Product(Base):
    __tablename__ = "product"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    supplier: Mapped[str] = mapped_column(String(255), nullable=False)
