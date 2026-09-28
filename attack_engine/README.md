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

These payloads currently target `NaiveCompliantLLM`'s specific
vulnerability signature (see the warning in `target_agent/llm.py`) since
there's no real model to attack yet — build order step 6. Real ASR
numbers require a real model; treat step 2's numbers as pipeline
validation.
