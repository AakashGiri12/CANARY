variable "project_id" {
  description = "GCP project ID to protect"
  type        = string
}

variable "billing_account_id" {
  description = "Billing account ID linked to project_id (format XXXXXX-XXXXXX-XXXXXX, from `gcloud billing accounts list`)"
  type        = string
}

variable "budget_amount_usd" {
  description = <<-EOT
    Threshold that triggers the kill switch. Deliberately well under the
    full $300 trial credit, not right up against it — this is a
    first-time, untested setup, and the function itself takes a few
    seconds to run once triggered. $100-150 leaves real margin; raise it
    once you've test-fired this (see README) and trust it.
  EOT
  type        = number
  default     = 100
}
