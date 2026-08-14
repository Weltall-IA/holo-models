#!/usr/bin/env bash
# Serve o Ternary-Bonsai-27B com o fork PrismML do llama.cpp.
# Usa as libs CUDA 12 do venv do torch (libcudart.so.12 + libcublas.so.12).
set -e

NV="/home/alpha/Playstoria/models/.venv/lib/python3.12/site-packages/nvidia"
PRISM="/home/alpha/Playstoria/models/prism-llama/llama-prism-b9599-9ca265a"
MODEL="/home/alpha/Playstoria/models/text/Ternary-Bonsai-27B-Q2_0/Ternary-Bonsai-27B-Q2_0.gguf"
PORT="${BONSAI_PORT:-8083}"

export LD_LIBRARY_PATH="$NV/cuda_runtime/lib:$NV/cublas/lib:$PRISM"

exec "$PRISM/llama-server" -m "$MODEL" -ngl 99 --port "$PORT" --no-webui "$@"
