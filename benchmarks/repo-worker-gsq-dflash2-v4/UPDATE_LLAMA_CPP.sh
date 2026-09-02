#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/alpha/Playstoria/models
RUNTIME_REPO="$ROOT/engines/llama.cpp"
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
  echo 'ERROR: nvidia-smi not found; CUDA llama.cpp runtime cannot be prepared.' >&2
  exit 4
fi

# This is the canonical llama.cpp runtime for new GGUF work. The historical
# DeepGrove checkout is intentionally left untouched for reproducibility only.
if [[ -e "$RUNTIME_REPO" && ! -d "$RUNTIME_REPO/.git" ]]; then
  echo "ERROR: $RUNTIME_REPO exists but is not a git checkout; refusing to overwrite it." >&2
  exit 5
fi

if [[ ! -d "$RUNTIME_REPO/.git" ]]; then
  git clone "$UPSTREAM" "$RUNTIME_REPO"
fi

origin=$(git -C "$RUNTIME_REPO" remote get-url origin 2>/dev/null || true)
case "$origin" in
  "$UPSTREAM"|https://github.com/ggml-org/llama.cpp|git@github.com:ggml-org/llama.cpp.git) ;;
  *)
    echo "ERROR: canonical llama.cpp path has unexpected origin: $origin" >&2
    exit 6
    ;;
esac

if [[ -n "$(git -C "$RUNTIME_REPO" status --porcelain --untracked-files=no)" ]]; then
  echo 'ERROR: canonical llama.cpp checkout has tracked local modifications; refusing to discard them.' >&2
  exit 7
fi

# Pin the exact upstream revision used by this benchmark. This is the normal
# ggml-org/llama.cpp checkout, not a benchmark-specific fork or duplicate.
git -C "$RUNTIME_REPO" fetch origin "$REV"
git -C "$RUNTIME_REPO" checkout --detach "$REV"
actual=$(git -C "$RUNTIME_REPO" rev-parse HEAD)
if [[ "$actual" != "$REV" ]]; then
  echo "ERROR: llama.cpp revision mismatch: $actual" >&2
  exit 8
fi

rm -rf "$BUILD_DIR"
cmake -S "$RUNTIME_REPO" -B "$BUILD_DIR" \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA=ON
cmake --build "$BUILD_DIR" --config Release -j "$JOBS" --target llama-server

SERVER="$BUILD_DIR/bin/llama-server"
if [[ ! -x "$SERVER" ]]; then
  echo "ERROR: llama-server was not built: $SERVER" >&2
  exit 9
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
  '--fit'
)
for token in "${required[@]}"; do
  if ! grep -Fq -- "$token" <<<"$help"; then
    echo "ERROR: canonical llama.cpp missing required feature: $token" >&2
    exit 10
  fi
done

version=$(LD_LIBRARY_PATH="$BUILD_DIR/bin:${LD_LIBRARY_PATH:-}" "$SERVER" --version 2>&1 | head -5)
cat <<EOF
LLAMA_CPP_UPDATED=YES
RUNTIME_ROLE=canonical-upstream
RUNTIME_REPO=$RUNTIME_REPO
RUNTIME_REVISION=$actual
RUNTIME_BIN=$SERVER
RUNTIME_FEATURES=DFlash2,Froggeric-Jinja,reasoning-effort,reasoning-budget
HISTORICAL_DEEPGROVE_UNTOUCHED=YES
RUNTIME_VERSION_BEGIN
$version
RUNTIME_VERSION_END
EOF
