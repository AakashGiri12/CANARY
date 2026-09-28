# datasets

Labeled injection examples and the task suite the Target Agent is evaluated
against.

Includes:
- Seed attack patterns adapted from AgentDojo and InjecAgent (cloned/extended,
  not vendored wholesale — see attack_engine).
- The Target Agent's task suite (email, calendar, file ops, web fetch
  scenarios) with ground-truth expected outcomes for Utility scoring.
- Hand-labeled examples used to validate the Eval Harness judge model.

Not a Python package — data files (JSON/CSV/JSONL) and dataset-builder
scripts only.

## Contents

- `tasks.json` — the Target Agent task suite. Currently one task
  (`q3-plan-check`) with `expected_keywords` used by
  `eval_harness.scoring.score_utility`.
- `injection_classifier/` — labeled dataset for the Defense Layer's
  trained classifier (build order step 5): `train.csv` / `val.csv` /
  `held_out.csv` plus the `build_dataset.py` generator. Currently
  synthetic/templated, not scraped from AgentDojo/InjecAgent — see its
  own README for why and what upgrading it would take.
