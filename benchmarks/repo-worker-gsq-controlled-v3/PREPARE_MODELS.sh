#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/alpha/Playstoria/models
DEST="$ROOT/text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-MTP"
REPO=ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF
REV=b71b542
IQ2=Qwen3.8-27B-GSQ-RCO-IQ2_S-mtp.gguf
IQ3=Qwen3.8-27B-GSQ-RCO-IQ3_XXS-mtp.gguf
IQ2_SHA=e6406238a5cc0043775cd1963b6f9e5b8707400276e38d9fde742304906b1330

if ! command -v hf >/dev/null 2>&1; then
  echo 'ERROR: `hf` CLI not found. Do not substitute another model or repository.' >&2
  exit 2
fi

mkdir -p "$DEST"
hf download "$REPO" "$IQ2" "$IQ3" --revision "$REV" --local-dir "$DEST"

actual_iq2=$(sha256sum "$DEST/$IQ2" | awk '{print $1}')
actual_iq3=$(sha256sum "$DEST/$IQ3" | awk '{print $1}')

if [[ "$actual_iq2" != "$IQ2_SHA" ]]; then
  echo "ERROR: IQ2_S MTP SHA mismatch: $actual_iq2" >&2
  exit 3
fi

cat <<EOF
MODEL_PREPARED=YES
HF_REPO=$REPO
HF_REVISION=$REV
IQ2_PATH=$DEST/$IQ2
IQ2_SHA256=$actual_iq2
IQ3_PATH=$DEST/$IQ3
IQ3_SHA256=$actual_iq3
EOF
