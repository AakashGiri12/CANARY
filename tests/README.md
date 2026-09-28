# tests

pytest suite covering target_agent, attack_engine, defense_layer,
eval_harness, and api.

Runs in CI on every push (see `.github/workflows/`). Unit tests mock LLM calls
and embeddings rather than hitting real models — no local LLM/embedding
inference is available on the Intel Mac dev machine, and CI has no GPU either.

`attack_engine`'s memory/adaptive tests (`test_attack_engine_memory.py`,
`test_attack_engine_adaptive.py`) do need a real Postgres+pgvector —
that's local, free, and fast (`docker compose -f infra/docker-compose.yml
up -d && alembic -c infra/alembic.ini upgrade head`), unlike an LLM. CI
runs a `pgvector/pgvector:pg16` service container for the same reason. The
`unique_model_defense` fixture in `conftest.py` keeps tests from
polluting each other's retrieval queries instead of requiring a full
DB reset between tests.
