# Reranker V2 — HOLO

All quality numbers below are measured on the same frozen candidate pools. No projected scores are admitted.

## Quality

| Model | NDCG@10 (95% CI) | MRR@10 (95% CI) | MAP | Hit@1 | Recall@10 | Recall@20 |
|---|---:|---:|---:|---:|---:|---:|
| Ettin 400M | 0.9330 [0.8823, 0.9723] | 0.9147 [0.8523, 0.9637] | 0.9157 | 0.8618 | 0.9868 | 1.0000 |
| Jina v3.5 | 0.8884 [0.8281, 0.9376] | 0.8541 [0.7788, 0.9167] | 0.8548 | 0.7533 | 0.9901 | 1.0000 |
| Nemotron 1B v2 | 0.8831 [0.8391, 0.9249] | 0.8509 [0.7951, 0.9036] | 0.8520 | 0.7763 | 0.9836 | 0.9967 |
| Qwen3-Reranker-0.6B | 0.7929 [0.7230, 0.8598] | 0.7326 [0.6447, 0.8180] | 0.7341 | 0.5855 | 0.9770 | 1.0000 |

## By category

| Group | Model | NDCG@10 | MRR@10 | MAP | Hit@1 | Recall@10 | Recall@20 |
|---|---|---:|---:|---:|---:|---:|---:|
| agents | Ettin 400M | 0.9974 | 0.9965 | 0.9965 | 0.9931 | 1.0000 | 1.0000 |
| agents | Jina v3.5 | 0.9436 | 0.9238 | 0.9238 | 0.8542 | 1.0000 | 1.0000 |
| agents | Nemotron 1B v2 | 0.8682 | 0.8331 | 0.8344 | 0.7639 | 0.9792 | 0.9931 |
| agents | Qwen3-Reranker-0.6B | 0.8329 | 0.7891 | 0.7913 | 0.6806 | 0.9653 | 1.0000 |
| rules | Ettin 400M | 0.9623 | 0.9491 | 0.9491 | 0.9028 | 1.0000 | 1.0000 |
| rules | Jina v3.5 | 0.9367 | 0.9144 | 0.9144 | 0.8333 | 1.0000 | 1.0000 |
| rules | Nemotron 1B v2 | 0.9692 | 0.9583 | 0.9583 | 0.9167 | 1.0000 | 1.0000 |
| rules | Qwen3-Reranker-0.6B | 0.8265 | 0.7671 | 0.7671 | 0.5833 | 1.0000 | 1.0000 |
| capabilities | Ettin 400M | 0.9177 | 0.8901 | 0.8901 | 0.8125 | 1.0000 | 1.0000 |
| capabilities | Jina v3.5 | 0.7686 | 0.7129 | 0.7173 | 0.5625 | 0.9375 | 1.0000 |
| capabilities | Nemotron 1B v2 | 0.9616 | 0.9479 | 0.9479 | 0.8958 | 1.0000 | 1.0000 |
| capabilities | Qwen3-Reranker-0.6B | 0.7177 | 0.6333 | 0.6346 | 0.4583 | 0.9792 | 1.0000 |
| routing | Ettin 400M | 0.6409 | 0.5625 | 0.5730 | 0.3750 | 0.8750 | 1.0000 |
| routing | Jina v3.5 | 0.8366 | 0.7812 | 0.7812 | 0.6250 | 1.0000 | 1.0000 |
| routing | Nemotron 1B v2 | 0.5453 | 0.4235 | 0.4292 | 0.1875 | 0.9375 | 1.0000 |
| routing | Qwen3-Reranker-0.6B | 0.7383 | 0.6557 | 0.6557 | 0.5000 | 1.0000 | 1.0000 |
| docs | Ettin 400M | 0.6837 | 0.6042 | 0.6108 | 0.3750 | 0.9167 | 1.0000 |
| docs | Jina v3.5 | 0.6863 | 0.5856 | 0.5856 | 0.3750 | 1.0000 | 1.0000 |
| docs | Nemotron 1B v2 | 0.7824 | 0.7260 | 0.7295 | 0.5833 | 0.9583 | 1.0000 |
| docs | Qwen3-Reranker-0.6B | 0.6392 | 0.5392 | 0.5430 | 0.3333 | 0.9583 | 1.0000 |

## By language

