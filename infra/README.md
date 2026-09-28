# infra

Infrastructure-as-code and local dev environment.

- `docker-compose.yml` — local Postgres+pgvector and Redis for development
  without touching cloud services.
- Terraform — lifecycle (including scripted teardown) for the GCP spot/
  preemptible T4 GPU VM used for LLM serving during eval runs. Not provisioned
  permanently; spun up only for eval runs.
- Alembic migrations for the shared Postgres schema (`runs`, `attacks`,
  `scores`, `attack_memory`).

Oracle Always Free VM (Ampere A1, ARM) and Vercel/Neon/Supabase/Upstash are
managed as free-tier cloud services, not local infra — see the root CLAUDE.md
"Infra decisions" table.
