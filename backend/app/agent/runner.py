import json
from collections.abc import AsyncGenerator, Iterator
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.agent.graph import get_compiled_graph, graph_config


def _extract_interrupt(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, dict) and payload.get("type") == "approval_required":
        return payload
    if isinstance(payload, list) and payload:
        item = payload[0]
        if hasattr(item, "value"):
            return item.value
        if isinstance(item, dict):
            return item.get("value") or item
    return None


def run_message_stream(
    *,
    thread_id: int,
    user_id: int,
    content: str,
) -> Iterator[dict[str, Any]]:
    graph = get_compiled_graph()
    config = graph_config(thread_id)
    initial: dict[str, Any] = {
        "thread_id": thread_id,
        "user_id": user_id,
        "messages": [HumanMessage(content=content)],
        "tool_results": [],
        "assistant_parts": [],
        "sse_events": [],
        "pending_index": 0,
        "halted": False,
    }
    for chunk in graph.stream(initial, config=config, stream_mode="updates"):
        for _node, update in chunk.items():
            if not isinstance(update, dict):
                continue
            for ev in update.get("sse_events") or []:
                yield ev
            if "__interrupt__" in chunk:
                intr = _extract_interrupt(chunk["__interrupt__"])
                if intr:
                    yield {"type": "approval_required", "data": intr}
    # Flush interrupt from final state if stream ended paused
    snap = graph.get_state(config)
    if snap.next:
        for task in snap.tasks:
            if task.interrupts:
                for intr in task.interrupts:
                    val = intr.value if hasattr(intr, "value") else intr
                    parsed = _extract_interrupt(val)
                    if parsed:
                        yield {"type": "approval_required", "data": parsed}


def resume_thread(
    *,
    thread_id: int,
    decision: str,
    edits: dict[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    graph = get_compiled_graph()
    config = graph_config(thread_id)
    payload = {"decision": decision, "edits": edits or {}}
    for chunk in graph.stream(Command(resume=payload), config=config, stream_mode="updates"):
        if "__interrupt__" in chunk:
            intr = _extract_interrupt(chunk["__interrupt__"])
            if intr:
                yield {"type": "approval_required", "data": intr}
        for _node, update in chunk.items():
            if not isinstance(update, dict):
                continue
            for ev in update.get("sse_events") or []:
                yield ev
    snap = graph.get_state(config)
    if snap.next:
        for task in snap.tasks:
            if task.interrupts:
                for intr in task.interrupts:
                    val = intr.value if hasattr(intr, "value") else intr
                    parsed = _extract_interrupt(val)
                    if parsed:
                        yield {"type": "approval_required", "data": parsed}
    else:
        yield {"type": "done", "data": {"message": "Resume complete"}}


async def sse_from_iterator(events: Iterator[dict[str, Any]]) -> AsyncGenerator[str, None]:
    for ev in events:
        yield f"event: {ev['type']}\ndata: {json.dumps(ev.get('data', {}))}\n\n"
