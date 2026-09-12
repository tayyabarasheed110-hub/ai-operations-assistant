import json
from typing import Any

from pydantic import Field
from sqlalchemy.orm import Session

from app.capabilities import POLICY_READ
from app.retrieval.chroma_store import query_policy
from app.services.users import user_has_capability
from app.tools.base import StrictToolInput, ToolResult, audit_and_return, check_user_active
from app.utils.sanitize import wrap_untrusted

TOOL_NAME = "retrieve_policy"


class RetrievePolicyInput(StrictToolInput):
    query: str = Field(min_length=1, max_length=2000)


def retrieve_policy(
    db: Session,
    *,
    user_id: int,
    thread_id: int | None,
    query: str,
) -> ToolResult:
    args = {"query": query}
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
    if not user_has_capability(db, user_id, POLICY_READ):
        result = ToolResult(ok=False, outcome="denied", error="Missing capability: policy:read")
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
        parsed = RetrievePolicyInput(query=query)
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
    hits = query_policy(parsed.query)
    chunks: list[dict[str, Any]] = []
    for h in hits:
        meta = h.get("metadata") or {}
        title = meta.get("title", "Unknown")
        section = meta.get("page_or_section", "n/a")
        chunks.append(
            {
                "citation": f"[{title}, {section}]",
                "content": wrap_untrusted(h.get("content") or ""),
            }
        )
    result = ToolResult(ok=True, outcome="success", data={"chunks": chunks, "count": len(chunks)})
    return audit_and_return(
        db,
        user_id=user_id,
        tool=TOOL_NAME,
        arguments={"query": parsed.query},
        outcome="success",
        thread_id=thread_id,
        result=result,
    )


def retrieve_policy_from_raw(db: Session, user_id: int, raw: dict[str, Any], thread_id: int | None) -> ToolResult:
    return retrieve_policy(db, user_id=user_id, thread_id=thread_id, query=raw.get("query", ""))
