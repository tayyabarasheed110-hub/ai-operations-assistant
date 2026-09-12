from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.capabilities import ALLOWED_TOOLS
from app.tools.base import ToolResult
from app.tools.email_tool import (
    TOOL_DRAFT as EMAIL_DRAFT,
    TOOL_EXECUTE as EMAIL_EXECUTE,
    draft_email_from_raw,
    execute_email_from_raw,
)
from app.tools.lookup_inventory import TOOL_NAME as LOOKUP_INVENTORY, lookup_inventory_from_raw
from app.tools.orders import (
    TOOL_DRAFT as ORDER_DRAFT,
    TOOL_EXECUTE as ORDER_EXECUTE,
    draft_order_from_raw,
    execute_order_from_raw,
)
from app.tools.retrieve_policy import TOOL_NAME as RETRIEVE_POLICY, retrieve_policy_from_raw

ReadToolFn = Callable[[Session, int, dict[str, Any], int | None], ToolResult]

READ_TOOL_REGISTRY: dict[str, ReadToolFn] = {
    RETRIEVE_POLICY: retrieve_policy_from_raw,
    LOOKUP_INVENTORY: lookup_inventory_from_raw,
    ORDER_DRAFT: draft_order_from_raw,
    EMAIL_DRAFT: draft_email_from_raw,
}

ExecuteToolFn = Callable[[Session, int, dict[str, Any], int | None], ToolResult]

EXECUTE_TOOL_REGISTRY: dict[str, ExecuteToolFn] = {
    ORDER_EXECUTE: execute_order_from_raw,
    EMAIL_EXECUTE: execute_email_from_raw,
}


def invoke_read_tool(
    db: Session,
    tool_name: str,
    user_id: int,
    arguments: dict[str, Any],
    thread_id: int | None,
) -> ToolResult:
    if tool_name not in ALLOWED_TOOLS:
        from app.services.audit import write_audit

        write_audit(
            db,
            user_id=user_id,
            tool=tool_name,
            arguments=arguments,
            outcome="denied",
            thread_id=thread_id,
        )
        return ToolResult(ok=False, outcome="denied", error=f"Unknown tool: {tool_name}")
    fn = READ_TOOL_REGISTRY.get(tool_name)
    if not fn:
        from app.services.audit import write_audit

        write_audit(
            db,
            user_id=user_id,
            tool=tool_name,
            arguments=arguments,
            outcome="denied",
            thread_id=thread_id,
        )
        return ToolResult(ok=False, outcome="denied", error=f"Tool not invokable: {tool_name}")
    return fn(db, user_id, arguments, thread_id)


def invoke_execute_tool(
    db: Session,
    tool_name: str,
    user_id: int,
    arguments: dict[str, Any],
    thread_id: int | None,
) -> ToolResult:
    if tool_name not in ALLOWED_TOOLS:
        from app.services.audit import write_audit

        write_audit(
            db,
            user_id=user_id,
            tool=tool_name,
            arguments=arguments,
            outcome="denied",
            thread_id=thread_id,
        )
        return ToolResult(ok=False, outcome="denied", error=f"Unknown tool: {tool_name}")
    fn = EXECUTE_TOOL_REGISTRY.get(tool_name)
    if not fn:
        from app.services.audit import write_audit

        write_audit(
            db,
            user_id=user_id,
            tool=tool_name,
            arguments=arguments,
            outcome="denied",
            thread_id=thread_id,
        )
        return ToolResult(ok=False, outcome="denied", error=f"Tool not executable: {tool_name}")
    return fn(db, user_id, arguments, thread_id)
