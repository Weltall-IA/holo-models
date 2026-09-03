# coding-mini-v1 — Avaliação de Candidatos: Jack Coder 27B vs Whittle MoE 27B

Avaliação de dois modelos candidatos para possível substituição ou complementação do `Qwen3.8-27B GSQ-RCO IQ2_S + DFlash2` como modelo principal de código.

## Metadados dos Modelos

### 1. Jack-3.8-27B-Coder-16GB-VRAM
- **Repositório Hugging Face**: `JackAgentLead/Jack-3.8-27B-Coder-16GB-VRAM`
- **Arquivo GGUF**: `Jack-3.8-27B-Coder-16GB-VRAM.gguf`
- **Tamanho**: 12.599.204.320 bytes (11.73 GiB)
- **SHA256**: `e7fecb29086afb4f6ca054b0f1469f2704a24e56db27c5980827f5f32d26f041`
- **Arquitetura**: `qwen35` (dense 27B, ~3.7 bpw custom mix)
- **Configuração de Execução**: `seed: 9137, temp: 0.2, top_p: 0.95, reasoning: off, np: 1, threads: 8, ctx: 8192, FA: on, ngl: 99, ctk: q8_0, ctv: q4_0`

### 2. Whittle-MoE Qwen3.8-27B A17.8B/A18B
- **Repositório Hugging Face**: `logic65/Qwen3.8-Whittle-MoE-27B-A17.8B-GGUF`
- **Arquivo GGUF**: `Whittle-MoE-27B-A18B-v2.2.1-Q3_K_M.gguf`
- **Tamanho**: 13.874.251.328 bytes (12.92 GiB)
- **SHA256**: `b32cc1f4f4661925e163937213932c4571e88d3d5da381ed79515cffae46e305`
- **Arquitetura**: `qwen35moe` / gated-deltanet (A18B ativos)
- **Configuração de Execução**: `seed: 9137, temp: 0.2, top_p: 0.95, reasoning: off, np: 1, threads: 8, ctx: 8192, FA: on, ngl: 99, ctk: q8_0, ctv: q4_0`

---

## Tabela Comparativa Consolidada

| Modelo | PASS / 6 | Python / 3 | C++ / 3 | Mediana tok/s | Mediana Wall Time | Pico VRAM | Gate DFlash2 | Conclusão |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **GSQ-RCO IQ2_S (Base)** *(Histórico)* | **6/6** | 3/3 | 3/3 | 24.70 tok/s | 20.14 s | 11.216 MiB | Aprovado | **Referência Base** |
| **GSQ-RCO IQ2_S + DFlash2** *(Histórico)* | **6/6** | 3/3 | 3/3 | **46.00 tok/s** | **13.63 s** | 14.086 MiB | Aprovado | **Líder Principal** |
| **Jack-3.8-27B-Coder (Nativo)** | **4/6** | 2/3 | 2/3 | 7.92 tok/s | 130.68 s | 13.049 MiB | Reprovado (4/6 < 5/6) | **NÃO_COMPENSA** |
| **Whittle-MoE-27B-A18B (Nativo)** | **1/6** | 1/3 | 0/3 | 19.39 tok/s | 45.97 s | 15.194 MiB | Reprovado (1/6 < 5/6) | **NÃO_COMPENSA** |

---

## Detalhamento Caso a Caso

### Jack-3.8-27B-Coder-16GB-VRAM (Nativo)

| Caso | Nome | Linguagem | Compile | Public | Hidden | Status | tok/s | Wall (s) | Pico VRAM |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **PY01** | `ttl_cache_injected_clock` | Python | PASS | PASS | PASS | **PASS** | 8.18 | 135.68 | 13.049 MiB |
| **PY02** | `retry_decorator_repair` | Python | PASS | PASS | PASS | **PASS** | 8.12 | 125.68 | 12.865 MiB |
| **PY03** | `deterministic_dependency_order` | Python | PASS | FAIL | FAIL | **FAIL** | 7.64 | 210.75 | 12.947 MiB |
| **CPP01** | `normalize_int64_ranges` | C++20 | PASS | PASS | PASS | **PASS** | 8.22 | 105.74 | 12.947 MiB |
| **CPP02** | `sliding_window_statistics_repair` | C++20 | PASS | PASS | PASS | **PASS** | 7.73 | 172.60 | 12.916 MiB |
| **CPP03** | `lazy_segment_tree_affine` | C++20 | FAIL | FAIL | FAIL | **FAIL** | 7.42 | 294.21 | 12.961 MiB |

*Falhas do Jack*:
- `PY03`: Quebra no desempate lexicográfico dinâmico de dependências topológicas.
- `CPP03`: Falha de compilação C++ (chave de fechamento faltando ao final da struct).
- Velocidade: Muito penalizada pelo template agentic que injeta tokens de contexto de estado operacional.

### Whittle-MoE-27B-A18B-v2.2.1-Q3_K_M (Nativo)

| Caso | Nome | Linguagem | Compile | Public | Hidden | Status | tok/s | Wall (s) | Pico VRAM |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **PY01** | `ttl_cache_injected_clock` | Python | PASS | FAIL | FAIL | **FAIL** | 21.29 | 10.37 | 15.059 MiB |
| **PY02** | `retry_decorator_repair` | Python | PASS | PASS | PASS | **PASS** | 22.04 | 7.78 | 15.075 MiB |
| **PY03** | `deterministic_dependency_order` | Python | FAIL | FAIL | FAIL | **FAIL** | 18.20 | 85.30 | 15.194 MiB |
| **CPP01** | `normalize_int64_ranges` | C++20 | FAIL | FAIL | FAIL | **FAIL** | 18.88 | 66.44 | 14.985 MiB |
| **CPP02** | `sliding_window_statistics_repair` | C++20 | PASS | FAIL | FAIL | **FAIL** | 19.90 | 25.50 | 14.993 MiB |
| **CPP03** | `lazy_segment_tree_affine` | C++20 | FAIL | FAIL | FAIL | **FAIL** | 15.95 | 130.06 | 15.043 MiB |

*Falhas do Whittle*:
- `PY01`: Remoção prematura de chaves não expiradas.
- `PY03`: `SyntaxError: closing parenthesis ')' does not match opening parenthesis '['`.
- `CPP01`: `error: ‘std::int64_t’ is not a class, namespace, or enumeration` (falta include `<cstdint>`).
- `CPP02`: Timeout na execução do teste público (> 5s).
- `CPP03`: Assinatura de método `apply` duplicada e conflitante na struct.

---

## Conclusão Final

- **Jack-3.8-27B-Coder-16GB-VRAM**: `NÃO_COMPENSA`
- **Whittle-MoE-27B-A18B**: `NÃO_COMPENSA`
- **Modelo Principal Mantido**: `Qwen3.8-27B GSQ-RCO IQ2_S + DFlash2 Q4_K_M` (6/6 PASS, 46.00 tok/s).
