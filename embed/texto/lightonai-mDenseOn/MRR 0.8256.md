# lightonai-mDenseOn — MRR@10 0.8256

**Embedding de texto de produção.**
Benchmark v2 forte: 240 queries (60/domínio), corpus 2000 docs, int8, 768 dims.
VRAM: 1.37 GB | RAM: ~1.08 GB | Disco: 1.2 GB | Vetor: 768 B (int8)

## Top 10 — ranking de texto (240 queries, int8)

| # | Modelo | Dim | MRR@10 |
|---|---|---|---|
| **1** | **lightonai-mDenseOn** | 768 | **0.8256** |
| 2 | pplx-4B | 1024 | 0.8014 |
| 3 | embeddinggemma-300m | 768 | 0.7992 |
| 4 | nemotron-8B | 1024 | 0.7950 |
| 5 | qwen3-4B | 1024 | 0.7915 |
| 6 | jina-v5-omni-small | 1024 | 0.7580 |
| 7 | nemotron-1B-Q4 | 1024 | 0.7054 |
| 8 | nemotron-1B-NVFP4 | 1024 | 0.7056 |
| 9 | bekko-a25m | 384 | 0.6854 |
| 10 | LFM2.5-350M | 1024 | 0.7481* |

*LFM2.5 ficaria em 9º (0.7481); a lista reflete ordem real do ranking.

## Quem ganhou de quem

- **Venceu todos os 16 modelos testados** (líder absoluto de texto).
- Com reranker llama-nemotron-rerank-1b-v2: **0.9257** (melhor pipeline de texto).
- Com reranker qwen3-reranker-06: 0.8970.

## Notas

- Modelo da família LightOn (late-interaction foi o mLateOn, 11º — este DenseOn é o denso).
- 768 dims, treinado para retrieval — supera modelos 4B (pplx, qwen3, nemotron-8B) com fração do custo.
- Validação externa: família LightOn aparece bem em leaderboards de eficiência; ranking local confirma.
