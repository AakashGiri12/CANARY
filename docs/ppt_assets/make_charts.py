"""Generates the Findings-and-Results charts for FINAL_PRESENTATION.pptx
from the real, validated numbers produced this session (not placeholder
data) — see the session's eval_harness.run output and docs/DEEPSEEK_PIVOT.md
for where each figure comes from:

- config_comparison: the 6-config Utility/ASR line chart, same data shape
  as the live dashboard's ConfigComparison panel (/api/eval/compare),
  using the DeepSeek rows' 25-trial judge-validated numbers (87%/0% and
  100%/0%) rather than a single noisy trial, and the other four configs'
  deterministic numbers.
- adaptive_curve: the adaptive Attack Engine's ASR by generation against
  naive-compliant+defense (blocked, blocked, breach, breach, breach —
  confirmed live via /api/eval/adaptive-run/naive-compliant+defense).
- classifier_bars: the two trained DeBERTa-v3 classifiers' accuracy/F1
  (git commit e84d115's recorded numbers).

Run once: .venv/bin/python3 docs/ppt_assets/make_charts.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT_DIR = Path(__file__).parent

EMERALD = "#1a9e6e"
ROSE = "#e0455f"
SLATE = "#475569"
PURPLE = "#8b5cf6"
AMBER = "#d97706"

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.size": 12,
        "axes.edgecolor": "#cbd5e1",
        "axes.labelcolor": SLATE,
        "xtick.color": SLATE,
        "ytick.color": SLATE,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)


def config_comparison_chart() -> None:
    configs = [
        "Scripted\nBaseline",
        "Scripted\nBaseline+Def",
        "Rule-based\nTarget",
        "Rule-based\nTarget+Def",
        "Target Agent\n(real LLM)",
        "Target Agent\n+ Defense",
    ]
    asr = [0, 0, 71, 0, 0, 0]
    utility = [100, 100, 38, 100, 87, 100]

    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    x = range(len(configs))
    ax.plot(x, asr, marker="o", color=ROSE, linewidth=2.5, markersize=8, label="Attack Success Rate")
    ax.plot(x, utility, marker="o", color=EMERALD, linewidth=2.5, markersize=8, label="Task Utility")
    ax.set_xticks(list(x))
    ax.set_xticklabels(configs, fontsize=10)
    ax.set_ylabel("%")
    ax.set_ylim(-5, 108)
    ax.set_title("Utility / ASR across defense configs (live, real data)", fontsize=13, weight="bold", color="#1e293b")
    ax.legend(loc="center right", frameon=False)
    ax.grid(axis="y", alpha=0.25)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "config_comparison.png", dpi=200)
    plt.close(fig)


def adaptive_curve_chart() -> None:
    gens = [1, 2, 3, 4, 5]
    asr = [0, 0, 100, 100, 100]

    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    ax.plot(gens, asr, marker="o", color=ROSE, linewidth=2.5, markersize=9)
    ax.fill_between(gens, asr, color=ROSE, alpha=0.08)
    ax.set_xticks(gens)
    ax.set_xlabel("Adaptive generation")
    ax.set_ylabel("Attack Success Rate (%)")
    ax.set_ylim(-5, 108)
    ax.set_title("Adaptive attacker vs. prompt-based defense", fontsize=12, weight="bold", color="#1e293b")
    ax.annotate(
        "defense breached\n(new framing found)",
        xy=(3, 100),
        xytext=(3.15, 65),
        fontsize=9,
        color=SLATE,
        arrowprops={"arrowstyle": "->", "color": SLATE},
    )
    ax.grid(axis="y", alpha=0.25)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "adaptive_curve.png", dpi=200)
    plt.close(fig)


def classifier_bars_chart() -> None:
    models = ["deberta-v3-small\n(validated)", "deberta-v3-base\n(collapsed)"]
    accuracy = [83, 50]
    f1 = [85, 66.7]

    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    x = [0, 1]
    width = 0.32
    ax.bar([i - width / 2 for i in x], accuracy, width, label="Accuracy", color=PURPLE)
    ax.bar([i + width / 2 for i in x], f1, width, label="F1", color=AMBER)
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=10)
    ax.set_ylabel("%")
    ax.set_ylim(0, 100)
    ax.set_title("Trained classifier defense (Kaggle-trained)", fontsize=12, weight="bold", color="#1e293b")
    ax.legend(loc="upper right", frameon=False)
    ax.grid(axis="y", alpha=0.25)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "classifier_bars.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    config_comparison_chart()
    adaptive_curve_chart()
    classifier_bars_chart()
    print("wrote:", [p.name for p in OUT_DIR.glob("*.png")])
