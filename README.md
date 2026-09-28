# CANARY

Adversarial agent security: studying prompt injection attacks against AI
agents, with an adaptive, self-improving attacker as the core contribution.

Four components:

- **`target_agent/`** — a LangGraph agent that does real tasks (email,
  calendar, file ops, web fetch) via tool calls, exposed to poisoned tool
  outputs.
- **`attack_engine/`** — generates and adaptively mutates prompt injection
  attacks against the Target Agent, retrieving past attack outcomes from
  pgvector to inform new mutations.
- **`defense_layer/`** — detects/blocks injected instructions, via
  prompt-based defenses and a trained classifier.
- **`eval_harness/`** — scores every run on Utility (did the real task
  succeed) and ASR (attack success rate); the headline result is the Pareto
  frontier between them across defense configs.

See `CLAUDE.md` for full project context, hard constraints, infra decisions,
and build order.

## Repo layout

```
canary/
├── target_agent/       # LangGraph agent + tool definitions/mocks
├── attack_engine/       # static attack library + adaptive attacker loop + retrieval
├── defense_layer/       # classifier + structural defenses
├── eval_harness/        # scoring, ASR/utility computation, Pareto analysis, judge validation
├── datasets/             # labeled injection examples, task suite
├── api/                  # FastAPI service
├── dashboard/            # Next.js frontend
├── infra/                # Docker Compose, Terraform, Alembic migrations
├── tests/
└── .github/workflows/    # CI
```

## Local dev setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

docker compose -f infra/docker-compose.yml up -d   # Postgres+pgvector, Redis

pytest

cd dashboard && npm install && npm run dev
```
