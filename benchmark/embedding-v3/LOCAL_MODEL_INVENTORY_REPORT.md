# Local Model Inventory Report

Generated: 2026-07-19

## Summary

| Metric | Count |
|---|---|
| Total models discovered | 52 |
| BENCHMARKED | 9 |
| BLOCKED | 3 |
| HEALTHCHECK_PASSED | 16 |
| NOT_APPLICABLE | 24 |
| **coverage_complete** | **true** |

## By Category

| Category | Count |
|---|---|
| embedding | 13 |
| text_llm | 30 |
| image | 3 |
| audio | 2 |
| video | 4 |

## Embedding Models (13)

### BENCHMARKED (9)
| ID | Repo | Revision |
|---|---|---|
| colibri_ptbr | tardellirs/colibri-embed-ptbr | 95a4d4f3a1c0 |
| multilingual_e5_large_instruct | intfloat/multilingual-e5-large-instruct | 274baa43b0e1 |
| qwen3_embedding_06 | Qwen/Qwen3-Embedding-0.6B | 97b0c614be4d |
| bge_m3_dense | BAAI/bge-m3 | 5617a9f61b02 |
| voyage4_nano | voyageai/voyage-4-nano | 67fabc9bef01 |
| qwen3_embedding_8b_gguf | Qwen/Qwen3-Embedding-8B-GGUF | 69d0e58a13e4 |
| embeddinggemma_gguf | ggml-org/embeddinggemma-300M-GGUF | 0f741b5a6585 |
| qwen3_embedding_06_gguf | Qwen/Qwen3-Embedding-0.6B-GGUF | 370f27d7550e |
| qwen3-embedding-0.6b | Ollama (benchmarked via Gate 2) | — |

### BLOCKED (3)
| ID | Repo | Reason |
|---|---|---|
| gte_multilingual_base | Alibaba-NLP/gte-multilingual-base | CUDA index out of bounds em trust_remote_code |
| bitnet_270m | microsoft/bitnet-embedding-270m | GGUF TYPE_IQ4_NL_4_4 incompatível com llama.cpp 9972 |
| bitnet_06b | microsoft/bitnet-embedding-0.6b | GGUF TYPE_IQ4_NL_4_4 incompatível com llama.cpp 9972 |

## Text LLMs (30)

### HEALTHCHECK_PASSED (16 — Ollama)
Todos os 16 modelos Ollama (chat) passaram health check com inferência de 1 token.

### NOT_APPLICABLE (14 — GGUFs sem Ollama)
GGUFs em `text/` que não estão registrados no Ollama. Classificados como NOT_APPLICABLE por não terem runner de inferência associado.

## Image Models (3)
- sd3.5_medium, Qwen-Image-vae-2d, qwen-image-edit-2511
- Status: NOT_APPLICABLE — sem runner de health check local

## Audio Models (2)
- Domínio `audio/`
- Status: NOT_APPLICABLE — sem runner de health check local

## Video Models (4)
- Domínio `video/`
- Status: NOT_APPLICABLE — sem runner de health check local
