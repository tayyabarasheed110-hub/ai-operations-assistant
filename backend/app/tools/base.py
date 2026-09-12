from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.services.audit import write_audit
from app.services.users import get_user_by_id, user_has_capability


OutcomeKind = Literal["success", "denied", "invalid", "not_found", "error"]


@dataclass
class ToolResult:
    ok: bool
    outcome: OutcomeKind
    data: dict[str, Any] | None = None
    error: str | None = None


class StrictToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


def audit_and_return(
    db: Session,
    *,
    user_id: int,
    tool: str,
    arguments: dict[str, Any],
    outcome: OutcomeKind,
    thread_id: int | None,
    result: ToolResult,
) -> ToolResult:
    write_audit(
        db,
        user_id=user_id,
        tool=tool,
        arguments=arguments,
        outcome=outcome,
        thread_id=thread_id,
    )
    return result


def check_user_active(db: Session, user_id: int) -> ToolResult | None:
    user = get_user_by_id(db, user_id)
    if not user:
        return ToolResult(ok=False, outcome="denied", error="User not found")
    if not user.is_active:
        return ToolResult(ok=False, outcome="denied", error="User account is inactive")
    return None
