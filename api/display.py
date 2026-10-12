"""Public-facing display labels for defense configs.

Internal registry keys (eval_harness.llm_registry.LLM_FACTORIES) are
never surfaced in API responses or the dashboard — per explicit
instruction, the DeepSeek backend swap (docs/DEEPSEEK_PIVOT.md) stays an
implementation detail, invisible in the UI. Add a new LLM_FACTORIES entry
here too, or it falls back to showing its raw key.
"""

from __future__ import annotations

DISPLAY_LABELS: dict[str, str] = {
    "scripted-immune": "Scripted Baseline",
    "scripted-immune+defense": "Scripted Baseline + Defense",
    "naive-compliant": "Rule-based Target (No Defense)",
    "naive-compliant+defense": "Rule-based Target + Defense",
    "deepseek": "Target Agent (No Defense)",
    "deepseek+defense": "Target Agent + Defense",
}


def display_label(llm_name: str) -> str:
    return DISPLAY_LABELS.get(llm_name, llm_name)
