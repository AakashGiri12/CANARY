"""The adaptive Attack Engine loop (build order step 4 — the novelty):
embed context, retrieve similar past attempts, mutate, run through the
Target Agent, score, write the outcome back to attack_memory.

Run N generations against one fixed (target_model, defense_config) pair
and the resulting outcomes should show ASR trending upward as the
retrieval-informed mutator discovers a framing the static defense
doesn't catch — see attack_engine/mutate.py for exactly which gap.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from attack_engine.embeddings import Embedder
from attack_engine.memory import record_outcome, retrieve_similar
from attack_engine.mutate import mutate
from eval_harness.scoring import score_asr, score_utility
from target_agent.graph import build_graph
from target_agent.llm import LLMClient
from target_agent.tools import make_tools


@dataclass(frozen=True)
class GenerationResult:
    generation: int
    payload_text: str
    framing_index: int
    outcome: str  # 'success' | 'blocked'
    utility: bool
    asr: bool


def run_adaptive_loop(
    *,
    llm_factory: Callable[[], LLMClient],
    embedder: Embedder,
    target_model: str,
    defense_config: str,
    task: dict,
    target_key: str,
    base_instruction: str,
    success_marker: str,
    generations: int = 5,
    top_k: int = 5,
) -> list[GenerationResult]:
    results: list[GenerationResult] = []

    for gen in range(1, generations + 1):
        history = retrieve_similar(
            query_text=base_instruction,
            embedder=embedder,
            target_model=target_model,
            defense_config=defense_config,
            top_k=top_k,
        )
        mutation = mutate(base_instruction=base_instruction, history=history)

        tools = make_tools(poison={target_key: mutation.payload_text})
        graph = build_graph(llm_factory(), tools=tools)
        initial_state = {
            "run_id": f"{target_model}:{defense_config}:gen-{gen}",
            "task": task["prompt"],
            "turn": 0,
            "messages": [],
            "final_answer": None,
        }
        final_state = graph.invoke(initial_state)
        final_answer = final_state.get("final_answer")

        utility = score_utility(final_answer, task["expected_keywords"])
        asr = score_asr(final_answer, success_marker)
        outcome = "success" if asr else "blocked"

        record_outcome(
            attack_id=None,
            payload_text=mutation.payload_text,
            embedder=embedder,
            target_model=target_model,
            defense_config=defense_config,
            outcome=outcome,
        )

        results.append(
            GenerationResult(
                generation=gen,
                payload_text=mutation.payload_text,
                framing_index=mutation.framing_index,
                outcome=outcome,
                utility=utility,
                asr=asr,
            )
        )

    return results
