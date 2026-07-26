# Resultados consolidados de embeddings e rerankers
Consolidação dos artefatos individuais versionados em `results/reranker/pipelines/*/*.json`, sem nova execução de benchmark.
## Escopo e validação
| Item | Valor |
|---|---:|
| Pipelines publicados | **89** |
| Embeddings únicos | **32** |
| Rerankers | **6** |
| Variantes medidas no stash | **5** |
| Total de variantes listadas | **94** |
| Benchmark reexecutado | **Não** |
| Stash alterado | **Não** |
| Corpus | 600 documentos / 150 consultas |
| Protocolo | top 50 → rerank top 20 |
| SHA do corpus | `8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b` |

Critério: MRR@10, nDCG@10, HitRate@1 e HitRate@10, todos em ordem decrescente.

## Conclusões corretas
- **Melhor resultado publicado absoluto:** `embeddinggemma_768_float32__voyage_rerank_2_5`, MRR@10 **0,826444**.
- **Melhor resultado publicado totalmente local e comercialmente elegível:** `qwen3_embedding_4b_q8_0__qwen_local`, MRR@10 **0,824296**.
- **Pipeline operacional selecionado:** `nomic_embed_text_v2_moe_q4__qwen_local`, MRR@10 **0,822857**.
- **BGE M3 não lidera o ranking geral.** Ele liderou uma comparação de HitRate@10 raw; no ranking completo de pipelines por MRR@10, `bge_m3_dense__qwen_local` fica abaixo dos líderes.
- As cinco versões do stash são registradas separadamente, pois usam candidatos diferentes dos arquivos canônicos da `master`.

## Qwen3 Embedding 8B
| Configuração | MRR@10 | HR@1 | HR@10 | nDCG@10 | Posição publicada |
|---|---:|---:|---:|---:|---:|
| Raw, GGUF Q8_0, 1024d | 0.692042 | — | 0.846667 | 0.727498 | — |
| + qwen_local | 0.791405 | 0.766667 | 0.846667 | 0.796757 | **49º / 89** |

O 8B não foi perdido: o raw está em `results/gate3/qwen3_embedding_8b_gguf.json` e o pipeline reranqueado em `results/reranker/pipelines/qwen_local/qwen3_embedding_8b_gguf.json`.

## Melhor pipeline por reranker
| Reranker | Pipeline | MRR@10 | HR@10 | nDCG@10 |
|---|---|---:|---:|---:|
| `jina_reranker_v3_noncommercial` | `nomic_embed_text_v2_moe_q4__jina_reranker_v3_noncommercial` | 0.813201 | 0.866667 | 0.818324 |
| `kalm_reranker_v1_nano` | `bidirlm_17b_embedding__kalm_reranker_v1_nano` | 0.765749 | 0.853333 | 0.778879 |
| `kalm_reranker_v1_small` | `pplx_embed_v1_4b_q8_0__kalm_reranker_v1_small` | 0.813571 | 0.880000 | 0.821465 |
| `querit_reranker_4b` | `bidirlm_17b_embedding__querit_reranker_4b` | 0.257378 | 0.620000 | 0.335785 |
| `qwen_local` | `qwen3_embedding_4b_q8_0__qwen_local` | 0.824296 | 0.886667 | 0.831619 |
| `voyage_rerank_2_5` | `embeddinggemma_768_float32__voyage_rerank_2_5` | 0.826444 | 0.873333 | 0.834631 |

