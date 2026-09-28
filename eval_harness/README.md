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

## Contents

- `scoring.py` — `score_utility` / `score_asr`, both binary for now
  (keyword match / success-marker match against the final answer).
- `runner.py` — `run_static_eval`: runs the no-attack baseline plus every
  attack in `attack_engine.library.STATIC_ATTACKS` against one or more
  named `LLMClient`s, scoring each run. No persistence yet (Postgres is
  build order step 6) — returns an in-memory `list[RunResult]`.
- `report.py` — turns results into a text summary table + per-LLM
  utility/ASR rates.
- `run.py` — entrypoint: `python3 -m eval_harness.run`.

## Run it

```bash
python3 -m eval_harness.run
```
