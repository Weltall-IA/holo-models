#!/usr/bin/env bash
set -euo pipefail

echo 'ERROR: UPDATE_LLAMA_CPP.sh is retired.' >&2
echo 'Do not compile llama.cpp locally and do not use the stale Arch llama-cpp package for DFlash2.' >&2
echo 'Run PREPARE_LLAMA_APP.sh to install the pinned official prebuilt llama.app runtime instead.' >&2
exit 2
