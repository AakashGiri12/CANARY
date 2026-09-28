from __future__ import annotations

from typing import Any, Optional, TypedDict


class AgentMessage(TypedDict, total=False):
    role: str  # "assistant" | "tool"
    tool: str
    args: dict
    content: Any
    ok: bool


class AgentState(TypedDict):
    run_id: str
    task: str
    turn: int
    messages: list[AgentMessage]
    final_answer: Optional[str]
