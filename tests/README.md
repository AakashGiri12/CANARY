# tests

pytest suite covering target_agent, attack_engine, defense_layer,
eval_harness, and api.

Runs in CI on every push (see `.github/workflows/`). Unit tests mock LLM calls
and embeddings rather than hitting real models — no local LLM/embedding
inference is available on the Intel Mac dev machine, and CI has no GPU either.
