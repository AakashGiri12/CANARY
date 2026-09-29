"""Entrypoint: run the static attack library against LLM stand-ins, with
and without the step-3 prompt-based defense, and print ASR/Utility
numbers — the first Pareto data point (build order step 3, extending
step 2's baseline).

    python3 -m eval_harness.run

LLM clients compared (see eval_harness.llm_registry for the registry):
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
ASR/Utility numbers require the vLLM-backed model, which still needs the
GCP spot T4 VM provisioned and running (build order step 6's Terraform
piece), not just the persistence layer step 6 also adds.
"""

from __future__ import annotations

from eval_harness.llm_registry import LLM_FACTORIES
from eval_harness.report import summarize
from eval_harness.runner import run_static_eval
from target_agent.logging import configure_logging


def main() -> None:
    configure_logging()
    results = run_static_eval(LLM_FACTORIES)
    print(summarize(results))


if __name__ == "__main__":
    main()
