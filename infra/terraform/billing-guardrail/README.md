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

**Status: deployed and applied for real** (not just `validate`/`plan` —
see "What actually happened" below). Terraform manages everything except
the budget itself, which is created manually through the Console — see
"Creating the budget" below for why.

## What actually happened deploying this

Four real API errors on the first live apply, each a genuine bug caught
by actually running it rather than trusting `validate`/`plan`:

1. **Quota project**: `billingbudgets.googleapis.com` rejected bare ADC
   with "requires a quota project" even after `gcloud auth
   application-default set-quota-project`. Tried fixing this with
   `user_project_override` on the *default* provider — that broke every
   other resource on the next plan ("Cloud Resource Manager API has not
   been used in this project"), including ones that had already applied
   successfully moments earlier. Caught by re-planning immediately
   rather than assuming the fix was safe; fix scoped to an aliased
   provider instead, used only where actually needed.
2. **Wrong IAM role name**: `roles/billing.projectManager` (the first
   guess) doesn't exist as an assignable role at all — real error: "Role
   roles/billing.projectManager is not supported for this resource."
   Corrected via search to `roles/billing.admin` (Billing Account
   Administrator) — broader than ideal, but the actual documented role
   for this operation, confirmed against Google's own reference
   tutorials for this exact pattern.
3. **Missing API**: forgot `billingbudgets.googleapis.com` in the
   services list entirely (it's distinct from `cloudbilling
   .googleapis.com`) — caught by the resulting 403.
4. **Cloud Functions build step failure**: "Unable to retrieve the
   repository metadata for .../repositories/gcf-artifacts" — the
   default service agents' auto-provisioned IAM bindings for a
   freshly-enabled API hadn't propagated yet, since those APIs were only
   just enabled in the same apply. Fixed with a 90s `time_sleep` between
   enabling APIs and creating the function.

After those four, everything **except the budget itself** deployed
successfully and is confirmed in Terraform state (`terraform plan`
reports "No changes"): the Pub/Sub topic, the Cloud Function, the
service account, both IAM grants, all required APIs.

## Creating the budget (manual step — do this)

The budget resource itself hit a wall: three more real, distinct errors
(quota project on this specific resource, then a vague "Error 400:
Request contains an invalid argument" once the previous two were fixed).
Traced the 400 to a missing `pubsub.publisher` grant for Cloud Billing's
notification agent on the topic — a real, documented requirement
(confirmed via search of a known `hashicorp/terraform-provider-google`
issue matching this exact symptom). But the agent's exact service
account identity turned out to be **undocumented even in Google's own
official docs** — fetched the docs page directly to check, not just
searched; it says permission is required but never names who to grant it
to. Guessed once (`cloud-billing-budgets@system.gserviceaccount.com`) —
confirmed wrong: "Service account ... does not exist."

Rather than guess a third time, the budget is created through the
**Console**, whose "Connect a Pub/Sub topic" flow is documented to
handle that grant automatically:

1. Console → Billing → **Budgets & Alerts** → **Create Budget**
2. Scope: this project (`canary-510014`)
3. Amount: **$100** (matches `budget_amount_usd` in `variables.tf` — the
   Terraform variable is kept as the reference value even though nothing
   reads it anymore, so it isn't just a number typed once and forgotten)
4. Actions → check **"Connect a Pub/Sub topic to this budget"** → select
   the existing topic **`canary-budget-alerts`** (already created by
   Terraform — don't create a new one)
5. Set thresholds at 50%, 90%, 100% of the budget amount
6. Save

Terraform stays authoritative for everything it could actually create
without guessing at undocumented internals; the budget is the one piece
the Console can do more reliably.

## Test-fire it before trusting it — this is not optional

Do this **before** creating the GPU VM. Manually publish a synthetic
budget-breach message straight to the Pub/Sub topic — this triggers the
Cloud Function exactly as a real budget breach would (the function
doesn't care whether the message came from the real budget or this
command), including **actually disabling billing on your project**,
which is the whole point of testing it:

```bash
gcloud pubsub topics publish canary-budget-alerts \
  --message='{"budgetDisplayName":"canary-hard-stop","costAmount":150,"budgetAmount":100,"currencyCode":"USD"}'
```

Then check:
```bash
# Cloud Function logs — confirm it ran and took action
gcloud functions logs read canary-billing-killer --region=us-central1 --limit=50

# Confirm billing is actually disabled
gcloud billing projects describe canary-510014
```

**Re-enable billing immediately after the test** (one command, confirmed
working):
```bash
gcloud billing projects link canary-510014 --billing-account=01EB33-618CB6-30FDEA
```
Re-linking billing does not automatically restart anything the function
stopped — that's deliberate, so nothing silently resumes spending
without you choosing to. If the VM stack was running, you'd separately
`terraform apply` it again in `infra/terraform/`.

If the test doesn't work as expected (function doesn't fire, billing
doesn't actually get disabled, permissions errors in the logs) —
**fix it before creating the GPU VM**, not after.

## What's still genuinely unverified

1. **The budget itself** — created manually per above, not yet
   confirmed to actually fire and publish correctly when real spend
   crosses the threshold. The test-fire above verifies the
   function/Pub/Sub/billing-disable path works; it does not verify the
   budget → Pub/Sub link specifically, since it bypasses the budget
   entirely. Worth a real (or at least closer-to-real) end-to-end check
   once you're comfortable — e.g., temporarily setting the budget very
   low and confirming a real cost signal reaches the function.
2. **`credit_types` isn't set on the budget** — since it's created via
   Console rather than Terraform, double check whichever credit-tracking
   option the Console defaults to actually tracks raw usage cost (what
   draws down the $300 credit), not cost *after* the credit is applied.
3. **`google_cloudfunctions_function` (Gen1)** — Google has been pushing
   Gen2 (Cloud Run-based) functions; Gen1 still works for this pattern
   as of this writing but may eventually need migrating.

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
