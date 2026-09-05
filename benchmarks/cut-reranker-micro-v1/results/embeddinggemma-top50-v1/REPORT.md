# Cut reranker microbenchmark — EmbeddingGemma top-50

This is a small second-stage test for scene/cut search. Embeddings are not rerun.

## Protocol

- 150 PT-BR scene queries, 600 chunks, fixed top-50 from the existing EmbeddingGemma run.
- Only Nemotron 1B v2 and Ettin 400M rerank the exact same 50 candidates.
- Primary: pipeline NDCG@10 over all queries. Paired CI95: 10,000 bootstrap resamples stratified by query_type.
- Telemetry after one warmup: Torch VRAM, nvidia-smi VRAM/GPU%/watts/temp, latency, throughput and approximate energy.

## First-stage coverage

EmbeddingGemma put a relevant cut in top-50 for **150/150 (100.00%)** queries.

## Quality

| Model | NDCG@10 | MRR@10 | MAP | Hit@1 | R@10 | R@20 |
|---|---:|---:|---:|---:|---:|---:|
| Nemotron 1B v2 | 0.8337 | 0.8313 | 0.8289 | 0.8133 | 0.8633 | 0.9633 |
| Ettin 400M | 0.7719 | 0.7550 | 0.7577 | 0.7133 | 0.8433 | 0.9733 |

Conditional (only queries with a relevant cut already in top-50):

| Model | NDCG@10 | MRR@10 | Hit@1 |
|---|---:|---:|---:|
| Nemotron 1B v2 | 0.8337 | 0.8313 | 0.8133 |
| Ettin 400M | 0.7719 | 0.7550 | 0.7133 |

## Paired decision

- Ettin − Nemotron ndcg@10: **-0.0619**, CI95 [-0.0890, -0.0356] → **NEMOTRON_WINS**
- Ettin − Nemotron mrr@10: **-0.0764**, CI95 [-0.1070, -0.0470] → **NEMOTRON_WINS**

## Efficiency

| Model | Torch alloc/reserved peak MiB | nvidia-smi VRAM max MiB | GPU avg/p95/max % | Power avg/p95/max W | Energy Wh | p50/p95 s | q/s | pairs/s | total s | load s | temp max C |
|---|---:|---:|---|---|---:|---|---:|---:|---:|---:|---:|
| Nemotron 1B v2 | 2917/4270 | 6493 | 96.2/100.0/100.0 | 148.6/150.6/151.9 | 9.819 | 1.518/1.722 | 0.638 | 31.9 | 235.0 | 9.22 | 73.0 |
| Ettin 400M | 1695/1886 | 4117 | 97.8/100.0/100.0 | 149.2/150.2/151.0 | 14.664 | 2.339/2.385 | 0.427 | 21.4 | 350.9 | 5.74 | 74.0 |

## By query type

| Type | Nemotron NDCG | Ettin NDCG | Ettin−Nemo |
|---|---:|---:|---:|
| character_name | 0.3203 | 0.2157 | -0.1046 |
| context_dependency | 0.5613 | 0.5751 | +0.0138 |
| emotion_intention | 1.0000 | 1.0000 | +0.0000 |
| exact_phrase | 1.0000 | 0.8787 | -0.1213 |
| indirect_dialogue | 1.0000 | 0.9815 | -0.0185 |
| semantic_event | 1.0000 | 0.9598 | -0.0402 |
| similar_scene | 0.8418 | 0.3482 | -0.4936 |

## Decision

**NEMOTRON_WINS** on pipeline NDCG@10. This decision is only for `EmbeddingGemma top-50 → reranker` on the scene/cut corpus.

Whole-GPU nvidia-smi telemetry can include desktop activity; Torch allocated/reserved peaks are process-local.
