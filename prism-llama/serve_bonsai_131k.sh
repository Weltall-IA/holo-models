#!/usr/bin/env bash
# Bonsai 27B com 131K de contexto (mmproj para visão). Porta 8083.
set -e
NV="/home/alpha/Playstoria/models/.venv/lib/python3.12/site-packages/nvidia"
PRISM="/home/alpha/Playstoria/models/prism-llama/llama-prism-b9599-9ca265a"
MODEL="/home/alpha/Playstoria/models/text/Ternary-Bonsai-27B-Q2_0/Ternary-Bonsai-27B-Q2_0.gguf"
MMPROJ="/home/alpha/Playstoria/models/text/Ternary-Bonsai-27B-Q2_0/Ternary-Bonsai-27B-mmproj-Q8_0.gguf"
export LD_LIBRARY_PATH="$NV/cuda_runtime/lib:$NV/cublas/lib:$PRISM"
exec "$PRISM/llama-server" -m "$MODEL" --mmproj "$MMPROJ" -ngl 99 -c 131072 --port 8083 --no-webui "$@"
