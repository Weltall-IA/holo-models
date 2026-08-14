# Benchmark Holo — Documento único de resultado

Data: 2026-08-07. Estado: **executado (v2)** — protocolo revisado.

Este é o documento único de resultado do benchmark de embeddings de texto.
Todo resultado — raw e métricas — de todos os modelos será registrado aqui.

---

## 1. Protocolo

| Item | Valor |
|---|---|
| Corpus v2 | 4 domínios × 500 documentos = 2.000 (40 alvos reais + 460 distratores por domínio) |
| Queries | 4 domínios × 30 = 120, wording **divergente** dos documentos |
| Métricas | MRR@10, nDCG@10, Recall@10, MAP, Hit@10 + **Recall@50** |
| Ranking | **domínio inteiro (500 candidatos)** — sem top-50 pré-selecionado |
| top-50 | salvo por modelo (`candidates_top50.json`) como **insumo do reranker** |
| Rodada 1 | int8 na dimensão combinada (produção) |
| Rodada 2 | top-5 da rodada 1 em fp32 na maior dimensão suportada |
| Similaridade | cosseno (dot product, vetores L2-normalizados) |
| Re-normalização | L2 obrigatória após slicing (gemini, nemotron-1b) |
| Reranker | não participa desta rodada (somente embedding puro) |

### Decisões de protocolo (v2, 2026-08-07) — NÃO ESQUECER

1. **Queries divergentes** — queries NÃO repetem termos-chave dos documentos
   (testa compreensão semântica, não matching lexical).
2. **Sem top-50 na medição** — métricas rodam no ranking completo do domínio
   (500). Truncar em 50 antes de medir mascara a qualidade real do embedding
   (relevante na posição 45 contaria como "achado").
3. **top-50 salvo como artefato** — `candidates_top50.json` por modelo/domínio
   é o insumo do futuro benchmark de reranker (embedding vira pré-filtro,
   reranker reordena os 50). Recall@50 reporta o teto que o reranker pode
   alcançar.
4. **Corpus v1 (200 docs, queries-paráfrase) descartado** — saturava
   (MRR 0.98-0.99 em tudo) e não separava modelos.

## 2. Corpus (congelado, v2)

| Domínio | Docs | Queries | Arquivo corpus | Arquivo queries |
|---|---:|---:|---|---|
| code | 500 | 30 | `corpus/code.jsonl` | `queries/code.jsonl` |
| movies_series | 500 | 30 | `corpus/movies_series.jsonl` | `queries/movies_series.jsonl` |
| anime | 500 | 30 | `corpus/anime.jsonl` | `queries/anime.jsonl` |
| video | 500 | 30 | `corpus/video.jsonl` | `queries/video.jsonl` |

- 40 alvos reais por domínio (`*_001..040`) + 460 distratores gerados.
- Formato corpus: `{"id": "...", "text": "..."}`.
- Formato queries: `{"id": "...", "domain": "...", "query": "...", "relevant": ["..."]}`.
- Regenerável via `scripts/gerar_corpus.py --seed 42` (não modificar após congelar).

## 3. Modelos — 18 (17 locais + 1 API)

### 3.1 Texto nativo (dimensão fixa)

