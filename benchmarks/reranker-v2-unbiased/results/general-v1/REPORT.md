# Reranker V2 — GENERAL

All quality numbers below are measured on the same frozen candidate pools. No projected scores are admitted.

## Quality

| Model | NDCG@10 (95% CI) | MRR@10 (95% CI) | MAP | Hit@1 | Recall@10 | Recall@20 |
|---|---:|---:|---:|---:|---:|---:|
| Nemotron 1B v2 | 0.7609 [0.7230, 0.7977] | 0.7512 [0.7077, 0.7940] | 0.7234 | 0.6480 | 0.8004 | 0.8674 |
| Jina v3.5 | 0.7435 [0.7052, 0.7818] | 0.7291 [0.6851, 0.7730] | 0.6978 | 0.6240 | 0.8007 | 0.8691 |
| Ettin 400M | 0.7197 [0.6783, 0.7602] | 0.7280 [0.6818, 0.7738] | 0.6778 | 0.6360 | 0.7626 | 0.8433 |
| Qwen3-Reranker-0.6B | 0.7069 [0.6663, 0.7478] | 0.7047 [0.6596, 0.7506] | 0.6662 | 0.5880 | 0.7606 | 0.8291 |

## Per dataset

### NanoFiQA2018

| Model | NDCG@10 | MRR@10 |
|---|---:|---:|
| Nemotron 1B v2 | 0.7020 | 0.7233 |
| Jina v3.5 | 0.7027 | 0.7217 |
| Ettin 400M | 0.6535 | 0.7054 |
| Qwen3-Reranker-0.6B | 0.6148 | 0.6431 |

### NanoMSMARCO

| Model | NDCG@10 | MRR@10 |
|---|---:|---:|
| Nemotron 1B v2 | 0.6938 | 0.6157 |
| Jina v3.5 | 0.7020 | 0.6265 |
| Ettin 400M | 0.7215 | 0.6533 |
| Qwen3-Reranker-0.6B | 0.7061 | 0.6202 |

### NanoNFCorpus

| Model | NDCG@10 | MRR@10 |
|---|---:|---:|
| Nemotron 1B v2 | 0.6681 | 0.7369 |
| Jina v3.5 | 0.6817 | 0.7490 |
| Ettin 400M | 0.6463 | 0.7719 |
| Qwen3-Reranker-0.6B | 0.6357 | 0.7319 |

### NanoNQ

| Model | NDCG@10 | MRR@10 |
|---|---:|---:|
| Nemotron 1B v2 | 0.8780 | 0.8480 |
| Jina v3.5 | 0.8114 | 0.7639 |
| Ettin 400M | 0.8027 | 0.7775 |
| Qwen3-Reranker-0.6B | 0.7564 | 0.7346 |

### NanoSciFact

| Model | NDCG@10 | MRR@10 |
|---|---:|---:|
| Nemotron 1B v2 | 0.8625 | 0.8322 |
| Jina v3.5 | 0.8195 | 0.7845 |
| Ettin 400M | 0.7743 | 0.7317 |
| Qwen3-Reranker-0.6B | 0.8216 | 0.7935 |

## Dataset decisions

| Dataset | Point-estimate leader | NDCG@10 decision vs runner-up | 95% CI |
|---|---|---|---:|
| NanoFiQA2018 | Jina v3.5 | INCONCLUSIVE | [-0.0588, +0.0622] |
| NanoMSMARCO | Ettin 400M | INCONCLUSIVE | [-0.0546, +0.0866] |
| NanoNFCorpus | Jina v3.5 | INCONCLUSIVE | [-0.0121, +0.0438] |
| NanoNQ | Nemotron 1B v2 | Nemotron 1B v2 | [+0.0248, +0.1137] |
| NanoSciFact | Nemotron 1B v2 | Nemotron 1B v2 | [+0.0046, +0.0802] |
## Paired significance

| Comparison | Metric | Mean delta | 95% CI | Verdict |
|---|---|---:|---:|---|
| Nemotron 1B v2 − Jina v3.5 | ndcg@10 | +0.0174 | [-0.0064, +0.0411] | INCONCLUSIVE |
| Nemotron 1B v2 − Jina v3.5 | mrr@10 | +0.0221 | [-0.0091, +0.0533] | INCONCLUSIVE |
| Nemotron 1B v2 − Qwen3-Reranker-0.6B | ndcg@10 | +0.0540 | [+0.0294, +0.0782] | A_WINS |
| Nemotron 1B v2 − Qwen3-Reranker-0.6B | mrr@10 | +0.0466 | [+0.0168, +0.0757] | A_WINS |
| Nemotron 1B v2 − Ettin 400M | ndcg@10 | +0.0412 | [+0.0152, +0.0675] | A_WINS |
| Nemotron 1B v2 − Ettin 400M | mrr@10 | +0.0233 | [-0.0103, +0.0571] | INCONCLUSIVE |
| Jina v3.5 − Qwen3-Reranker-0.6B | ndcg@10 | +0.0366 | [+0.0116, +0.0618] | A_WINS |
| Jina v3.5 − Qwen3-Reranker-0.6B | mrr@10 | +0.0245 | [-0.0063, +0.0555] | INCONCLUSIVE |
| Jina v3.5 − Ettin 400M | ndcg@10 | +0.0238 | [+0.0002, +0.0481] | A_WINS |
| Jina v3.5 − Ettin 400M | mrr@10 | +0.0012 | [-0.0283, +0.0317] | INCONCLUSIVE |
| Qwen3-Reranker-0.6B − Ettin 400M | ndcg@10 | -0.0127 | [-0.0393, +0.0141] | INCONCLUSIVE |
| Qwen3-Reranker-0.6B − Ettin 400M | mrr@10 | -0.0233 | [-0.0566, +0.0105] | INCONCLUSIVE |

## Efficiency

| Model | GPU alloc peak MiB | GPU reserved peak MiB | RSS peak MiB | p50 s | p95 s | queries/s | total s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Nemotron 1B v2 | 3022.3 | 4218.0 | 2058.3 | 1.675 | 3.200 | 0.563 | 443.806 |
| Jina v3.5 | 2748.6 | 2858.0 | 2036.3 | 1.973 | 3.428 | 0.477 | 523.832 |
| Ettin 400M | 6631.2 | 10724.0 | 1738.6 | 2.453 | 7.249 | 0.368 | 679.516 |
| Qwen3-Reranker-0.6B | 12654.4 | 13098.0 | 1929.9 | 1.856 | 5.263 | 0.485 | 515.632 |

## Efficiency trade-offs

| Model | NDCG@10 | Peak VRAM GiB | p50 s | NDCG/GiB | NDCG/p50 s |
|---|---:|---:|---:|---:|---:|
| Nemotron 1B v2 | 0.7609 | 2.951 | 1.675 | 0.2578 | 0.4544 |
| Jina v3.5 | 0.7435 | 2.684 | 1.973 | 0.2770 | 0.3768 |
| Ettin 400M | 0.7197 | 6.476 | 2.453 | 0.1111 | 0.2934 |
| Qwen3-Reranker-0.6B | 0.7069 | 12.358 | 1.856 | 0.0572 | 0.3809 |

## Decision

- Point-estimate leader: **Nemotron 1B v2**.
- **No statistically supported winner** between Nemotron 1B v2 and Jina v3.5 at 95% confidence.
- Best quality/VRAM: **Jina v3.5** (NDCG per peak GiB).
- Best quality/latency: **Nemotron 1B v2** (NDCG per p50 second).
- GENERAL and HOLO are separate decisions; this report does not combine them into one score.
