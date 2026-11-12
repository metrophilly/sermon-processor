#!/usr/bin/env bash
# Resumable, hash-checked download of one Hugging Face file into the HF cache.
# Usage: dl_hf.sh mlx-community/whisper-large-v3-mlx weights.npz
set -u
REPO=$1; FILE=$2
D=~/.cache/huggingface/hub/models--${REPO//\//--}
B=$D/blobs
F=$(ls -S $B/*.incomplete | head -1)           # largest partial file
H=$(basename "$F" | cut -d. -f1)                # blob name = sha256 of the file
for i in $(seq 1 300); do
  curl -sL -C - --connect-timeout 20 --speed-limit 20000 --speed-time 30 -o "$F" "https://huggingface.co/$REPO/resolve/main/$FILE" && break
  echo "retry $i at $(stat -f %z "$F")"; sleep 3
done
S=$(shasum -a 256 "$F" | cut -d' ' -f1)
if [ "$S" = "$H" ]; then
  mv "$F" "$B/$H"; rm -f $B/$H.*.incomplete
  SN=$(ls -d $D/snapshots/*/ | head -1); ln -sf ../../blobs/$H "${SN}$FILE"
  echo VERIFIED
else echo "HASH-MISMATCH $S"; fi
