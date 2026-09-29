# infra/terraform

Provisions the GCP spot/preemptible T4 GPU VM that serves the real
LLM (vLLM, OpenAI-compatible endpoint) for Target Agent + Attack Engine
reasoning, per the root CLAUDE.md's infra decisions table. **Not applied
by this session** — this is real, billable cloud infrastructure, and
provisioning it needs your GCP credentials and your explicit go-ahead
each time, not something to run automatically.

`terraform validate` passes (checked — catches config errors without
needing GCP credentials). `terraform plan`/`apply` have not been run;
they need your project set up first.

## What's genuinely unverified here

Flagging these explicitly rather than presenting untested infra as if
it's known-good:

1. **`boot_disk_image_family`** (`variables.tf`) — GCP's Deep Learning
   VM image family naming has changed since this project's context was
   written. A search confirmed current families look like
   `pytorch-2-9-cu129-ubuntu-2204-nvidia-580`, not the older
   `common-cuXXX` scheme assumed here. The default value is a best
   guess, **not verified to exist**. Before `apply`:
   ```bash
   gcloud compute images list --project deeplearning-platform-release \
     --filter="family~'common-cu'" --show-deprecated
   ```
   and confirm whatever you pick actually supports T4 (compute
   capability 7.5 / Turing — newer CUDA/driver stacks don't always keep
   Turing support).
2. **`vllm_model`** default (`Qwen/Qwen2.5-7B-Instruct-AWQ`) — exact HF
   repo name not verified to currently exist, or its license terms.
   Check `huggingface.co/Qwen` before relying on it.
3. **GPU quota** — CLAUDE.md's guide says new GCP projects often start
   at 0 GPU quota and approval can take days; you said this was already
   requested/granted, but this config has never actually been applied
   against your project to confirm the quota covers this exact request
   (1x T4 in whatever zone you pick).

## Prerequisites (your part — I can't do these)

1. A GCP project with billing enabled and Compute Engine API turned on.
2. `gcloud` CLI installed and authenticated:
   ```bash
   gcloud auth application-default login
   ```
3. Copy `terraform.tfvars.example` to `terraform.tfvars`, fill in your
   real `project_id` (this file is gitignored — never commit it).

## Running it

```bash
cd infra/terraform
terraform init
terraform plan     # review what it would create before applying anything
terraform apply    # costs real money from here on, even at spot pricing
```

Get the vLLM endpoint once it's up:
```bash
terraform output vllm_endpoint
curl $(terraform output -raw vllm_endpoint)/models
```

Point `target_agent.llm.VLLMChatClient(base_url=...)` at that endpoint.

## Cost discipline

**Primary guardrail: `max_runtime_hours` (default 2).** The VM
self-shuts-down via `shutdown -h` this many hours after boot, no matter
what — scheduled as literally the first thing the startup script does,
before model download or anything else, so the clock starts at boot
regardless of setup time. This is deliberate, not a nice-to-have:

- GCP's native Spend Cap (Billing → Budgets & Alerts) only covers
  services already active on the billing account. On a fresh
  project/account, **Compute Engine isn't even selectable** in its
  service picker — confirmed directly in the console before writing
  this, not assumed. So Spend Cap cannot protect against this VM's cost.
- Regular budget alerts are notification-only (email), not an automatic
  stop — useful as a secondary signal, but not a guarantee.
- `shutdown -h` needs no billing API, no IAM permissions, nothing that
  depends on GCP's account-specific state or could be silently
  misconfigured — just a plain Linux command baked into the image. It's
  the only guardrail here I can actually stand behind as verified-to-work
  (`man shutdown`), rather than something whose correctness depends on
  GCP APIs I can't test without your credentials.

Cost ceiling this gives you: spot T4 + n1-standard-4 is roughly
$0.15–0.20/hr (**UNVERIFIED — check GCP's pricing calculator for current
numbers**), so 2 hours caps worst-case compute spend at well under $1,
even in the worst case of forgetting about it entirely. Raise
`max_runtime_hours` once you trust the setup and need longer eval runs.

**Also tear it down manually when done, don't rely on the timer alone:**
```bash
terraform destroy
```
The model-cache disk (`google_compute_disk.model_cache`) has
`prevent_destroy = true` — it survives `destroy` so cached weights don't
need re-downloading next time, but the VM itself does not. A stopped/
terminated VM (whether from the timer or `destroy`) stops compute/GPU
billing; the persistent disks (boot + model-cache, ~150GB by default)
keep billing at the much lower storage rate regardless — check GCP's
current SSD persistent disk pricing for what that costs per month if
left around, and delete the cache disk manually
(`gcloud compute disks delete canary-model-cache --zone=...`) if you
want to eliminate even that.

Spot VMs can also be reclaimed by GCP mid-run regardless of any of the
above — eval batches need to checkpoint to Postgres and resume
(`api.tasks`, build order step 6) rather than assume a run completes
uninterrupted.

**Recommended, in addition to the timer, not instead of it:** set up a
regular (non-Spend-Cap) budget alert covering all services at a low
threshold (e.g. $10–20) for early-warning email notifications. This is
a secondary signal, not a hard stop — the timer above is what actually
enforces a ceiling.

## Firewall

`google_compute_firewall.vllm_api` opens port 8000 to `0.0.0.0/0` (the
whole internet) by default, for simplicity. Tighten `source_ranges` to
your own IP before leaving this running for any length of time.
