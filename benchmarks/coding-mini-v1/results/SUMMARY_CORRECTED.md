# coding-mini-v1 — Corrected Results Summary

Deterministic re-evaluation of 5 local open-weight models across 6 coding cases (3 Python, 3 C++20) following canonical evaluator corrections in `EVALUATOR_CORRECTIONS.md`.

Execution conditions: seed 9137, temperature 0.2, top_p 0.95, reasoning off, 8 threads, full GPU offload, FA on, KV cache q8_0/q4_0, context 8192.

Evaluator corrections applied: type-coercion strictness removed from PY01/PY02 hidden loops; public expected output for CPP03 normalized to exact 26.

## Consolidated Performance & Accuracy Table

| Modelo | PASS / 6 | Python / 3 | C++ / 3 | tok/s mediano | Peak VRAM |
|---|:---:|:---:|:---:|:---:|:---:|
| **Qwen3.8-27B Fable Distill Heretic ARA Q3_K_M** | **5/6** | 3/3 | 2/3 | 17.35 tok/s | 14561 MiB |
| **Qwen3.8-27B Heretic RVN IQ3_M multilingual MTP** | **5/6** | 3/3 | 2/3 | 18.13 tok/s | 14234 MiB |
| **Qwen3.8-27B Uncensored YMQ S-Pro** | **6/6** | 3/3 | 3/3 | 18.94 tok/s | 14063 MiB |
| **Qwen3.8-27B GSQ-RCO IQ2_S** | **6/6** | 3/3 | 3/3 | 24.7 tok/s | 11216 MiB |
| **Qwen3.8-9B Distill uncensored heretic i1-Q4_K_M** | **3/6** | 2/3 | 1/3 | 50.66 tok/s | 6911 MiB |

---

## Case-by-Case Breakdown

### PY01 — ttl_cache_injected_clock (PYTHON, Medium)

| Modelo | Compile / Syntax | Public Tests | Hidden Tests | Status | Geração (s) | tok/s |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Qwen3.8-27B Fable Distill Heretic ARA Q3_K_M | PASS | PASS | PASS | **PASS** | 11.80s | 17.54 |
| Qwen3.8-27B Heretic RVN IQ3_M multilingual MTP | PASS | PASS | PASS | **PASS** | 14.85s | 19.10 |
| Qwen3.8-27B Uncensored YMQ S-Pro | PASS | PASS | PASS | **PASS** | 12.54s | 19.64 |
| Qwen3.8-27B GSQ-RCO IQ2_S | PASS | PASS | PASS | **PASS** | 8.99s | 25.72 |
| Qwen3.8-9B Distill uncensored heretic i1-Q4_K_M | PASS | PASS | PASS | **PASS** | 4.19s | 52.25 |

### PY02 — retry_decorator_repair (PYTHON, Medium)

| Modelo | Compile / Syntax | Public Tests | Hidden Tests | Status | Geração (s) | tok/s |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Qwen3.8-27B Fable Distill Heretic ARA Q3_K_M | PASS | PASS | PASS | **PASS** | 9.76s | 17.62 |
| Qwen3.8-27B Heretic RVN IQ3_M multilingual MTP | PASS | PASS | PASS | **PASS** | 9.38s | 19.54 |
| Qwen3.8-27B Uncensored YMQ S-Pro | PASS | PASS | PASS | **PASS** | 12.54s | 19.55 |
| Qwen3.8-27B GSQ-RCO IQ2_S | PASS | PASS | PASS | **PASS** | 7.33s | 25.30 |
| Qwen3.8-9B Distill uncensored heretic i1-Q4_K_M | PASS | PASS | PASS | **PASS** | 7.14s | 51.81 |

### PY03 — deterministic_dependency_order (PYTHON, Hard)

| Modelo | Compile / Syntax | Public Tests | Hidden Tests | Status | Geração (s) | tok/s |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Qwen3.8-27B Fable Distill Heretic ARA Q3_K_M | PASS | PASS | PASS | **PASS** | 17.33s | 17.87 |
| Qwen3.8-27B Heretic RVN IQ3_M multilingual MTP | PASS | PASS | PASS | **PASS** | 30.26s | 18.66 |
| Qwen3.8-27B Uncensored YMQ S-Pro | PASS | PASS | PASS | **PASS** | 31.33s | 19.20 |
| Qwen3.8-27B GSQ-RCO IQ2_S | PASS | PASS | PASS | **PASS** | 17.90s | 25.39 |
| Qwen3.8-9B Distill uncensored heretic i1-Q4_K_M | PASS | PASS | FAIL | **FAIL** | 12.83s | 50.73 |

### CPP01 — normalize_int64_ranges (CPP, Medium)

| Modelo | Compile / Syntax | Public Tests | Hidden Tests | Status | Geração (s) | tok/s |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Qwen3.8-27B Fable Distill Heretic ARA Q3_K_M | PASS | PASS | PASS | **PASS** | 26.45s | 17.17 |
| Qwen3.8-27B Heretic RVN IQ3_M multilingual MTP | PASS | PASS | PASS | **PASS** | 60.17s | 17.60 |
| Qwen3.8-27B Uncensored YMQ S-Pro | PASS | PASS | PASS | **PASS** | 33.91s | 18.69 |
| Qwen3.8-27B GSQ-RCO IQ2_S | PASS | PASS | PASS | **PASS** | 25.58s | 24.09 |
| Qwen3.8-9B Distill uncensored heretic i1-Q4_K_M | PASS | PASS | FAIL | **FAIL** | 12.47s | 50.59 |

### CPP02 — sliding_window_statistics_repair (CPP, Medium)

| Modelo | Compile / Syntax | Public Tests | Hidden Tests | Status | Geração (s) | tok/s |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Qwen3.8-27B Fable Distill Heretic ARA Q3_K_M | PASS | FAIL | FAIL | **FAIL** | 29.73s | 15.96 |
| Qwen3.8-27B Heretic RVN IQ3_M multilingual MTP | PASS | PASS | PASS | **PASS** | 32.03s | 17.56 |
| Qwen3.8-27B Uncensored YMQ S-Pro | PASS | PASS | PASS | **PASS** | 83.30s | 16.21 |
| Qwen3.8-27B GSQ-RCO IQ2_S | PASS | PASS | PASS | **PASS** | 22.38s | 23.06 |
| Qwen3.8-9B Distill uncensored heretic i1-Q4_K_M | PASS | PASS | PASS | **PASS** | 12.60s | 47.39 |

### CPP03 — lazy_segment_tree_affine (CPP, Hard)

| Modelo | Compile / Syntax | Public Tests | Hidden Tests | Status | Geração (s) | tok/s |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Qwen3.8-27B Fable Distill Heretic ARA Q3_K_M | PASS | PASS | PASS | **PASS** | 76.07s | 14.68 |
| Qwen3.8-27B Heretic RVN IQ3_M multilingual MTP | PASS | PASS | FAIL | **FAIL** | 117.55s | 14.80 |
| Qwen3.8-27B Uncensored YMQ S-Pro | PASS | PASS | PASS | **PASS** | 85.73s | 16.75 |
| Qwen3.8-27B GSQ-RCO IQ2_S | PASS | PASS | PASS | **PASS** | 55.72s | 21.14 |
| Qwen3.8-9B Distill uncensored heretic i1-Q4_K_M | FAIL | FAIL | FAIL | **FAIL** | 40.50s | 41.79 |

