# candidate-round-v1 — Coding Summary

Avaliação comparativa determinística dos novos candidatos de código contra o controle histórico `Qwen3.8-27B GSQ-RCO IQ2_S + DFlash2`.

Condições de teste: seed 9137, temperature 0.2, top_p 0.95, reasoning off, 8 threads, full GPU offload, Flash Attention ON, KV cache q8_0/q4_0, context 8192.

## Tabela Consolidada de Código

| Modelo / Candidato | PASS / 6 | Python / 3 | C++ / 3 | tok/s mediano | Peak VRAM | Status Operacional |
|---|:---:|:---:|:---:|:---:|:---:|---|
| **[Controle] Qwen3.8-27B GSQ IQ2_S + DFlash2** | **6/6** | 3/3 | 3/3 | 46.00 tok/s | 14086 MiB | Baseline de referência |
| **Nanbeige4.2-3B Q4_K_M** | **5/6** | 2/3 | 3/3 | 18.48 tok/s | 4790 MiB | Concluído |
| **Ornith-1.5-9B Q5_K_M** | **2/6** | 2/3 | 0/3 | 39.08 tok/s | 8050 MiB | Concluído |
| **Spark-X2.5-4B Q4_K_M** | **0/6** | 0/3 | 0/3 | N/A | N/A | **Bloqueador de Infraestrutura**: Server failed to load model (unknown architecture / runtime incompatible) |
| **Qwen3.8-27B Escha-W2 (Q8E)** | **5/6** | 3/3 | 2/3 | 12.79 tok/s | 10908 MiB | Concluído |

---

## Detalhamento Caso a Caso

### PY01 — ttl_cache_injected_clock (PYTHON, Medium)

| Modelo | Compile | Public | Hidden | Status | Tempo (s) | tok/s |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| [Controle] GSQ IQ2_S + DFlash2 | PASS | PASS | PASS | **PASS** | 4.89s | 58.44 |
| Nanbeige4.2-3B Q4_K_M | PASS | PASS | PASS | **PASS** | 12.66s | 19.65 |
| Ornith-1.5-9B Q5_K_M | PASS | PASS | PASS | **PASS** | 5.74s | 40.80 |
| Spark-X2.5-4B Q4_K_M | N/A | N/A | N/A | **BLOCKED** | N/A | N/A |
| Qwen3.8-27B Escha-W2 (Q8E) | PASS | PASS | PASS | **PASS** | 16.65s | 13.50 |

### PY02 — retry_decorator_repair (PYTHON, Medium)

| Modelo | Compile | Public | Hidden | Status | Tempo (s) | tok/s |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| [Controle] GSQ IQ2_S + DFlash2 | PASS | PASS | PASS | **PASS** | 4.02s | 56.98 |
| Nanbeige4.2-3B Q4_K_M | PASS | PASS | PASS | **PASS** | 25.84s | 17.92 |
| Ornith-1.5-9B Q5_K_M | PASS | PASS | PASS | **PASS** | 3.77s | 40.19 |
| Spark-X2.5-4B Q4_K_M | N/A | N/A | N/A | **BLOCKED** | N/A | N/A |
| Qwen3.8-27B Escha-W2 (Q8E) | PASS | PASS | PASS | **PASS** | 17.97s | 13.25 |

### PY03 — deterministic_dependency_order (PYTHON, Hard)

| Modelo | Compile | Public | Hidden | Status | Tempo (s) | tok/s |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| [Controle] GSQ IQ2_S + DFlash2 | PASS | PASS | PASS | **PASS** | 15.50s | 38.24 |
| Nanbeige4.2-3B Q4_K_M | PASS | FAIL | FAIL | **FAIL** | 27.65s | 19.04 |
| Ornith-1.5-9B Q5_K_M | PASS | PASS | FAIL | **FAIL** | 6.39s | 41.62 |
| Spark-X2.5-4B Q4_K_M | N/A | N/A | N/A | **BLOCKED** | N/A | N/A |
| Qwen3.8-27B Escha-W2 (Q8E) | PASS | PASS | PASS | **PASS** | 48.11s | 13.25 |

### CPP01 — normalize_int64_ranges (CPP, Medium)

| Modelo | Compile | Public | Hidden | Status | Tempo (s) | tok/s |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| [Controle] GSQ IQ2_S + DFlash2 | PASS | PASS | PASS | **PASS** | 22.98s | 35.31 |
| Nanbeige4.2-3B Q4_K_M | PASS | PASS | PASS | **PASS** | 19.27s | 19.67 |
| Ornith-1.5-9B Q5_K_M | FAIL | FAIL | FAIL | **FAIL** | 21.01s | 37.98 |
| Spark-X2.5-4B Q4_K_M | N/A | N/A | N/A | **BLOCKED** | N/A | N/A |
| Qwen3.8-27B Escha-W2 (Q8E) | PASS | PASS | PASS | **PASS** | 80.90s | 12.34 |

### CPP02 — sliding_window_statistics_repair (CPP, Medium)

| Modelo | Compile | Public | Hidden | Status | Tempo (s) | tok/s |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| [Controle] GSQ IQ2_S + DFlash2 | PASS | PASS | PASS | **PASS** | 11.76s | 49.37 |
| Nanbeige4.2-3B Q4_K_M | PASS | PASS | PASS | **PASS** | 44.23s | 14.18 |
| Ornith-1.5-9B Q5_K_M | PASS | FAIL | FAIL | **FAIL** | 13.61s | 37.48 |
| Spark-X2.5-4B Q4_K_M | N/A | N/A | N/A | **BLOCKED** | N/A | N/A |
| Qwen3.8-27B Escha-W2 (Q8E) | PASS | PASS | PASS | **PASS** | 49.89s | 12.28 |

### CPP03 — lazy_segment_tree_affine (CPP, Hard)

| Modelo | Compile | Public | Hidden | Status | Tempo (s) | tok/s |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| [Controle] GSQ IQ2_S + DFlash2 | PASS | PASS | PASS | **PASS** | 29.55s | 42.63 |
| Nanbeige4.2-3B Q4_K_M | PASS | PASS | PASS | **PASS** | 130.32s | 11.22 |
| Ornith-1.5-9B Q5_K_M | FAIL | FAIL | FAIL | **FAIL** | 40.11s | 34.40 |
| Spark-X2.5-4B Q4_K_M | N/A | N/A | N/A | **BLOCKED** | N/A | N/A |
| Qwen3.8-27B Escha-W2 (Q8E) | PASS | FAIL | FAIL | **FAIL** | 105.51s | 11.60 |

