#!/bin/bash
set -u
ROOT=/home/alpha/Playstoria/models
OUT=$ROOT/bench/benchmarks/extra-tests
LOG=$OUT/pipeline.log
mkdir -p "$OUT"
ENGINE=$ROOT/engines/deepgrove-llama.cpp/build/bin
VENV=/home/alpha/tmp/holoplay-venvs/humaneval-venv/bin/python
MODEL_PID=""
stop(){ [ -n "$MODEL_PID" ] && kill "$MODEL_PID" 2>/dev/null || true; [ -n "$MODEL_PID" ] && wait "$MODEL_PID" 2>/dev/null || true; MODEL_PID=""; fuser -k 8081/tcp 2>/dev/null || true; }
trap stop EXIT INT TERM
say(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
start(){ local file=$1 dir=$2 reasoning=${3:-off}; stop; mkdir -p "$dir"; local extra=(); [ "$reasoning" = on ] || extra+=(--reasoning off); env LD_LIBRARY_PATH=$ENGINE "$ENGINE/llama-server" -m "$file" -c 4096 -b 128 -ub 64 -t 6 -np 1 -ngl 99 -fa on -ctk q4_0 -ctv q4_0 --jinja "${extra[@]}" --host 127.0.0.1 --port 8081 > "$dir/server.log" 2>&1 & MODEL_PID=$!; for i in $(seq 1 120); do curl -s --max-time 3 http://127.0.0.1:8081/health 2>/dev/null | grep -q '"status":"ok"' && return 0; kill -0 "$MODEL_PID" 2>/dev/null || return 1; sleep 2; done; return 1; }
run_case(){ local name=$1 model=$2 mode=$3 file=$4 reasoning=${5:-off}; local dir="$OUT/$name"; say "start $name"; if ! start "$file" "$dir" "$reasoning"; then say "FAIL load $name"; return 1; fi; (cd "$ROOT/bench" && "$VENV" extra_tests.py http://127.0.0.1:8081/v1 "$mode" "$dir" "$model") > "$dir/run.log" 2>&1 || true; stop; say "stop $name"; }

RVN="$ROOT/text/0bserverx-Qwen3.8-27B-Heretic-RVN-IQ3_M-multilingual-MTP/RVN-IQ3_M-multilingual-mtp.gguf"
VIREQO="$ROOT/text/Vita0818-Vireqo-27B-Plus-260816/Vireqo-27B-Plus-260816.gguf"
SDK="$ROOT/text/sdkyuan-Qwen3.8-27B-QAT-Q2_0/qwen38-27b-qat-q2_0.gguf"
FABLE="$ROOT/text/mradermacher-Qwen3.8-27B-Fable-Distill-Heretic-ara-i1-IQ3_M/Qwen3.8-27B-Fable-Distill-Heretic-ara.i1-IQ3_M.gguf"

say "RVN agentic"
run_case rvn-agentic rvn agentic "$RVN"
say "Vireqo normal quality/json/tool"
run_case vireqo-normal-quality vireqo quality-normal "$VIREQO"
run_case vireqo-normal-json-tool vireqo json-tool-normal "$VIREQO"
say "Vireqo engineered quality/json/tool"
run_case vireqo-engineered-quality vireqo quality-engineered "$VIREQO"
run_case vireqo-engineered-json-tool vireqo json-tool-engineered "$VIREQO"
say "sdkyuan normal quality/json/tool"
run_case sdkyuan-normal-quality sdkyuan-q2 quality-normal "$SDK"
run_case sdkyuan-normal-json-tool sdkyuan-q2 json-tool-normal "$SDK"
say "sdkyuan engineered quality/json/tool"
run_case sdkyuan-engineered-quality sdkyuan-q2 quality-engineered "$SDK"
run_case sdkyuan-engineered-json-tool sdkyuan-q2 json-tool-engineered "$SDK"
say "Fable thinking xhigh quality"
run_case fable-thinking-xhigh fable-distill quality-thinking "$FABLE" on
say "extra tests complete"
