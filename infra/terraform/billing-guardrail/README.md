# infra/terraform/billing-guardrail

Account-wide kill switch: a Cloud Billing budget → Pub/Sub → Cloud
Function that **disables billing on the project entirely** once cost
crosses a threshold, plus stops any running Compute Engine instances
immediately as a faster first action. This is the "nuclear option" —
disabling billing is the only mechanism that guarantees zero further
overage regardless of what's running, since it isn't scoped to any
specific resource type (unlike `infra/terraform/`'s VM self-shutdown
timer, which only protects that one VM).

Deploy and test-fire **this module before ever creating the GPU VM**.
It's deliberately a separate Terraform root (own state, own apply) from
`infra/terraform/` so it protects the account independently of that
VM's lifecycle — destroying the VM stack doesn't touch this.

`terraform validate` passes. Not applied, not deployed, not test-fired
— that all needs your credentials and is your call to make.

## What's genuinely unverified here

This is written from memory against Google's documented reference
pattern for this exact use case, not tested against a live account.
Specific things to check:

1. **`credit_types_treatment = "EXCLUDE_ALL_CREDITS"`** — this is what
   makes the budget track raw usage cost (which draws down your $300
   trial credit) rather than cost *after* the credit is applied. If this
   field doesn't behave as expected, the budget might not fire until
   you've already exhausted the credit. Verify with the test-fire below
   before trusting it.
2. **`roles/billing.projectManager`** — recalled as the narrowest
   predefined IAM role that includes permission to unlink a project from
   its billing account. Not confirmed against a live account.
3. **`google_cloudfunctions_function` (Gen1)** — Google has been pushing
   Gen2 (Cloud Run-based) functions; Gen1 still works for this pattern
   as of this writing but may eventually need migrating.
4. Whether your project even has **Cloud Functions / Cloud Build APIs**
   enabled cleanly on a fresh trial account — `google_project_service`
   handles enabling them, but first-time API enablement occasionally
   needs a minute to propagate before dependent resources can be created.

## Prerequisites (your part)

1. `gcloud auth application-default login`
2. Find your billing account ID: `gcloud billing accounts list`
3. Copy `terraform.tfvars.example` → `terraform.tfvars`, fill in
   `project_id` and `billing_account_id` (gitignored — never commit it)

## Deploying

```bash
cd infra/terraform/billing-guardrail
terraform init
terraform plan     # review every resource before creating anything
terraform apply
```

## Test-fire it before trusting it — this is not optional

Do this **before** creating the GPU VM. Manually publish a synthetic
budget-breach message to the Pub/Sub topic — this triggers the Cloud
Function exactly as a real breach would, including **actually disabling
billing on your project**, which is the whole point of testing it (a
test that doesn't pull the trigger doesn't prove anything):

```bash
gcloud pubsub topics publish canary-budget-alerts \
  --message='{"budgetDisplayName":"canary-hard-stop","costAmount":150,"budgetAmount":100,"currencyCode":"USD"}'
```

Then check:
```bash
# Cloud Function logs — confirm it ran and took action
gcloud functions logs read canary-billing-killer --region=us-central1 --limit=50

# Confirm billing is actually disabled
gcloud billing projects describe PROJECT_ID
```

**Re-enable billing immediately after the test** (this is the one-command
re-enable, confirmed):
```bash
gcloud billing projects link PROJECT_ID --billing-account=BILLING_ACCOUNT_ID
```
Re-linking billing does not automatically restart anything the function
stopped — that's deliberate, so nothing silently resumes spending
without you choosing to. If the VM stack was running, you'd separately
`terraform apply` it again in `infra/terraform/`.

If the test doesn't work as expected (function doesn't fire, billing
doesn't actually get disabled, permissions errors in the logs) —
**fix it before creating the GPU VM**, not after.

## Layering with the VM's own shutdown timer

Two independent layers, not redundant:
- `infra/terraform/`'s `max_runtime_hours` bounds *this one VM's*
  worst-case runtime via a plain Linux command — works even if this
  entire billing-guardrail stack has a bug, since it depends on nothing
  GCP-account-specific.
- This module bounds *everything in the project* — catches costs this
  VM's timer wouldn't (persistent disks, other resources, mistakes
  elsewhere), but depends on GCP's budget/Pub/Sub/IAM machinery working
  correctly, which is exactly why it needs testing first.