| Group | Model | NDCG@10 | MRR@10 | MAP | Hit@1 | Recall@10 | Recall@20 |
|---|---|---:|---:|---:|---:|---:|---:|
| pt-BR | Ettin 400M | 0.9322 | 0.9138 | 0.9148 | 0.8618 | 0.9868 | 1.0000 |
| pt-BR | Jina v3.5 | 0.8809 | 0.8435 | 0.8439 | 0.7368 | 0.9934 | 1.0000 |
| pt-BR | Nemotron 1B v2 | 0.8515 | 0.8131 | 0.8148 | 0.7368 | 0.9737 | 0.9934 |
| pt-BR | Qwen3-Reranker-0.6B | 0.7943 | 0.7344 | 0.7359 | 0.5987 | 0.9803 | 1.0000 |
| en | Ettin 400M | 0.9338 | 0.9156 | 0.9167 | 0.8618 | 0.9868 | 1.0000 |
| en | Jina v3.5 | 0.8958 | 0.8646 | 0.8656 | 0.7697 | 0.9868 | 1.0000 |
| en | Nemotron 1B v2 | 0.9147 | 0.8887 | 0.8893 | 0.8158 | 0.9934 | 1.0000 |
| en | Qwen3-Reranker-0.6B | 0.7915 | 0.7307 | 0.7323 | 0.5724 | 0.9737 | 1.0000 |
## Paired significance

| Comparison | Metric | Mean delta | 95% CI | Verdict |
|---|---|---:|---:|---|
| Nemotron 1B v2 − Jina v3.5 | ndcg@10 | -0.0053 | [-0.0639, +0.0609] | INCONCLUSIVE |
| Nemotron 1B v2 − Jina v3.5 | mrr@10 | -0.0032 | [-0.0768, +0.0780] | INCONCLUSIVE |
| Nemotron 1B v2 − Qwen3-Reranker-0.6B | ndcg@10 | +0.0902 | [+0.0136, +0.1654] | A_WINS |
| Nemotron 1B v2 − Qwen3-Reranker-0.6B | mrr@10 | +0.1183 | [+0.0205, +0.2145] | A_WINS |
| Nemotron 1B v2 − Ettin 400M | ndcg@10 | -0.0499 | [-0.0911, -0.0078] | B_WINS |
| Nemotron 1B v2 − Ettin 400M | mrr@10 | -0.0638 | [-0.1165, -0.0103] | B_WINS |
| Jina v3.5 − Qwen3-Reranker-0.6B | ndcg@10 | +0.0955 | [+0.0450, +0.1464] | A_WINS |
| Jina v3.5 − Qwen3-Reranker-0.6B | mrr@10 | +0.1215 | [+0.0593, +0.1846] | A_WINS |
| Jina v3.5 − Ettin 400M | ndcg@10 | -0.0446 | [-0.0869, -0.0074] | B_WINS |
| Jina v3.5 − Ettin 400M | mrr@10 | -0.0606 | [-0.1108, -0.0151] | B_WINS |
| Qwen3-Reranker-0.6B − Ettin 400M | ndcg@10 | -0.1401 | [-0.1984, -0.0822] | B_WINS |
| Qwen3-Reranker-0.6B − Ettin 400M | mrr@10 | -0.1821 | [-0.2545, -0.1097] | B_WINS |

## Efficiency

| Model | GPU alloc peak MiB | GPU reserved peak MiB | RSS peak MiB | p50 s | p95 s | queries/s | total s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Ettin 400M | 4318.3 | 4570.0 | 1612.4 | 13.634 | 14.186 | 0.073 | 4144.221 |
| Jina v3.5 | 3738.2 | 3896.0 | 2010.7 | 7.912 | 8.561 | 0.127 | 2402.936 |
| Nemotron 1B v2 | 3478.4 | 3590.0 | 1977.2 | 7.824 | 9.136 | 0.128 | 2368.041 |
| Qwen3-Reranker-0.6B | 4986.0 | 5180.0 | 1854.4 | 7.713 | 7.918 | 0.130 | 2343.206 |

## Efficiency trade-offs

| Model | NDCG@10 | Peak VRAM GiB | p50 s | NDCG/GiB | NDCG/p50 s |
|---|---:|---:|---:|---:|---:|
| Ettin 400M | 0.9330 | 4.217 | 13.634 | 0.2212 | 0.0684 |
| Jina v3.5 | 0.8884 | 3.651 | 7.912 | 0.2434 | 0.1123 |
| Nemotron 1B v2 | 0.8831 | 3.397 | 7.824 | 0.2600 | 0.1129 |
| Qwen3-Reranker-0.6B | 0.7929 | 4.869 | 7.713 | 0.1628 | 0.1028 |

## Decision

- Point-estimate leader: **Ettin 400M**.
- Statistically supported NDCG@10 winner: **Ettin 400M** (paired 95% CI vs Jina v3.5 excludes zero).
- Best quality/VRAM: **Nemotron 1B v2** (NDCG per peak GiB).
- Best quality/latency: **Nemotron 1B v2** (NDCG per p50 second).
- GENERAL and HOLO are separate decisions; this report does not combine them into one score.
