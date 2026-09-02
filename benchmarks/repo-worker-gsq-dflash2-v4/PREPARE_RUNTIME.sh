#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/alpha/Playstoria/models
RUNTIME_REPO="$ROOT/engines/llama.cpp-dflash2-v4"
BUILD_DIR="$RUNTIME_REPO/build"
UPSTREAM=https://github.com/ggml-org/llama.cpp.git
REV=b96806d96061049a5b574269b049bf6241d63d46
JOBS=8

if ! command -v git >/dev/null 2>&1; then
  echo 'ERROR: git not found.' >&2
  exit 2
fi
if ! command -v cmake >/dev/null 2>&1; then
  echo 'ERROR: cmake not found.' >&2
  exit 3
fi
if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo 'ERROR: nvidia-smi not found; CUDA benchmark runtime cannot be prepared.' >&2
  exit 4
fi

if [[ ! -d "$RUNTIME_REPO/.git" ]]; then
  git clone "$UPSTREAM" "$RUNTIME_REPO"
fi

origin=$(git -C "$RUNTIME_REPO" remote get-url origin 2>/dev/null || true)
if [[ "$origin" != "$UPSTREAM" && "$origin" != "https://github.com/ggml-org/llama.cpp" ]]; then
  echo "ERROR: unexpected runtime origin: $origin" >&2
  exit 5
fi

# Fetch the exact benchmark-pinned commit and detach at it. Do not follow master.
git -C "$RUNTIME_REPO" fetch --depth 1 origin "$REV"
git -C "$RUNTIME_REPO" checkout --detach "$REV"
actual=$(git -C "$RUNTIME_REPO" rev-parse HEAD)
if [[ "$actual" != "$REV" ]]; then
  echo "ERROR: runtime revision mismatch: $actual" >&2
  exit 6
fi

rm -rf "$BUILD_DIR"
cmake -S "$RUNTIME_REPO" -B "$BUILD_DIR" \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA=ON
cmake --build "$BUILD_DIR" --config Release -j "$JOBS" --target llama-server

SERVER="$BUILD_DIR/bin/llama-server"
if [[ ! -x "$SERVER" ]]; then
  echo "ERROR: llama-server was not built: $SERVER" >&2
  exit 7
fi

help=$(LD_LIBRARY_PATH="$BUILD_DIR/bin:${LD_LIBRARY_PATH:-}" "$SERVER" --help 2>&1)
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
)
for token in "${required[@]}"; do
  if ! grep -Fq -- "$token" <<<"$help"; then
    echo "ERROR: pinned runtime missing required feature: $token" >&2
    exit 8
  fi
done

version=$(LD_LIBRARY_PATH="$BUILD_DIR/bin:${LD_LIBRARY_PATH:-}" "$SERVER" --version 2>&1 | head -5)
cat <<EOF
RUNTIME_PREPARED=YES
RUNTIME_REPO=$RUNTIME_REPO
RUNTIME_REVISION=$actual
RUNTIME_BIN=$SERVER
RUNTIME_FEATURES=DFlash2,Froggeric-Jinja,reasoning-effort,reasoning-budget
RUNTIME_VERSION_BEGIN
$version
RUNTIME_VERSION_END
EOF
