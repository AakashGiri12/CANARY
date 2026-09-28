# attack_engine

Generates and adaptively mutates prompt injection attacks against the Target
Agent. This is CANARY's core novel contribution — not a static attack library
run once, but a loop that retrieves past attack outcomes from `attack_memory`
(pgvector, in the shared Postgres) and uses them as few-shot context to inform
new mutations.

Two layers:
- **Static attack library** — seed patterns from AgentDojo / InjecAgent, used
  first (build order step 2) before adaptation is introduced.
- **Adaptive attacker loop** — embeds the current context, pulls top-k similar
  past attacks filtered by target model / defense config, mutates, runs, and
  writes the new outcome back. Introduced in build order step 4, not before.

## Contents

- `library.py` — `STATIC_ATTACKS`: five seed `AttackSpec`s (direct
  override, fake system message, authority impersonation, tool-boundary
  breakout, urgency pretext), each poisoning one target_agent tool
  fixture and declaring a `success_marker` for ASR scoring. Run against
  the Target Agent via `eval_harness.run`.
- `db.py` — SQLAlchemy models (`Attack`, `AttackMemory`) matching the
  root CLAUDE.md's schema. Connects to local Docker Postgres by default;
  set `DATABASE_URL` for a real instance.
- `embeddings.py` — `Embedder` interface: `MockEmbedder` (deterministic,
  no torch, used everywhere today) and `MiniLMEmbedder` (the real thing,
  behind the `ml` extra — runs on the Oracle VM, not this laptop).
- `memory.py` — `record_attack`/`record_outcome`/`retrieve_similar`
  (pgvector cosine-distance top-k, filtered by target_model/
  defense_config) / `clear_memory`.
- `mutate.py` — the "LLM mutator" stand-in: rotates a fixed set of
  delimiter framings, skipping ones retrieved history shows were
  blocked. Not a real generative mutator yet — see its docstring.
- `adaptive.py` / `run_adaptive.py` — the adaptive loop itself: embed →
  retrieve → mutate → run → score → write outcome back. Run with
  `python3 -m attack_engine.run_adaptive` (needs local Postgres up and
  migrated — see `infra/README.md`).

These payloads currently target `NaiveCompliantLLM`'s specific
vulnerability signature (see the warning in `target_agent/llm.py`) since
there's no real model to attack yet — build order step 6. Real ASR
numbers require a real model; treat these numbers as pipeline
validation, including the "ASR improves across generations" result from
the adaptive loop — it demonstrates the retrieval/mutation *mechanism*
works, not that any of this generalizes to a real LLM's behavior.
