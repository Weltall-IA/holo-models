# Benchmark Report: Literary MiniLM vs EmbeddingGemma

## Configuration

- **Dataset**: holo_fake_scenes_v3 (600 docs, 150 queries)
- **Corpus SHA-256**: `59cf7d64a68770731e28308e421129d3193eacd2a10ba182da8dcf286249d85b`
- **Queries SHA-256**: `9aa48f789df1e3b246979a049478b217cfda1e47fad12a131b5618f4f17e329b`
- **Combined SHA-256**: `8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b`
- **CPU Threads**: 8
- **All results**: measured=true, projected=false

## Models

| Model | Repository | Revision |
|-------|-----------|----------|
| EmbeddingGemma | `google/embeddinggemma-300m` | `57c266a740f537b4dc058e1b0cda161fd15afa75` |
| Literary MiniLM | `RafaelUI/literary-minilm` | `92a6516f32321dc4048b49c9e6eb2b9aaa7e8e8f` |
| Nemotron Reranker | `nvidia/llama-nemotron-rerank-1b-v2` | `7b6d977e129a50b29c6b557d5d38c2e7c0f527e7` |

## EMBEDDING PURO

| Model | NDCG@10 | MRR@10 | Hit@1 | R@10 | R@20 | R@50 | Dim | VRAM (MiB) | p50 (ms) | q/s | docs/s |
|-------|---------|--------|-------|------|------|------|-----|------------|----------|-----|--------|
| EmbeddingGemma | 0.7501 | 0.7290 | 0.6667 | 0.8367 | 0.9667 | 1.0000 | 768 | 2969.7 | 100.5 | 565.73 | 62.4 |
| Literary MiniLM | 0.1320 | 0.0821 | 0.0333 | 0.3033 | 0.6167 | 0.7733 | 384 | 602.9 | 24.5 | 2168.40 | 592.9 |

## PIPELINE (Embedding + Nemotron)

| Pipeline | NDCG@10 | MRR@10 | Hit@1 | R@10 | R@20 | R@50 | Top-50 Coverage | VRAM (MiB) | p50 (ms) | q/s | pairs/s |
|---------|---------|--------|-------|------|------|------|----------------|------------|----------|-----|--------|
| Gemma + Nemotron | 0.8277 | 0.8233 | 0.8000 | 0.8633 | 0.9667 | 1.0000 | 1.0000 | 2634.7 | 1608.1 | 0.60 | 30.12 |
| Literary + Nemotron | 0.6402 | 0.6378 | 0.6200 | 0.6700 | 0.7733 | 0.7733 | 0.7733 | 2630.9 | 2234.4 | 0.50 | 24.83 |

## Bootstrap Results (Paired, Stratified by query_type, 10,000 resamples, seed 20260904)

### Embedding Only

| Comparison | Mean Diff | CI95 Lower | CI95 Upper | Verdict |
|-----------|-----------|------------|------------|---------|
| NDCG@10 | -0.6185 | -0.6710 | -0.5659 | EMBEDDINGGEMMA_WINS |
| MRR@10 | -0.6475 | -0.6991 | -0.5948 | EMBEDDINGGEMMA_WINS |

### Pipeline (Embedding + Nemotron)

| Comparison | Mean Diff | CI95 Lower | CI95 Upper | Verdict |
|-----------|-----------|------------|------------|---------|
| NDCG@10 | -0.1873 | -0.2461 | -0.1339 | EMBEDDINGGEMMA_WINS |
| MRR@10 | -0.1854 | -0.2436 | -0.1322 | EMBEDDINGGEMMA_WINS |

## Metrics by Query Type

### EmbeddingGemma

| Query Type | NDCG@10 | MRR@10 | Hit@1 | Recall@50 |
|-----------|---------|--------|-------|-----------|
| character_name | 0.1546 | 0.0806 | 0.0000 | 1.0000 |
| context_dependency | 0.4754 | 0.4861 | 0.4333 | 1.0000 |
| emotion_intention | 0.9557 | 0.9400 | 0.8800 | 1.0000 |
| exact_phrase | 0.7823 | 0.7083 | 0.5000 | 1.0000 |
| indirect_dialogue | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| semantic_event | 0.9238 | 0.8994 | 0.8500 | 1.0000 |
| similar_scene | 0.7262 | 0.7000 | 0.6000 | 1.0000 |

### Literary MiniLM

| Query Type | NDCG@10 | MRR@10 | Hit@1 | Recall@50 |
|-----------|---------|--------|-------|-----------|
| character_name | 0.2932 | 0.2053 | 0.1333 | 1.0000 |
| context_dependency | 0.1873 | 0.1092 | 0.0333 | 0.8000 |
| emotion_intention | 0.0848 | 0.0502 | 0.0000 | 0.9200 |
| exact_phrase | 0.0672 | 0.0292 | 0.0000 | 0.6000 |
| indirect_dialogue | 0.1305 | 0.0955 | 0.0500 | 0.8000 |
| semantic_event | 0.1095 | 0.0624 | 0.0250 | 0.7500 |
| similar_scene | 0.0000 | 0.0000 | 0.0000 | 0.2000 |

## Truncation Analysis

### EmbeddingGemma (max seq length: 2048)

- Document tokens: mean=355.0, p50=354.0, p95=372.0, max=388.0
- Over limit: 0 (0.0%)
- Query tokens: mean=36.4, p50=37.0, p95=45.0, max=47.0

### Literary MiniLM (max seq length: 128)

- Document tokens: mean=362.2, p50=362.0, p95=378.0, max=391.0
- Over limit: 600 (100.0%)
- Query tokens: mean=30.2, p50=31.5, p95=39.5, max=44.0

## Verdict Summary

### Pipeline Quality (Primary Decision)
- **Winner (NDCG@10)**: EMBEDDINGGEMMA_WINS (CI95: [-0.2461, -0.1339])
- **Winner (MRR@10)**: EMBEDDINGGEMMA_WINS (CI95: [-0.2436, -0.1322])

### Embedding Quality (Secondary)
- **Winner (NDCG@10)**: EMBEDDINGGEMMA_WINS (CI95: [-0.6710, -0.5659])
- **Winner (MRR@10)**: EMBEDDINGGEMMA_WINS (CI95: [-0.6991, -0.5948])

## Decision Priority

1. Pipeline quality with Nemotron (primary)
2. Retrieval/Top-50 quality
3. Efficiency

---

*Generated: 2026-09-05 05:47:57 UTC*
*All results: measured=true, projected=false*
