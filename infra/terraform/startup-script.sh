#!/bin/bash
set -euo pipefail
set -x # verbose: this script has already had two real bugs caught only
       # by reading the serial console — keep everything visible there.

# HARD COST CEILING — scheduled first, before anything else, so the
# clock starts at boot regardless of how long model download/setup
# takes. This is the PRIMARY spending guardrail for this VM: GCP's
# native Spend Cap only covers services already active on the billing
# account and does not cover Compute Engine on a fresh account/project
# (confirmed directly in the console before writing this), so nothing
# on the billing side protects against this VM's own cost. `shutdown -h`
# stops the guest OS, which transitions the GCE instance to STOPPED and
# ends compute/GPU billing — it does not touch the persistent disks
# (see infra/terraform/README.md's cost section for that).
#
# MAX_RUNTIME_MINUTES is a pre-computed INTEGER from Terraform
# (floor(max_runtime_hours * 60)), not hours. Real bug found live on
# 2026-10-12: `shutdown -h "+$(( 0.15 * 60 ))"` failed with "0.15:
# syntax error: invalid arithmetic operator" (bash's $(( )) is
# integer-only) — and `set -e` did NOT catch it (a known bash quirk:
# arithmetic-expansion failures during simple-command argument
# construction don't always trigger -e), so the script silently
# continued with NO shutdown ever scheduled. The only reason the first
# real attempt's VM ever stopped was GCP spot preemption, not this
# timer. Doing the hours->minutes math in Terraform instead of bash
# eliminates the whole bug class rather than papering over it.
MAX_RUNTIME_MINUTES=$(curl -s -H "Metadata-Flavor: Google" \
  "http://metadata.google.internal/computeMetadata/v1/instance/attributes/max-runtime-minutes")
shutdown -h "+${MAX_RUNTIME_MINUTES}"

echo "=== GPU driver check ==="
nvidia-smi || echo "nvidia-smi not available / GPU driver missing - investigate before trusting this image again"

# Real bug found live on 2026-10-12: this image family does NOT ship
# Docker pre-installed, despite what this script previously assumed
# ("common-cuXXX-nvidia-YYY" apparently only provides CUDA + NVIDIA
# drivers) - real error: "docker: command not found". Installing it
# explicitly rather than trusting the image again.
if ! command -v docker >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y docker.io
fi
systemctl enable --now docker

# NVIDIA Container Toolkit so `docker run --gpus all` actually works -
# not in Ubuntu's default repos, needs NVIDIA's own.
if ! command -v nvidia-ctk >/dev/null 2>&1; then
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
    | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
  curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
    > /etc/apt/sources.list.d/nvidia-container-toolkit.list
  apt-get update -y
  apt-get install -y nvidia-container-toolkit
fi
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker

MODEL=$(curl -s -H "Metadata-Flavor: Google" \
  "http://metadata.google.internal/computeMetadata/v1/instance/attributes/vllm-model")
HF_TOKEN=$(curl -s -H "Metadata-Flavor: Google" \
  "http://metadata.google.internal/computeMetadata/v1/instance/attributes/hf-token" || echo "")

# Mount the persistent model-cache disk (format only on first boot —
# blkid succeeding means it already has a filesystem from a prior run).
DEVICE=/dev/disk/by-id/google-model-cache
MOUNT_POINT=/mnt/model-cache
mkdir -p "$MOUNT_POINT"
if ! blkid "$DEVICE" >/dev/null 2>&1; then
  mkfs.ext4 -F "$DEVICE"
fi
mount "$DEVICE" "$MOUNT_POINT"
grep -q "$MOUNT_POINT" /etc/fstab || echo "$DEVICE $MOUNT_POINT ext4 defaults 0 2" >> /etc/fstab

docker run -d \
  --name vllm \
  --restart unless-stopped \
  --gpus all \
  -p 8000:8000 \
  -v "$MOUNT_POINT:/root/.cache/huggingface" \
  -e HUGGING_FACE_HUB_TOKEN="$HF_TOKEN" \
  vllm/vllm-openai:latest \
  --model "$MODEL" \
  --quantization awq \
  --max-model-len 8192

echo "=== startup script finished, vllm container launching in background ==="
