from typing import Any, Literal

from pydantic import BaseModel, Field


class RouteDecision(BaseModel):
    route: Literal["knowledge", "action", "both"]


class PlannedToolCall(BaseModel):
    tool: Literal["retrieve_policy", "lookup_inventory", "draft_order", "draft_email"]
    arguments: dict[str, Any] = Field(default_factory=dict)


class ActionPlan(BaseModel):
    tool_calls: list[PlannedToolCall] = Field(default_factory=list)
    summary: str = ""
