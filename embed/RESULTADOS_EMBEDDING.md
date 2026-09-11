# RESULTADOS DOS TESTES DE EMBEDDING — HISTÓRICO

Este arquivo registra os resultados dos benchmarks de embedding realizados
nesta máquina. Ao testar novos modelos no futuro, consulte aqui os resultados
anteriores antes de decidir o que testar. Última atualização: 2026-08-10.

Resultados detalhados (JSON bruto): `/home/alpha/Playstoria/models/holo-bench/results/`
Documento completo com protocolo: `/home/alpha/Playstoria/models/holo-bench/RESULTADOS_BENCHMARK.md`

---

## DECISÃO DE PRODUÇÃO (2026-08-10)

**Embeddings de texto mantidos:**
| # | Modelo | Dim | VRAM | Vetor int8 | MRR@10 (240q) |
|---|---|---|---|---|---|
| 1 | lightonai-mDenseOn | 768 | 1.37 GB | 768 B | 0.8256 |
| 2 | embeddinggemma-300m | 768 | 0.06 GB | 768 B | 0.7992 |

**Reranker de produção:** llama-nemotron-rerank-1b-v2 (pipeline NATIVO
transformers, template `question:{q} \n \n passage:{p}` como UMA sequência —
CrossEncoder QUEBRA este modelo).
- MRR final: 0.9257 (mDenseOn) / 0.9221 (gemma)

**Descartados:** pplx-4B (decepção: 3 GB VRAM, MRR 0.80), qwen3-4B,
nemotron-8B, jina-omni-small, nemotron-1B, bekko.

---

## RANKING VERSÃO FORTE — 240 queries (60/domínio, int8)

Corpus: 2.000 docs (500/domínio: code, movies_series, anime, video).
Queries com wording divergente. Ranking no domínio inteiro.

| # | Modelo | Dim | MRR@10 | nDCG@10 | R@10 | R@50 | MAP | Hit@10 |
|---|---|---|---|---|---|---|---|---|
| 1 | lightonai-mDenseOn | 768 | 0.8256 | 0.8480 | 0.9317 | 0.9719 | 0.8000 | 0.9542 |
| 2 | pplx-4B | 1024 | 0.8014 | 0.8124 | 0.8594 | 0.9277 | 0.7790 | 0.8833 |
| 3 | embeddinggemma-300m | 768 | 0.7992 | 0.8193 | 0.9036 | 0.9558 | 0.7770 | 0.9292 |
| 4 | nemotron-8B | 1024 | 0.7950 | 0.8084 | 0.8675 | 0.9317 | 0.7730 | 0.8958 |
| 5 | qwen3-4B | 1024 | 0.7915 | 0.8109 | 0.8835 | 0.9438 | 0.7680 | 0.9042 |
| 6 | jina-v5-omni-small | 1024 | 0.7580 | 0.7858 | 0.8916 | 0.9277 | 0.7400 | 0.9083 |
| 7 | nemotron-1B-Q4 | 1024 | 0.7054 | 0.7280 | 0.8112 | 0.8514 | 0.6800 | 0.8333 |
| 8 | bekko-a25m | 384 | 0.6854 | 0.7089 | 0.7912 | 0.8876 | 0.6600 | 0.8042 |
| 9 | **nemotron-1B-NVFP4** (vLLM) | 1024 | 0.7056 | 0.7277 | 0.8153 | 0.8474 | — | 0.8417 |

### Por domínio (240q, MRR@10 int8)
| Modelo | code | movies_series | anime | video |
|---|---:|---:|---:|---:|
| lightonai-mDenseOn | 0.893 | 0.978 | 0.845 | 0.896 |
| pplx-4B | 0.735 | 0.933 | 0.917 | 0.901 |
| embeddinggemma-300m | 0.812 | 1.000 | 0.887 | 0.859 |
| nemotron-8B | 0.800 | 0.883 | 0.917 | 0.920 |
| qwen3-4B | 0.694 | 0.967 | 0.903 | 0.814 |

