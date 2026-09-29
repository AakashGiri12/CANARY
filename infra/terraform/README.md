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

**Tear it down when you're not actively running evals:**
```bash
terraform destroy
```
The model-cache disk (`google_compute_disk.model_cache`) has
`prevent_destroy = true` — it survives `destroy` so cached weights don't
need re-downloading next time, but the VM itself does not. Per CLAUDE.md:
forgetting to tear this down is the single most common way to burn
through trial credit. Spot VMs can also be reclaimed by GCP mid-run
regardless — eval batches need to checkpoint to Postgres and resume
(`api.tasks`, build order step 6) rather than assume a run completes
uninterrupted.

## Firewall

`google_compute_firewall.vllm_api` opens port 8000 to `0.0.0.0/0` (the
whole internet) by default, for simplicity. Tighten `source_ranges` to
your own IP before leaving this running for any length of time.
