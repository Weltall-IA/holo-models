# jina-reranker-v3.5

## Identificação técnica

- Arquivo / Repositório: `jinaai/jina-reranker-v3.5`
- Parâmetros: 596.836.352 (~0.6B)
- Arquitetura: `JinaForRanking` (Qwen3-0.6B backbone, 28 camadas com atenção híbrida 3L2G + MLP projector 1024→512→512)
- Quantização / Dtype: `bfloat16` / `auto`
- Backend / Pipeline: Transformers Listwise nativo (`model.rerank(query, documents)`)
- Licença: CC-BY-NC-4.0

## Especialidade, pontos fortes e trade-offs

- Reranker listwise multilíngue com suporte nativo a listas de documentos e ranking conjunto via causal self-attention.
- Avaliado no benchmark de rerankers do workspace (top-8 embeddings × 150 queries × 50 candidatos = 60.000 pares).
- **Não superou** o atual líder de produção `llama-nemotron-rerank-1b-v2` em nenhum dos 8 embeddings (perdeu 8 de 8 confrontos).
- **Trade-off desfavorável em inferência local**: O pipeline listwise com 50 documentos gera sequências de ~22.500 tokens, exigindo **5.07 GB de VRAM** e **~5.87s por query** (~4× mais lento que o Nemotron e o Qwen3-0.6B).
- **Decisão no Workspace**: **NÃO_COMPENSA**. `llama-nemotron-rerank-1b-v2` permanece o líder e `qwen3-reranker-06` permanece como opção leve.

## MEDIDO LOCALMENTE

Hardware: NVIDIA GeForce RTX 5060 Ti 16 GB (CUDA 13.3, PyTorch 2.11+cu128).
Data da medição: `2026-09-04`.
Script executor: `tasks/run_jina_reranker_v35_benchmark.py`.
Relatório consolidado: `rerank/jina_reranker_v3_5/MRR_REPORT.md`.

### Resultados por embedding (MRR@10)

| Embedding | Base Puro | Qwen3-0.6B | Nemotron 1B v2 | **Jina v3.5** | Δ vs Base | Δ vs Nemotron | Vencedor |
|---|---:|---:|---:|---:|---:|---:|:---:|
| **lightonai-mDenseOn** | 0.6324 | 0.8001 | 0.8138 | **0.8043** | +0.1719 | -0.0095 | Nemotron |
| **embeddinggemma-300m** | 0.7072 | 0.8197 | 0.8227 | **0.8135** | +0.1063 | -0.0092 | Nemotron |
| **nemotron-8B (Abiray 1024)** | 0.7459 | 0.8192 | 0.8232 | **0.7885** | +0.0426 | -0.0347 | Nemotron |
| **pplx-embed-v1-4b (Q8_0)** | 0.7562 | 0.8221 | 0.8233 | **0.8122** | +0.0560 | -0.0111 | Nemotron |
| **qwen3-embedding-4b (Q8_0)** | 0.7010 | 0.8243 | 0.8245 | **0.8100** | +0.1089 | -0.0146 | Nemotron |
| **jina-embeddings-v5-small** | 0.6742 | 0.8216 | 0.8234 | **0.8097** | +0.1355 | -0.0137 | Nemotron |
| **nemotron-1B (Q4_K_M)** | 0.7695 | 0.8174 | 0.8227 | **0.8136** | +0.0441 | -0.0090 | Nemotron |
| **colibri_ptbr / bekko (Dense PT-BR)** | 0.7036 | 0.8198 | 0.8233 | **0.8179** | +0.1143 | -0.0055 | Nemotron |
| **MÉDIA GERAL** | **0.7113** | **0.8180** | **0.8221** | **0.8087** | **+0.0974** | **-0.0134** | **Nemotron** |

### Telemetria e Recursos

- VRAM de pico: **5,195 MiB** (~5.07 GiB)
- RAM de pico: **2,481 MiB** (~2.42 GiB)
- Latência mediana por lista de 50 docs: **5.87 s**
- Tempo total (150 queries × 50 docs = 7.500 pares): **880.2 s** (~14.7 minutos por embedding)

## DECLARADO PELO AUTOR/ORIGEM

O autor declara nDCG@10 de 63.20 no BEIR e 74.11 no MIRACL em retrieval multilíngue geral. No corpus específico do Holo em português brasileiro, o modelo ficou atrás do Nemotron 1B v2 e do Qwen3-0.6B.