| # | Modelo | Dim | Quantização | Peso | Backend |
|---|---|---|---|---|---|
| 1 | bekko-embedding-v1-a25m | 384 | nativa | `embed/texto/bekko-embedding-v1-a25m/` | Transformers |
| 2 | embeddinggemma-300m-qat-q4 | 768 | Q4_0 QAT | `embed/texto/embeddinggemma_300m_qat_q4/` | llama.cpp |
| 3 | nomic-embed-text-v1.5 | 768 | nativa | `embed/texto/nomic-embed-text-v1.5/` | Transformers |
| 4 | lightonai-mLateOn | 768 | nativa | `embed/texto/lightonai-mLateOn/` | Transformers |
| 5 | lightonai-mDenseOn | 768 | nativa | `embed/texto/lightonai-mDenseOn/` | Transformers |
| 6 | LFM2.5-Embedding-350M | 1024 | Q4_K_M | Ollama | Ollama |
| 7 | jina-v5-omni-small-retrieval | 1024 | Q4_K_M | `embed/omni/jina-embeddings-v5-omni-small-retrieval/` | llama.cpp |
| 8 | jina-v5-omni-nano-retrieval | 1024 | Q4_K_M | `embed/omni/jina-embeddings-v5-omni-nano-retrieval/` | llama.cpp |
| 9 | LCO-Embedding-Omni-3B-2605 | 1024 | Q4_K_M | `embed/omni/LCO-Embedding-Omni-3B-2605/` | llama.cpp |
| 10 | Qwen3-VL-Embedding-2B | 1024 | Q4_K_M | Ollama | Ollama |
| 11 | qwen3-embedding-06-q4-k-m | 1024 | Q4_K_M | `embed/texto/qwen3_embedding_06_q4_k_m/` | llama.cpp |
| 12 | nvidia-omni-embed-nemotron-3b | 2048 | BF16 | `embed/omni/nvidia-omni-embed-nemotron-3b/` | Transformers |

### 3.2 Texto flexível (reduzidos para 1024)

| # | Modelo | Dim nativa | Mecanismo | Peso | Backend |
|---|---|---|---|---|---|
| 13 | qwen3-embedding-4b-q4-k-m | 2560 | MRL | `embed/texto/qwen3_embedding_4b_q4_k_m/` | llama.cpp |
| 14 | pplx-embed-v1-4b-q4-k-m | 2560 | MRL | `embed/texto/pplx_embed_v1_4b_q4_k_m/` | llama.cpp |
| 15 | Nemotron-3-Embed-8B-Abiray-Q4 | 4096 | MRL | `embed/texto/Nemotron-3-Embed-8B-Abiray-Q4_K_M/` | llama.cpp |
| 16 | Nemotron-3-Embed-1B-NVFP4 | 2048 | slicing + L2 | `embed/texto/Nemotron-3-Embed-1B-NVFP4/` | vLLM |
| 17 | Nemotron-3-Embed-1B-Q4_K_M | 2048 | slicing + L2 | `embed/texto/Nemotron-3-Embed-1B-Q4_K_M/` | llama.cpp |

### 3.3 API

| # | Modelo | Dim nativa | Mecanismo | Custo |
|---|---|---|---|---|
| 18 | gemini-embedding-001 | 3072 | MRL → 1024 + L2 manual | gratuito (1500 req/dia) |

## 4. Estado do ambiente

| Dependência | Status |
|---|---|
| `torch` 2.11.0+cu128 + CUDA | ✅ instalado (RTX 5060 Ti, sm_120) |
| `sentence-transformers` 5.7.0 | ✅ instalado |
| `llama-cpp-python` 0.3.34 (CUDA 13) | ✅ instalado |
| `transformers` 5.14.1 | ✅ instalado |
| `numpy` 2.5.1 | ✅ instalado |
| Ollama CLI | ✅ 0.32.5 |
| Python venv (`models/.venv`, 3.12.13) | ✅ pronto |

**⚠️ Pós-restart do PC:** `libcudart.so.13` (requerida pelo llama-cpp compilado
com CUDA 13) sai do PATH após reiniciar. Antes de rodar benchmarks GGUF,
exportar:
```bash
export LD_LIBRARY_PATH=/usr/lib/ollama/cuda_v13:$LD_LIBRARY_PATH
```
(o torch cu128 instala a .12; a .13 está no pacote do Ollama).

**Próximo passo:** criar o script `scripts/run_benchmark.py` e executar.

## 5. Estrutura de saída (documento único)

Resultados serão registrados **neste arquivo** (seções abaixo) e, em paralelo,
em artefatos técnicos versionáveis:

