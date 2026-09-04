# Reranker V2 — Unbiased Benchmark

Decision benchmark for reranker selection.

This benchmark is deliberately separated from the legacy 150/240-query reranker experiments. It has two independent tracks:

- `GENERAL`: external NanoBEIR datasets, used to measure general retrieval quality.
- `HOLO`: held-out Holo-specific queries, used to measure repository/tool/skill/document retrieval quality.

The two tracks are never averaged together.

Core rules:

1. Candidate pools are frozen before reranking and shared by every model.
2. Every query gets the same candidate IDs for every reranker.
3. Hard negatives come from the first-stage retriever, not random sampling.
4. Primary metric is NDCG@10. Secondary metrics are MRR@10, MAP, Hit@1, Recall@10, Recall@20.
5. NDCG@10 and MRR@10 are reported with paired bootstrap 95% confidence intervals.
6. Pairwise model comparisons use per-query deltas. A small mean delta is not called a win when the 95% CI crosses zero.
7. Quality and efficiency are reported separately. VRAM/latency never alter the quality score.
8. No projected or extrapolated scores are allowed.
9. Raw per-query outputs are retained so every aggregate can be recomputed.
10. Model-specific official inference paths are allowed; fairness is enforced at the query/candidate level, not by forcing a common incompatible API.

Models in the initial panel:

- `nvidia/llama-nemotron-rerank-1b-v2`
- `jinaai/jina-reranker-v3.5`
- `Qwen/Qwen3-Reranker-0.6B`
- `cross-encoder/ettin-reranker-400m-v1`

See `METHODOLOGY.md` and `manifest.json` for the exact protocol.
