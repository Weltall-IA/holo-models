# Reranker Pipeline Benchmark — v1.5.2

- Frozen corpus SHA-256: `8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b`
- Benchmark status: `PASS`
- Pipelines completed: 15 / 15

| Rank | Pipeline | HitRate@1 | HitRate@10 | MRR@10 | nDCG@10 | Rescue | Damage |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | embeddinggemma_768_float32__voyage_rerank_2_5 | 0.813333 | 0.873333 | 0.826444 | 0.834631 | 0.440000 | 0.000000 |
| 2 | voyage_4_large_1024_float32__voyage_rerank_2_5 | 0.813333 | 0.873333 | 0.826056 | 0.830447 | 0.368421 | 0.009174 |
| 3 | voyage4_nano_1024_float32__voyage_rerank_2_5 | 0.806667 | 0.866667 | 0.820989 | 0.827871 | 0.450000 | 0.009615 |
| 4 | voyage4_nano_2048_int8__voyage_rerank_2_5 | 0.806667 | 0.866667 | 0.820037 | 0.825795 | 0.411765 | 0.009259 |
| 5 | voyage4_nano_2048_float32__voyage_rerank_2_5 | 0.806667 | 0.866667 | 0.819481 | 0.825333 | 0.447368 | 0.009524 |
| 6 | embeddinggemma_768_float32__qwen_local | 0.760000 | 0.873333 | 0.791074 | 0.805547 | 0.440000 | 0.080000 |
| 7 | voyage_4_large_1024_float32__qwen_local | 0.760000 | 0.873333 | 0.790296 | 0.804706 | 0.368421 | 0.082569 |
| 8 | voyage4_nano_2048_float32__qwen_local | 0.753333 | 0.860000 | 0.783704 | 0.796649 | 0.473684 | 0.095238 |
| 9 | voyage4_nano_2048_int8__qwen_local | 0.753333 | 0.860000 | 0.783545 | 0.796497 | 0.441176 | 0.092593 |
| 10 | voyage4_nano_1024_float32__qwen_local | 0.753333 | 0.860000 | 0.783471 | 0.796417 | 0.475000 | 0.096154 |
| 11 | voyage_4_large_1024_float32__none | 0.726667 | 0.860000 | 0.772794 | 0.786095 | — | — |
| 12 | voyage4_nano_2048_int8__none | 0.720000 | 0.860000 | 0.768119 | 0.783713 | — | — |
| 13 | voyage4_nano_2048_float32__none | 0.700000 | 0.860000 | 0.756071 | 0.774639 | — | — |
| 14 | voyage4_nano_1024_float32__none | 0.693333 | 0.853333 | 0.752757 | 0.771872 | — | — |
| 15 | embeddinggemma_768_float32__none | 0.666667 | 0.860000 | 0.738852 | 0.760875 | — | — |

## Embedding resources

| Variant | Dimension | Dtype | Vector bytes | Model bytes | Peak VRAM | Total seconds |
|---|---:|---|---:|---:|---:|---:|
| voyage_4_large_1024_float32 | 1024 | float32 | 4096 | — | — | 0.758 |
| voyage4_nano_2048_int8 | 2048 | int8 | 2048 | 704450676 | 2624768512 | 24.0132 |
| voyage4_nano_2048_float32 | 2048 | float32 | 8192 | 704450676 | 2624768512 | 24.0132 |
| voyage4_nano_1024_float32 | 1024 | float32 | 4096 | 704450676 | 2624768512 | 24.0132 |
| embeddinggemma_768_float32 | 768 | float32 | — | 333590944 | 383090688 | 12.3958 |

## Reranker runtime

### `voyage_rerank_2_5`

- Model: `rerank-2.5`
- Backend: `Voyage Batch API`
- Total seconds: `304.2701`
- Latency p50/p95/max: `None` / `None` / `None` seconds
- Peak VRAM: `None` bytes
- Peak process-tree RSS: `None` bytes
- API usage: `{'tokens': 2275458, 'requests': 150, 'retries': 0, 'seconds': 304.2701, 'estimated_standard_price_usd': 0.1137729, 'charged_cost_usd': None}`

### `qwen_local`

- Model: `e61197ed45024b0ed8a2d74b80b4d909f1255473`
- Backend: `sentence-transformers.CrossEncoder`
- Total seconds: `388.1375`
- Latency p50/p95/max: `2.5037` / `3.622` / `4.3147` seconds
- Peak VRAM: `3144946176` bytes
- Peak process-tree RSS: `3353128960` bytes
- API usage: `None`

The ranking covers only completed pipelines and does not establish statistical significance between near-tied results.
The 2048 int8 variant uses corpus-calibrated scalar quantization with dequantized cosine scoring; native vector-database latency was not measured.
No merge or production choice is implicit.
