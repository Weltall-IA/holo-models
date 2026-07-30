# Complete Embedding x Reranker Matrix — Top 15 Raw

Generated: 2026-07-30T15:14:53Z

## Top 15 Raw Embeddings

| Rank | Profile | Raw MRR@10 |
|-----:|---------|-----------:|
| 1 | nemotron_3_embed_1b_nvfp4 | 0.7753 |
| 2 | voyage-4-large | 0.7728 |
| 3 | voyage_4_large_1024_float32 | 0.7728 |
| 4 | nemotron_3_embed_1b_q4_k_m_gguf | 0.7695 |
| 5 | voyage4_nano_2048_int8 | 0.7681 |
| 6 | embeddinggemma | 0.7562 |
| 7 | pplx_embed_v1_4b_q8_0 | 0.7562 |
| 8 | voyage4_nano_2048_float32 | 0.7561 |
| 9 | voyage4_nano | 0.7528 |
| 10 | voyage4_nano_1024_float32 | 0.7528 |
| 11 | nemotron_8b_abiray_q4_audit_1024 | 0.7459 |
| 12 | voyage-context-4 | 0.7433 |
| 13 | nomic_embed_text_v2_moe_q4 | 0.7420 |
| 14 | embeddinggemma_768_float32 | 0.7389 |
| 15 | embeddinggemma_gguf | 0.7389 |

*nemotron_8b_abiray_q4_audit_4096 excluded; bge_m3_dense promoted to #15*

## Matrix Coverage

| Status | Count |
|--------|------:|
| BLOCKED_NO_RUNNER | 36 |
| BLOCKED_PAID_API | 5 |
| MISSING | 21 |
| NO_CANDIDATES | 10 |
| VALID_REUSABLE | 48 |
| **TOTAL** | **120** |

## Ranking of Valid Pipelines (48 cells)

