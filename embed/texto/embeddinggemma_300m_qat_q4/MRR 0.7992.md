# embeddinggemma-300m-qat-q4 — MRR@10 0.7992

**Embedding de texto de produção (fallback leve).**
Benchmark v2 forte: 240 queries, corpus 2000 docs, int8, 768 dims.
VRAM: **0.06 GB** | RAM: ~0.15 GB | Disco: 265 MB | Vetor: 768 B (int8)

## Top 10 — ranking de texto (240 queries, int8)

| # | Modelo | Dim | MRR@10 |
|---|---|---|---|
| 1 | lightonai-mDenseOn | 768 | 0.8256 |
| 2 | pplx-4B | 1024 | 0.8014 |
| **3** | **embeddinggemma-300m** | 768 | **0.7992** |
| 4 | nemotron-8B | 1024 | 0.7950 |
| 5 | qwen3-4B | 1024 | 0.7915 |
| 6 | jina-v5-omni-small | 1024 | 0.7580 |
| 7 | nemotron-1B-Q4 | 1024 | 0.7054 |
| 8 | nemotron-1B-NVFP4 | 1024 | 0.7056 |
| 9 | bekko-a25m | 384 | 0.6854 |
| 10 | LFM2.5-350M | 1024 | 0.7481* |

*LFM2.5 ficaria em 9º (0.7481); ordem real do ranking.

## Quem ganhou de quem

- **Venceu: nemotron-8B (4º), qwen3-4B (5º), jina-omni-small (6º), nemotron-1B (7º), bekko (9º), nomic (16º)** e todos abaixo.
- **Perdeu apenas para: mDenseOn (0.8256) e pplx-4B (0.8014)** — por margem de 0.002-0.026.
- Com reranker llama-nemotron: **0.9221** — só 0.0036 atrás do mDenseOn+reranker (0.9257), com 23× menos VRAM.

## Notas

- **Melhor custo-benefício da stack inteira**: 0.06 GB VRAM, 265 MB disco, 0.7992.
- QAT Q4_0 (Google EmbeddingGemma 300M quantizado) — praticamente grátis de rodar.
- Perde só 0.0036 MRR final (com reranker) para o líder mDenseOn — escolha ideal para produção leve ou batch grande.
