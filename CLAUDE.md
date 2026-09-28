# CANARY — Project Context for Claude Code

Adversarial agent security project. Major/production-grade academic project. Read this fully before making architectural decisions — constraints below are non-negotiable unless the user says otherwise.

## What CANARY is
A system for studying prompt injection attacks against AI agents, with an **adaptive, self-improving attacker** as the core novel contribution (not just a static benchmark run).

Four components:
1. **Target Agent** — does real tasks (email, calendar, file ops, web fetch) via tool calls; exposed to poisoned tool outputs
2. **Attack Engine** — generates and adaptively mutates prompt injection attacks against the Target Agent, using retrieval over past attack outcomes to inform new mutations
3. **Defense Layer** — detects/blocks injected instructions (prompt-based + a trained classifier)
4. **Eval Harness** — scores every run on two axes: **Utility** (did the real task still succeed) and **ASR** (attack success rate); the headline result is the Pareto frontier between them across defense configs

## Hard constraints
- **Everything must be free.** No paid APIs (no Anthropic API key available). No paid cloud tiers beyond time-boxed trial credits used deliberately.
- **No local LLM serving.** Mentor requires all LLM inference to run in the cloud, not on the user's own machine. (Local ML training for the small classifier is fine — deploying trained weights to the cloud afterward is the normal workflow — but prefer a free cloud GPU notebook over local training so the whole pipeline stays cloud-based; see Classifier Training Workflow below.)
- **No Streamlit.** Frontend must be a real production stack (Next.js), not a prototyping tool — mentor's explicit call.
- Must look and behave like a genuinely production-ready system: CI, containerization, observability, migrations, infra-as-code — not a notebook or a script with a UI bolted on.

## Development machines
Two laptops are in play; neither runs project inference or training directly — both are just dev/orchestration machines:
- **MacBook Pro 16" 2019** (Intel i9, AMD Radeon Pro 5500M, 64GB RAM, macOS Tahoe): primary dev machine. Runs Claude Code, Git, Docker Compose (Postgres+pgvector, Redis), FastAPI, Celery, pytest, and the Next.js dev server without issue. Has no CUDA-capable GPU — do not attempt to run vLLM, PyTorch model training, or local embedding inference here. Recent PyTorch releases have dropped Intel Mac wheels, so even CPU-only PyTorch use here should be minimal (mock embeddings in unit tests instead).
- **HP Victus (RTX 3050, 4GB VRAM)**: secondary machine, useful only as a *debugging* environment for the classifier training script (small batch size or LoRA to fit 4GB VRAM) before running the real job on a free cloud GPU. Not the primary training path — see below.
- **Architecture consequence:** the Oracle Always Free VM is ARM64. Docker images built on either laptop (both x86) will not match it — build production images for `linux/arm64` via GitHub Actions buildx, not by emulating ARM locally (slow and unreliable).

## Infra decisions (already made — don't re-litigate without reason)

| Component | Where | Why |
|---|---|---|
| Self-hosted LLM (Target Agent + Attack Engine reasoning) | GCP GPU VM (T4, **spot/preemptible**), spun up only for eval runs, torn down after | Only piece that needs a GPU. Spot pricing makes the $300 trial credit last much longer. Design eval batches to be resumable/checkpointed since spot instances can be reclaimed. |
| Injection-detection classifier (Defense Layer) | Oracle Cloud Always Free VM (Ampere A1, CPU, ARM) | Small classifier (DeBERTa-v3-small) runs fine on CPU |
| Embedding model for attack memory | Same Oracle Always Free VM (CPU) | `sentence-transformers/all-MiniLM-L6-v2`, 384-dim, no API needed |
| FastAPI backend + Celery workers | Oracle Always Free VM | Permanent, $0 forever |
| Postgres (+ pgvector) | Neon or Supabase free tier | Don't self-host DB on the constrained 12GB Oracle box; pgvector extension is included free on both |
| Redis | Upstash free tier (serverless) | Same logic — offload from the Oracle box |
| Frontend | Next.js on Vercel free tier | Free forever for this scale, handles CDN/SSL/build |

**Note:** Oracle Always Free was cut from 4 OCPU/24GB to **2 OCPU/12GB** in June 2026 — design around the smaller number. Prefer `eu-frankfurt-1` or `ap-singapore-1` for Oracle region (better Ampere A1 capacity availability than US regions).

## Judge model (replaces needing Anthropic API)
Use one of the self-hosted models as the Eval Harness judge. Validate it: hand-label a 50–100 example subset, measure the judge's agreement rate against those labels, report that agreement rate in the writeup. Don't skip this — it's the methodological justification for not using a paid frontier judge.

## Memory / Knowledge base
Two kinds, don't conflate:
1. **Structured lineage** — relational tables (`runs`, `attacks`, `scores`) in the same Postgres
2. **Semantic retrieval memory** — `attack_memory` table with a `pgvector` column in the *same* Postgres (not a separate vector DB — keeps metadata and embeddings joinable in one query)

