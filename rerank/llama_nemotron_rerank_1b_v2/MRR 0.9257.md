# llama-nemotron-rerank-1b-v2 — MRR@10 0.9257 (com mDenseOn)

**Reranker de produção (LÍDER).**
Benchmark rerankers: top-8 embeddings × 240 queries, reordena 50 candidatos → top-20.
VRAM: 2.30 GB | RAM: 1.05 GB | Disco: 7.0 GB | Tamanho: 1B params
Pipeline: **NATIVO transformers** (template `question:{q} \n \n passage:{p}` como UMA sequência)

## Ranking de rerankers (MRR médio sobre top-8 embeddings, 240 queries)

| # | Reranker | MRR médio | Δ vs embedding puro |
|---|---|---|---|
| **1** | **llama-nemotron-rerank-1b-v2** | **0.8867** | **+0.1166** |
| 2 | qwen3-reranker-06 | 0.8563 | +0.0856 |
| 3 | mxbai-rerank-base-v2 | 0.8575 (120q) | +0.0152 |
| 4 | lamar-600m | 0.8205 (120q) | -0.0219 |
| 5 | ettin-reranker-150m | 0.7453 (120q) | -0.0970 |
| 6 | ettin-reranker-68m | 0.6594 (120q) | -0.1830 |

## Resultados finais por embedding (240 queries)

| Embedding | Base | + llama-nemotron | + qwen3 | vencedor |
|---|---:|---:|---:|---|
| lightonai-mDenseOn | 0.8256 | **0.9257** | 0.8970 | nemotron |
| embeddinggemma-300m | 0.7992 | **0.9221** | 0.8874 | nemotron |
| nemotron-8B | 0.7950 | **0.9024** | 0.8606 | nemotron |
| pplx-4B | 0.8014 | **0.8802** | 0.8569 | nemotron |
| qwen3-4B | 0.7915 | **0.9113** | 0.8699 | nemotron |
| jina-v5-omni-small | 0.7580 | **0.8849** | 0.8587 | nemotron |
| nemotron-1B-Q4 | 0.7054 | **0.8177** | 0.7877 | nemotron |
| bekko-a25m | 0.6854 | **0.8493** | 0.8319 | nemotron |

## Quem ganhou de quem

- **Venceu TODOS os outros rerankers em TODOS os 8 embeddings.**
- Ganho vs qwen3-reranker-06: +0.0304 médio (0.8867 vs 0.8563).
- Ganho vs embedding puro: +0.057 a +0.132 por embedding.

## Notas ⚠️ IMPORTANTE

- **DEVE rodar com pipeline nativo transformers** (`AutoModelForSequenceClassification` + template `question:{q} \n \n passage:{p}` como UMA sequência).
- **CrossEncoder (sentence-transformers) QUEBRA o modelo**: tokeniza como 2 sequências → scores ~0.017 sem separação (0.7252 vs 0.9353 de média).
- Média com pipeline correto: **0.9353** (120q) / **0.8867** (240q).
- Melhor pipeline final da stack: mDenseOn + este reranker = **0.9257 MRR@10**.
