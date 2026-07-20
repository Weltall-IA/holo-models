# Reranker Pipeline Benchmark — v1.5.1

- Frozen corpus SHA-256: `8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b`
- Pipelines completed: 10

| Rank | Pipeline | HitRate@1 | HitRate@10 | MRR@10 | nDCG@10 | Rescue | Damage |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | embeddinggemma_768_float32__qwen_local | 0.760000 | 0.873333 | 0.791074 | 0.805547 | 0.440000 | 0.080000 |
| 2 | voyage_4_large_1024_float32__qwen_local | 0.760000 | 0.873333 | 0.790296 | 0.804706 | 0.368421 | 0.082569 |
| 3 | voyage4_nano_2048_float32__qwen_local | 0.753333 | 0.860000 | 0.783704 | 0.796649 | 0.473684 | 0.095238 |
| 4 | voyage4_nano_2048_int8__qwen_local | 0.753333 | 0.860000 | 0.783545 | 0.796497 | 0.441176 | 0.092593 |
| 5 | voyage4_nano_1024_float32__qwen_local | 0.753333 | 0.860000 | 0.783471 | 0.796417 | 0.475000 | 0.096154 |
| 6 | voyage_4_large_1024_float32__none | 0.726667 | 0.860000 | 0.772794 | 0.786095 | — | — |
| 7 | voyage4_nano_2048_int8__none | 0.720000 | 0.860000 | 0.768119 | 0.783713 | — | — |
| 8 | voyage4_nano_2048_float32__none | 0.700000 | 0.860000 | 0.756071 | 0.774639 | — | — |
| 9 | voyage4_nano_1024_float32__none | 0.693333 | 0.853333 | 0.752757 | 0.771872 | — | — |
| 10 | embeddinggemma_768_float32__none | 0.666667 | 0.860000 | 0.738852 | 0.760875 | — | — |

## Embedding resources

| Variant | Dimension | Dtype | Vector bytes | Model bytes | Peak VRAM | Total seconds |
|---|---:|---|---:|---:|---:|---:|
| voyage_4_large_1024_float32 | 1024 | float32 | 4096 | — | — | 0.758 |
| voyage4_nano_2048_int8 | 2048 | int8 | 2048 | 704450676 | 2624768512 | 24.0132 |
| voyage4_nano_2048_float32 | 2048 | float32 | 8192 | 704450676 | 2624768512 | 24.0132 |
| voyage4_nano_1024_float32 | 1024 | float32 | 4096 | 704450676 | 2624768512 | 24.0132 |
| embeddinggemma_768_float32 | 768 | float32 | — | 333590944 | 383090688 | 12.3958 |

## Reranker runtime

### `qwen_local`

- Model: `e61197ed45024b0ed8a2d74b80b4d909f1255473`
- Backend: `sentence-transformers.CrossEncoder`
- Total seconds: `388.1375`
- Latency p50/p95/max: `2.5037` / `3.622` / `4.3147` seconds
- Peak VRAM: `3144946176` bytes
- Peak process-tree RSS: `3353128960` bytes
- API usage: `None`

O relatório separa qualidade, custo de API e recursos locais. Nenhum merge ou escolha de produção é implícito.
