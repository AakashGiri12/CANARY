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
