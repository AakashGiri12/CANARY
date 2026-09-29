variable "project_id" {
  description = "GCP project ID to protect"
  type        = string
}

variable "region" {
  description = "Region for the Cloud Function"
  type        = string
  default     = "us-central1"
}

variable "billing_account_id" {
  description = "Billing account ID linked to project_id (format XXXXXX-XXXXXX-XXXXXX, from `gcloud billing accounts list`)"
  type        = string
}

variable "budget_amount_usd" {
  description = <<-EOT
    Not wired into any Terraform resource — the budget itself is created
    manually in the Console (see README), since Terraform couldn't
    reliably create it. Kept here as the single reference value to use
    when creating that budget, so it isn't just a number typed once and
    forgotten. Deliberately well under the full $300 trial credit: this
    is a first-time, untested setup, and the function itself takes a few
    seconds to run once triggered. $100-150 leaves real margin; raise it
    once you've test-fired this and trust it.
  EOT
  type    = number
  default = 100
}
