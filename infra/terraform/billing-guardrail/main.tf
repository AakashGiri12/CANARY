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
  }
}

provider "google" {
  project = var.project_id
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
    "cloudfunctions.googleapis.com",
    "cloudbuild.googleapis.com",
    "pubsub.googleapis.com",
  ])
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_pubsub_topic" "budget_alerts" {
  name = "canary-budget-alerts"
}

# credit_types_treatment = EXCLUDE_ALL_CREDITS: track raw usage cost, not
# cost net of the $300 trial credit. The credit draws down against raw
# usage cost, so that's what needs to stay under budget_amount_usd — if
# this tracked *post-credit* cost instead it wouldn't fire until you'd
# already burned through the entire credit. UNVERIFIED against a live
# account; the exact enum value is recalled from memory, not tested.
resource "google_billing_budget" "guardrail" {
  billing_account = var.billing_account_id
  display_name    = "canary-hard-stop"

  budget_filter {
    projects               = ["projects/${data.google_project.this.number}"]
    credit_types_treatment = "EXCLUDE_ALL_CREDITS"
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.budget_amount_usd)
    }
  }

  threshold_rules { threshold_percent = 0.5 }
  threshold_rules { threshold_percent = 0.9 }
  threshold_rules { threshold_percent = 1.0 }

  all_updates_rule {
    pubsub_topic   = google_pubsub_topic.budget_alerts.id
    schema_version = "1.0"
  }
}

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

# Disabling billing needs a permission granted at the BILLING ACCOUNT
# level, not the project level — billing.resourceAssociations.delete,
# which unlinks a project from its billing account.
# roles/billing.projectManager is, per Google's docs, the narrowest
# predefined role that includes it (short of a fully custom
# billing-account-level role, which needs Billing Account Administrator
# to even create — a bootstrapping problem not worth solving here).
# UNVERIFIED against a live account.
resource "google_billing_account_iam_member" "killer_billing_role" {
  billing_account_id = var.billing_account_id
  role               = "roles/billing.projectManager"
  member             = "serviceAccount:${google_service_account.killer.email}"
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

  depends_on = [google_project_service.required]
}
