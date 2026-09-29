#!/bin/bash
set -euo pipefail

# The Deep Learning VM image family (see variables.tf) ships NVIDIA
# drivers + Docker + nvidia-container-toolkit already configured. If
# boot_disk_image_family ever gets pointed at a plain Debian/Ubuntu image
# instead, all of that needs installing here first — this script only
# handles mounting the cache disk and starting vLLM.

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
