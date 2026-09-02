#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/alpha/Playstoria/models
DEST="$ROOT/text/z-lab-Qwen3.8-27B-DFlash2-GGUF"
FILE=Qwen3.8-27B-DFlash2-Q4_K_M.gguf
URL="https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2-GGUF/resolve/main/$FILE?download=true"
EXPECTED_SHA=1a25c56858e1ebe93f2718ac1d49d1151f9323325c1bbfd6209370f4db131ebd
TARGET="$ROOT/text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-IQ2_S/Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf"
TARGET_SHA=16c9802111aa9ef3acde465188d6d601f8db128ee3d828ad983a5caca4135ecb

if [[ ! -f "$TARGET" ]]; then
  echo "ERROR: target IQ2_S missing: $TARGET" >&2
  exit 2
fi

actual_target=$(sha256sum "$TARGET" | awk '{print $1}')
if [[ "$actual_target" != "$TARGET_SHA" ]]; then
  echo "ERROR: target IQ2_S SHA mismatch: $actual_target" >&2
  exit 3
fi

mkdir -p "$DEST"

if [[ -f "$DEST/$FILE" ]]; then
  actual=$(sha256sum "$DEST/$FILE" | awk '{print $1}')
  if [[ "$actual" == "$EXPECTED_SHA" ]]; then
    echo "DFLASH2_ALREADY_PRESENT=YES"
  else
    echo "ERROR: existing DFlash2 file has unexpected SHA: $actual" >&2
    echo "Do not overwrite or substitute it automatically." >&2
    exit 4
  fi
else
  if ! command -v curl >/dev/null 2>&1; then
    echo 'ERROR: curl not found; do not substitute another draft model.' >&2
    exit 5
  fi
  tmp="$DEST/$FILE.part"
  curl -L --fail --retry 4 --retry-delay 2 --continue-at - -o "$tmp" "$URL"
  actual=$(sha256sum "$tmp" | awk '{print $1}')
  if [[ "$actual" != "$EXPECTED_SHA" ]]; then
    echo "ERROR: downloaded DFlash2 SHA mismatch: $actual" >&2
    exit 6
  fi
  mv "$tmp" "$DEST/$FILE"
fi

actual=$(sha256sum "$DEST/$FILE" | awk '{print $1}')
cat <<EOF
DFLASH2_PREPARED=YES
DFLASH2_PATH=$DEST/$FILE
DFLASH2_SHA256=$actual
TARGET_PATH=$TARGET
TARGET_SHA256=$actual_target
EOF