Schema:
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE attack_memory (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attack_id       UUID REFERENCES attacks(id),
    payload_text    TEXT NOT NULL,
    embedding       VECTOR(384),
    target_model    TEXT NOT NULL,
    defense_config  TEXT NOT NULL,
    outcome         TEXT NOT NULL,        -- 'success' | 'blocked' | 'partial'
    asr_delta       FLOAT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON attack_memory USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

Retrieval flow: before generating a new mutation, embed the current context, pull top-k similar past attacks filtered by `target_model`/`defense_config`, feed them into the mutation prompt as few-shot context, write the new result back after the run. This is the mechanism that makes the Attack Engine's adaptation explainable rather than "the LLM just improvised differently."

A local Chroma instance is fine as a personal dev-loop scratch space, but Postgres/pgvector is the system of record — don't let logic depend on local-only storage.

## Classifier training workflow (Defense Layer)
DeBERTa is an encoder classifier (label + confidence), not generative — it cannot hallucinate, it can only misclassify (false negative = injection slips through; false positive = benign content blocked, hurting Utility). Don't settle on one model size by assumption — compare, and report the comparison.

**Models to train and evaluate as separate defense configurations (each becomes its own Pareto point):**
1. `microsoft/deberta-v3-small` (~141M params) — cheapest to run on the Oracle CPU box; use if base's accuracy gain doesn't justify its inference cost
2. `microsoft/deberta-v3-base` (~184M params) — often meaningfully more accurate; train this too, don't assume small is sufficient
3. An off-the-shelf public injection classifier (e.g. search Hugging Face for ProtectAI's deberta-v3-base prompt-injection model, or Meta's Prompt Guard — check current names/licenses, Prompt Guard may be gated) as a **baseline to beat**, not something to build from scratch

**Where training happens (cloud, not local):**
1. **Kaggle Notebooks** (preferred) — free P100/T4 GPU, ~30hr/week quota (verify current limits), supports "Save & Run All" so a dropped session doesn't kill the job, persists datasets/outputs
2. **Google Colab free tier** — good for quick iteration; T4 access isn't guaranteed and sessions time out, so checkpoint to Google Drive or the Hugging Face Hub as you go
3. **Lightning AI Studios** — monthly free credits, persistent environment; backup if Kaggle quota runs out
4. **GCP GPU VM** (the same one provisioned for vLLM) — last resort since it spends trial credit; fine if the free options are exhausted
5. HP Victus RTX 3050 — local only for debugging the training script (small batch/LoRA), never the actual training run

**Workflow:** version the training script + dataset builder in the repo → train on Kaggle/Colab → push trained weights to a private Hugging Face Hub repo → Oracle VM pulls weights from the Hub at deploy time. Keeps training reproducible and the whole pipeline cloud-based, which is also a stronger methodology story for the writeup (small vs. base vs. off-the-shelf, with the adaptive Attack Engine expected to eventually erode all three — that erosion is a finding, not a failure).

## Tech stack summary
- **Agent framework:** LangGraph (or Pydantic AI as fallback)
- **LLM serving:** vLLM on the GCP spot T4, OpenAI-compatible endpoint; models: Llama 3.1 8B Instruct / Qwen 2.5 7B Instruct, AWQ/GPTQ quantization if going bigger
- **Classifier training:** PyTorch + Hugging Face Transformers + PEFT/LoRA, trained on Kaggle/Colab (see Classifier training workflow above), base models `microsoft/deberta-v3-small` and `microsoft/deberta-v3-base` compared against an off-the-shelf baseline
- **Attack/eval baselines:** AgentDojo (clone, extend), InjecAgent (seed attack patterns)
- **Data:** Postgres via Neon/Supabase (+ pgvector), Redis via Upstash, Celery for async batch runs, SQLAlchemy + Alembic
- **Backend:** FastAPI + Pydantic
- **Observability:** Langfuse (self-hosted or free cloud tier), `structlog`, optional Grafana + Prometheus
- **Testing/CI:** pytest, GitHub Actions (fail build if ASR regresses past a threshold)
- **Frontend:** Next.js + TypeScript + Tailwind + shadcn/ui + Recharts/Tremor, SSE/WebSocket to FastAPI for live attack demo
- **Infra:** Docker Compose per service, Terraform for the GCP spot VM lifecycle (script the teardown — don't rely on remembering to stop it)

## Known risks to keep in mind while building
- GCP GPU quota can be 0 for new accounts — request increase early, don't block on it later
- Spot T4 can be reclaimed mid-run — eval batches must checkpoint to Postgres and resume
- Cache model weights on a persistent disk/GCS bucket — don't re-download from Hugging Face on every VM boot
- Test `pip install` on the actual Oracle ARM VM early — not all wheels have `aarch64` builds; build/test Docker images for `linux/arm64` via CI buildx rather than emulating ARM on the (x86) dev laptops
- vLLM on T4 (compute capability 7.5): stick to AWQ/GPTQ quantization, not the newest Ampere-only quant kernels
- Llama 3.1 license has acceptable-use terms — fine for academic use, note it in the writeup
- Free-GPU-notebook quotas (Kaggle/Colab) change over time — check current limits before planning training schedules around them
- Classifier training is cloud-based (Kaggle/Colab), not on either dev laptop — neither has a training-suitable cloud-free GPU path locally (Mac has no CUDA GPU; Victus's RTX 3050 is debug-only)

## Repo structure (target)
```
canary/
├── target_agent/       # LangGraph agent + tool definitions/mocks
├── attack_engine/      # static attack library + adaptive attacker loop + retrieval
├── defense_layer/      # classifier + structural defenses
├── eval_harness/       # scoring, ASR/utility computation, Pareto analysis, judge validation
├── datasets/           # labeled injection examples, task suite
├── api/                # FastAPI service
├── dashboard/          # Next.js frontend
├── infra/              # Docker Compose, Terraform, Alembic migrations
├── tests/
└── .github/workflows/  # CI
```

## Build order (don't skip ahead)
1. Target Agent + 3 mock tools + logging → one clean end-to-end task run
2. Static Attack Engine (no adaptation yet) + basic Eval Harness → first ASR/Utility numbers
3. One simple Defense (prompt-based) → first Pareto data point
4. Adaptive Attack Engine loop + pgvector retrieval → the novelty; don't start here
5. Trained classifier Defense → second data point, real ML story
6. Celery + Postgres persistence, spot-VM Terraform lifecycle → "production" story
7. FastAPI + Next.js dashboard + CI → polish pass
