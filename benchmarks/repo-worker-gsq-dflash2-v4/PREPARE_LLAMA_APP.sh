#!/usr/bin/env bash
set -euo pipefail

LLAMA_VERSION=b10752
LLAMA_COMMIT=b96806d96061049a5b574269b049bf6241d63d46
INSTALL_URL=https://llama.app/install.sh
BIN="$HOME/.local/bin/llama"

if ! command -v curl >/dev/null 2>&1; then
  echo 'ERROR: curl not found.' >&2
  exit 2
fi

# Use the official prebuilt llama.cpp installer. No local CMake build.
curl -LsSf "$INSTALL_URL" | LLAMA_VERSION="$LLAMA_VERSION" sh

if [[ ! -x "$BIN" ]]; then
  echo "ERROR: official llama binary not installed at $BIN" >&2
  exit 3
fi

version=$("$BIN" version 2>&1)
if ! grep -Eq "${LLAMA_VERSION}|build ${LLAMA_VERSION#b}" <<<"$version"; then
  echo "ERROR: llama.app release mismatch: $version" >&2
  exit 4
fi
if ! grep -Fq "${LLAMA_COMMIT:0:7}" <<<"$version" && ! grep -Fq "$LLAMA_COMMIT" <<<"$version"; then
  echo "ERROR: llama.app commit mismatch: $version" >&2
  exit 5
fi

help=$("$BIN" serve --help 2>&1)
required=(
  '--spec-type'
  'draft-dflash'
  '--spec-draft-model'
  '--spec-draft-n-max'
  '--spec-draft-ngl'
  '--reasoning-budget'
  '--reasoning-effort'
  '--chat-template-file'
  '--chat-template-kwargs'
  '--reasoning-format'
  '--jinja'
  '--fit'
)
for token in "${required[@]}"; do
  if ! grep -Fq -- "$token" <<<"$help"; then
    echo "ERROR: official llama.app runtime missing required feature: $token" >&2
    exit 6
  fi
done

cat <<EOF
LLAMA_APP_PREPARED=YES
RUNTIME_SOURCE=official-llama.app-prebuilt
RUNTIME_RELEASE=$LLAMA_VERSION
RUNTIME_COMMIT=$LLAMA_COMMIT
RUNTIME_BIN=$BIN
RUNTIME_VERSION_BEGIN
$version
RUNTIME_VERSION_END
EOF
