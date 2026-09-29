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

**Status: fully deployed, budget created, and test-fired for real.** Not
just `validate`/`plan` — see "What actually happened" below for the
deploy, and "Test-fire" below for the live run. Confirmed end to end on
2026-09-29: published a synthetic budget-breach message, the function
ran, logged `cost (150) >= budget (100) — acting now`, then `billing
disabled for canary-510014`, finished in ~16s, and `gcloud billing
projects describe` independently confirmed `billingEnabled: false`.
Billing was re-enabled immediately after via `gcloud billing projects
link` (also confirmed). The budget itself is created through the Console
(₹7000 target, scoped to `canary-510014` only — not "All projects",
since the function only acts on that one project), linked to the
`canary-budget-alerts` topic; after creating it, `gcloud pubsub topics
get-iam-policy` confirmed the Console auto-granted
`billing-budget-alert@system.gserviceaccount.com` publisher access on
the topic — the identity that earlier attempts to set this up in
Terraform had guessed wrong twice. That grant is now also captured in
Terraform (`google_pubsub_topic_iam_member.billing_publisher`, applied
as a safe idempotent no-op against what the Console already created), so
Terraform is accurate again even though the budget object itself stays
Console-managed.

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

## The budget (created manually — done)

The budget resource itself hit a wall in Terraform: three more real,
distinct errors (quota project on this specific resource, then a vague
"Error 400: Request contains an invalid argument" once the previous two
were fixed). Traced the 400 to a missing `pubsub.publisher` grant for
Cloud Billing's notification agent on the topic — a real, documented
requirement (confirmed via search of a known
`hashicorp/terraform-provider-google` issue matching this exact
symptom). But the agent's exact service account identity turned out to
be **undocumented even in Google's own official docs** — fetched the
docs page directly to check, not just searched; it says permission is
required but never names who to grant it to. Guessed once
(`cloud-billing-budgets@system.gserviceaccount.com`) — confirmed wrong:
"Service account ... does not exist."

Rather than guess a third time, the budget was created through the
**Console** instead, whose "Connect a Pub/Sub topic" flow handled that
grant automatically (verified after the fact — see "Status" above):

- Scope: **`canary-510014` only** (not "All projects" — the kill-switch
  function only acts on this one project, so tracking spend elsewhere
  would create a mismatch between what's measured and what can respond)
- Amount: **₹7000** (~24% of the ₹28,664 total free-trial credit —
  conservative for a first, freshly-tested threshold; `budget_amount_usd`
  in `variables.tf` is stale/informational now that the real amount is
  in ₹, not $)
- Thresholds: 50/90/100%, triggered on **Actual** spend (not forecasted)
- Pub/Sub topic: **`canary-budget-alerts`** (the one Terraform created)
- Budget type: **Alerts only** (not Spend Cap — Spend Cap is still
  limited to a small set of services and doesn't cover Compute Engine,
  confirmed directly in the Console before choosing Alerts-only)

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

1. **The full automatic path, end to end** — every individual link is
   now confirmed: the Function → billing-disable path (real test-fire),
   and the budget → Pub/Sub IAM wiring (`get-iam-policy` showed the
   Console's auto-granted binding). What's NOT yet observed is a *real*
   cost signal flowing budget → Pub/Sub → function on its own, since
   that needs actual billed usage to accrue (the Console itself notes
   actual costs can take up to 24h to show up) and nothing has spent
   money yet. Worth treating the first real GPU VM session as that final
   check — watch for it working, don't just assume it will because the
   pieces individually check out.
2. **`credit_types` isn't set on the budget** — since it's created via
   Console rather than Terraform, double check whichever credit-tracking
   option the Console defaults to actually tracks raw usage cost (what
   draws down the free-trial credit), not cost *after* the credit is
   applied.
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
