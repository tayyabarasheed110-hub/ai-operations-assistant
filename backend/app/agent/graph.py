import json
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from sqlalchemy.orm import Session

from app.agent.prompts import (
    ACTION_PLAN_PROMPT,
    KNOWLEDGE_ANSWER_PROMPT,
    SUPERVISOR_PROMPT,
    SYSTEM_POLICY,
)
from app.agent.schemas import ActionPlan, RouteDecision
from app.agent.state import AgentState
from app.config import get_settings
from app.db.session import SessionLocal
from app.llm.client import chat_completion, structured_output
from app.tools.email_tool import TOOL_EXECUTE as EXECUTE_EMAIL
from app.tools.orders import TOOL_EXECUTE as EXECUTE_ORDER
from app.tools.registry import invoke_execute_tool, invoke_read_tool


def _append_event(state: AgentState, event: dict[str, Any]) -> list[dict[str, Any]]:
    events = list(state.get("sse_events") or [])
    events.append(event)
    return events


def supervisor_node(state: AgentState) -> dict[str, Any]:
    messages = state.get("messages") or []
    user_text = ""
    for m in reversed(messages):
        if getattr(m, "type", None) == "human" or (isinstance(m, dict) and m.get("role") == "user"):
            user_text = getattr(m, "content", None) or m.get("content", "")
            break
    prompt = [
        {"role": "system", "content": SYSTEM_POLICY + "\n\n" + SUPERVISOR_PROMPT},
        {"role": "user", "content": user_text},
    ]
    decision = structured_output(RouteDecision, prompt)
    return {"route": decision.route, "sse_events": _append_event(state, {"type": "token", "data": ""})}


def knowledge_node(state: AgentState) -> dict[str, Any]:
    db = SessionLocal()
    try:
        messages = state.get("messages") or []
        user_text = ""
        for m in reversed(messages):
            if getattr(m, "type", None) == "human":
                user_text = m.content
                break
            if isinstance(m, dict) and m.get("role") == "user":
                user_text = m.get("content", "")
                break
        from app.tools.retrieve_policy import retrieve_policy

        tr = retrieve_policy(db, user_id=state["user_id"], thread_id=state["thread_id"], query=user_text)
        event_tool = {"type": "tool_result", "data": {"tool": "retrieve_policy", "result": tr.__dict__}}
        excerpts = ""
        if tr.ok and tr.data:
            parts = []
            for c in tr.data.get("chunks", []):
                parts.append(f"{c.get('citation')}\n{c.get('content')}")
            excerpts = "\n\n".join(parts)
        if not excerpts.strip():
            answer = "The policy documents do not cover this topic."
        else:
            prompt = [
                {"role": "system", "content": SYSTEM_POLICY},
                {
                    "role": "user",
                    "content": KNOWLEDGE_ANSWER_PROMPT.format(excerpts=excerpts, question=user_text),
                },
            ]
            answer = chat_completion(prompt)
        parts = list(state.get("assistant_parts") or [])
        parts.append(answer)
        tool_results = list(state.get("tool_results") or [])
        tool_results.append({"tool": "retrieve_policy", "result": tr.__dict__})
        events = _append_event(state, event_tool)
        return {
            "knowledge_answer": answer,
            "assistant_parts": parts,
            "tool_results": tool_results,
            "sse_events": events,
        }
    finally:
        db.close()


def action_plan_node(state: AgentState) -> dict[str, Any]:
    if state.get("halted"):
        return {}
    messages = state.get("messages") or []
    convo_lines = []
    for m in messages[-8:]:
        role = getattr(m, "type", "unknown")
        content = getattr(m, "content", str(m))
        if role == "human":
            convo_lines.append(f"User: {content}")
        else:
            convo_lines.append(f"Assistant: {content}")
    knowledge_context = state.get("knowledge_answer") or ""
    prompt = [
        {"role": "system", "content": SYSTEM_POLICY},
        {
            "role": "user",
            "content": ACTION_PLAN_PROMPT.format(
                knowledge_context=knowledge_context,
                conversation="\n".join(convo_lines),
            ),
        },
    ]
    plan = structured_output(ActionPlan, prompt)
    pending: list[dict[str, Any]] = []
    tool_results = list(state.get("tool_results") or [])
    events = list(state.get("sse_events") or [])
    db = SessionLocal()
    try:
        for call in plan.tool_calls:
            events.append({"type": "tool_started", "data": {"tool": call.tool, "arguments": call.arguments}})
            result = invoke_read_tool(
                db, call.tool, state["user_id"], call.arguments, state["thread_id"]
            )
            tool_results.append({"tool": call.tool, "result": result.__dict__})
            events.append({"type": "tool_result", "data": {"tool": call.tool, "result": result.__dict__}})
            if call.tool in ("draft_order", "draft_email") and result.ok and result.data:
                pending.append(result.data["pending"])
        parts = list(state.get("assistant_parts") or [])
        if plan.summary:
            parts.append(plan.summary)
        return {
            "pending_writes": pending,
            "pending_index": 0,
            "tool_results": tool_results,
            "assistant_parts": parts,
            "sse_events": events,
        }
    finally:
        db.close()