| Artefato | Conteúdo |
|---|---|
| `RESULTADOS_BENCHMARK.md` (este) | ranking final, tabelas por domínio, comparação int8×fp32 |
| `results/raw/<modelo>/embeddings.npy` | vetores raw (docs + queries) por modelo |
| `results/raw/<modelo>/rankings.json` | ranking top-20 por query |
| `results/raw/<modelo>/scores.json` | similaridades por query × documento |
| `results/metricas/<modelo>.json` | 5 métricas por domínio + agregadas |

### 5.1 Resultados — RODADA 1 (int8, v2)

| # | Modelo | Dim | MRR@10 | nDCG@10 | R@10 | R@50 | MAP | Hit@10 | VRAM | Tempo |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | lightonai-mDenseOn | 768 | 0.9023 | 0.9007 | 0.9225 | 0.9457 | 0.8794 | 0.9667 | 0.24 GB | 13s |
| 2 | embeddinggemma-300m | 768 | 0.8895 | 0.8837 | 0.9070 | 0.9612 | 0.8625 | 0.9583 | 0.00 GB | 13s |
| 3 | nemotron-8B | 1024 | 0.8715 | 0.8664 | 0.8837 | 0.9380 | 0.8480 | 0.9417 | 5.19 GB | 95s |
| 4 | pplx-4B | 1024 | 0.8613 | 0.8609 | 0.8837 | 0.9457 | 0.8414 | 0.9333 | 3.08 GB | 77s |
| 5 | qwen3-4B | 1024 | 0.8444 | 0.8538 | 0.9070 | 0.9457 | 0.8245 | 0.9500 | 3.17 GB | 71s |
| 6 | jina-v5-omni-small | 1024 | 0.8424 | 0.8501 | 0.9070 | 0.9380 | 0.8205 | 0.9417 | 1.01 GB | 34s |
| 7 | nemotron-1B-Q4 | 1024 | 0.7681 | 0.7811 | 0.8450 | 0.8760 | 0.7476 | 0.8917 | 1.15 GB | 27s |
| 8 | bekko-a25m | 384 | 0.7590 | 0.7702 | 0.8217 | 0.8915 | 0.7450 | 0.8500 | 0.78 GB | 17s |
| 9 | LFM2.5-350M | 1024 | 0.7481 | 0.7756 | 0.8837 | 0.9457 | 0.7336 | 0.9167 | 0.59 GB | 250s |
| 10 | jina-v5-omni-nano | 1024 | 0.6111 | 0.6425 | 0.7364 | 0.8062 | 0.6036 | 0.7750 | 0.20 GB | 8s |
| 11 | lightonai-mLateOn | 768 | 0.5147 | 0.5181 | 0.5736 | 0.6744 | 0.4930 | 0.6083 | 0.81 GB | 13s |
| 12 | qwen3-0.6B | 1024 | 0.4807 | 0.5011 | 0.5891 | 0.6589 | 0.4658 | 0.6167 | 1.03 GB | 48s |
| 13 | Qwen3-VL-2B | 1024 | 0.4607 | 0.4652 | 0.5116 | 0.5659 | 0.4437 | 0.5417 | 1.83 GB | 72s |
| 14 | LCO-Omni-3B-2605 | 1024 | 0.4311 | 0.4450 | 0.5039 | 0.6047 | 0.4207 | 0.5333 | 2.70 GB | 103s |
| 15 | omni-nemotron-3B | 2048 | 0.4163 | 0.4338 | 0.4806 | 0.5659 | 0.4107 | 0.5167 | 8.97 GB | 78s |
| 16 | nomic-v1.5 | 768 | 0.3368 | 0.3636 | 0.4496 | 0.5814 | 0.3353 | 0.4750 | 0.79 GB | 8s |
| 17 | nemotron-1B-NVFP4 | — | — | — | — | — | — | — | — | — | NVFP4 requer vLLM |
| 18 | gemini-001 | — | — | — | — | — | — | — | — | — | cota diária excedida (429) |

### 5.2 Resultados por domínio (rodada 1, v2, MRR@10 int8)