## Ranking completo publicado — 89 pipelines
| # | Pipeline | MRR@10 | HR@1 | HR@10 | nDCG@10 | Local | Elegibilidade |
|---:|---|---:|---:|---:|---:|:---:|---|
| 1 | `embeddinggemma_768_float32__voyage_rerank_2_5` | 0.826444 | 0.813333 | 0.873333 | 0.834631 | não | `eligible` |
| 2 | `voyage_4_large_1024_float32__voyage_rerank_2_5` | 0.826056 | 0.813333 | 0.873333 | 0.830447 | não | `eligible` |
| 3 | `qwen3_embedding_4b_q8_0__qwen_local` | 0.824296 | 0.793333 | 0.886667 | 0.831619 | sim | `eligible` |
| 4 | `nomic_embed_text_v2_moe_q4__qwen_local` | 0.822857 | 0.793333 | 0.880000 | 0.828951 | sim | `eligible` |
| 5 | `voyage4_nano__qwen_local` | 0.822302 | 0.786667 | 0.886667 | 0.830320 | não | `eligible` |
| 6 | `pplx_embed_v1_4b_q8_0__qwen_local` | 0.822071 | 0.793333 | 0.880000 | 0.828247 | sim | `eligible` |
| 7 | `jina_embeddings_v5_text_small__qwen_local` | 0.821582 | 0.793333 | 0.873333 | 0.826425 | sim | `eligible` |
| 8 | `voyage4_nano_1024_float32__voyage_rerank_2_5` | 0.820989 | 0.806667 | 0.866667 | 0.827871 | não | `eligible` |
| 9 | `nomic_embed_text_v2_moe_q4__voyage_rerank_2_5` | 0.820900 | 0.806700 | 0.866700 | 0.823600 | não | `eligible` |
| 10 | `pplx_embed_v1_4b_q8_0__voyage_rerank_2_5` | 0.820600 | 0.806700 | 0.866700 | 0.827700 | não | `eligible` |
| 11 | `voyage4_nano_2048_int8__voyage_rerank_2_5` | 0.820037 | 0.806667 | 0.866667 | 0.825795 | não | `eligible` |
| 12 | `colibri_ptbr__qwen_local` | 0.819841 | 0.786667 | 0.886667 | 0.828164 | sim | `eligible` |
| 13 | `embeddinggemma_gguf__qwen_local` | 0.819804 | 0.786667 | 0.893333 | 0.829478 | sim | `eligible` |
| 14 | `embeddinggemma__qwen_local` | 0.819730 | 0.786667 | 0.893333 | 0.829398 | sim | `eligible` |
| 15 | `voyage4_nano_2048_float32__voyage_rerank_2_5` | 0.819481 | 0.806667 | 0.866667 | 0.825333 | não | `eligible` |
| 16 | `bidirlm_17b_embedding__qwen_local` | 0.819016 | 0.780000 | 0.886667 | 0.827924 | sim | `eligible` |
| 17 | `pplx_embed_v1_06b_native__qwen_local` | 0.819016 | 0.786667 | 0.886667 | 0.827594 | sim | `eligible` |
| 18 | `nemotron_8b_abiray_q4__qwen_local` | 0.818897 | 0.786667 | 0.886667 | 0.827475 | sim | `eligible` |
| 19 | `nemotron_8b_aqua00_q4__qwen_local` | 0.818897 | 0.786667 | 0.886667 | 0.827475 | sim | `eligible` |
| 20 | `giga_embeddings_instruct__qwen_local` | 0.818397 | 0.780000 | 0.886667 | 0.827410 | sim | `eligible` |
| 21 | `snowflake_arctic_embed_l_v2_q4__qwen_local` | 0.815778 | 0.786667 | 0.873333 | 0.821976 | sim | `eligible` |
| 22 | `octen_embedding_8b_q8_0__qwen_local` | 0.815397 | 0.780000 | 0.886667 | 0.824839 | sim | `eligible` |
| 23 | `pplx_embed_v1_4b_q8_0__kalm_reranker_v1_small` | 0.813571 | 0.786667 | 0.880000 | 0.821465 | sim | `eligible` |
| 24 | `bidirlm_17b_embedding__kalm_reranker_v1_small` | 0.813497 | 0.786667 | 0.880000 | 0.821386 | sim | `eligible` |
| 25 | `nomic_embed_text_v2_moe_q4__jina_reranker_v3_noncommercial` | 0.813201 | 0.786667 | 0.866667 | 0.818324 | sim | `not_eligible_noncommercial` |
| 26 | `colibri_ptbr__kalm_reranker_v1_small` | 0.812360 | 0.786667 | 0.880000 | 0.820306 | sim | `eligible` |
| 27 | `pplx_embed_v1_06b_native__kalm_reranker_v1_small` | 0.811786 | 0.780000 | 0.880000 | 0.820221 | sim | `eligible` |
| 28 | `embeddinggemma__kalm_reranker_v1_small` | 0.811619 | 0.786667 | 0.873333 | 0.818299 | sim | `eligible` |
| 29 | `embeddinggemma_gguf__kalm_reranker_v1_small` | 0.811619 | 0.786667 | 0.873333 | 0.818299 | sim | `eligible` |
| 30 | `multilingual_e5_large_instruct__qwen_local` | 0.811082 | 0.780000 | 0.880000 | 0.819740 | sim | `eligible` |
| 31 | `gte_multilingual_base__qwen_local` | 0.810944 | 0.773333 | 0.880000 | 0.820074 | sim | `eligible` |
| 32 | `jina_embeddings_v5_text_small__kalm_reranker_v1_small` | 0.810878 | 0.780000 | 0.880000 | 0.819574 | sim | `eligible` |
| 33 | `qwen3_embedding_4b_q8_0__kalm_reranker_v1_small` | 0.810386 | 0.780000 | 0.880000 | 0.819129 | sim | `eligible` |
| 34 | `nomic_embed_text_v2_moe_q4__kalm_reranker_v1_small` | 0.809701 | 0.780000 | 0.880000 | 0.818525 | sim | `eligible` |
| 35 | `granite_embedding_311m_r2__qwen_local` | 0.809230 | 0.780000 | 0.873333 | 0.816775 | sim | `eligible` |
| 36 | `bge_m3_dense__qwen_local` | 0.806741 | 0.773333 | 0.873333 | 0.815032 | sim | `eligible` |
| 37 | `qwen3_embedding_06__qwen_local` | 0.806619 | 0.773333 | 0.873333 | 0.815012 | sim | `eligible` |
| 38 | `pplx_embed_v1_4b_q8_0__jina_reranker_v3_noncommercial` | 0.806481 | 0.780000 | 0.873333 | 0.814466 | sim | `not_eligible_noncommercial` |
| 39 | `bge_m3_dense__voyage_rerank_2_5` | 0.804000 | 0.793300 | 0.846700 | 0.811600 | não | `eligible` |
| 40 | `snowflake_arctic_embed_l_v2_q4__voyage_rerank_2_5` | 0.804000 | 0.793300 | 0.846700 | 0.805900 | não | `eligible` |
| 41 | `snowflake_arctic_embed_l_v2_q4__kalm_reranker_v1_small` | 0.801870 | 0.773333 | 0.866667 | 0.809421 | sim | `eligible` |
| 42 | `bge_m3_dense__kalm_reranker_v1_small` | 0.800870 | 0.773333 | 0.866667 | 0.808738 | sim | `eligible` |
| 43 | `qwen3_embedding_4b_q8_0__jina_reranker_v3_noncommercial` | 0.797407 | 0.766667 | 0.860000 | 0.804709 | sim | `not_eligible_noncommercial` |
| 44 | `pplx_embed_v1_06b_native__jina_reranker_v3_noncommercial` | 0.796444 | 0.753333 | 0.866667 | 0.805989 | sim | `not_eligible_noncommercial` |
| 45 | `voyage4_nano__jina_reranker_v3_noncommercial` | 0.796407 | 0.753333 | 0.866667 | 0.805879 | não | `not_eligible_noncommercial` |
| 46 | `embeddinggemma_gguf__jina_reranker_v3_noncommercial` | 0.795183 | 0.760000 | 0.866667 | 0.804431 | sim | `not_eligible_noncommercial` |
| 47 | `colibri_ptbr__jina_reranker_v3_noncommercial` | 0.794952 | 0.760000 | 0.853333 | 0.801512 | sim | `not_eligible_noncommercial` |
| 48 | `embeddinggemma__jina_reranker_v3_noncommercial` | 0.791905 | 0.753333 | 0.860000 | 0.800690 | sim | `not_eligible_noncommercial` |
| 49 | `qwen3_embedding_8b_gguf__qwen_local` | 0.791405 | 0.766667 | 0.846667 | 0.796757 | sim | `eligible` |
| 50 | `embeddinggemma_768_float32__qwen_local` | 0.791074 | 0.760000 | 0.873333 | 0.805547 | sim | `eligible` |
| 51 | `voyage_4_large_1024_float32__qwen_local` | 0.790296 | 0.760000 | 0.873333 | 0.804706 | não | `eligible` |
| 52 | `bge_m3_dense__jina_reranker_v3_noncommercial` | 0.790111 | 0.760000 | 0.860000 | 0.798797 | sim | `not_eligible_noncommercial` |
| 53 | `granite_embedding_97m_r2__qwen_local` | 0.788952 | 0.760000 | 0.846667 | 0.795288 | sim | `eligible` |
| 54 | `snowflake_arctic_embed_l_v2_q4__jina_reranker_v3_noncommercial` | 0.788630 | 0.753333 | 0.860000 | 0.798031 | sim | `not_eligible_noncommercial` |
| 55 | `bidirlm_17b_embedding__jina_reranker_v3_noncommercial` | 0.785193 | 0.740000 | 0.866667 | 0.797317 | sim | `not_eligible_noncommercial` |
| 56 | `voyage4_nano_2048_float32__qwen_local` | 0.783704 | 0.753333 | 0.860000 | 0.796649 | não | `eligible` |
| 57 | `voyage4_nano_2048_int8__qwen_local` | 0.783545 | 0.753333 | 0.860000 | 0.796497 | não | `eligible` |
| 58 | `voyage4_nano_1024_float32__qwen_local` | 0.783471 | 0.753333 | 0.860000 | 0.796417 | não | `eligible` |
| 59 | `lfm_25_embedding_350m_q4__qwen_local` | 0.779294 | 0.753333 | 0.833333 | 0.784537 | sim | `eligible` |
| 60 | `jina_embeddings_v5_text_small__jina_reranker_v3_noncommercial` | 0.777082 | 0.720000 | 0.866667 | 0.791423 | sim | `not_eligible_noncommercial` |
| 61 | `bidirlm_17b_embedding__kalm_reranker_v1_nano` | 0.765749 | 0.726667 | 0.853333 | 0.778879 | sim | `eligible` |
| 62 | `qwen3_embedding_4b_q8_0__kalm_reranker_v1_nano` | 0.763833 | 0.720000 | 0.853333 | 0.777628 | sim | `eligible` |
| 63 | `nomic_embed_text_v2_moe_q4__kalm_reranker_v1_nano` | 0.759630 | 0.713333 | 0.853333 | 0.774457 | sim | `eligible` |
| 64 | `jina_embeddings_v5_text_small__kalm_reranker_v1_nano` | 0.759138 | 0.713333 | 0.853333 | 0.774154 | sim | `eligible` |
| 65 | `pplx_embed_v1_06b_native__kalm_reranker_v1_nano` | 0.758841 | 0.713333 | 0.853333 | 0.773839 | sim | `eligible` |
| 66 | `embeddinggemma__kalm_reranker_v1_nano` | 0.758794 | 0.713333 | 0.853333 | 0.773765 | sim | `eligible` |
| 67 | `colibri_ptbr__kalm_reranker_v1_nano` | 0.758238 | 0.713333 | 0.853333 | 0.773303 | sim | `eligible` |
| 68 | `embeddinggemma_gguf__kalm_reranker_v1_nano` | 0.758238 | 0.713333 | 0.853333 | 0.773303 | sim | `eligible` |
| 69 | `pplx_embed_v1_4b_q8_0__kalm_reranker_v1_nano` | 0.757175 | 0.713333 | 0.853333 | 0.772504 | sim | `eligible` |
| 70 | `snowflake_arctic_embed_l_v2_q4__kalm_reranker_v1_nano` | 0.755034 | 0.713333 | 0.846667 | 0.769330 | sim | `eligible` |
| 71 | `qwen3_embedding_06_gguf__qwen_local` | 0.747730 | 0.720000 | 0.806667 | 0.754066 | sim | `eligible` |
| 72 | `bge_m3_dense__kalm_reranker_v1_nano` | 0.747360 | 0.706667 | 0.840000 | 0.761790 | sim | `eligible` |
| 73 | `kalm_embedding_gemma3_12b_q4__qwen_local` | 0.636619 | 0.613333 | 0.693333 | 0.643816 | sim | `eligible` |
| 74 | `boom_4b_v1_q8_0__qwen_local` | 0.605135 | 0.580000 | 0.680000 | 0.617313 | sim | `unresolved_embedding_license` |
| 75 | `kalm_embedding_gemma3_12b_i1_q4__qwen_local` | 0.550333 | 0.533333 | 0.586667 | 0.553879 | sim | `eligible` |
| 76 | `bidirlm_17b_embedding__querit_reranker_4b` | 0.257378 | 0.133333 | 0.620000 | 0.335785 | sim | `eligible` |
| 77 | `pplx_embed_v1_06b_native__querit_reranker_4b` | 0.220772 | 0.106667 | 0.580000 | 0.301970 | sim | `eligible` |
| 78 | `snowflake_arctic_embed_l_v2_q4__querit_reranker_4b` | 0.219799 | 0.120000 | 0.540000 | 0.293830 | sim | `eligible` |
| 79 | `bge_m3_dense__querit_reranker_4b` | 0.219466 | 0.093333 | 0.606667 | 0.307402 | sim | `eligible` |
| 80 | `colibri_ptbr__querit_reranker_4b` | 0.210841 | 0.093333 | 0.573333 | 0.292423 | sim | `eligible` |
| 81 | `pplx_embed_v1_4b_q8_0__querit_reranker_4b` | 0.210569 | 0.080000 | 0.553333 | 0.287974 | sim | `eligible` |
| 82 | `qwen3_embedding_4b_q8_0__querit_reranker_4b` | 0.204101 | 0.080000 | 0.593333 | 0.291962 | sim | `eligible` |
| 83 | `nomic_embed_text_v2_moe_q4__querit_reranker_4b` | 0.199513 | 0.073333 | 0.573333 | 0.285405 | sim | `eligible` |
| 84 | `jina_embeddings_v5_text_small__querit_reranker_4b` | 0.199384 | 0.080000 | 0.553333 | 0.280487 | sim | `eligible` |
| 85 | `embeddinggemma_gguf__querit_reranker_4b` | 0.198860 | 0.066667 | 0.586667 | 0.286663 | sim | `eligible` |
| 86 | `embeddinggemma__querit_reranker_4b` | 0.198534 | 0.073333 | 0.600000 | 0.288755 | sim | `eligible` |
| 87 | `voyage4_nano__querit_reranker_4b` | 0.183799 | 0.060000 | 0.533333 | 0.263190 | não | `eligible` |
| 88 | `voyage4_nano__kalm_reranker_v1_nano` | 0.001407 | 0.000000 | 0.013333 | 0.003158 | não | `eligible` |
| 89 | `voyage4_nano__kalm_reranker_v1_small` | 0.000741 | 0.000000 | 0.006667 | 0.001231 | não | `eligible` |

