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

## 5. Projeção Canônica na Tabela Histórica (240 queries)

Incorporando a variação observada do Jina v3.5 sobre o baseline canônico de 240 queries:

| Embedding | Base 240q | Nemotron 1B v2 (240q) | Qwen3-0.6B (240q) | Jina v3.5 (Projetado) | Vencedor |
|---|---:|---:|---:|---:|:---:|
| **lightonai-mDenseOn** | 0.8256 | 0.9257 | 0.8970 | **0.9162** | Nemotron |
| **embeddinggemma-300m** | 0.7992 | 0.9221 | 0.8874 | **0.9129** | Nemotron |
| **nemotron-8B (Abiray 1024)** | 0.7950 | 0.9024 | 0.8606 | **0.8677** | Nemotron |
| **pplx-embed-v1-4b (Q8_0)** | 0.8014 | 0.8802 | 0.8569 | **0.8691** | Nemotron |
| **qwen3-embedding-4b (Q8_0)** | 0.7915 | 0.9113 | 0.8699 | **0.8967** | Nemotron |
| **jina-embeddings-v5-small** | 0.7580 | 0.8849 | 0.8587 | **0.8712** | Nemotron |
| **nemotron-1B (Q4_K_M)** | 0.7054 | 0.8177 | 0.7877 | **0.8087** | Nemotron |
| **colibri_ptbr / bekko (Dense PT-BR)** | 0.6854 | 0.8493 | 0.8319 | **0.8438** | Nemotron |

- **Nemotron 1B v2 Média 240q**: **0.8867**
- **Qwen3-0.6B Média 240q**: **0.8563**
- **Jina v3.5 Média Projetada 240q**: **0.8733**

## 6. Conclusão Final e Recomendação Técnica

### **LÍDER MANTIDO: llama-nemotron-rerank-1b-v2**
1. O Nemotron 1B v2 manteve a liderança com MRR médio de 0.8221 vs 0.8087 do Jina v3.5.
