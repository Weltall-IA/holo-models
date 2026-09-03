# score-completion-template-ablation-v1 — Coding Summary

Avaliação comparativa determinística dos candidatos de código nesta rodada contra os controles históricos.
Condições de teste: seed 9137, temperature 0.2, top_p 0.95, reasoning off, 8 threads, full GPU offload, Flash Attention ON, KV cache q8_0/q4_0, context 8192.

## 1. Ranking Consolidado de Código (Ordenado por PASS/6 Descendente)

| Posição | Modelo / Preset | PASS / 6 | Python / 3 | C++ / 3 | tok/s mediano | Peak VRAM | Status / Observações |
|:---:|---|:---:|:---:|:---:|:---:|:---:|---|
| **1º** | **[Controle] Qwen3.8-27B GSQ IQ2_S + DFlash2** | **6/6** | 3/3 | 3/3 | 46.00 tok/s | 14086 MiB | Baseline de referência perfeita |
| **1º** | **[Controle] Qwen3.8-27B GSQ IQ2_S Base** | **6/6** | 3/3 | 3/3 | 24.70 tok/s | 11216 MiB | Baseline sem speculative |
| **1º** | **[Controle] Qwen3.8-27B Uncensored YMQ S-Pro** | **6/6** | 3/3 | 3/3 | 18.94 tok/s | 14063 MiB | Baseline IQ3 |
| **2º** | **Qwen3.8-27B Escha-W2 (Q8E) + Froggeric v22.4** | **5/6** | 3/3 | 2/3 | 14.71 tok/s | 13444 MiB | Aprovado (PY 3/3, CPP 2/3) |
| **2º** | **Qwen3.8-27B Escha-W2 (Q8E) Native** | **5/6** | 3/3 | 2/3 | 12.80 tok/s | 13444 MiB | Aprovado (PY 3/3, CPP 2/3) |
| **2º** | **[Controle] Qwen3.8-27B Fable Heretic Q3_K_M** | **5/6** | 3/3 | 2/3 | 17.35 tok/s | 14561 MiB | Aprovado (PY 3/3, CPP 2/3) |
| **2º** | **[Controle] Qwen3.8-27B Heretic RVN IQ3_M MTP** | **5/6** | 3/3 | 2/3 | 18.13 tok/s | 14234 MiB | Aprovado (PY 3/3, CPP 2/3) |
| **2º** | **Nanbeige4.2-3B Q4_K_M** | **5/6** | 2/3 | 3/3 | 18.48 tok/s | 4519 MiB | Destaque 3B (C++ 3/3 impecável) |
| **3º** | **[Controle] Qwen3.8-9B Distill Heretic Q4_K_M** | **3/6** | 2/3 | 1/3 | 50.66 tok/s | 6911 MiB | Rápido, mas errou lógica complexa |
| **4º** | **Spark-X2.5-4B Q4_K_M (Runtime Isolado)** | **2/6** | 2/3 | 0/3 | 38.04 tok/s | 4520 MiB | Aprovado em PY01/PY02; falhou em C++ |
| **4º** | **[Controle] Ornith-1.5-9B Q5_K_M** | **2/6** | 2/3 | 0/3 | 39.08 tok/s | 8119 MiB | Aprovado em PY01/PY02; falhou em C++ |
| **—** | **Qwen3.8-27B Escha-W2 + DFlash2** | **N/A** | N/A | N/A | N/A | N/A | **BLOCKED_RUNTIME_UNSUPPORTED** (Fork Escha sem DFlash2 PR) |

---

## 2. Detalhamento dos Novos Testes de Código

| Caso | Spark-X2.5-4B | Escha W2-Q8E + Froggeric | GSQ+DFlash2 (Controle) |
|---|:---:|:---:|:---:|
| **PY01** (`ttl_cache_injected_clock`) | **PASS** (40.17 t/s, 6.5s) | **PASS** (15.45 t/s, 14.5s) | **PASS** (58.44 t/s, 4.9s) |
| **PY02** (`retry_decorator_repair`) | **PASS** (38.05 t/s, 6.5s) | **PASS** (15.30 t/s, 15.3s) | **PASS** (56.98 t/s, 4.0s) |
| **PY03** (`deterministic_dependency_order`) | **FAIL** (39.44 t/s, 13.1s) | **PASS** (15.00 t/s, 42.6s) | **PASS** (38.24 t/s, 15.5s) |
| **CPP01** (`normalize_int64_ranges`) | **FAIL** (38.03 t/s, 13.6s) | **PASS** (14.35 t/s, 69.8s) | **PASS** (35.31 t/s, 23.0s) |
| **CPP02** (`sliding_window_statistics_repair`) | **FAIL** (31.73 t/s, 19.5s) | **PASS** (14.41 t/s, 42.6s) | **PASS** (49.37 t/s, 11.8s) |
| **CPP03** (`lazy_segment_tree_affine`) | **FAIL** (28.71 t/s, 55.8s) | **FAIL** (13.64 t/s, 89.7s) | **PASS** (42.63 t/s, 29.6s) |

