# Benchmark de Rerankers: jina-reranker-v3.5 vs llama-nemotron-rerank-1b-v2 vs qwen3-reranker-06

## 1. Identificação Técnica do jina-reranker-v3.5

- **Repositório Hugging Face**: `jinaai/jina-reranker-v3.5`
- **Arquitetura**: `JinaForRanking` (Qwen3-0.6B backbone, 28 camadas com atenção híbrida 3L2G + MLP projector 1024→512→512)
- **Tipo de Inferência**: **Listwise nativo** (`model.rerank(query, documents)` via causal self-attention e similaridade de cosseno)
- **Parâmetros**: 596.836.352 (~0.6B)
- **Dtype**: `bfloat16` / `auto`
- **Protocolo**: 8 conjuntos canônicos de embeddings × 150 queries × 50 candidatos = **60.000 pares query-documento** avaliados.
- **Hardware**: NVIDIA GeForce RTX 5060 Ti 16 GB (CUDA 13.3, PyTorch 2.11+cu128, Transformers 5.14.1)

## 2. Tabela Comparativa Consolidada nos 8 Embeddings (MRR@10)

| # | Embedding Base | Base Puro | Qwen3-0.6B | Nemotron 1B v2 | **Jina v3.5** | Δ vs Base | Δ vs Nemotron | Δ vs Qwen3 | Vencedor |
|---|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | **lightonai-mDenseOn** | 0.6324 | 0.8001 | 0.8138 | **0.8043** | +0.1719 | -0.0095 | +0.0042 | Nemotron |
| 2 | **embeddinggemma-300m** | 0.7072 | 0.8197 | 0.8227 | **0.8135** | +0.1063 | -0.0092 | -0.0062 | Nemotron |
| 3 | **nemotron-8B (Abiray 1024)** | 0.7459 | 0.8192 | 0.8232 | **0.7885** | +0.0426 | -0.0347 | -0.0307 | Nemotron |
| 4 | **pplx-embed-v1-4b (Q8_0)** | 0.7562 | 0.8221 | 0.8233 | **0.8122** | +0.0560 | -0.0111 | -0.0098 | Nemotron |
| 5 | **qwen3-embedding-4b (Q8_0)** | 0.7010 | 0.8243 | 0.8245 | **0.8100** | +0.1089 | -0.0146 | -0.0143 | Nemotron |
| 6 | **jina-embeddings-v5-small** | 0.6742 | 0.8216 | 0.8234 | **0.8097** | +0.1355 | -0.0137 | -0.0119 | Nemotron |
| 7 | **nemotron-1B (Q4_K_M)** | 0.7695 | 0.8174 | 0.8227 | **0.8136** | +0.0441 | -0.0090 | -0.0038 | Nemotron |
| 8 | **colibri_ptbr / bekko (Dense PT-BR)** | 0.7036 | 0.8198 | 0.8233 | **0.8179** | +0.1143 | -0.0055 | -0.0020 | Nemotron |
| — | **MÉDIA GERAL (8 Embeddings)** | **0.7113** | **0.8180** | **0.8221** | **0.8087** | **+0.0974** | **-0.0134** | **-0.0093** | **Nemotron** |

## 3. Confrontos Diretos (Head-to-Head)

- **Jina v3.5 vs Nemotron 1B v2**: Jina venceu **0 de 8** confrontos (0.0%).
- **Jina v3.5 vs Qwen3-0.6B**: Jina venceu **1 de 8** confrontos (12.5%).
- **Diferença Média Absoluta vs Nemotron**: **-0.0134** (-1.63%).
- **Diferença com `lightonai-mDenseOn`**: Jina atingiu **0.8043** vs **0.8138** do Nemotron (-0.0095).

## 4. Eficiência: Qualidade × VRAM × Latência

| Modelo | Dim / Params | Backend / Pipeline | MRR Médio | VRAM de Pico | RAM | Latência p50 (lista 50 docs) | Tempo Total (150 queries) |
|---|:---:|---|---:|---:|---:|---:|---:|
| **Jina Reranker v3.5** | 0.6B | Transformers (Listwise nativo) | **0.8087** | **5194.64 MiB** (~5.07 GB) | 2480.59 MiB | 5.873 s | 880.2 s |
| **Nemotron 1B v2** | 1.0B | Transformers (SequenceClassification) | **0.8221** | **4010.6 MiB** (~3.92 GB) | 2468.2 MiB | 1.502 s | 225.7 s |
| **Qwen3-Reranker-0.6B** | 0.6B | sentence-transformers (CrossEncoder) | **0.8180** | **2409.8 MiB** (~2.35 GB) | 2576.83 MiB | 1.402 s | 210.2 s |

## 5. Esclarecimento Metodológico: Medições Reais (150q) vs Benchmark Histórico (240q)

1. **Painel de 150 Queries (MEDIDO)**:
   - Os scores apresentados nas seções 2, 3 e 4 são **100% MEDIDOS** no dataset `holo_fake_scenes_v3` (150 queries × 50 candidatos em 8 embeddings).
   - Nesse confronto idêntico e direto:
     - **Nemotron 1B v2**: **0.8221** (média 8 embeddings) / **0.8138** (com `mDenseOn`).
     - **Qwen3-0.6B**: **0.8180** (média 8 embeddings) / **0.8001** (com `mDenseOn`).
     - **Jina-Reranker-v3.5**: **0.8087** (média 8 embeddings) / **0.8043** (com `mDenseOn`).
2. **Benchmark Histórico de 240 Queries (NÃO REPRODUZÍVEL)**:
   - O benchmark histórico registrado em documentações anteriores utilizou 2.000 documentos e 240 queries (60/domínio) geradas por scripts locais cujos arquivos intermediários e dataset de queries não foram versionados no repositório Git.
   - Uma auditoria minuciosa no histórico de commits e no disco confirmou que os conjuntos brutos de 240 queries não estão disponíveis para reexecução.
3. **Rejeição de Projeções Sintéticas**:
   - Fórmulas de projeção linear como `Jina_240 = Nemotron_240 + (Jina_150 - Nemotron_150)` (que estimavam 0.8733 ou 0.9162) são **projeções não validadas** e foram formalmente descartadas. Apenas os valores de 150 queries medidos são tratados como evidência canônica.

## 6. Conclusão Final e Recomendação Técnica

### **LÍDER MANTIDO: llama-nemotron-rerank-1b-v2**
1. **Desempenho em Retrieval**: No painel medido de 150 queries, o **Nemotron 1B v2** venceu o Jina v3.5 em **8 de 8 embeddings** (0.8221 vs 0.8087), incluindo no `lightonai-mDenseOn` (0.8138 vs 0.8043).
2. **Eficiência de VRAM e Latência**: O Nemotron consome **3.92 GB** de VRAM e processa cada lista de 50 candidatos em **~1.50s**, enquanto o Jina v3.5 listwise exige **5.07 GB** e **~5.87s** por lista (devido à sequência longa de 22.500 tokens).
3. **Alternativa Leve**: O `qwen3-reranker-06` permanece como a opção leve recomendada (2.35 GB VRAM, 1.40s e superior ao Jina em 7 dos 8 embeddings).
4. **Decisão**: `jina-reranker-v3.5` **NÃO COMPENSA** como substituto no pipeline de busca local.
