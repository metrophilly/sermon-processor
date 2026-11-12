#!/usr/bin/env bash
# Resumable download of the turbo weights straight into the HF cache blob file.
set -u
B=~/.cache/huggingface/hub/models--mlx-community--whisper-large-v3-turbo/blobs
F=$(ls $B/*.incomplete | head -1)
for i in $(seq 1 200); do
  curl -sL -C - --connect-timeout 20 --speed-limit 20000 --speed-time 30 -o "$F" https://huggingface.co/mlx-community/whisper-large-v3-turbo/resolve/main/weights.safetensors && { echo done; exit 0; }
  echo "retry $i at $(stat -f %z "$F")"; sleep 3
done
