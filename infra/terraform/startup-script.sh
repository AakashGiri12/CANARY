#!/bin/bash
set -euo pipefail

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
MAX_RUNTIME_HOURS=$(curl -s -H "Metadata-Flavor: Google" \
  "http://metadata.google.internal/computeMetadata/v1/instance/attributes/max-runtime-hours")
shutdown -h "+$(( MAX_RUNTIME_HOURS * 60 ))"

# The Deep Learning VM image family (see variables.tf) ships NVIDIA
# drivers + Docker + nvidia-container-toolkit already configured. If
# boot_disk_image_family ever gets pointed at a plain Debian/Ubuntu image
# instead, all of that needs installing here first — the rest of this
# script only handles mounting the cache disk and starting vLLM.

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
