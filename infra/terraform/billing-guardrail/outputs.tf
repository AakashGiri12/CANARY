output "pubsub_topic" {
  value = google_pubsub_topic.budget_alerts.id
}

output "function_name" {
  value = google_cloudfunctions_function.killer.name
}