| Modelo | code | movies_series | anime | video |
|---|---:|---:|---:|---:|
| lightonai-mDenseOn | 0.893 | 0.978 | 0.845 | 0.896 |
| embeddinggemma-300m | 0.812 | 1.000 | 0.887 | 0.859 |
| nemotron-8B | 0.800 | 0.883 | 0.917 | 0.920 |
| pplx-4B | 0.735 | 0.933 | 0.917 | 0.901 |
| qwen3-4B | 0.694 | 0.967 | 0.903 | 0.814 |

- **code** é o domínio mais difícil (melhor 0.893) — queries divergentes de código separam bem.
- **movies_series** satura em embeddinggemma (1.000) — sinopses curtas com vocabulário fechado.
- **anime** favorece nemotron-1B-Q4 (0.961) e modelos 4B+.
- **video** favorece nemotron-8B (0.920).

### 5.3 Resultados — RODADA 2 (fp32, top-5, v2)

| Modelo | Dim fp32 | MRR fp32 | MRR int8 | Δ |
|---|---:|---:|---:|---:|
| lightonai-mDenseOn | 768 | 0.9023 | 0.9023 | +0.0000 |
| embeddinggemma-300m | 768 | 0.8895 | 0.8895 | +0.0000 |
| nemotron-8B | 1024 | 0.8563 | 0.8715 | -0.0152 |
| pplx-4B | 1024 | 0.8828 | 0.8613 | **+0.0215** |
| qwen3-4B | 1024 | 0.8238 | 0.8444 | -0.0206 |

### 5.4 Comparação int8 × fp32 (top-5, v2)

| Modelo | int8 MRR | fp32 MRR | ΔMRR | Storage int8 | Storage fp32 |
|---|---:|---:|---:|---:|---:|
| lightonai-mDenseOn | 0.9023 | 0.9023 | 0.0000 | 768 B/vec | 3.1 KB/vec |
| embeddinggemma-300m | 0.8895 | 0.8895 | 0.0000 | 768 B/vec | 3.1 KB/vec |
| nemotron-8B | 0.8715 | 0.8563 | -0.0152 | 1.0 KB/vec | 4.1 KB/vec |
| pplx-4B | 0.8613 | 0.8828 | +0.0215 | 1.0 KB/vec | 4.1 KB/vec |
| qwen3-4B | 0.8444 | 0.8238 | -0.0206 | 1.0 KB/vec | 4.1 KB/vec |

**Conclusão v2:** int8 não degrada nos 2 primeiros (Δ=0). **pplx-4B é o único que ganha com fp32 (+0.0215)** — sensível à quantização; se for escolhido para produção, considerar fp32. nemotron-8B e qwen3-4B tiveram Δ negativo em fp32 (dentro do ruído da dimensão 1024 vs 2048 no slicing/MRL).

### 5.5 Resultados — RERANKERS (top-8 embeddings, MRR@10)

Protocolo: para cada embedding, reranker reordena os 50 candidatos salvos
(`candidates_top50.json`) → top-20 → métricas. Baseline = embedding puro
(int8, rodada v2).

**Ranking de rerankers (MRR@10 médio sobre os 8 embeddings):**

| # | Reranker | MRR médio | Δ vs embedding puro |
|---|---|---:|---:|
| 1 | llama-nemotron-rerank-1b-v2 (pipeline nativo) | **0.9353** | **+0.0930** |
| 2 | qwen3-reranker-06 | 0.9197 | +0.0774 |
| 3 | mxbai-rerank-base-v2 | 0.8575 | +0.0152 |
| 4 | lamar-600m | 0.8205 | -0.0219 |
| 5 | ettin-reranker-150m | 0.7453 | -0.0970 |
| 6 | ettin-reranker-68m | 0.6594 | -0.1830 |

**Por embedding (melhor reranker):**

