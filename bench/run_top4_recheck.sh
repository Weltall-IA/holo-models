#!/bin/bash
set -u
ROOT=/home/alpha/Playstoria/models
OUT=$ROOT/bench/benchmarks/top4-recheck
LOG=$OUT/pipeline.log
mkdir -p "$OUT"
source "$ROOT/bench/lib/run_model.sh"

while pgrep -f "run_vireqo_sdkyuan_fable.sh" >/dev/null 2>&1; do say "aguardando bateria vireqo/sdkyuan/fable terminar..."; sleep 60; done
sleep 15
say "bateria anterior encerrada; iniciando top4"

run_one ara "$ROOT/text/Qwen3.8-27B-heretic-ara-IQ4_MIX/Qwen3.8-27B-heretic-ara-IQ4-MIX.gguf"
run_one joyfox "$ROOT/text/joyfox-Qwen3.8-27B-Uncensored-Aggressive-Q3_K_M/Qwen3.8-27B-Uncensored-JoyFox-Aggressive-Q3_K_M.gguf"
run_one ektome "$ROOT/text/mradermacher-Ektome-Qwen3.8-27B-PristinelyUncensored-i1-IQ3_M/Ektome-Qwen3.8-27B-PristinelyUncensored.i1-IQ3_M.gguf"
run_one rvn "$ROOT/text/0bserverx-Qwen3.8-27B-Heretic-RVN-IQ3_M-multilingual-MTP/RVN-IQ3_M-multilingual-mtp.gguf"

write_summary "$OUT" ara joyfox ektome rvn
say "==> SUMMARY.md atualizado; bateria top4 concluida"
echo done > "$OUT/pipeline.done"