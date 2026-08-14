#!/usr/bin/env bash
# Serve o maple-preview (deepgrove runtime — suporta arquitetura maple).
# Porta padrão: 8082
# --skip-chat-parsing: evita o bug "Pattern must start with '^' and end with '$'"
#   na geração automática de parser de tools/JSON schema (necessário p/ o Kilo agente).
set -e

DG="/home/alpha/Playstoria/models/deepgrove-llama.cpp/build/bin"
MODEL="/home/alpha/Playstoria/models/text/maple-preview/maple-preview-TQ2_0-head-F16.gguf"
PORT="${MAPLE_PORT:-8082}"
CTX="${MAPLE_CTX:-131072}"

export LD_LIBRARY_PATH="$DG"

exec "$DG/llama-server" -m "$MODEL" -ngl 99 -c "$CTX" --port "$PORT" --no-webui --skip-chat-parsing "$@"
