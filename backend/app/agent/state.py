from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    thread_id: int
    user_id: int
    route: str
    messages: Annotated[list[Any], add_messages]
    knowledge_answer: str
    tool_results: list[dict[str, Any]]
    pending_writes: list[dict[str, Any]]
    pending_index: int
    halted: bool
    assistant_parts: list[str]
    sse_events: list[dict[str, Any]]
    approval_payload: dict[str, Any] | None
    resume_decision: dict[str, Any] | None
