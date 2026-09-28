"""Turns a list of RunResult into a human-readable summary. The headline
Pareto-frontier chart comes later (dashboard, once there's more than one
defense config to plot against) — this is just a text table for now.
"""

from __future__ import annotations

from eval_harness.runner import RunResult


def summarize(results: list[RunResult]) -> str:
    header = f"{'llm':<20}{'attack':<32}{'utility':<10}{'asr':<6}"
    lines = [header, "-" * len(header)]

    for r in results:
        lines.append(
            f"{r.llm_name:<20}{(r.attack_id or 'baseline'):<32}"
            f"{str(r.utility):<10}{str(r.asr):<6}"
        )

    lines.append("")
    for llm_name in sorted({r.llm_name for r in results}):
        subset = [r for r in results if r.llm_name == llm_name]
        attacked = [r for r in subset if r.attack_id is not None]
        utility_rate = sum(r.utility for r in subset) / len(subset)
        asr_rate = sum(r.asr for r in attacked) / len(attacked) if attacked else 0.0
        lines.append(
            f"{llm_name}: utility={utility_rate:.0%} over {len(subset)} runs, "
            f"ASR={asr_rate:.0%} over {len(attacked)} attacked runs"
        )

    return "\n".join(lines)
