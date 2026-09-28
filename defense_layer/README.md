# defense_layer

Detects and blocks injected instructions before they reach or influence the
Target Agent.

Two kinds of defense, each a distinct Eval Harness / Pareto configuration:
- **Prompt-based defenses** — instruction hardening, delimiters, sandwiching,
  etc. (build order step 3, first Pareto data point).
- **Trained classifier** — a DeBERTa-v3 encoder (small and base, compared
  against an off-the-shelf baseline) that labels tool output as
  injection/benign with a confidence score. Trained in the cloud (Kaggle/Colab,
  never on the dev laptops), served from the Oracle Always Free VM. See the
  "Classifier training workflow" section of the root CLAUDE.md.
