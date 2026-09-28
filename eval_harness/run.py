"""Entrypoint: run the static attack library against LLM stand-ins, with
and without the step-3 prompt-based defense, and print ASR/Utility
numbers — the first Pareto data point (build order step 3, extending
step 2's baseline).

    python3 -m eval_harness.run

LLM clients compared:
- scripted-immune[+defense]: ScriptedLLM with a fixed plan that ignores
  tool content entirely (same plan as target_agent.run's demo) — ASR=0%
  regardless of defense, since it was never vulnerable. Included as a
  sanity check that the defense doesn't break behavior it doesn't need to.
- naive-compliant[+defense]: NaiveCompliantLLM, a deliberately naive
  rule-based "no defense" stand-in (see target_agent/llm.py) — ASR=100%
  undefended. The "+defense" variant wraps it in
  defense_layer.PromptDefendedLLM.

None of this is a real model — see the warnings in target_agent/llm.py,
attack_engine/library.py, and defense_layer/prompt_defense.py. Real
ASR/Utility numbers require the vLLM-backed model from build order
step 6.
"""

from __future__ import annotations

from defense_layer.prompt_defense import PromptDefendedLLM
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
        "scripted-immune+defense": lambda: PromptDefendedLLM(
            ScriptedLLM(plan=_immune_plan())
        ),
        "naive-compliant": lambda: NaiveCompliantLLM(),
        "naive-compliant+defense": lambda: PromptDefendedLLM(NaiveCompliantLLM()),
    }
    results = run_static_eval(llm_factories)
    print(summarize(results))


if __name__ == "__main__":
    main()
