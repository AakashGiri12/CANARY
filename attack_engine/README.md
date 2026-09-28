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
