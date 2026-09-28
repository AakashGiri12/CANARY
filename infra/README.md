# infra

Infrastructure-as-code and local dev environment.

- `docker-compose.yml` — local Postgres+pgvector and Redis for development
  without touching cloud services.
- Terraform — lifecycle (including scripted teardown) for the GCP spot/
  preemptible T4 GPU VM used for LLM serving during eval runs. Not provisioned
  permanently; spun up only for eval runs.
- `alembic.ini` / `migrations/` — Alembic migrations for the shared Postgres
  schema. So far: `attacks` and `attack_memory` (pgvector), the tables
  `attack_engine`'s adaptive loop needs (build order step 4). `runs` and
  `scores` — the rest of the "structured lineage" — come with step 6's
  Celery + Postgres persistence work.

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
