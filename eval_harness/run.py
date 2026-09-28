"""Entrypoint: run the static attack library against two LLM stand-ins and
print first ASR/Utility numbers. Build order step 2's deliverable.

    python3 -m eval_harness.run

Two LLM clients are compared:
- scripted-immune: ScriptedLLM with a fixed plan that ignores tool
  content entirely (same plan as target_agent.run's demo) — expected
  ASR=0% since it never reads what the tools return.
- naive-compliant: NaiveCompliantLLM, a deliberately naive rule-based
  "no defense" stand-in (see target_agent/llm.py) — expected ASR>0%.

Neither is a real model. Real ASR/Utility numbers require the vLLM-backed
model from build order step 6; this proves the scoring pipeline works.
"""

from __future__ import annotations

from eval_harness.report import summarize
from eval_harness.runner import run_static_eval
from target_agent.llm import FinalAnswerAction, NaiveCompliantLLM, ScriptedLLM, ToolCallAction
from target_agent.logging import configure_logging


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


def main() -> None:
    configure_logging()
    llm_factories = {
        "scripted-immune": lambda: ScriptedLLM(plan=_immune_plan()),
        "naive-compliant": lambda: NaiveCompliantLLM(),
    }
    results = run_static_eval(llm_factories)
    print(summarize(results))


if __name__ == "__main__":
    main()
