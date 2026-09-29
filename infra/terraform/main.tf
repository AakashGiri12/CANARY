terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Survives VM teardown/recreation between eval sessions — the whole
# point of caching model weights instead of re-downloading them from
# Hugging Face every time the spot VM comes back up.
resource "google_compute_disk" "model_cache" {
  name = "canary-model-cache"
  zone = var.zone
  size = var.model_cache_disk_size_gb
  type = "pd-ssd"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_compute_instance" "vllm" {
  name         = "canary-vllm-spot"
  machine_type = var.machine_type
  zone         = var.zone

  scheduling {
    preemptible                 = true
    automatic_restart           = false
    instance_termination_action = "STOP"
    provisioning_model           = "SPOT"
  }

  guest_accelerator {
    type  = var.gpu_type
    count = var.gpu_count
  }

  boot_disk {
    initialize_params {
      image = "projects/${var.boot_disk_image_project}/global/images/family/${var.boot_disk_image_family}"
      size  = var.boot_disk_size_gb
      type  = "pd-ssd"
    }
  }

  attached_disk {
    source      = google_compute_disk.model_cache.id
    device_name = "model-cache"
  }

  network_interface {
    network = "default"
    access_config {} # ephemeral external IP
  }

  metadata = {
    install-nvidia-driver = "True"
    vllm-model            = var.vllm_model
    hf-token              = var.huggingface_token
  }

  metadata_startup_script = file("${path.module}/startup-script.sh")

  tags = ["canary-vllm"]
}

# Tightened to your own IP is strongly preferred over 0.0.0.0/0 — see
# README's cost/security discipline section.
resource "google_compute_firewall" "vllm_api" {
  name    = "canary-allow-vllm-8000"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["8000"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["canary-vllm"]
}
