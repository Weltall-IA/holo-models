#!/usr/bin/env bash
# Run remaining panel cells for a given reranker, resumable per cell.
# Usage: run_panel_batch.sh <model-id> <reranker-dir> <candidate-dir> <model-path> <batch-size>
set -u
MODEL_ID="${1:?model id required}"
RERANKER_DIR="${2:?reranker dir required}"
CAND_DIR="${3:?candidate dir required}"
MODEL_PATH="${4:?model path required}"
BATCH="${5:-8}"

ROOT=/tmp/holo-models-modern-embed-rerank
BENCH="$ROOT/benchmark/embedding-v3"
PY="$ROOT/benchmark/embedding-v3/runtimes_python"  # placeholder, replaced below
RUNNER_PY=/home/alpha/Playstoria/models-embed-batch2-light/runtimes/vllm-nemotron-0.25.1/bin/python

if [ "$MODEL_ID" = "llama_nemotron_rerank_1b_v2" ]; then
  MODULE=holo_benchmark.nemotron_transformers_panel
  MODEL_FLAG=""
else
  MODULE=holo_benchmark.native_cross_encoder_panel
  MODEL_FLAG="--model-id $MODEL_ID"
fi

PROFILES=(
  nemotron_3_embed_1b_nvfp4
  voyage_4_large_1024_float32
  nemotron_3_embed_1b_q4_k_m_gguf
  voyage4_nano_2048_int8
  embeddinggemma
  pplx_embed_v1_4b_q8_0
  voyage4_nano_2048_float32
  voyage4_nano
  voyage4_nano_1024_float32
  nemotron_8b_abiray_q4_audit_1024
  voyage-context-4
  nomic_embed_text_v2_moe_q4
  embeddinggemma_768_float32
  embeddinggemma_gguf
)

mkdir -p "$BENCH/results/reranker/pipelines/$RERANKER_DIR" "$BENCH/results/reranker/scores/$RERANKER_DIR"

for PROFILE in "${PROFILES[@]}"; do
  PIPELINE="$BENCH/results/reranker/pipelines/$RERANKER_DIR/$PROFILE.json"
  SCORE="$BENCH/results/reranker/scores/$RERANKER_DIR/$PROFILE.json"
  CAND="$BENCH/results/reranker/candidates/$PROFILE.json"
  if [ -f "$PIPELINE" ]; then
    echo "SKIP $PROFILE (pipeline exists)"
    continue
  fi
  if [ ! -f "$CAND" ]; then
    echo "BLOCKED $PROFILE (no candidate artifact)"
    continue
  fi
  echo "RUN $MODEL_ID/$PROFILE"
  cd "$BENCH" || exit 2
  timeout 900 env PYTHONPATH=. "$RUNNER_PY" -u -m "$MODULE" \
    $MODEL_FLAG \
    --profile-id "$PROFILE" \
    --model-path "$MODEL_PATH" \
    --candidate "results/reranker/candidates/$PROFILE.json" \
    --canonical ALL_BENCHMARK_RESULTS.json \
    --score-output "results/reranker/scores/$RERANKER_DIR/$PROFILE.json" \
    --pipeline-output "results/reranker/pipelines/$RERANKER_DIR/$PROFILE.json" \
    --batch-size "$BATCH" > "/tmp/panel_${MODEL_ID}_${PROFILE}.log" 2>&1
  RC=$?
  if [ $RC -ne 0 ]; then
    echo "FAIL $MODEL_ID/$PROFILE exit=$RC"
    tail -3 "/tmp/panel_${MODEL_ID}_${PROFILE}.log"
  elif [ ! -f "$PIPELINE" ]; then
    echo "FAIL $MODEL_ID/$PROFILE (no pipeline produced, exit=0)"
    tail -5 "/tmp/panel_${MODEL_ID}_${PROFILE}.log"
  else
    echo "OK $MODEL_ID/$PROFILE"
  fi
done
echo "BATCH_DONE $MODEL_ID"