| Rank | Raw# | Embedding | Reranker | MRR@10 | HR@1 | HR@10 | nDCG@10 |
|-----:|-----:|-----------|----------|-------:|-----:|------:|--------:|
| 1 | 13 | nomic_embed_text_v2_moe_q4 | llama_nemotron_rerank_1b_v2 | 0.8320 | 0.8133 | 0.8800 | 0.8357 |
| 2 | 1 | nemotron_3_embed_1b_nvfp4 | llama_nemotron_rerank_1b_v2 | 0.8318 | 0.8133 | 0.8800 | 0.8355 |
| 3 | 11 | nemotron_8b_abiray_q4_audit_1024 | voyage_rerank_2_5 | 0.8307 | 0.8200 | 0.8667 | 0.8312 |
| 4 | 6 | embeddinggemma | llama_nemotron_rerank_1b_v2 | 0.8299 | 0.8133 | 0.8800 | 0.8339 |
| 5 | 14 | embeddinggemma_768_float32 | voyage_rerank_2_5 | 0.8264 | 0.8133 | 0.8733 | 0.8346 |
| 6 | 3 | voyage_4_large_1024_float32 | voyage_rerank_2_5 | 0.8261 | 0.8133 | 0.8733 | 0.8304 |
| 7 | 10 | voyage4_nano_1024_float32 | voyage_rerank_2_5 | 0.8210 | 0.8067 | 0.8667 | 0.8279 |
| 8 | 13 | nomic_embed_text_v2_moe_q4 | voyage_rerank_2_5 | 0.8209 | 0.8067 | 0.8667 | 0.8236 |
| 9 | 7 | pplx_embed_v1_4b_q8_0 | voyage_rerank_2_5 | 0.8206 | 0.8067 | 0.8667 | 0.8277 |
| 10 | 5 | voyage4_nano_2048_int8 | voyage_rerank_2_5 | 0.8200 | 0.8067 | 0.8667 | 0.8258 |
| 11 | 8 | voyage4_nano_2048_float32 | voyage_rerank_2_5 | 0.8195 | 0.8067 | 0.8667 | 0.8253 |
| 12 | 13 | nomic_embed_text_v2_moe_q4 | mxbai_rerank_base_v2 | 0.8047 | 0.7733 | 0.8733 | 0.8149 |
| 13 | 6 | embeddinggemma | mxbai_rerank_base_v2 | 0.8013 | 0.7667 | 0.8733 | 0.8124 |
| 14 | 1 | nemotron_3_embed_1b_nvfp4 | mxbai_rerank_base_v2 | 0.8003 | 0.7667 | 0.8667 | 0.8101 |
| 15 | 14 | embeddinggemma_768_float32 | qwen_local | 0.7911 | 0.7600 | 0.8733 | 0.8055 |
| 16 | 11 | nemotron_8b_abiray_q4_audit_1024 | qwen_local | 0.7907 | 0.7600 | 0.8600 | 0.7996 |
| 17 | 3 | voyage_4_large_1024_float32 | qwen_local | 0.7903 | 0.7600 | 0.8733 | 0.8047 |
| 18 | 1 | nemotron_3_embed_1b_nvfp4 | qwen_local | 0.7892 | 0.7600 | 0.8667 | 0.8011 |
| 19 | 4 | nemotron_3_embed_1b_q4_k_m_gguf | qwen_local | 0.7890 | 0.7600 | 0.8667 | 0.8009 |
| 20 | 12 | voyage-context-4 | qwen_local | 0.7887 | 0.7600 | 0.8667 | 0.8007 |
| 21 | 8 | voyage4_nano_2048_float32 | qwen_local | 0.7837 | 0.7533 | 0.8600 | 0.7966 |
| 22 | 5 | voyage4_nano_2048_int8 | qwen_local | 0.7835 | 0.7533 | 0.8600 | 0.7965 |
| 23 | 10 | voyage4_nano_1024_float32 | qwen_local | 0.7835 | 0.7533 | 0.8600 | 0.7964 |
| 24 | 6 | embeddinggemma | qwen_local | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 25 | 6 | embeddinggemma | jina_reranker_v3_noncommercial | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 26 | 6 | embeddinggemma | kalm_reranker_v1_small | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 27 | 6 | embeddinggemma | kalm_reranker_v1_nano | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 28 | 6 | embeddinggemma | querit_reranker_4b | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 29 | 7 | pplx_embed_v1_4b_q8_0 | qwen_local | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 30 | 7 | pplx_embed_v1_4b_q8_0 | jina_reranker_v3_noncommercial | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 31 | 7 | pplx_embed_v1_4b_q8_0 | kalm_reranker_v1_small | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 32 | 7 | pplx_embed_v1_4b_q8_0 | kalm_reranker_v1_nano | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 33 | 7 | pplx_embed_v1_4b_q8_0 | querit_reranker_4b | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 34 | 9 | voyage4_nano | qwen_local | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 35 | 9 | voyage4_nano | jina_reranker_v3_noncommercial | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 36 | 9 | voyage4_nano | kalm_reranker_v1_small | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 37 | 9 | voyage4_nano | kalm_reranker_v1_nano | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 38 | 9 | voyage4_nano | querit_reranker_4b | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 39 | 13 | nomic_embed_text_v2_moe_q4 | qwen_local | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 40 | 13 | nomic_embed_text_v2_moe_q4 | jina_reranker_v3_noncommercial | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 41 | 13 | nomic_embed_text_v2_moe_q4 | kalm_reranker_v1_small | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 42 | 13 | nomic_embed_text_v2_moe_q4 | kalm_reranker_v1_nano | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 43 | 13 | nomic_embed_text_v2_moe_q4 | querit_reranker_4b | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 44 | 15 | embeddinggemma_gguf | qwen_local | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 45 | 15 | embeddinggemma_gguf | jina_reranker_v3_noncommercial | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 46 | 15 | embeddinggemma_gguf | kalm_reranker_v1_small | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 47 | 15 | embeddinggemma_gguf | kalm_reranker_v1_nano | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 48 | 15 | embeddinggemma_gguf | querit_reranker_4b | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

## Blocked Cells

- **BLOCKED_NO_RUNNER** (36): jina, kalm_reranker_v1_small, kalm_reranker_v1_nano, querit_reranker_4b — no score_* function exists in reranker_backends.py for these rerankers
- **BLOCKED_PAID_API** (5): voyage_rerank_2_5 for embeddings without Voyage candidates
- **NO_CANDIDATES** (10): voyage4_nano and voyage4_nano variants lacking candidate artifacts
- **MISSING** (21): cells where both embedding candidates and reranker runner exist but pipeline was not generated

*Top 15 raw comparado na matriz canonica de rerankers, reutilizando resultados validos e executando somente as celulas faltantes.*
