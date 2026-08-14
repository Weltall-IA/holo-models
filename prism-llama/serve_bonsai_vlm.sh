#!/usr/bin/env bash
# Serve o Ternary-Bonsai-27B com mmproj (VLM) usando o fork PrismML.
# Usa as libs CUDA 12 do venv do torch (libcudart.so.12 + libcublas.so.12).
set -e

NV="/home/alpha/Playstoria/models/.venv/lib/python3.12/site-packages/nvidia"
PRISM="/home/alpha/Playstoria/models/prism-llama/llama-prism-b9599-9ca265a"
MODEL="/home/alpha/Playstoria/models/text/Ternary-Bonsai-27B-Q2_0/Ternary-Bonsai-27B-Q2_0.gguf"
MMPROJ="/home/alpha/Playstoria/models/text/Ternary-Bonsai-27B-Q2_0/Ternary-Bonsai-27B-mmproj-Q8_0.gguf"
PORT="${BONSAI_PORT:-8082}"
CTX="${BONSAI_CTX:-8192}"

export LD_LIBRARY_PATH="$NV/cuda_runtime/lib:$NV/cublas/lib:$PRISM"

exec "$PRISM/llama-server" -m "$MODEL" --mmproj "$MMPROJ" -ngl 99 -c "$CTX" --port "$PORT" --no-webui "$@"
