# Local Model Inventory Report — v1.4.1

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
| BENCHMARKED | 9 |
| BLOCKED | 21 |
| HEALTHCHECK_PASSED | 22 |
| **Total** | **52** |

| Category | Count |
|---|---|
| embedding | 13 |
| text_llm | 30 |
| image | 3 |
| audio | 2 |
| video | 4 |

## Embedding Models (13)

### BENCHMARKED (9 + 1 alias)
Models executed in Gates 0-3 with full metrics:
- colibri_ptbr, multilingual_e5_large_instruct, qwen3_embedding_06, bge_m3_dense, voyage4_nano
- qwen3_embedding_8b_gguf, embeddinggemma_gguf, qwen3_embedding_06_gguf
- qwen3-embedding:0.6b (alias of qwen3_embedding_06, verified via /api/embed)

### BLOCKED (3)
- gte_multilingual_base: CUDA index out of bounds in trust_remote_code
- bitnet_270m: GGUF TYPE_IQ4_NL_4_4 removed in llama.cpp 9972
- bitnet_06b: Same GGUF format incompatibility

## Text LLMs (30)

### HEALTHCHECK_PASSED (16 Ollama + 5 GGUF aliases)
All 17 Ollama models and 5 verified GGUF-Ollama aliases passed /api/generate with 8+ tokens.

## Image (3), Audio (2), Video (4)
All BLOCKED with structured evidence: runtime, error, attempts.

## Evidence Structure
Every model has:
- `evidence.runtime`: identified runtime
- `evidence.endpoint` or `evidence.command`: specific invocation
- `evidence.result`: actual output or error
- Blocked models have `evidence.attempts` list
