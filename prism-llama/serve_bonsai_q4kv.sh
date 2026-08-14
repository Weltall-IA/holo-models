#!/usr/bin/env bash
# Bonsai 27B com KV cache Q4_0 (4-bit) — permite 131K-262K de contexto na 16GB.
# Uso: BONSAI_CTX=131072 ./serve_bonsai_q4kv.sh
set -e
NV="/home/alpha/Playstoria/models/.venv/lib/python3.12/site-packages/nvidia"
PRISM="/home/alpha/Playstoria/models/prism-llama/llama-prism-b9599-9ca265a"
MODEL="/home/alpha/Playstoria/models/text/Ternary-Bonsai-27B-Q2_0/Ternary-Bonsai-27B-Q2_0.gguf"
MMPROJ="/home/alpha/Playstoria/models/text/Ternary-Bonsai-27B-Q2_0/Ternary-Bonsai-27B-mmproj-Q8_0.gguf"
CTX="${BONSAI_CTX:-131072}"
export LD_LIBRARY_PATH="$NV/cuda_runtime/lib:$NV/cublas/lib:$PRISM"
exec "$PRISM/llama-server" -m "$MODEL" --mmproj "$MMPROJ" \
  -ngl 99 -c "$CTX" -np 1 \
  --cache-type-k q4_0 --cache-type-v q4_0 \
  --port 8083 --no-webui "$@"
