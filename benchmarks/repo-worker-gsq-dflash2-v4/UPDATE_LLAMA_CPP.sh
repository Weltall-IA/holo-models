#!/usr/bin/env bash
set -euo pipefail

echo 'ERROR: UPDATE_LLAMA_CPP.sh is retired. Do not compile llama.cpp locally.' >&2
echo 'Use the Arch Linux packages llama-cpp and ggml-cuda; the benchmark runner uses llama-server from PATH.' >&2
exit 2
