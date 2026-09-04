# Cut reranker microbenchmark v1

Small decision benchmark for the production cut/scene retrieval path:

`EmbeddingGemma-300m -> fixed top-50 scene chunks -> reranker`

It compares only:

- `nvidia/llama-nemotron-rerank-1b-v2`
- `cross-encoder/ettin-reranker-400m-v1`

No embedding is recomputed. The harness reuses the already measured `embeddinggemma_300m/rankings.json` from `embedding-v3/results/wemm-v1`, freezes the first 50 candidate IDs for each of the 150 PT-BR scene queries, and supplies the exact same candidates to both rerankers.

## Why 150 queries is still a micro-test

Only two second-stage models run. Each model scores 150 x 50 = 7,500 query/document pairs. Existing embedding models, Jina, Qwen and WeMM are not rerun.

## Quality outputs

Primary decision metric is pipeline NDCG@10 over all 150 queries. The report also includes MRR@10, MAP, Hit@1, Recall@10/20, query-type breakdowns, and conditional reranker quality restricted to queries whose relevant cut was already present in the EmbeddingGemma top-50.

The Ettin-vs-Nemotron delta receives a paired 95% bootstrap CI with 10,000 resamples, stratified by `query_type`. Queries where EmbeddingGemma missed the relevant cut in top-50 remain in the primary pipeline score as zero; the reranker is not credited with candidates it never received.

## Efficiency outputs

After one warmup query, the harness records:

- Torch CUDA peak allocated and reserved VRAM;
- whole-GPU VRAM from `nvidia-smi`;
- average / p95 / max GPU utilization;
- average / p95 / max board power in watts;
- approximate energy consumption in Wh;
- average / max GPU temperature and average SM clock;
- model load time;
- p50 / p95 query latency;
- queries/s and query-document pairs/s;
- total measured reranking time;
- process RSS from the shared reranker harness.

`nvidia-smi` values are whole-GPU measurements, so desktop or other GPU clients can affect them. Torch allocated/reserved peaks are process-local and are the cleaner model-memory comparison.

## Run

From the repository root, using the same Python environment that successfully ran `reranker-v2-unbiased`:

```bash
python benchmarks/cut-reranker-micro-v1/run_micro.py \
  --device cuda \
  --cpu-threads 8 \
  --nemotron-batch-size 16 \
  --telemetry-interval 0.5
```

Outputs are written to:

`benchmarks/cut-reranker-micro-v1/results/embeddinggemma-top50-v1/`

Expected files after a complete run:

- `candidates_top50.json`
- `nemotron_1b_v2.json`
- `ettin_400m.json`
- `comparison.json`
- `REPORT.md`

Each completed model JSON is written immediately, so an interrupted second model does not erase the first result. Re-running without `--force` reuses completed model files after validating the frozen first-stage hashes.
