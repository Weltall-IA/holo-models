# Local Model Inventory Report — v1.4.6

Generated from canonical benchmark artifacts.

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
|---|---:|
| BENCHMARKED | 12 |
| BLOCKED | 19 |
| HEALTHCHECK_PASSED | 22 |
| **Total** | **53** |

| Category | Count |
|---|---:|
| embedding | 14 |
| text_llm | 30 |
| image | 3 |
| audio | 2 |
| video | 4 |

## Embedding Models (14)

Composition: **11 benchmarked unique models + 1 verified alias + 2 blocked models = 14 entries**.

### Canonical benchmark results

| Rank | ID | Backend | MRR@10 | nDCG@10 | HitRate@1 | Tokens | Source |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | voyage-4-large | Voyage API | 0.772794 | 0.786095 | 0.726667 | 259.246 | Patch 1.4.4 |
| 2 | voyage4_nano | sentence-transformers/CUDA | 0.752757 | 0.771872 | 0.693333 | local | Gate 2 |
| 3 | voyage-context-4 | Voyage API contextual | 0.743304 | 0.774832 | 0.666667 | 259.906 | Patch 1.4.4 |
| 4 | embeddinggemma_gguf | llama.cpp/CUDA | 0.738852 | 0.760875 | 0.666667 | local | Gate 3 |
| 5 | bge_m3_dense | sentence-transformers/CUDA | 0.718167 | 0.749013 | 0.646667 | local | Gate 2 |
| 6 | colibri_ptbr | sentence-transformers/CUDA | 0.696611 | 0.725809 | 0.606667 | local | Gate 2 |
| 7 | qwen3_embedding_8b_gguf | llama.cpp/CUDA | 0.692042 | 0.727498 | 0.613333 | local | Gate 3 |
| 8 | multilingual_e5_large_instruct | sentence-transformers/CUDA | 0.632894 | 0.678763 | 0.526667 | local | Gate 2 |
| 9 | qwen3_embedding_06 | sentence-transformers/CUDA | 0.616349 | 0.663419 | 0.520000 | local | Gate 2 |
| 10 | qwen3_embedding_06_gguf | llama.cpp/CUDA | 0.615349 | 0.662491 | 0.520000 | local | Gate 3 |
| 11 | gte_multilingual_base | sentence-transformers/CUDA | 0.567590 | 0.625176 | 0.446667 | local | Patch 1.4.3 |

### Verified alias

- `qwen3-embedding:0.6b` → `qwen3_embedding_06`. It is excluded from the unique-model ranking.

### Blocked embeddings

| ID | Reason |
|---|---|
| bitnet_06b | GGUF TYPE_IQ4_NL_4_4 removed in llama.cpp 9972 |
| bitnet_270m | GGUF TYPE_IQ4_NL_4_4 removed in llama.cpp 9972 |

## Voyage API

- `voyage-4-large`: 259.246 tokens, 31 requests, 0 retries, US$ 0.00 within the informed allowance.
- `voyage-context-4`: 259.906 tokens, 31 requests, 0 retries, US$ 0.00 within the informed allowance.
- SDK: `voyageai 0.5.0`.
- Frozen corpus SHA-256: `8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b`.

## Other categories

The detailed status and structured evidence for text, image, audio and video models remain in `local_model_inventory.json`.
