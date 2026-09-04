# GSQ Froggeric Ablation v1 — Summary

## 1. Overview

Determines whether the canonical Froggeric v22.4 chat template improves the current `Qwen3.8-27B GSQ-RCO IQ2_S` operating point across Coding, Writing, and Speculative Decoding (DFlash2).

- **Target Model**: `Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf`
- **Draft Model**: `Qwen3.8-27B-DFlash2-Q4_K_M.gguf`
- **Froggeric Template**: `chat_template.jinja` (SHA256: `c47c82b0...`, version: `qwen3.8-froggeric-v22.4`)

## 2. Direct Comparison Table

| Track / Configuration | Score / PASS | Mediana tok/s | Speed Delta | Peak VRAM | Draft Acc Mediana | Mean Acc Length |
|---|:---:|---:|---:|---:|:---:|:---:|
| **1. GSQ Native Coding (Histórico)** | **6/6** | 24.70 t/s | baseline | 11216 MiB | N/A | 1.00 |
| **2. GSQ + Froggeric Coding (Novo)** | **6/6** | 19.78 t/s | -19.9% | 12213 MiB | N/A | 1.00 |
| **3. GSQ + DFlash2 n=7 Native (Histórico)** | **6/6** | 46.00 t/s | baseline | 14086 MiB | 86.9% | ~6.50 |
| **4. GSQ + DFlash2 n=7 + Froggeric (Novo)** | **6/6** | 46.38 t/s | +0.8% | 14374 MiB | 86.9% | 7.08 |
| **5. GSQ Native Writing (Histórico)** | **3.54/5.0** (N:3.83, A:3.25) | 20.40 t/s | baseline | 10985 MiB | N/A | N/A |
| **6. GSQ + Froggeric Writing (Novo)** | **3.52/5.0** (N:3.42, A:3.62) | 21.30 t/s | +4.4% | 11700 MiB | N/A | N/A |

## 3. Case-by-Case Breakdown

### Coding Cases (Arm A vs Histórico & Arm C vs Histórico)

| Caso | GSQ Native | GSQ + Froggeric | GSQ+DF2 Native | GSQ+DF2+Froggeric | Froggeric Coding t/s | DF2+Froggeric t/s | DF2 Acc Ratio |
|---|:---:|:---:|:---:|:---:|---:|---:|:---:|
| **PY01** | PASS | **PASS** | PASS | **PASS** | 15.98 t/s | 56.67 t/s | 173/189 |
| **PY02** | PASS | **PASS** | PASS | **PASS** | 18.22 t/s | 58.69 t/s | 129/147 |
| **PY03** | PASS | **PASS** | PASS | **PASS** | 22.57 t/s | 38.34 t/s | 437/784 |
| **CPP01** | PASS | **PASS** | PASS | **PASS** | 22.02 t/s | 35.73 t/s | 617/1064 |
| **CPP02** | PASS | **PASS** | PASS | **PASS** | 21.13 t/s | 50.28 t/s | 412/455 |
| **CPP03** | PASS | **PASS** | PASS | **PASS** | 18.43 t/s | 42.47 t/s | 1019/1183 |

### Writing Runs (Arm B vs Histórico)

| Prompt / Repetition | Palavras | Speed (t/s) | Qualidade (1–5) | Flags Comportamentais |
|---|---:|---:|:---:|---|
| **neutral r1 (seed 9137)** | 661 | 19.38 | 3.38 | WORD_COUNT_OUT |
| **adult r1 (seed 9137)** | 568 | 21.42 | 3.62 | CLEAN |
| **adult r2 (seed 9138)** | 609 | 21.52 | 3.62 | WORD_COUNT_OUT |
| **neutral r2 (seed 9138)** | 687 | 20.89 | 3.38 | WORD_COUNT_OUT |
| **neutral r3 (seed 9139)** | 623 | 21.19 | 3.50 | WORD_COUNT_OUT |
| **adult r3 (seed 9139)** | 421 | 22.22 | 3.62 | WORD_COUNT_OUT |

## 4. Conclusão Final

**Decisão**: `KEEP_NATIVE`

- O template nativo permanece como padrão. O Froggeric v22.4 não trouxe ganho material suficiente ou causou regressões em relação aos controles já validados.
