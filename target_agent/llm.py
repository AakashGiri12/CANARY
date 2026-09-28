"""LLM client abstraction the agent graph decides its next action through.

Two implementations satisfy the same interface:

- ScriptedLLM: a deterministic stand-in that walks a fixed plan of actions
  instead of reasoning. Used now, since there's no LLM endpoint yet (the
  GCP spot T4 running vLLM is build order step 6) and no paid API is
  available. This is what makes "one clean end-to-end task run" possible
  today — it proves the graph, tool execution, and logging all work.
- VLLMChatClient: a thin OpenAI-compatible client for the real vLLM
  server, built now against the same interface so the graph doesn't need
  to change when that infra exists.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol, Sequence, Union


@dataclass(frozen=True)
class ToolCallAction:
    tool: str
    args: dict


@dataclass(frozen=True)
class FinalAnswerAction:
    text: str


AgentAction = Union[ToolCallAction, FinalAnswerAction]


class LLMClient(Protocol):
    def next_action(
        self, *, task: str, messages: Sequence[dict], tool_specs: Sequence[dict]
    ) -> AgentAction: ...


class ScriptedLLM:
    """Walks a fixed plan of actions, ignoring task/message content."""

    def __init__(self, plan: Sequence[AgentAction]):
        self._plan = list(plan)
        self._step = 0

    def next_action(
        self, *, task: str, messages: Sequence[dict], tool_specs: Sequence[dict]
    ) -> AgentAction:
        if self._step >= len(self._plan):
            return FinalAnswerAction(text="(scripted plan exhausted)")
        action = self._plan[self._step]
        self._step += 1
        return action


class VLLMChatClient:
    """OpenAI-compatible client for the vLLM server (Llama 3.1 8B / Qwen
    2.5 7B, per the root CLAUDE.md tech stack). Not exercised until that
    VM is provisioned.
    """

    def __init__(self, *, base_url: str, model: str, api_key: str = "not-needed"):
        from openai import OpenAI  # imported lazily: not a hard dep of the demo path

        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._model = model

    def next_action(
        self, *, task: str, messages: Sequence[dict], tool_specs: Sequence[dict]
    ) -> AgentAction:
        openai_messages = [{"role": "system", "content": f"Task: {task}"}]
        for message in messages:
            if message["role"] == "assistant" and "tool" in message:
                openai_messages.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": message["tool"],
                                "type": "function",
                                "function": {
                                    "name": message["tool"],
                                    "arguments": json.dumps(message["args"]),
                                },
                            }
                        ],
                    }
                )
            elif message["role"] == "tool":
                openai_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": message["tool"],
                        "content": json.dumps(message["content"]),
                    }
                )
            else:
                openai_messages.append(message)

        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": spec["name"],
                    "description": spec["description"],
                    "parameters": spec["parameters"],
                },
            }
            for spec in tool_specs
        ]

        response = self._client.chat.completions.create(
            model=self._model,
            messages=openai_messages,
            tools=openai_tools,
        )
        choice = response.choices[0].message
        if choice.tool_calls:
            call = choice.tool_calls[0]
            return ToolCallAction(
                tool=call.function.name, args=json.loads(call.function.arguments)
            )
        return FinalAnswerAction(text=choice.content or "")
