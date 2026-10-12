"""Registry mapping a stable llm_name string to a fresh LLMClient
instance. Exists because Celery tasks (build order step 6) only receive
JSON-serializable args, not Python closures — a worker process needs to
rebuild the same LLM instances eval_harness.run uses interactively, from
just a name string.
"""

from __future__ import annotations

import os
from typing import Callable

from dotenv import load_dotenv

from defense_layer.prompt_defense import PromptDefendedLLM
from target_agent.llm import (
    DeepSeekChatClient,
    FinalAnswerAction,
    LLMClient,
    NaiveCompliantLLM,
    ScriptedLLM,
    ToolCallAction,
)

# Loads .env (gitignored) once at import time so DEEPSEEK_API_KEY is
# available via os.environ without every caller remembering to export it.
# See docs/DEEPSEEK_PIVOT.md for why a real paid API is in this registry
# at all — mentor-approved, time-constrained deviation from CLAUDE.md.
load_dotenv()


def _deepseek_api_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError(
            "DEEPSEEK_API_KEY not set. Put it in a .env file at the repo "
            "root (gitignored): DEEPSEEK_API_KEY=sk-... — see "
            "docs/DEEPSEEK_PIVOT.md."
        )
    return key


def _immune_plan() -> list:
    return [
        ToolCallAction(tool="read_email", args={"message_id": "msg-1"}),
        ToolCallAction(tool="read_file", args={"path": "docs/q3_plan.txt"}),
        ToolCallAction(
            tool="fetch_url", args={"url": "https://intranet.example.com/roadmap"}
        ),
        FinalAnswerAction(
            text=(
                "Alice's numbers check out: the Q3 plan and the roadmap page "
                "both list Target Agent for September, matching what she "
                "asked about."
            )
        ),
    ]


LLM_FACTORIES: dict[str, Callable[[], LLMClient]] = {
    "scripted-immune": lambda: ScriptedLLM(plan=_immune_plan()),
    "scripted-immune+defense": lambda: PromptDefendedLLM(ScriptedLLM(plan=_immune_plan())),
    "naive-compliant": lambda: NaiveCompliantLLM(),
    "naive-compliant+defense": lambda: PromptDefendedLLM(NaiveCompliantLLM()),
    # Real model, real ASR/Utility numbers — see docs/DEEPSEEK_PIVOT.md.
    # Not the originally planned backend (that's VLLMChatClient /
    # infra/terraform/), but the same LLMClient interface either way.
    "deepseek": lambda: DeepSeekChatClient(api_key=_deepseek_api_key()),
    "deepseek+defense": lambda: PromptDefendedLLM(
        DeepSeekChatClient(api_key=_deepseek_api_key())
    ),
}


def build_llm(llm_name: str) -> LLMClient:
    if llm_name not in LLM_FACTORIES:
        raise ValueError(f"unknown llm_name: {llm_name!r}; known: {sorted(LLM_FACTORIES)}")
    return LLM_FACTORIES[llm_name]()


def defense_label(llm_name: str) -> str:
    """Derives the defense_config label (used for attack_memory
    filtering and the `runs` table) from the llm_name convention."""
    return "prompt-defense" if "+defense" in llm_name else "none"
