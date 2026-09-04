# jina-reranker-v3.5 — MRR@10 0.8043 (com mDenseOn, painel 150q)

**Reranker Listwise 0.6B.**
Benchmark de rerankers medido: top-8 embeddings × 150 queries (`holo_fake_scenes_v3`), reordena 50 candidatos → top-20 (60.000 pares query-documento avaliados).
VRAM: **5.07 GB** (5195 MiB) | RAM: 2.42 GB | Tamanho: 0.6B params (596.836.352)
Pipeline: **NATIVO transformers listwise** (`AutoModel.from_pretrained('jinaai/jina-reranker-v3.5')`, causal self-attention conjunta em lista de 50 docs, similaridade de cosseno via MLP projector 1024→512→512).

## Ranking de rerankers no painel medido (150 queries)

| # | Reranker | MRR Médio (Medido 150q) | mDenseOn (Medido 150q) | Δ vs Embedding Puro | VRAM Pico | Latência p50 (50 docs) |
|---|---|---:|---:|---:|---:|---:|
| **1** | **llama-nemotron-rerank-1b-v2** | **0.8221** | **0.8138** | **+0.1108** | 3.92 GB | **1.50 s** |
| 2 | qwen3-reranker-06 | 0.8180 | 0.8001 | +0.1067 | **2.35 GB** | **1.40 s** |
| 3 | **jina-reranker-v3.5** | **0.8087** | **0.8043** | +0.0974 | 5.07 GB | 5.87 s |

## Resultados por embedding (comparativo medido de 150 queries)

| Embedding | Base Puro | llama-nemotron | qwen3-0.6B | **jina-v3.5** | Vencedor |
|---|---:|---:|---:|---:|:---:|
| **lightonai-mDenseOn** | 0.6324 | **0.8138** | 0.8001 | **0.8043** | Nemotron |
| **embeddinggemma-300m** | 0.7072 | **0.8227** | 0.8197 | **0.8135** | Nemotron |
| **nemotron-8B (Abiray 1024)** | 0.7459 | **0.8232** | 0.8192 | **0.7885** | Nemotron |
| **pplx-embed-v1-4b (Q8_0)** | 0.7562 | **0.8233** | 0.8221 | **0.8122** | Nemotron |
| **qwen3-embedding-4b (Q8_0)** | 0.7010 | **0.8245** | 0.8243 | **0.8100** | Nemotron |
| **jina-embeddings-v5-small** | 0.6742 | **0.8234** | 0.8216 | **0.8097** | Nemotron |
| **nemotron-1B (Q4_K_M)** | 0.7695 | **0.8227** | 0.8174 | **0.8136** | Nemotron |
| **colibri_ptbr / bekko (Dense PT-BR)** | 0.7036 | **0.8233** | 0.8198 | **0.8179** | Nemotron |
| **MÉDIA GERAL (8 Embeddings)** | **0.7113** | **0.8221** | **0.8180** | **0.8087** | **Nemotron** |

## Quem ganhou de quem

- **Nemotron 1B v2 venceu Jina v3.5 em 8 de 8 confrontos (100%)**.
- **Qwen3-0.6B venceu Jina v3.5 em 7 de 8 confrontos (87.5%)** (Jina superou o Qwen apenas no mDenseOn: 0.8043 vs 0.8001).
- **Diferença Média vs Nemotron**: -0.0134 (-1.63%).
- **Diferença no mDenseOn vs Nemotron**: -0.0095 (0.8043 vs 0.8138).

## Distinção entre Medições e o Benchmark Histórico de 240 Queries

- **Valores Medidos (Painel 150q)**: Jina v3.5 atingiu **0.8087** na média dos 8 embeddings e **0.8043** com o mDenseOn.
- **Benchmark Histórico de 240q**: O benchmark histórico (2.000 documentos / 4 domínios × 500 docs, 60 queries/domínio), onde o Nemotron atingiu 0.8867 de média e 0.9257 no mDenseOn, teve seus arquivos intermediários e dataset de queries não versionados no repositório; portanto, esse painel histórico específico não é reexecutável.
- **Não-projeção**: Valores calculados por offset linear (ex: 0.8733 ou 0.9162) são **projeções sintéticas não validadas** e foram descartados deste relatório. Apenas os valores efetivamente medidos no painel de 150q são canônicos.

## Avaliação Técnica & Trade-offs (Qualidade × VRAM × Latência)

1. **Critério de Liderança**:
   - O Nemotron 1B v2 superou o Jina v3.5 em todos os 8 embeddings testados no painel de 150 queries.
   - O Jina v3.5 **não superou** o Nemotron no mDenseOn (0.8043 vs 0.8138) e nem na média geral (0.8087 vs 0.8221).
2. **Custo da Arquitetura Listwise em Documentos Longos**:
   - Para reranquear 50 candidatos por query, o pipeline listwise formata uma única sequência de até **22.523 tokens**.
   - Devido à atenção causal quadrática sobre sequências longas, a latência do Jina v3.5 atingiu **~5.87 segundos por query** (contra **1.50s do Nemotron** e **1.40s do Qwen** — cerca de **4× mais lento**).
   - O consumo de VRAM subiu para **5.07 GB** (5195 MiB), superando os 3.92 GB do Nemotron e os 2.35 GB do Qwen.
3. **Conclusão**:
   - **Líder Mantido**: `llama-nemotron-rerank-1b-v2` permanece o **reranker de produção absoluto** da stack (maior qualidade, menor latência e menor VRAM).
   - **Alternativa Leve**: `qwen3-reranker-06` permanece a **alternativa leve recomendada** (2.35 GB VRAM, 1.4s de latência, MRR superior ao Jina em 7 dos 8 embeddings).
   - `jina-reranker-v3.5` **NÃO COMPENSA** como substituto no pipeline de busca local.
