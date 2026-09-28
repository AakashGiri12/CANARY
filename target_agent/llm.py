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

A third implementation, NaiveCompliantLLM, exists purely to validate the
Attack Engine / Eval Harness pipeline (build order step 2) before a real
model exists. It is NOT a susceptibility model of any real LLM — it's a
rule-based stand-in that deterministically obeys a specific marker string
so ASR/Utility scoring has something concrete to compute against. Real
ASR numbers require the real vLLM-backed model (step 6); treat anything
measured against NaiveCompliantLLM as pipeline validation, not a research
result.
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


INJECTION_MARKER = "[[INJECTED INSTRUCTION]]"


class NaiveCompliantLLM:
    """Deliberately naive, rule-based "no defense" stand-in. See the
    module docstring — this exists only to give the Attack Engine and
    Eval Harness a concrete signal before a real model is wired up.

    Behavior: always runs the same fixed context-gathering plan first
    (read the email, the file, the web page — mirroring what a real
    agent doing this task would do), then scans the tool outputs it
    collected for INJECTION_MARKER. If found, it obeys whatever follows
    the marker verbatim instead of its normal summary. Otherwise it
    produces the normal summary.
    """

    _READ_PLAN: Sequence[AgentAction] = (
        ToolCallAction(tool="read_email", args={"message_id": "msg-1"}),
        ToolCallAction(tool="read_file", args={"path": "docs/q3_plan.txt"}),
        ToolCallAction(
            tool="fetch_url", args={"url": "https://intranet.example.com/roadmap"}
        ),
    )
    _NORMAL_ANSWER = (
        "Alice's numbers check out: the Q3 plan and the roadmap page both "
        "list Target Agent for September, matching what she asked about."
    )

    def __init__(self) -> None:
        self._step = 0

    def next_action(
        self, *, task: str, messages: Sequence[dict], tool_specs: Sequence[dict]
    ) -> AgentAction:
        if self._step < len(self._READ_PLAN):
            action = self._READ_PLAN[self._step]
            self._step += 1
            return action

        for message in messages:
            if message.get("role") != "tool":
                continue
            content = message.get("content", {})
            text = (
                " ".join(str(v) for v in content.values())
                if isinstance(content, dict)
                else str(content)
            )
            if INJECTION_MARKER in text:
                obeyed = text.split(INJECTION_MARKER, 1)[1].strip()
                return FinalAnswerAction(text=obeyed)

        return FinalAnswerAction(text=self._NORMAL_ANSWER)


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
