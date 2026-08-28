#!/bin/bash
set -u
ROOT=/home/alpha/Playstoria/models
OUT=$ROOT/bench/benchmarks/vireqo-sdkyuan-fable
LOG=$OUT/pipeline.log
mkdir -p "$OUT"
source "$ROOT/bench/lib/run_model.sh"

wait_file "$ROOT/text/Vita0818-Vireqo-27B-Plus-260816/Vireqo-27B-Plus-260816.gguf"
wait_file "$ROOT/text/sdkyuan-Qwen3.8-27B-QAT-Q2_0/qwen38-27b-qat-q2_0.gguf"

run_one vireqo "$ROOT/text/Vita0818-Vireqo-27B-Plus-260816/Vireqo-27B-Plus-260816.gguf"
run_one sdkyuan-q2 "$ROOT/text/sdkyuan-Qwen3.8-27B-QAT-Q2_0/qwen38-27b-qat-q2_0.gguf"
run_one fable-distill "$ROOT/text/mradermacher-Qwen3.8-27B-Fable-Distill-Heretic-ara-i1-IQ3_M/Qwen3.8-27B-Fable-Distill-Heretic-ara.i1-IQ3_M.gguf"

write_summary "$OUT" vireqo sdkyuan-q2 fable-distill
say "==> SUMMARY.md atualizado"