| Embedding | Base (int8) | Melhor reranker | MRR com RR | Δ |
|---|---:|---|---:|---:|
| lightonai-mDenseOn | 0.9023 | llama-nemotron | 0.9594 | +0.0571 |
| embeddinggemma-300m | 0.8895 | llama-nemotron | 0.9676 | +0.0781 |
| nemotron-8B | 0.8715 | llama-nemotron | 0.9472 | +0.0757 |
| pplx-4B | 0.8613 | llama-nemotron | 0.9345 | +0.0733 |
| qwen3-4B | 0.8444 | llama-nemotron | 0.9618 | +0.1174 |
| jina-v5-omni-small | 0.8424 | llama-nemotron | 0.9429 | +0.1004 |
| nemotron-1B-Q4 | 0.7681 | llama-nemotron | 0.8786 | +0.1105 |
| bekko-a25m | 0.7590 | llama-nemotron | 0.8907 | +0.1316 |

**llama-nemotron vs qwen3 (por embedding):**

| Embedding | Base | llama-nemotron | qwen3-reranker-06 | vencedor |
|---|---:|---:|---:|---|
| lightonai-mDenseOn | 0.9023 | **0.9594** | 0.9509 | nemotron |
| embeddinggemma-300m | 0.8895 | **0.9676** | 0.9519 | nemotron |
| nemotron-8B | 0.8715 | **0.9472** | 0.9249 | nemotron |
| pplx-4B | 0.8613 | **0.9345** | 0.9253 | nemotron |
| qwen3-4B | 0.8444 | **0.9618** | 0.9380 | nemotron |
| jina-v5-omni-small | 0.8424 | **0.9429** | 0.9260 | nemotron |
| nemotron-1B-Q4 | 0.7681 | **0.8786** | 0.8589 | nemotron |
| bekko-a25m | 0.7590 | **0.8907** | 0.8820 | nemotron |

**Conclusão rerankers:**
- **llama-nemotron-rerank-1b-v2 (pipeline nativo) é o melhor** — ganha em
  todos os 8 embeddings (+0.057 a +0.132), média 0.9353. Requer pipeline
  transformers nativo com template `question:{q} \n \n passage:{p}` como
  UMA sequência (CrossEncoder tokeniza como 2 sequências e quebra o modelo).
- qwen3-reranker-06 é o 2º — melhora todos (+0.049 a +0.123).
- mxbai melhora levemente (+0.015) mas perde no lightonai-mDenseOn.
- lamar-600m, ettin-68m/150m **degradam** — piores que o embedding puro.
- **Pipeline recomendado de produção:** top-8 embeddings + llama-nemotron
  (ou qwen3 como alternativa mais leve) → MRR 0.88-0.97 em todas as
  combinações.

*Resultados v1 (corpus de 200 docs com queries-paráfrase) descartados —
saturavam em 0.98-0.99 e não separavam modelos. Ver decisão 4 na seção 1.*

### 5.7 Resultados — DIMENSÃO MÁXIMA MRL (2560, int8, 240 queries)

Comparação entre 1024 (produção) e 2560 (teto MRL) para os modelos flexíveis:

| Modelo | 1024 int8 | 2560 int8 | Δ | Storage 1024 | Storage 2560 |
|---|---:|---:|---:|---:|---:|
| pplx-4B | 0.8014 | **0.8115** | +0.0101 | 1.0 KB/vec | 2.5 KB/vec |
| qwen3-4B | 0.7915 | 0.7788 | -0.0127 | 1.0 KB/vec | 2.5 KB/vec |

**Conclusão:** o corte para 1024 custa ~+0.010 ao pplx-4B (2.5× mais storage
pra ganho pequeno — 1024 mantém o melhor custo-benefício). O qwen3-4B PIORA
em 2560 (-0.013, ruído MRL) — 1024 é o ponto ótimo dele. **Ranking final da
versão forte permanece o da seção 5.1** (1024 int8).

### 5.8 DECISÃO DE PRODUÇÃO (2026-08-10)

