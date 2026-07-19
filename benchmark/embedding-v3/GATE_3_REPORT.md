# GATE 3 REPORT

- modo: execução
- resultado: PASS
- corpus SHA-256: `8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b`
- llama-server: `version: 9972 (c92e806d1)
built with GNU 16.1.1 for Linux x86_64`

## Modelos

| modelo | GGUF | quant | dimensão | HitRate@10 | MRR@10 | nDCG@10 | docs/s | consultas/s |
|---|---|---|---:|---:|---:|---:|---:|---:|
| qwen3_embedding_8b_gguf | `Qwen3-Embedding-8B-Q8_0.gguf` | Q8_0 | 1024 | 0.846667 | 0.692042 | 0.727498 | 4.1892 | 15.516 |
| embeddinggemma_gguf | `embeddinggemma-300M-Q8_0.gguf` | Q8_0 | 768 | 0.860000 | 0.738852 | 0.760875 | 29.7565 | 195.7731 |
| qwen3_embedding_06_gguf | `Qwen3-Embedding-0.6B-Q8_0.gguf` | Q8_0 | 1024 | 0.826667 | 0.615349 | 0.662491 | 13.6033 | 76.7373 |

## Falhas e bloqueios
- nenhuma

Pesos e caches permanecem fora do Git. Gates 4 a 6 não foram executados.