def approval_node(state: AgentState) -> dict[str, Any]:
    if state.get("halted"):
        return {}
    pending = state.get("pending_writes") or []
    idx = state.get("pending_index") or 0
    if idx >= len(pending):
        return {}
    current = pending[idx]
    decision = interrupt({"type": "approval_required", "pending": current, "index": idx, "total": len(pending)})
    return {"approval_payload": current, "resume_decision": decision}


def process_approval_node(state: AgentState) -> dict[str, Any]:
    decision = state.get("resume_decision") or {}
    pending = state.get("pending_writes") or []
    idx = state.get("pending_index") or 0
    if idx >= len(pending):
        return {}
    current = pending[idx]
    action_type = current.get("action_type")
    choice = decision.get("decision")
    edits = decision.get("edits") or {}
    events = list(state.get("sse_events") or [])
    parts = list(state.get("assistant_parts") or [])
    db = SessionLocal()
    try:
        if choice == "reject":
            parts.append(f"Rejected pending {action_type}. Dependent actions will not run.")
            events.append({"type": "tool_result", "data": {"tool": "approval", "result": {"outcome": "rejected"}}})
            return {
                "halted": True,
                "assistant_parts": parts,
                "pending_index": idx + 1,
                "sse_events": events,
            }
        payload = {**current, **edits}
        if action_type == "order":
            tool = EXECUTE_ORDER
            args = {
                "sku": payload["sku"],
                "quantity": payload["quantity"],
                "supplier": payload["supplier"],
                "idempotency_key": payload["idempotency_key"],
            }
        elif action_type == "email":
            tool = EXECUTE_EMAIL
            args = {
                "recipient": payload["recipient"],
                "subject": payload["subject"],
                "body": payload["body"],
                "idempotency_key": payload["idempotency_key"],
            }
        else:
            return {"halted": True}
        events.append({"type": "tool_started", "data": {"tool": tool, "arguments": args}})
        result = invoke_execute_tool(db, tool, state["user_id"], args, state["thread_id"])
        events.append({"type": "tool_result", "data": {"tool": tool, "result": result.__dict__}})
        if result.ok:
            parts.append(f"Approved and executed {action_type}: {json.dumps(result.data)}")
        else:
            parts.append(f"Execution failed for {action_type}: {result.error}")
            return {"halted": True, "assistant_parts": parts, "sse_events": events}
        return {
            "assistant_parts": parts,
            "pending_index": idx + 1,
            "sse_events": events,
            "resume_decision": None,
        }
    finally:
        db.close()


def finalize_node(state: AgentState) -> dict[str, Any]:
    parts = state.get("assistant_parts") or []
    if not parts:
        parts = ["Done."]
    text = "\n\n".join(parts)
    events = _append_event(state, {"type": "done", "data": {"message": text}})
    return {"sse_events": events}


def route_after_supervisor(state: AgentState) -> str:
    route = state.get("route", "action")
    if route == "knowledge":
        return "knowledge"
    if route == "both":
        return "knowledge"
    return "action_plan"


def route_after_knowledge(state: AgentState) -> str:
    route = state.get("route", "knowledge")
    if route == "both":
        return "action_plan"
    return "finalize"


def route_after_action_plan(state: AgentState) -> str:
    pending = state.get("pending_writes") or []
    if pending and not state.get("halted"):
        return "approval"
    return "finalize"


def route_approval_loop(state: AgentState) -> str:
    if state.get("halted"):
        return "finalize"
    pending = state.get("pending_writes") or []
    idx = state.get("pending_index") or 0
    if idx < len(pending):
        return "approval"
    return "finalize"


def build_graph(checkpointer: SqliteSaver):
    g = StateGraph(AgentState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("knowledge", knowledge_node)
    g.add_node("action_plan", action_plan_node)
    g.add_node("approval", approval_node)
    g.add_node("process_approval", process_approval_node)
    g.add_node("finalize", finalize_node)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges("supervisor", route_after_supervisor, {"knowledge": "knowledge", "action_plan": "action_plan"})
    g.add_conditional_edges(
        "knowledge", route_after_knowledge, {"action_plan": "action_plan", "finalize": "finalize"}
    )
    g.add_conditional_edges(
        "action_plan",
        route_after_action_plan,
        {"approval": "approval", "finalize": "finalize"},
    )
    g.add_edge("approval", "process_approval")
    g.add_conditional_edges(
        "process_approval", route_approval_loop, {"approval": "approval", "finalize": "finalize"}
    )
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer)


_checkpointer: SqliteSaver | None = None
_compiled = None


def get_compiled_graph():
    global _checkpointer, _compiled
    if _compiled is None:
        settings = get_settings()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        cp_path = settings.data_dir / "checkpoints.sqlite"
        _checkpointer = SqliteSaver.from_conn_string(str(cp_path))
        _checkpointer.setup()
        _compiled = build_graph(_checkpointer)
    return _compiled


def graph_config(thread_id: int) -> dict[str, Any]:
    return {"configurable": {"thread_id": str(thread_id)}}