### Rodada 2 (fp32, top-5, 240q)
| Modelo | Dim fp32 | MRR fp32 | MRR int8 | Δ |
|---|---:|---:|---:|---:|
| lightonai-mDenseOn | 768 | 0.9023 | 0.9023 | +0.0000 |
| embeddinggemma-300m | 768 | 0.8895 | 0.8895 | +0.0000 |
| nemotron-8B | 1024 | 0.8563 | 0.8715 | -0.0152 |
| pplx-4B | 1024 | 0.8828 | 0.8613 | +0.0215 |
| qwen3-4B | 1024 | 0.8238 | 0.8444 | -0.0206 |

### NVFP4 vs Q4_K_M — consumo e velocidade (240q)
| Métrica | NVFP4 (vLLM) | Q4_K_M (llama.cpp) |
|---|---:|---:|
| VRAM pico | 1356 MiB | 1218 MiB |
| RAM do processo | 4.47 GB | 1.11 GB |
| Tempo 2240 requests | 60.2s | 27.0s |
| Throughput | ~37 req/s | ~83 req/s |
| MRR@10 (240q) | 0.7056 | 0.7054 |

Conclusão: NVFP4 = Q4_K_M em qualidade (Δ 0.0002), 2.2× mais lento e 4× mais
RAM (overhead HTTP). Q4_K_M (llama.cpp) é a escolha; vLLM só para servido
concorrente. Guia completo: `models/vllm/COMO_USAR.md`.

### Dimensão máxima MRL (2560, int8)
| Modelo | 1024 int8 | 2560 int8 | Δ | Storage 1024 | Storage 2560 |
|---|---:|---:|---:|---:|---:|
| pplx-4B | 0.8014 | 0.8115 | +0.0101 | 1.0 KB/vec | 2.5 KB/vec |
| qwen3-4B | 0.7915 | 0.7788 | -0.0127 | 1.0 KB/vec | 2.5 KB/vec |

Conclusão: 1024 é o ponto ótimo; 2560 não justifica o dobro de storage.

---

## RANKING DE RERANKERS (top-8 embeddings, 240 queries)

Protocolo: reranker reordena os 50 candidatos salvos → top-20 → métricas.

| # | Reranker | MRR médio | Δ vs embedding puro |
|---|---|---|---|
| 1 | llama-nemotron-rerank-1b-v2 (nativo) | 0.8867 | +0.1166 |
| 2 | qwen3-reranker-06 | 0.8563 | +0.0856 |
| 3 | mxbai-rerank-base-v2 | 0.8575 (120q) | +0.0152 |
| 4 | lamar-600m | 0.8205 (120q) | -0.0219 |
| 5 | ettin-reranker-150m | 0.7453 (120q) | -0.0970 |
| 6 | ettin-reranker-68m | 0.6594 (120q) | -0.1830 |

⚠️ llama-nemotron DEVE rodar com pipeline nativo transformers. CrossEncoder
tokeniza como 2 sequências e quebra o modelo (scores ~0.017, sem separação).
⚠️ ettins/lamar DEGRADAM o embedding puro neste corpus — não usar.

### Por embedding (melhor reranker, versão forte 240q)
| Embedding | Base | llama-nemotron | qwen3 | vencedor |
|---|---:|---:|---:|---|
| lightonai-mDenseOn | 0.8256 | **0.9257** | 0.8970 | nemotron |
| embeddinggemma-300m | 0.7992 | **0.9221** | 0.8874 | nemotron |
| nemotron-8B | 0.7950 | **0.9024** | 0.8606 | nemotron |
| pplx-4B | 0.8014 | **0.8802** | 0.8569 | nemotron |
| qwen3-4B | 0.7915 | **0.9113** | 0.8699 | nemotron |
| jina-v5-omni-small | 0.7580 | **0.8849** | 0.8587 | nemotron |
| nemotron-1B-Q4 | 0.7054 | **0.8177** | 0.7877 | nemotron |
| bekko-a25m | 0.6854 | **0.8493** | 0.8319 | nemotron |

---

## RANKING VERSÃO ANTERIOR (120 queries — referência histórica)

Corpus: 2.000 docs, 120 queries (30/domínio). Protocolo idêntico.

