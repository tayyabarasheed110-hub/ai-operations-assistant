import secrets
import uuid
from typing import Any

from pydantic import Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.capabilities import ORDER_CREATE
from app.models.order import Order
from app.models.product import Product
from app.services.users import get_user_by_id, user_has_capability
from app.tools.base import StrictToolInput, ToolResult, audit_and_return, check_user_active

TOOL_DRAFT = "draft_order"
TOOL_EXECUTE = "execute_order"


class DraftOrderInput(StrictToolInput):
    sku: str = Field(min_length=1, max_length=64)
    quantity: int = Field(gt=0, le=1_000_000)
    supplier: str = Field(min_length=1, max_length=255)
    idempotency_key: str | None = Field(default=None, max_length=128)

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, v: str) -> str:
        return v.strip().upper()


def draft_order(
    db: Session,
    *,
    user_id: int,
    thread_id: int | None,
    sku: str,
    quantity: int,
    supplier: str,
    idempotency_key: str | None = None,
) -> ToolResult:
    args = {"sku": sku, "quantity": quantity, "supplier": supplier}
    inactive = check_user_active(db, user_id)
    if inactive:
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_DRAFT,
            arguments=args,
            outcome=inactive.outcome,
            thread_id=thread_id,
            result=inactive,
        )
    if not user_has_capability(db, user_id, ORDER_CREATE):
        result = ToolResult(ok=False, outcome="denied", error="Missing capability: order:create")
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_DRAFT,
            arguments=args,
            outcome="denied",
            thread_id=thread_id,
            result=result,
        )
    try:
        parsed = DraftOrderInput(sku=sku, quantity=quantity, supplier=supplier.strip())
    except Exception as e:
        result = ToolResult(ok=False, outcome="invalid", error=str(e))
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_DRAFT,
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
            tool=TOOL_DRAFT,
            arguments=args,
            outcome="not_found",
            thread_id=thread_id,
            result=result,
        )
    key = idempotency_key or secrets.token_urlsafe(16)
    user = get_user_by_id(db, user_id)
    pending = {
        "action_type": "order",
        "sku": parsed.sku,
        "quantity": parsed.quantity,
        "supplier": parsed.supplier,
        "requested_by": user_id,
        "requested_by_email": user.email if user else None,
        "idempotency_key": key,
        "product_name": product.name,
    }
    result = ToolResult(ok=True, outcome="success", data={"pending": pending, "requires_approval": True})
    return audit_and_return(
        db,
        user_id=user_id,
        tool=TOOL_DRAFT,
        arguments={**args, "idempotency_key": key},
        outcome="success",
        thread_id=thread_id,
        result=result,
    )


def execute_order(
    db: Session,
    *,
    user_id: int,
    thread_id: int | None,
    sku: str,
    quantity: int,
    supplier: str,
    idempotency_key: str,
) -> ToolResult:
    args = {
        "sku": sku,
        "quantity": quantity,
        "supplier": supplier,
        "idempotency_key": idempotency_key,
    }
    inactive = check_user_active(db, user_id)
    if inactive:
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_EXECUTE,
            arguments=args,
            outcome=inactive.outcome,
            thread_id=thread_id,
            result=inactive,
        )
    if not user_has_capability(db, user_id, ORDER_CREATE):
        result = ToolResult(ok=False, outcome="denied", error="Missing capability: order:create")
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_EXECUTE,
            arguments=args,
            outcome="denied",
            thread_id=thread_id,
            result=result,
        )
    try:
        parsed = DraftOrderInput(
            sku=sku, quantity=quantity, supplier=supplier, idempotency_key=idempotency_key
        )
    except Exception as e:
        result = ToolResult(ok=False, outcome="invalid", error=str(e))
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_EXECUTE,
            arguments=args,
            outcome="invalid",
            thread_id=thread_id,
            result=result,
        )
    existing = db.query(Order).filter(Order.idempotency_key == parsed.idempotency_key).first()
    if existing:
        result = ToolResult(
            ok=True,
            outcome="success",
            data={
                "order_reference": existing.order_reference,
                "duplicate": True,
                "sku": existing.sku,
                "quantity": existing.quantity,
            },
        )
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_EXECUTE,
            arguments=args,
            outcome="success",
            thread_id=thread_id,
            result=result,
        )
    product = db.query(Product).filter(Product.sku == parsed.sku).first()
    if not product:
        result = ToolResult(ok=False, outcome="not_found", error=f"SKU {parsed.sku} not found")
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_EXECUTE,
            arguments=args,
            outcome="not_found",
            thread_id=thread_id,
            result=result,
        )
    order_ref = f"PO-{uuid.uuid4().hex[:12].upper()}"
    order = Order(
        order_reference=order_ref,
        sku=parsed.sku,
        quantity=parsed.quantity,
        supplier=parsed.supplier,
        requested_by=user_id,
        idempotency_key=parsed.idempotency_key or idempotency_key,
    )
    db.add(order)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(Order).filter(Order.idempotency_key == parsed.idempotency_key).first()
        if existing:
            result = ToolResult(
                ok=True,
                outcome="success",
                data={"order_reference": existing.order_reference, "duplicate": True},
            )
            return audit_and_return(
                db,
                user_id=user_id,
                tool=TOOL_EXECUTE,
                arguments=args,
                outcome="success",
                thread_id=thread_id,
                result=result,
            )
        result = ToolResult(ok=False, outcome="error", error="Failed to create order")
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_EXECUTE,
            arguments=args,
            outcome="error",
            thread_id=thread_id,
            result=result,
        )
    db.refresh(order)
    print(
        f"[MOCK ORDER] reference={order.order_reference} sku={order.sku} qty={order.quantity} "
        f"supplier={order.supplier} by user_id={user_id}"
    )
    result = ToolResult(
        ok=True,
        outcome="success",
        data={
            "order_reference": order.order_reference,
            "sku": order.sku,
            "quantity": order.quantity,
            "supplier": order.supplier,
            "duplicate": False,
        },
    )
    return audit_and_return(
        db,
        user_id=user_id,
        tool=TOOL_EXECUTE,
        arguments=args,
        outcome="success",
        thread_id=thread_id,
        result=result,
    )


def draft_order_from_raw(db: Session, user_id: int, raw: dict[str, Any], thread_id: int | None) -> ToolResult:
    return draft_order(
        db,
        user_id=user_id,
        thread_id=thread_id,
        sku=raw.get("sku", ""),
        quantity=int(raw.get("quantity", 0)),
        supplier=raw.get("supplier", ""),
        idempotency_key=raw.get("idempotency_key"),
    )


def execute_order_from_raw(db: Session, user_id: int, raw: dict[str, Any], thread_id: int | None) -> ToolResult:
    return execute_order(
        db,
        user_id=user_id,
        thread_id=thread_id,
        sku=raw.get("sku", ""),
        quantity=int(raw.get("quantity", 0)),
        supplier=raw.get("supplier", ""),
        idempotency_key=raw.get("idempotency_key", ""),
    )
