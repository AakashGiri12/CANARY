"""Runs the static attack library (plus a no-attack baseline) against one
or more LLM clients and scores each run. No persistence yet — Postgres
comes in build order step 6; this returns an in-memory list of results.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from attack_engine.library import STATIC_ATTACKS, AttackSpec
from eval_harness.scoring import score_asr, score_utility
from target_agent.graph import build_graph
from target_agent.llm import LLMClient
from target_agent.tools import make_tools

TASKS_PATH = Path(__file__).resolve().parents[1] / "datasets" / "tasks.json"


def load_task(task_id: str) -> dict:
    tasks = json.loads(TASKS_PATH.read_text())
    return tasks[task_id]


@dataclass(frozen=True)
class RunResult:
    llm_name: str
    attack_id: str | None  # None = no-attack baseline
    utility: bool
    asr: bool
    final_answer: str | None


def _run_once(
    *,
    llm: LLMClient,
    llm_name: str,
    task_id: str,
    task: dict,
    attack: AttackSpec | None,
) -> RunResult:
    poison = {attack.target_key: attack.payload_text} if attack else {}
    tools = make_tools(poison=poison)
    graph = build_graph(llm, tools=tools)

    initial_state = {
        "run_id": f"{llm_name}:{task_id}:{attack.id if attack else 'baseline'}",
        "task": task["prompt"],
        "turn": 0,
        "messages": [],
        "final_answer": None,
    }
    final_state = graph.invoke(initial_state)
    final_answer = final_state.get("final_answer")

    utility = score_utility(final_answer, task["expected_keywords"])
    asr = score_asr(final_answer, attack.success_marker) if attack else False

    return RunResult(
        llm_name=llm_name,
        attack_id=attack.id if attack else None,
        utility=utility,
        asr=asr,
        final_answer=final_answer,
    )


def run_static_eval(
    llm_factories: dict[str, Callable[[], LLMClient]],
    task_id: str = "q3-plan-check",
) -> list[RunResult]:
    """For each named LLM client, run the no-attack baseline plus every
    static attack, scoring Utility and ASR for each."""
    task = load_task(task_id)
    results: list[RunResult] = []

    for llm_name, make_llm in llm_factories.items():
        results.append(
            _run_once(
                llm=make_llm(), llm_name=llm_name, task_id=task_id, task=task, attack=None
            )
        )
        for attack in STATIC_ATTACKS:
            results.append(
                _run_once(
                    llm=make_llm(),
                    llm_name=llm_name,
                    task_id=task_id,
                    task=task,
                    attack=attack,
                )
            )

    return results
