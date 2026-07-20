# Local Model Inventory Report — v1.4.5

Generated: 2026-07-19

## Coverage Validation

```json
{
  "passed": true,
  "finding_count": 0,
  "coverage_complete": true
}
```

## Summary

| Status | Count |
|---|---|
| BENCHMARKED | 12 |
| BLOCKED | 19 |
| HEALTHCHECK_PASSED | 22 |
| **Total** | **53** |

| Category | Count |
|---|---|
| embedding | 14 |
| text_llm | 30 |
| image | 3 |
| audio | 2 |
| video | 4 |

## Embedding Models (14)

### BENCHMARKED (11 models + 1 alias)

| # | ID | Backend | MRR@10 | nDCG@10 | Tokens | Source |
|---|---|---|---|---|---|---|
| 1 | colibri_ptbr | sentence-transformers/CUDA | 0.697 | 0.745 | local | Gate 2 |
| 2 | multilingual_e5_large_instruct | sentence-transformers/CUDA | 0.633 | 0.680 | local | Gate 2 |
| 3 | qwen3_embedding_06 | sentence-transformers/CUDA | 0.616 | 0.663 | local | Gate 2 |
| 4 | bge_m3_dense | sentence-transformers/CUDA | 0.718 | 0.745 | local | Gate 2 |
| 5 | voyage4_nano | sentence-transformers/CUDA | 0.753 | 0.772 | local | Gate 2 |
| 6 | qwen3_embedding_8b_gguf | llama.cpp/CUDA | 0.692 | 0.727 | local | Gate 3 |
| 7 | embeddinggemma_gguf | llama.cpp/CUDA | 0.739 | 0.761 | local | Gate 3 |
| 8 | qwen3_embedding_06_gguf | llama.cpp/CUDA | 0.615 | 0.662 | local | Gate 3 |
| 9 | gte_multilingual_base | sentence-transformers/CUDA | 0.568 | 0.625 | local | Patch 1.4.3 |
| 10 | voyage-4-large | Voyage API | **0.773** | **0.786** | 259.246 | Patch 1.4.4 |
| 11 | voyage-context-4 | Voyage API | 0.743 | 0.775 | 259.906 | Patch 1.4.4 |
| — | qwen3-embedding:0.6b | alias Ollama | — | — | — | alias of qwen3_embedding_06 |

### BLOCKED (3)
| ID | Reason |
|---|---|
| bitnet_270m | GGUF TYPE_IQ4_NL_4_4 incompatível com llama.cpp 9972 |
| bitnet_06b | GGUF TYPE_IQ4_NL_4_4 incompatível com llama.cpp 9972 |
| gte_multilingual_base_cuda | Entrada duplicada removida |

### Ranking por MRR@10

| Rank | Model | MRR@10 | nDCG@10 | HitRate@1 |
|---|---|---|---|---|
| 1 | **voyage-4-large** | 0.773 | 0.786 | 0.727 |
| 2 | voyage4_nano | 0.753 | 0.772 | 0.693 |
| 3 | voyage-context-4 | 0.743 | 0.775 | 0.667 |
| 4 | embeddinggemma_gguf | 0.739 | 0.761 | 0.667 |
| 5 | bge_m3_dense | 0.718 | 0.745 | 0.647 |
| 6 | colibri_ptbr | 0.697 | 0.745 | 0.607 |
| 7 | qwen3_embedding_8b_gguf | 0.692 | 0.727 | 0.613 |
| 8 | multilingual_e5_large_instruct | 0.633 | 0.680 | 0.527 |
| 9 | qwen3_embedding_06_gguf | 0.615 | 0.662 | 0.520 |
| 10 | qwen3_embedding_06 | 0.616 | 0.663 | 0.520 |
| 11 | gte_multilingual_base | 0.568 | 0.625 | 0.447 |

## Text LLMs (30)
- 16 Ollama + 5 GGUF aliases: HEALTHCHECK_PASSED
- 14 GGUFs sem Ollama: BLOCKED (sem runner)

## Image (3), Audio (2), Video (4)
- 9 modelos BLOCKED com evidence estruturada

## Voyage API
- voyage-4-large: 259.246 tokens, 31 requisições, 0 retries, US$ 0,00
- voyage-context-4: 259.906 tokens, 31 requisições, 0 retries, US$ 0,00
- SDK: voyageai 0.5.0
- Corpus hash: 8e1b7a6d...
