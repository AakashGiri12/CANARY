variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for the spot GPU VM"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone — must have T4 GPU + spot capacity in `region`"
  type        = string
  default     = "us-central1-a"
}

variable "machine_type" {
  description = "GCE machine type paired with the T4"
  type        = string
  default     = "n1-standard-4"
}

variable "gpu_type" {
  type    = string
  default = "nvidia-tesla-t4"
}

variable "gpu_count" {
  type    = number
  default = 1
}

variable "boot_disk_image_family" {
  description = <<-EOT
    UNVERIFIED — GCP's Deep Learning VM image family naming has changed
    since this was written (confirmed via search: current families look
    like "pytorch-2-9-cu129-ubuntu-2204-nvidia-580", not the older
    "common-cuXXX" scheme this project's earlier context assumed).
    Before terraform apply, run:
      gcloud compute images list --project deeplearning-platform-release \
        --filter="family~'common-cu'" --show-deprecated
    and set this to whatever the current "Common" (framework-agnostic,
    CUDA+drivers only) family actually is. Verify it supports T4
    (compute capability 7.5 / Turing) specifically — newer CUDA/driver
    stacks don't always keep Turing support.
  EOT
  type    = string
  default = "common-cu124-ubuntu-2204-py310" # best guess, NOT verified — check before applying
}

variable "boot_disk_image_project" {
  type    = string
  default = "deeplearning-platform-release"
}

variable "boot_disk_size_gb" {
  type    = number
  default = 50
}

variable "model_cache_disk_size_gb" {
  description = "Persistent disk for cached model weights, so vLLM doesn't re-download from Hugging Face on every boot"
  type        = number
  default     = 100
}

variable "vllm_model" {
  description = <<-EOT
    Model vLLM serves. AWQ/GPTQ quantized by default per the root
    CLAUDE.md's T4 note (compute capability 7.5 — stick to AWQ/GPTQ, not
    the newest Ampere-only quant kernels). UNVERIFIED exact HF repo name
    — check it still exists and its license before applying.
  EOT
  type    = string
  default = "Qwen/Qwen2.5-7B-Instruct-AWQ"
}

variable "huggingface_token" {
  description = "HF token, only needed for gated models (e.g. Llama 3.1). Pass via -var, never commit it."
  type        = string
  default     = ""
  sensitive   = true
}
