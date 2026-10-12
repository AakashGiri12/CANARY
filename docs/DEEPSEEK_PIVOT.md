# LLM backend pivot: DeepSeek API (temporary, mentor-approved)

**Date:** 2026-10-12
**Status:** active deviation from `CLAUDE.md`, scoped to the LLM backend only
**Authorization:** explicit, from the user, citing their mentor's "green
signal to use any means" given a hard "working, tested, validated by
tomorrow" deadline

## What this is

`CLAUDE.md` requires: everything free, no paid APIs, and all LLM inference
self-hosted in the cloud (specifically: vLLM on a GCP spot T4 VM —
`infra/terraform/`, `target_agent.llm.VLLMChatClient`). That remains **the
original, intended architecture** and is fully built: Terraform validated,
startup script debugged through multiple real deploy attempts (GPU quota,
Docker install, a bash integer-arithmetic bug in the shutdown timer — see
`infra/terraform/startup-script.sh` comments and
`infra/terraform/README.md`), and a real `terraform apply` did bring the VM
up and start pulling the model. The blocker was not a design flaw — it was
GCP spot preemption killing the VM ~76 seconds after boot, which is an
inherent, documented risk of spot pricing (`CLAUDE.md` flags it explicitly),
not something retrying once more was guaranteed to fix within the time
available.

Given the deadline, the user's mentor authorized using a paid API
(DeepSeek) instead, purely to get a real (non-mocked) LLM in the loop so
the Eval Harness can report real ASR/Utility numbers rather than numbers
measured against `NaiveCompliantLLM` (a rule-based stand-in — see
`target_agent/llm.py`'s module docstring).

## What changed, concretely

- **Added**, did not modify or delete: `target_agent.llm.DeepSeekChatClient`
  — a thin subclass of `VLLMChatClient` that only overrides the
  `base_url`/`model`/`api_key` defaults. DeepSeek's API is OpenAI-SDK
  compatible, so no new wire-format logic was needed.
- **Added** two registry entries in `eval_harness/llm_registry.py`:
  `"deepseek"` and `"deepseek+defense"`, built the same way every other
  registry entry is (so Celery/API/CLI callers don't need to know this is
  a different kind of backend).
- **Untouched**: `infra/terraform/*`, `VLLMChatClient`, and all their
  documentation. Nothing about the original plan was deleted or rewritten.

## Why a subclass, not a parallel implementation

`VLLMChatClient` already is "a thin OpenAI-compatible client" — DeepSeek's
API uses the same request/response shape. Duplicating that logic under a
different name would just be two copies of the same code to keep in sync;
subclassing keeps the only real difference (which endpoint/model/key) in
one place and makes the eventual swap back trivial.

## Swapping back to the original plan

Once the self-hosted VM is stable (or for the final presentation, to show
the intended end state), re-point the `"deepseek"` / `"deepseek+defense"`
factories in `eval_harness/llm_registry.py` at
`VLLMChatClient(base_url=<terraform output vllm_endpoint>, model=...)`
instead of `DeepSeekChatClient`. No other code changes — this is the whole
point of both classes satisfying the same `LLMClient` protocol.

## For the final PPT

Present two things, explicitly distinguished:

1. **Designed architecture** (what `CLAUDE.md` specifies, and what
   `infra/terraform/` + `VLLMChatClient` fully implement): self-hosted
   Qwen2.5-7B-AWQ via vLLM on a GCP spot T4, free-tier-only, with the real
   bugs found and fixed along the way (quota, Docker, the shutdown-timer
   bash bug) as evidence of real deployment work, not just a diagram.
2. **What the submitted demo actually ran on**: DeepSeek's API, as a
   time-boxed, mentor-approved substitution behind the identical
   `LLMClient` interface — framed as "swapped the backend, not the
   architecture" rather than "changed the plan."

## Secrets handling

`DEEPSEEK_API_KEY` goes in a `.env` file at the repo root (already
gitignored via the existing `.env` / `.env.*` rule) — never committed,
never pasted into chat. `eval_harness/llm_registry.py` loads it via
`python-dotenv` at import time.
