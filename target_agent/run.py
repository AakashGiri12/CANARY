"""Entrypoint: run one clean end-to-end Target Agent task and log every
model turn and tool call. Build order step 1's deliverable.

    python3 -m target_agent.run
"""

from __future__ import annotations

import uuid

from target_agent.graph import build_graph
from target_agent.llm import FinalAnswerAction, ScriptedLLM, ToolCallAction
from target_agent.logging import configure_logging, get_run_logger

TASK = (
    "Check Alice's latest email, verify the numbers she's asking about "
    "against docs/q3_plan.txt and the linked roadmap page, and reply with "
    "a summary."
)


def _demo_plan() -> list:
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


def run_demo_task() -> dict:
    configure_logging()
    run_id = str(uuid.uuid4())
    llm = ScriptedLLM(plan=_demo_plan())
    graph = build_graph(llm)

    initial_state = {
        "run_id": run_id,
        "task": TASK,
        "turn": 0,
        "messages": [],
        "final_answer": None,
    }

    logger = get_run_logger(run_id)
    logger.info("run_start", task=TASK)
    final_state = graph.invoke(initial_state)
    logger.info("run_end", final_answer=final_state["final_answer"])
    return final_state


if __name__ == "__main__":
    run_demo_task()
