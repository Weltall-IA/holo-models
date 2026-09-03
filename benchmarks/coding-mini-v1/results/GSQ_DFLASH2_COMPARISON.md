# coding-mini-v1 — Comparativo GSQ Base vs GSQ + DFlash2

Comparação direta e determinística entre o modelo base `Qwen3.8-27B GSQ-RCO IQ2_S` e sua versão acelerada por speculative decoding `GSQ-RCO IQ2_S + DFlash2 Q4_K_M`.

Configuração idêntica em ambos: seed 9137, temperature 0.2, top_p 0.95, reasoning off, 8 threads, full GPU offload, Flash Attention on, KV cache q8_0/q4_0, context 8192.

## Tabela Comparativa Consolidada

| Métrica | GSQ Base | GSQ + DFlash2 | Delta / Variação |
|---|:---:|:---:|:---:|
| **PASS / 6** | **6/6** | **6/6** | Preservado (100%) |
| **Python / 3** | 3/3 | 3/3 | Preservado |
| **C++ / 3** | 3/3 | 3/3 | Preservado |
| **Median tok/s** | 24.70 tok/s | 46.00 tok/s | **+86.26%** |
| **Median wall time** | 20.14 s | 13.63 s | **-32.32%** |
| **Peak VRAM** | 11216 MiB | 14086 MiB | +2870 MiB |
| **Draft Acceptance Mediana** | N/A | **86.9%** | N/A |

---

## Detalhamento Caso a Caso (Lado a Lado)

| Caso | GSQ Base Status | GSQ + DFlash2 Status | Base tok/s | DFlash2 tok/s | Base Time (s) | DFlash2 Time (s) | Draft Acc | Accepted / Generated |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **PY01** (ttl_cache_injected_clock) | **PASS** | **PASS** | 25.72 | 58.44 | 8.99s | 4.89s | 91.5% | 173 / 189 |
| **PY02** (retry_decorator_repair) | **PASS** | **PASS** | 25.30 | 56.98 | 7.33s | 4.02s | 87.8% | 129 / 147 |
| **PY03** (deterministic_dependency_order) | **PASS** | **PASS** | 25.39 | 38.24 | 17.90s | 15.50s | 55.7% | 437 / 784 |
| **CPP01** (normalize_int64_ranges) | **PASS** | **PASS** | 24.09 | 35.31 | 25.58s | 22.98s | 58.0% | 617 / 1064 |
| **CPP02** (sliding_window_statistics_repair) | **PASS** | **PASS** | 23.06 | 49.37 | 22.38s | 11.76s | 90.5% | 412 / 455 |
| **CPP03** (lazy_segment_tree_affine) | **PASS** | **PASS** | 21.14 | 42.63 | 55.72s | 29.55s | 86.1% | 1019 / 1183 |

---

## Conclusões Técnicas Objetivas

1. **DFlash preservou os mesmos 6/6?**: **SIM** (6/6 casos aprovados com aprovação integral em testes públicos e ocultos).

2. **Ganho/perda percentual em tok/s**: **+86.26%** (mediana subiu de 24.70 para 46.00 tok/s).

3. **Ganho/perda percentual em wall time**: **-32.32%** (mediana de tempo reduziu de 20.14s para 13.63s).

4. **Draft acceptance mediana**: **86.9%** (com pico de 91.5% no caso PY01).

5. **Vale usar DFlash2 como preset padrão de coding para o GSQ?**: **SIM**. Em tarefas de código sob temperatura 0.2, a previsibilidade da sintaxe em Python e C++ eleva a taxa de aceitação especulativa para ~87%, proporcionando aceleração real e consistente de vazão sem introduzir nenhuma regressão de exatidão lógica, mantendo o consumo de VRAM em 14086 MiB (com ~1.8 GB de margem segura na GPU de 16 GB).

