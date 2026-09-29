terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.11"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

data "google_project" "this" {
  project_id = var.project_id
}

# APIs this stack needs. Compute Engine's own API is enabled separately
# by the vLLM VM stack (../) — not duplicated here since this module
# should be deployable (and protecting the account) before that VM ever
# exists.
resource "google_project_service" "required" {
  for_each = toset([
    "cloudbilling.googleapis.com",
    "billingbudgets.googleapis.com", # distinct from cloudbilling.googleapis.com — missed this one, real error caught it
    "cloudfunctions.googleapis.com",
    "cloudbuild.googleapis.com",
    "pubsub.googleapis.com",
    "artifactregistry.googleapis.com",
  ])
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# Real error on first apply: Cloud Functions' build step couldn't read
# the gcf-artifacts Artifact Registry repo ("Ensure the Cloud Functions
# service account has artifactregistry.repositories.list/get") because
# the default service agents' auto-provisioned IAM bindings for a
# freshly-enabled API hadn't propagated yet — these three APIs were only
# just enabled above, in the same apply. A fixed wait is a blunt fix, but
# a reliable one for this known GCP eventual-consistency gap.
resource "time_sleep" "api_propagation" {
  depends_on      = [google_project_service.required]
  create_duration = "90s"
}

resource "google_pubsub_topic" "budget_alerts" {
  name = "canary-budget-alerts"
}

# Confirmed correct identity (not a guess): after the budget was created
# through the Console's "Connect a Pub/Sub topic" flow, `gcloud pubsub
# topics get-iam-policy` showed this exact binding already granted by
# that flow. Managing it here too is a safe no-op against what already
# exists (IAM binding grants are idempotent) - it just keeps Terraform
# accurate about what the real infrastructure requires, now that the
# identity is verified rather than guessed. The earlier guess
# (cloud-billing-budgets@system.gserviceaccount.com) was confirmed wrong
# by a real "service account does not exist" error - this is not that.
resource "google_pubsub_topic_iam_member" "billing_publisher" {
  topic  = google_pubsub_topic.budget_alerts.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:billing-budget-alert@system.gserviceaccount.com"
}

# The budget itself is deliberately NOT managed here — see
# billing-guardrail/README.md "Creating the budget (manual step)".
# Three real, distinct API errors on google_billing_budget with
# all_updates_rule.pubsub_topic set (quota project, wrong IAM role name,
# then a vague "invalid argument" traced to a missing pubsub.publisher
# grant for Cloud Billing's notification agent) - and that agent's exact
# service account identity turned out to be undocumented even in
# Google's own official docs (checked directly, not assumed). The
# Console's "Connect a Pub/Sub topic" budget flow is documented to
# handle that grant automatically, so the budget is created there,
# linked to the google_pubsub_topic.budget_alerts topic below - keeping
# Terraform authoritative for everything it could actually create
# without guessing at undocumented internals.

resource "google_service_account" "killer" {
  account_id   = "canary-billing-killer"
  display_name = "CANARY budget kill switch"
}

# Narrow, purpose-built role — not roles/billing.admin or
# roles/compute.instanceAdmin, which grant far more than this function
# needs. resourcemanager.projects.get is needed just to read project
# state; the rest is exactly stop+list for compute and nothing else.
resource "google_project_iam_custom_role" "killer" {
  role_id = "canaryBillingKiller"
  title   = "CANARY billing killer"
  permissions = [
    "resourcemanager.projects.get",
    "compute.instances.stop",
    "compute.instances.list",
  ]
}

resource "google_project_iam_member" "killer_project_role" {
  project = var.project_id
  role    = google_project_iam_custom_role.killer.id
  member  = "serviceAccount:${google_service_account.killer.email}"
}

# Disabling billing needs billing.resourceAssociations.delete, granted
# at the BILLING ACCOUNT level, to unlink a project from its billing
# account. roles/billing.projectManager (tried first) doesn't exist as
# an assignable role at all — real error: "Role roles/billing
# .projectManager is not supported for this resource". Corrected via
# search to roles/billing.admin (Billing Account Administrator) — the
# actual predefined role Google's own reference tutorials for this exact
# auto-disable-billing pattern use. It's broader than ideal (full billing
# account admin, not just this one permission), but there's no narrower
# predefined role, and creating a custom one at the billing-account level
# itself needs Billing Account Administrator to create — a bootstrapping
# problem not worth solving for a single-purpose service account with no
# human login.
resource "google_billing_account_iam_member" "killer_billing_role" {
  billing_account_id = var.billing_account_id
  role                = "roles/billing.admin"
  member              = "serviceAccount:${google_service_account.killer.email}"
}

data "archive_file" "function_source" {
  type        = "zip"
  source_dir  = "${path.module}/function-src"
  output_path = "${path.module}/function-src.zip"
}

resource "google_storage_bucket" "function_bucket" {
  name                        = "${var.project_id}-canary-billing-fn"
  location                    = "US"
  uniform_bucket_level_access = true
  force_destroy               = true
}

resource "google_storage_bucket_object" "function_source" {
  name   = "function-source-${data.archive_file.function_source.output_md5}.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = data.archive_file.function_source.output_path
}

resource "google_cloudfunctions_function" "killer" {
  name        = "canary-billing-killer"
  region      = var.region
  runtime     = "python312"
  entry_point = "stop_billing"

  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.function_source.name

  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource   = google_pubsub_topic.budget_alerts.id
  }

  service_account_email = google_service_account.killer.email

  environment_variables = {
    GCP_PROJECT_ID = var.project_id
  }

  depends_on = [time_sleep.api_propagation]
}
