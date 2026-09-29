"""Celery tasks (build order step 6): generate -> execute -> score.

Each task is idempotent against Postgres, keyed by a deterministic
`run_id` string (llm_name:task_id:attack_id-or-baseline) rather than a
random UUID — that determinism is what makes checkpointing possible:
resubmitting the same batch after a crash maps to the same `runs` rows,
and each task checks for already-completed work before doing any.
"""

from __future__ import annotations

from datetime import datetime, timezone

from celery import chain
from sqlalchemy import select

from api.celery_app import app
from attack_engine.db import Run, Score, get_session
from attack_engine.library import STATIC_ATTACKS
from attack_engine.memory import seed_static_attacks
from eval_harness.llm_registry import build_llm, defense_label
from eval_harness.runner import load_task
from eval_harness.scoring import score_asr, score_utility
from target_agent.graph import build_graph
from target_agent.tools import make_tools


@app.task(name="api.tasks.execute_task")
def execute_task(
    *,
    run_id: str,
    task_id: str,
    llm_name: str,
    defense_config: str,
    attack_id_str: str | None,
    target_key: str | None,
    payload_text: str | None,
) -> str:
    """Run the Target Agent graph for one (llm, task, attack) combo and
    write the result to `runs`. Skips actually running anything if
    `run_id` is already marked completed."""
    with get_session() as session:
        existing = session.get(Run, run_id)
        if existing is not None and existing.status == "completed":
            return run_id
        if existing is None:
            session.add(
                Run(
                    id=run_id,
                    task_id=task_id,
                    llm_name=llm_name,
                    defense_config=defense_config,
                    attack_id=attack_id_str,
                    status="running",
                )
            )
        else:
            existing.status = "running"
        session.commit()

    task = load_task(task_id)
    poison = {target_key: payload_text} if target_key and payload_text else {}
    tools = make_tools(poison=poison)
    llm = build_llm(llm_name)
    graph = build_graph(llm, tools=tools)

    initial_state = {
        "run_id": run_id,
        "task": task["prompt"],
        "turn": 0,
        "messages": [],
        "final_answer": None,
    }
    final_state = graph.invoke(initial_state)
    final_answer = final_state.get("final_answer")

    with get_session() as session:
        row = session.get(Run, run_id)
        row.status = "completed"
        row.final_answer = final_answer
        row.completed_at = datetime.now(timezone.utc)
        session.commit()

    return run_id


@app.task(name="api.tasks.score_task")
def score_task(run_id: str, *, task_id: str, success_marker: str | None) -> str:
    """Score a completed run's Utility/ASR and write to `scores`. Skips
    if a score already exists for this run_id."""
    with get_session() as session:
        existing_score = session.scalars(
            select(Score).where(Score.run_id == run_id)
        ).first()
        if existing_score is not None:
            return run_id

        run = session.get(Run, run_id)
        if run is None or run.status != "completed":
            raise RuntimeError(f"run {run_id!r} is not completed yet")

        task = load_task(task_id)
        utility = score_utility(run.final_answer, task["expected_keywords"])
        asr = score_asr(run.final_answer, success_marker) if success_marker else False

        session.add(Score(run_id=run_id, utility=utility, asr=asr))
        session.commit()

    return run_id


@app.task(name="api.tasks.generate_attack_task")
def generate_attack_task(
    *,
    target_model: str,
    defense_config: str,
    base_instruction: str,
    top_k: int = 5,
) -> dict:
    """Retrieval-informed mutation step of the adaptive loop (build
    order step 4), as a queued task rather than an inline call."""
    from attack_engine.embeddings import MockEmbedder
    from attack_engine.memory import retrieve_similar
    from attack_engine.mutate import mutate

    embedder = MockEmbedder()
    history = retrieve_similar(
        query_text=base_instruction,
        embedder=embedder,
        target_model=target_model,
        defense_config=defense_config,
        top_k=top_k,
    )
    mutation = mutate(base_instruction=base_instruction, history=history)
    return {"payload_text": mutation.payload_text, "framing_index": mutation.framing_index}


def run_static_batch(llm_names: list[str], task_id: str = "q3-plan-check") -> list[str]:
    """Submit the static attack library (+ baseline) for each llm_name as
    async execute->score chains. Returns the run_ids submitted.

    Safe to call again after a crash: attack_id_str/target_key/
    payload_text are recomputed the same way each time (deterministic),
    and execute_task/score_task skip already-completed work rather than
    redoing it — that's the checkpointing story. Submission itself isn't
    free (dispatches a no-op task for already-done work), just the
    expensive part (running the Target Agent graph) is skipped.
    """
    attack_ids = seed_static_attacks()
    run_ids: list[str] = []

    for llm_name in llm_names:
        config = defense_label(llm_name)

        run_id = f"{llm_name}:{task_id}:baseline"
        chain(
            execute_task.s(
                run_id=run_id,
                task_id=task_id,
                llm_name=llm_name,
                defense_config=config,
                attack_id_str=None,
                target_key=None,
                payload_text=None,
            ),
            score_task.s(task_id=task_id, success_marker=None),
        ).apply_async()
        run_ids.append(run_id)

        for attack in STATIC_ATTACKS:
            run_id = f"{llm_name}:{task_id}:{attack.id}"
            chain(
                execute_task.s(
                    run_id=run_id,
                    task_id=task_id,
                    llm_name=llm_name,
                    defense_config=config,
                    attack_id_str=str(attack_ids[attack.id]),
                    target_key=attack.target_key,
                    payload_text=attack.payload_text,
                ),
                score_task.s(task_id=task_id, success_marker=attack.success_marker),
            ).apply_async()
            run_ids.append(run_id)

    return run_ids
