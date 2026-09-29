# api

FastAPI service — the backend that ties everything together.

Exposes endpoints for triggering eval runs, querying run/attack/score history
(the `runs`, `attacks`, `scores` relational tables), and streaming live attack
demos to the Next.js dashboard over SSE/WebSocket. Dispatches long-running eval
batches to Celery workers rather than running them in-request.

Runs on the Oracle Always Free VM in production; Postgres is Neon/Supabase and
Redis is Upstash, both free tier — this service itself talks to them over the
network rather than hosting them.

## Contents (build order step 6)

- `celery_app.py` — the Celery app. Three queues (`attack_generation`,
  `task_execution`, `scoring`) so a slow LLM call in one stage doesn't
  block another. Broker/backend default to local Docker Redis.
- `tasks.py` — `execute_task` (runs the Target Agent graph),
  `score_task` (Utility/ASR), `generate_attack_task` (the adaptive
  loop's retrieval+mutation step, queued). All three are idempotent
  against Postgres, keyed by a deterministic `run_id` — that's what
  makes a batch resumable after a crash: resubmitting maps to the same
  rows, and already-completed work is skipped rather than redone.
  `run_static_batch(llm_names, task_id)` submits the static attack
  library + baseline as async execute→score chains.

No FastAPI app yet — the Celery pipeline above is real and tested (unit
tests use `.apply()`/eager mode; also verified against an actual
`celery worker` process + local Redis broker, not just in-process).
Wiring HTTP endpoints on top is still open.

## Running a batch locally

```bash
docker compose -f infra/docker-compose.yml up -d   # Postgres + Redis
alembic -c infra/alembic.ini upgrade head

celery -A api.celery_app worker --loglevel=info --pool=solo \
  -Q attack_generation,task_execution,scoring &

python3 -c "from api.tasks import run_static_batch; print(run_static_batch(['naive-compliant+defense']))"
```

(`--pool=solo` avoids fork-related issues on macOS; drop it on Linux.)
