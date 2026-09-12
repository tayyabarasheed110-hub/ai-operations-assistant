import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def write_audit(
    db: Session,
    *,
    user_id: int | None,
    tool: str,
    arguments: dict[str, Any],
    outcome: str,
    thread_id: int | None = None,
) -> AuditLog:
    row = AuditLog(
        user_id=user_id,
        tool=tool,
        arguments_json=json.dumps(arguments, default=str),
        outcome=outcome,
        thread_id=thread_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
