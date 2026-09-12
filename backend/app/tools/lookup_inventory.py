from decimal import Decimal
from typing import Any

from pydantic import Field
from sqlalchemy.orm import Session

from app.capabilities import INVENTORY_READ
from app.models.product import Product
from app.services.users import user_has_capability
from app.tools.base import StrictToolInput, ToolResult, audit_and_return, check_user_active

TOOL_NAME = "lookup_inventory"


class LookupInventoryInput(StrictToolInput):
    sku: str = Field(min_length=1, max_length=64)


def lookup_inventory(
    db: Session,
    *,
    user_id: int,
    thread_id: int | None,
    sku: str,
) -> ToolResult:
    args = {"sku": sku}
    inactive = check_user_active(db, user_id)
    if inactive:
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_NAME,
            arguments=args,
            outcome=inactive.outcome,
            thread_id=thread_id,
            result=inactive,
        )
    if not user_has_capability(db, user_id, INVENTORY_READ):
        result = ToolResult(ok=False, outcome="denied", error="Missing capability: inventory:read")
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_NAME,
            arguments=args,
            outcome="denied",
            thread_id=thread_id,
            result=result,
        )
    try:
        parsed = LookupInventoryInput(sku=sku.strip().upper())
    except Exception as e:
        result = ToolResult(ok=False, outcome="invalid", error=str(e))
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_NAME,
            arguments=args,
            outcome="invalid",
            thread_id=thread_id,
            result=result,
        )
    product = db.query(Product).filter(Product.sku == parsed.sku).first()
    if not product:
        result = ToolResult(ok=False, outcome="not_found", error=f"SKU {parsed.sku} not found")
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_NAME,
            arguments={"sku": parsed.sku},
            outcome="not_found",
            thread_id=thread_id,
            result=result,
        )
    data = {
        "sku": product.sku,
        "name": product.name,
        "quantity": product.quantity,
        "price": str(product.price),
        "supplier": product.supplier,
    }
    result = ToolResult(ok=True, outcome="success", data=data)
    return audit_and_return(
        db,
        user_id=user_id,
        tool=TOOL_NAME,
        arguments={"sku": parsed.sku},
        outcome="success",
        thread_id=thread_id,
        result=result,
    )


def lookup_inventory_from_raw(
    db: Session, user_id: int, raw: dict[str, Any], thread_id: int | None
) -> ToolResult:
    return lookup_inventory(db, user_id=user_id, thread_id=thread_id, sku=raw.get("sku", ""))