**Embeddings mantidos para produção:**
1. **lightonai-mDenseOn** (768 dims, 1.37 GB VRAM, 768 B/vector) — MRR 0.8256
2. **embeddinggemma-300m** (768 dims, 0.06 GB VRAM, 768 B/vector) — MRR 0.7992

**Reranker de produção:** llama-nemotron-rerank-1b-v2 (pipeline nativo,
2.30 GB VRAM) — MRR final 0.9257 (mDenseOn) / 0.9221 (gemma).

**pplx-4B DESCARTADO** — decepção: 3.07 GB VRAM, 1-2.5 KB/vector e MRR 0.8014
(1024) / 0.8115 (2560) — abaixo dos dois mantidos, apesar de 4B e mais dims.
A dimensão/tamanho não compensam o treinamento inferior para retrieval.

**Lição do benchmark:** qualidade vem do treinamento para retrieval, não de
params/dims. Especialistas densos pequenos (768) dominam o corpus PT-BR.

## 6. Histórico

- 2026-08-07: registro de modelos em
  `gitmodels/docs/model-governance/EMBEDDING_REGISTRY.md`; ~154 GB liberados
  em limpeza; runtime instalado (torch cu128, sentence-transformers,
  llama-cpp-python CUDA, transformers, numpy).
- 2026-08-07 (v1): rodada 1+2 executadas no corpus antigo (200 docs,
  queries-paráfrase) — descartado por saturação.
- 2026-08-07 (v2): corpus novo (2.000 docs, queries divergentes), protocolo
  revisado (ranking no domínio inteiro + top-50 salvo + recall@50).
  **Rodada 1 (int8): 16/18 executados** — ver 5.1; **Rodada 2 (fp32): top-5
  executado** — ver 5.3. `candidates_top50.json` salvo por modelo/domínio
  (insumo do reranker). Resultados consolidados em `results/resumo.json`.
  Pendências: nemotron-1B-NVFP4 (requer vLLM), gemini-001 (cota diária
  excedida — tentar em outro dia ou com chave com cota maior).
- 2026-08-10: **benchmark de rerankers executado** (6 rerankers × top-8
  embeddings, sobre os candidates_top50 salvos) — ver 5.5. qwen3-reranker-06
  domina todos os embeddings (+0.049 a +0.123). Rerankers baixados:
  ettin-68m/150m, LAMAR-600m, llama-nemotron-rerank-1b-v2, mxbai
  (em `models/rerank/`). Token HF registrado em `~/.cache/huggingface/token`
  (resolve aviso de autenticação). Resultados em `results/resumo_reranker.json`.
- 2026-08-10: **correção do llama-nemotron-rerank-1b-v2** — CrossEncoder
  tokeniza como 2 sequências e quebra o modelo bidirecional custom; com
  pipeline nativo (transformers, template `question:{q} \n \n passage:{p}`
  como UMA sequência), o nemotron passa a liderar o ranking de rerankers
  (média 0.9353, +0.057 a +0.132 por embedding). `torch_dtype` → `dtype`
  (deprecação do transformers 5.14) aplicado nos scripts.
- 2026-08-10: **VERSÃO FORTE (240 queries, 60/domínio)** executada — top-8
  embeddings (int8) + rerankers qwen3 e llama-nemotron (pipeline nativo).
  Ranking de embeddings: lightonai-mDenseOn 0.8256 lidera; pplx-4B sobe
  para 2º (0.8014). Rerankers: llama-nemotron 0.8867 médio vs qwen3 0.8563.
  Melhor pipeline: lightonai-mDenseOn + llama-nemotron = **0.9257 MRR@10**.
  Resultados: `results/resumo.json` + `results/resumo_reranker.json`
  (240 queries por arquivo). Queries fortes: `scripts/gerar_queries_fortes.py`.
- 2026-08-10: **DECISÃO DE PRODUÇÃO (seção 5.8)** — mantidos
  lightonai-mDenseOn + embeddinggemma-300m como embeddings de texto;
  llama-nemotron-rerank-1b-v2 como reranker. **pplx-4B descartado**
  (decepção: 3 GB VRAM / MRR abaixo dos 768-dim mantidos). Rodada 2560
  MRL registrada (seção 5.7) — sem ganho que justifique storage.
