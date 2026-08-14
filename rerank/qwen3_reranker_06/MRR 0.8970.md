# qwen3-reranker-06 — MRR@10 0.8970 (com mDenseOn)

**Reranker alternativo leve.**
Benchmark rerankers: top-8 embeddings × 240 queries.
VRAM: **1.11 GB** | RAM: 1.12 GB | Disco: 1.2 GB | Tamanho: 0.6B params
Pipeline: CrossEncoder (sentence-transformers)

## Ranking de rerankers (MRR médio sobre top-8 embeddings, 240 queries)

| # | Reranker | MRR médio | Δ vs embedding puro |
|---|---|---|---|
| 1 | llama-nemotron-rerank-1b-v2 | 0.8867 | +0.1166 |
| **2** | **qwen3-reranker-06** | **0.8563** | **+0.0856** |
| 3 | mxbai-rerank-base-v2 | 0.8575 (120q) | +0.0152 |
| 4 | lamar-600m | 0.8205 (120q) | -0.0219 |
| 5 | ettin-reranker-150m | 0.7453 (120q) | -0.0970 |
| 6 | ettin-reranker-68m | 0.6594 (120q) | -0.1830 |

## Quem ganhou de quem

- **Venceu: mxbai, lamar, ettin×2** (e o embedding puro em todos os 8).
- **Perdeu para: llama-nemotron-rerank-1b-v2** — em todos os 8 embeddings, por +0.0304 médio.

## Notas

- Mantido como **opção leve**: 1.11 GB VRAM vs 2.30 GB do llama-nemotron.
- Se um dia rodar em hardware menor (GPU ≤8 GB), este é o reranker viável — ainda ganha +0.0856 sobre o embedding puro.
- Nos 16 GB atuais, o llama-nemotron é a escolha (melhor qualidade, cabe folgado).
- Único reranker que melhora todos os embeddings junto com o llama-nemotron (os outros 4 degradam).
