# infra

Infrastructure-as-code and local dev environment.

- `docker-compose.yml` — local Postgres+pgvector and Redis for development
  without touching cloud services.
- `terraform/` — lifecycle (including scripted teardown) for the GCP spot/
  preemptible T4 GPU VM used for LLM serving during eval runs. Not provisioned
  permanently; spun up only for eval runs. Written but not applied — see its
  own README for what's unverified and what needs your action.
- `alembic.ini` / `migrations/` — Alembic migrations for the shared Postgres
  schema: `attacks` + `attack_memory` (pgvector, step 4), and `runs` +
  `scores` (structured lineage, step 6) — the tables `api.tasks`'
  Celery pipeline reads/writes.

Oracle Always Free VM (Ampere A1, ARM) and Vercel/Neon/Supabase/Upstash are
managed as free-tier cloud services, not local infra — see the root CLAUDE.md
"Infra decisions" table.

## Local dev

```bash
docker compose -f infra/docker-compose.yml up -d
alembic -c infra/alembic.ini upgrade head
```

`attack_engine/db.py` connects to `postgresql+psycopg2://canary:canary@localhost:5432/canary`
by default (matching the compose file above); set `DATABASE_URL` to point
elsewhere (a real Neon/Supabase instance, CI's service container, etc).