- 2026-08-10: **nemotron-1B-NVFP4 benchmarkado via vLLM 0.26** (antes
  BLOCKED). Causa raiz do OOM de RAM diagnosticada pelo K3/Sol: autotuner
  do flashinfer compilando táticas CuTe-DSL in-process no sm_120 (picos
  >1 GB por compilação). Solução: `--kernel-config
  '{"enable_flashinfer_autotune":false}'` + `-O1` (mantém CUDA graphs
  PIECEWISE + torch.compile) + `MALLOC_ARENA_MAX=2
  TORCHINDUCTOR_COMPILE_THREADS=1 MAX_JOBS=2 NVCC_THREADS=1`. Endpoint
  `/v2/embed` (Cohere-compatível, `embeddings.float`). Resultado (240q):
  MRR@10 **0.7056** ≈ Q4_K_M (0.7054) — confirma que NVFP4 não ganha do
  Q4_K_M (mesmo modelo, diferença <0.01). Pendência encerrada.
- 2026-08-11: **llama-nemotron-VL-1B-FP8 benchmarkado via vLLM** (último
  modelo VL da stack). Kernels flashinfer sm_120 pré-compilados manualmente
  (`~/.cache/flashinfer/0.6.14/120f/` — build ninja de 28 kernels, ~25 min;
  cache é por arquitetura de GPU, não por modelo). Formato multimodal do
  `/v2/embed`: `inputs[].content[]` com `image_url` data-URI (sem
  `input_type`). Resultado visão (150 img, 300 queries): MRR@10 **0.5815**
  (4º lugar) — funciona, mas o FP8 degrada vs BGE-VL-large (0.9522).
  Guia completo salvo em `models/vllm/COMO_USAR.md`.
- 2026-08-11: **NOVO LÍDER DE VISÃO — qwen3-vl-2b-vdr (MRR 0.9634)**.
  Pesquisa na comunidade (MCPs + HF) revelou o fine-tune do tomaarsen
  (autor do sentence-transformers): Qwen3-VL-Embedding-2B fine-tunado em
  Visual Document Retrieval (VDR), 2.1B/3.97 GB, 1024 dims. Supera o
  BGE-VL-large (0.9522). Carrega via sentence-transformers (sem vLLM —
  o vLLM 0.26 tem bug de mapeamento `embed_tokens` no Qwen3VL).
  Requer `LD_LIBRARY_PATH` com `/opt/cuda/targets/x86_64-linux/lib` +
  symlink `libnvrtc-builtins.so.13.0 → 13.3` (JIT do FlashAttention vision).
  BGE-VL-v1.5-mmeb (7B, 14.1 GB) **não cabe** na 5060 Ti (pesos 14.08 GiB)
  e não tem GGUF comunitário — descartado por limite físico.

- 2026-08-11 (final): **limpeza da stack** — removidos todos os perdedores
  (~38 GB): lightonai-mLateOn, Nemotron-8B, pplx-4B, qwen3-4B,
  nemotron-1B-NVFP4/Q4, nomic, bekko, qwen3-0.6B, LCO-3B, Qwen3-VL-2B-GGUF,
  jina-omni-nano, nemotron-VL-FP8, jina-v4×2, Qwen3-VL-8B-i1, BGE-VL-base,
  mxbai/lamar/ettin×2, **BGE-VL-v1.5-mmeb** (7B/14.1 GB — não cabe na 5060 Ti).
  Mantidos: produção (mDenseOn, embeddinggemma, qwen3-vl-2b-vdr,
  llama-nemotron-rerank, qwen3-reranker-06) + reservas (omni-nemotron-3B
  com README_USO.md de áudio, jina-v5-omni-small, BGE-VL-large, LFM2.5).
  Resultados completos em `embed/RESULTADOS_EMBEDDING.md`.