| # | Modelo | Dim | MRR@10 | VRAM | Tempo |
|---|---|---|---|---|---|
| 1 | lightonai-mDenseOn | 768 | 0.9023 | 1.26 GB | 13s |
| 2 | embeddinggemma-300m | 768 | 0.8895 | 0.38 GB | 13s |
| 3 | nemotron-8B | 1024 | 0.8715 | 5.19 GB | 95s |
| 4 | pplx-4B | 1024 | 0.8613 | 3.08 GB | 77s |
| 5 | qwen3-4B | 1024 | 0.8444 | 3.17 GB | 71s |
| 6 | jina-v5-omni-small | 1024 | 0.8424 | 1.01 GB | 34s |
| 7 | nemotron-1B-Q4 | 1024 | 0.7681 | 1.15 GB | 27s |
| 8 | bekko-a25m | 384 | 0.7590 | 0.78 GB | 17s |
| 9 | LFM2.5-350M | 1024 | 0.7481 | 0.59 GB | 250s |
| 10 | jina-v5-omni-nano | 1024 | 0.6111 | 0.20 GB | 8s |
| 11 | lightonai-mLateOn | 768 | 0.5147 | 0.81 GB | 13s |
| 12 | qwen3-0.6B | 1024 | 0.4807 | 1.03 GB | 48s |
| 13 | Qwen3-VL-2B | 1024 | 0.4607 | 1.83 GB | 72s |
| 14 | LCO-Omni-3B-2605 | 1024 | 0.4311 | 2.70 GB | 103s |
| 15 | omni-nemotron-3B | 2048 | 0.4163 | 8.97 GB | 78s |
| 16 | nomic-v1.5 | 768 | 0.3368 | 0.79 GB | 8s |

Pendências (não testados): gemini-001 (cota diária API excedida).
nemotron-1B-NVFP4 foi benchmarkado em 2026-08-11 via vLLM 0.26 — ver seção
acima (0.7056, ≈ Q4_K_M).

---

## NOTAS TÉCNICAS

1. **GGUF sem pooling embutido**: qwen3-0.6B (Mungert) e LCO retornam
   multi-vector (hidden states por token). Aplicada média pool (qwen3-0.6B)
   e MaxSim (LCO, late-interaction).
2. **LD_LIBRARY_PATH pós-restart**: `export LD_LIBRARY_PATH=/usr/lib/ollama/cuda_v13:/opt/cuda/targets/x86_64-linux/lib:$LD_LIBRARY_PATH`
   (llama-cpp compilado com CUDA 13; nvrtc do FlashAttention vision precisa
   do symlink `libnvrtc-builtins.so.13.0 → 13.3` em /opt/cuda).
3. **Storage**: int8 = dim bytes/vector; fp32 = dim × 4 bytes/vector.
4. **Omni em texto puro**: jina-v5-omni-small surpreende (6º), mas omni
   grandes (Qwen3-VL-2B, LCO, omni-nemotron) são fracos em texto — priorizam
   multimodalidade. Testes de visão usarão estes modelos no domínio deles.

---

## BENCHMARK DE VISÃO (retrieval visual texto→imagem)

Corpus: 150 imagens Flickr30k, 300 queries com wording divergente
(2ª/3ª legendas vs 1ª indexada). Protocolo idêntico ao de texto
(MRR@10, nDCG@10, Recall@10, MAP, Hit@10).

| # | Modelo | Dim | MRR@10 | nDCG@10 | R@10 | VRAM | RAM | Tempo |
|---|---|---|---|---|---|---|---|---|
| 1 | **qwen3-vl-2b-vdr** | 1024 | **0.9634** | 0.9727 | 1.0000 | 4.27 GB | 4.24 GB | 22.1s |
| 2 | BGE-VL-large | 768 | 0.9522 | 0.9615 | 0.9900 | 2.35 GB | 0.81 GB | 5.3s |
| 3 | omni-nemotron-3B | 2048 | 0.9402 | 0.9536 | 0.9933 | 9.82 GB | 3.90 GB | 75.0s |
| 4 | BGE-VL-base | 512 | 0.9303 | 0.9427 | 0.9800 | 1.33 GB | 1.73 GB | 9.0s |
| 5 | llama-nemotron-VL-FP8 | 2048 | 0.5815 | 0.6495 | 0.8667 | ~2.3 GB | — | 71.7s |
| 6 | Qwen3-VL-8B-i1 (GGUF IQ1) | 4096 | 0.0081 | 0.0168 | 0.0467 | ~0.1 GB | — | 114s |

