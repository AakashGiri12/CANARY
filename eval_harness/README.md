# eval_harness

Scores every run on two axes:

- **Utility** — did the Target Agent still complete the real task correctly,
  despite (or absent) a poisoned tool output.
- **ASR (Attack Success Rate)** — did the injection succeed in hijacking the
  agent's behavior.

The headline result of CANARY is the Pareto frontier between Utility and ASR
across defense configurations (no defense, prompt-based, classifier-small,
classifier-base, off-the-shelf baseline).

Also owns judge-model validation: the Eval Harness uses a self-hosted model as
an LLM judge (no paid Anthropic API), and this package must hand-label a
50-100 example subset and report the judge's agreement rate against those
labels as methodological justification.
