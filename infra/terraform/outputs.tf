output "vllm_external_ip" {
  value = google_compute_instance.vllm.network_interface[0].access_config[0].nat_ip
}

output "vllm_endpoint" {
  description = "OpenAI-compatible base URL — point target_agent.llm.VLLMChatClient's base_url here"
  value       = "http://${google_compute_instance.vllm.network_interface[0].access_config[0].nat_ip}:8000/v1"
}