**DECISÃO DE PRODUÇÃO (visão):** `qwen3-vl-2b-vdr` (tomaarsen) — fine-tune
VDR do Qwen3-VL-Embedding-2B, 4.27 GB VRAM, MRR 0.9634. BGE-VL-large
mantido como fallback (822 MB).

**Removidos da stack (perdedores, 2026-08-11):** BGE-VL-base, Qwen3-VL-8B-i1
(MRR 0.008 — vision IQ1 inútil), llama-nemotron-VL-FP8 (0.5815),
Qwen3-VL-2B-GGUF (sem mmproj), jina-v4×2, LCO-3B,
**BGE-VL-v1.5-mmeb** (7B/14.1 GB — pesos 14.08 GiB não cabem na 5060 Ti).

**Validação externa:** BGE-VL é SOTA no MMEB (benchmark acadêmico) — nosso
ranking local reproduz isso. O qwen3-vl-2b-vdr foi além por ser fine-tunado
em retrieval visual (VDR), confirmado com +0.011 sobre o BGE-VL-large.

---

## HISTÓRICO

- 2026-08-07: limpeza (~154 GB); runtime instalado; corpus v2 (2000 docs);
  rodada v1 (120q) + v2 (240q) de texto; decisão de produção texto
  (mDenseOn + embeddinggemma + llama-nemotron-rerank).
- 2026-08-10: benchmark de rerankers (6 × top-8); correção do
  llama-nemotron (pipeline nativo, não CrossEncoder); versão forte
  (240 queries) embeddings + rerankers; NVFP4 benchmarkado via vLLM
  (≈ Q4_K_M); visão v1 (30 img) e v2 (150 img, 300q).
- 2026-08-11: vLLM 0.26 instalado no venv (permanente); solução anti-OOM
  documentada em `models/vllm/COMO_USAR.md`; llama-nemotron-VL-FP8
  benchmarkado (0.5815); **qwen3-vl-2b-vdr = novo líder de visão (0.9634)**;
  limpeza final da stack (perdedores removidos, ~38 GB liberados);
  omni-nemotron-3B mantido como reserva de áudio
  (`embed/omni/nvidia-omni-embed-nemotron-3b/README_USO.md`).

**Stack final (produção):**
- Texto: lightonai-mDenseOn (0.8256) + embeddinggemma-300m (0.7992)
- Reranker: llama-nemotron-rerank-1b-v2 (nativo) → 0.9257/0.9221
- Visão: qwen3-vl-2b-vdr (0.9634) + BGE-VL-large fallback (0.9522)
- Reserva: omni-nemotron-3B (áudio), jina-v5-omni-small (generalista),
  LFM2.5 (reflink)

---

## ADENDO MEDIDO — WeMM-Embedding-2B (2026-09-04)

Execução textual separada, sem misturar com os resultados históricos acima.
Foi usado o corpus congelado `holo_fake_scenes_v3` (600 documentos, 150
queries PT-BR, ranking completo) e a implementação oficial
`SentenceTransformer.encode_query/encode_document` do WeMM. O resultado
completo, manifesto, rankings e vetores estão em:
`benchmarks/embedding-v3/results/wemm-v1/REPORT.md`.

| Modelo | NDCG@10 | MRR@10 | VRAM pico | RAM pico | p50 batch |
|---|---:|---:|---:|---:|---:|
| lightonai-mDenseOn | 0.7422 | 0.7249 | 1402 MiB | 2389 MiB | 0.180 s |
| embeddinggemma-300m | 0.7395 | 0.7123 | 524 MiB | 1310 MiB | 0.149 s |
| **WeMM-Embedding-2B** | **0.7261** | **0.6976** | 5499 MiB | 6445 MiB | 0.241 s |
| jina-v5-omni-small | 0.7059 | 0.6752 | 3862 MiB | 4778 MiB | 0.178 s |
| Qwen3-Embedding-4B | 0.7025 | 0.6656 | 7904 MiB | 5808 MiB | 0.194 s |
| Nemotron-Embedding atual | 0.4294 | 0.3511 | 9464 MiB | 5867 MiB | 0.166 s |

O WeMM ficou abaixo do mDenseOn no texto PT-BR e acima de Jina v5 e
Qwen3-Embedding-4B nesta execução. Inglês e labels `code/docs/tools/agent`
não existem no corpus congelado e permanecem `N/A`; nenhum teste visual foi
projetado ou misturado ao placar textual.