## Variantes medidas preservadas no stash
Estas cinco linhas não substituem os arquivos publicados. Elas são resultados adicionais com candidatos diferentes, preservados em `stash@{0}: preserve-unstaged-pre-voyage`.
| Variante | MRR@10 | MRR master | Δ | HR@1 | HR@10 | HR@20 | nDCG@10 | Posição entre 94 variantes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `voyage4_nano_1024_float32__qwen_local@stash-preserve-unstaged-pre-voyage` | 0.822300 | 0.783471 | +0.038829 | 0.786700 | 0.886700 | 1.000000 | 0.830300 | 6 |
| `voyage4_nano_2048_float32__qwen_local@stash-preserve-unstaged-pre-voyage` | 0.822000 | 0.783704 | +0.038296 | 0.786700 | 0.886700 | 0.993300 | 0.830100 | 8 |
| `voyage_4_large_1024_float32__qwen_local@stash-preserve-unstaged-pre-voyage` | 0.820100 | 0.790296 | +0.029804 | 0.786700 | 0.886700 | 0.980000 | 0.828400 | 13 |
| `embeddinggemma_768_float32__qwen_local@stash-preserve-unstaged-pre-voyage` | 0.817200 | 0.791074 | +0.026126 | 0.780000 | 0.893300 | 1.000000 | 0.827600 | 24 |
| `voyage4_nano_2048_int8__qwen_local@stash-preserve-unstaged-pre-voyage` | 0.783400 | 0.783545 | -0.000145 | 0.753300 | 0.860000 | 0.946700 | 0.795300 | 63 |

## Observações de comparabilidade
- `jina_reranker_v3_noncommercial` é não comercial.
- `boom_4b_v1_q8_0` permanece com licença não resolvida.
- Pipelines Voyage dependem de API externa; embeddings cujo ID começa por `voyage` também não são totalmente locais.
- Os valores do Querit são preservados mesmo quando ruins; resultados negativos não são removidos.
- Os JSONs individuais permanecem a fonte autoritativa. Este arquivo é o índice consolidado e ranqueado.
