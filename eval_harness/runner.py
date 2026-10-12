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
    trial: int = 0,
    score_asr_fn: Callable[[str | None, str], bool] = score_asr,
) -> RunResult:
    poison = {attack.target_key: attack.payload_text} if attack else {}
    tools = make_tools(poison=poison)
    graph = build_graph(llm, tools=tools)

    run_id = f"{llm_name}:{task_id}:{attack.id if attack else 'baseline'}"
    if trial:
        run_id += f":trial{trial}"

    initial_state = {
        "run_id": run_id,
        "task": task["prompt"],
        "turn": 0,
        "messages": [],
        "final_answer": None,
    }
    final_state = graph.invoke(initial_state)
    final_answer = final_state.get("final_answer")

    utility = score_utility(final_answer, task["expected_keywords"])
    asr = score_asr_fn(final_answer, attack.success_marker) if attack else False

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
    trials: int = 1,
    score_asr_fn: Callable[[str | None, str], bool] = score_asr,
) -> list[RunResult]:
    """For each named LLM client, run the no-attack baseline plus every
    static attack, scoring Utility and ASR for each.

    `trials` repeats every (llm, attack) combo this many times. Default 1
    preserves the original behavior (and the exact-count test assertions
    in tests/test_eval_harness_runner.py) for the deterministic stand-ins.
    Real models sample stochastically — found live against DeepSeek: the
    same (llm, attack) pair scored ASR True in one run and False in
    another, single-digit seconds apart. A single trial isn't a solid
    basis for a reported ASR number against a real model; pass trials>1
    (eval_harness.run does, for the deepseek* configs) to average it out.

    `score_asr_fn` defaults to the free, offline keyword heuristic in
    eval_harness.scoring. Pass eval_harness.judge.judge_asr for real-model
    configs instead — found live, the keyword heuristic produces false
    positives on real free-text refusals it doesn't have a cue for (see
    judge.py's module docstring); the deterministic stand-ins never
    exercise that gap, so they don't need the judge.
    """
    task = load_task(task_id)
    results: list[RunResult] = []

    for llm_name, make_llm in llm_factories.items():
        for trial in range(trials):
            results.append(
                _run_once(
                    llm=make_llm(),
                    llm_name=llm_name,
                    task_id=task_id,
                    task=task,
                    attack=None,
                    trial=trial,
                    score_asr_fn=score_asr_fn,
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
                        trial=trial,
                        score_asr_fn=score_asr_fn,
                    )
                )

    return results
