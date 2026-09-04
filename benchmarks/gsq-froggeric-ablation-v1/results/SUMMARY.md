# GSQ Froggeric Ablation v1 — Summary

## Status da auditoria

As 18 gerações do benchmark foram executadas e os braços de código são válidos para comparação com os controles históricos. A etapa de **avaliação qualitativa de writing**, porém, não seguiu o contrato do `SPEC.md`: o runner criou uma heurística própria com notas parcialmente fixas/derivadas de contagem de palavras e palavras-chave, em vez de aplicar a mesma auditoria qualitativa usada em `chat-writing-v1`.

Consequência: o valor `3.52/5.0` produzido por `WRITING_QUALITATIVE_REVIEW.json` **não é comparável** ao controle histórico `3.54/5.0` e não deve ser usado para decidir `KEEP_NATIVE` vs `SPLIT_PRESETS`.

Os textos já gerados permanecem válidos. **Não é necessário rerodar as 6 gerações de writing**; basta reavaliar as saídas existentes com a mesma rubrica cega de `benchmarks/chat-writing-v1/results/QUALITATIVE_REVIEW.json`.

## 1. Overview

Objetivo: determinar se o template canônico Froggeric v22.4 melhora o ponto operacional atual do `Qwen3.8-27B GSQ-RCO IQ2_S` em Coding, Writing e Speculative Decoding (DFlash2).

- **Target Model**: `Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf`
- **Draft Model**: `Qwen3.8-27B-DFlash2-Q4_K_M.gguf`
- **Froggeric Template**: `chat_template.jinja` (SHA256 `c47c82b0544752d454f4e427228d9d9d8c3df64c9e446cbd0229362f67948009`, versão `qwen3.8-froggeric-v22.4`)
- **Execução registrada**: commit `de6fe06b9656350cc037052a8be8154e14387a4e`

## 2. Comparação válida

| Track / Configuração | Score / PASS | Mediana tok/s | Delta | Pico VRAM | Draft Acc. mediana | Mean Acc. Length |
|---|:---:|---:|---:|---:|:---:|:---:|
| **GSQ Native Coding (histórico)** | **6/6** | 24.70 | baseline | 11,216 MiB | N/A | N/A |
| **GSQ + Froggeric Coding** | **6/6** | 19.78 | **-19.9%** | 12,213 MiB | N/A | N/A |
| **GSQ + DFlash2 n=7 Native (histórico)** | **6/6** | 46.00 | baseline | 14,086 MiB | 86.9% | ~6.50 |
| **GSQ + DFlash2 n=7 + Froggeric** | **6/6** | 46.38 | **+0.8%** | 14,374 MiB | 86.9% | 7.08 |
| **GSQ Native Writing (histórico)** | **3.54/5.0** | 20.40 | baseline | 10,985 MiB | N/A | N/A |
| **GSQ + Froggeric Writing** | **QUALITATIVE REVIEW INVALID/PENDING** | 21.30 | **+4.4% throughput** | 11,700 MiB | N/A | N/A |

### Interpretação

- **Código sem draft:** Froggeric preservou 6/6, mas caiu de 24.70 para 19.78 tok/s (**-19.9%**) e elevou o pico de VRAM. O template nativo é claramente preferível aqui.
- **Código com DFlash2 n=7:** Froggeric preservou 6/6 e ficou essencialmente empatado em throughput com o nativo (46.38 vs 46.00 tok/s). O ganho de +0.8% não é material e veio com +288 MiB de pico de VRAM.
- **Writing:** as 6 gerações são utilizáveis para revisão qualitativa posterior. A mediana de throughput foi 21.30 tok/s e 5/6 saídas ficaram fora da faixa de 425–575 palavras. A nota 3.52 gerada pelo runner é descartada como evidência comparável.

## 3. Coding — caso a caso

| Caso | GSQ Native | GSQ + Froggeric | GSQ+DF2 Native | GSQ+DF2+Froggeric | Froggeric t/s | DF2+Froggeric t/s | DF2 Acc Ratio |
|---|:---:|:---:|:---:|:---:|---:|---:|:---:|
| **PY01** | PASS | **PASS** | PASS | **PASS** | 15.98 | 56.67 | 173/189 |
| **PY02** | PASS | **PASS** | PASS | **PASS** | 18.22 | 58.69 | 129/147 |
| **PY03** | PASS | **PASS** | PASS | **PASS** | 22.57 | 38.34 | 437/784 |
| **CPP01** | PASS | **PASS** | PASS | **PASS** | 22.02 | 35.73 | 617/1064 |
| **CPP02** | PASS | **PASS** | PASS | **PASS** | 21.13 | 50.28 | 412/455 |
| **CPP03** | PASS | **PASS** | PASS | **PASS** | 18.43 | 42.47 | 1019/1183 |

## 4. Writing — métricas objetivas preservadas

| Prompt / Repetição | Palavras | Speed (t/s) | Status de faixa |
|---|---:|---:|---|
| neutral r1 | 661 | 19.38 | fora |
| adult r1 | 568 | 21.42 | dentro |
| adult r2 | 609 | 21.52 | fora |
| neutral r2 | 687 | 20.89 | fora |
| neutral r3 | 623 | 21.19 | fora |
| adult r3 | 421 | 22.22 | fora |

Não usar as notas do arquivo `WRITING_QUALITATIVE_REVIEW.json` como score canônico até uma reavaliação com a rubrica histórica.

## 5. Decisão

### Padrão operacional de código

**`KEEP_NATIVE`** para código.

O template nativo continua sendo o preset recomendado do GSQ, especialmente sem DFlash2. Com DFlash2, Froggeric é compatível, mas não oferece ganho material que justifique substituir o nativo.

### Decisão global do benchmark

**`WRITING_REVIEW_REQUIRED`**.

Ainda não é válido concluir `KEEP_NATIVE` vs `SPLIT_PRESETS` para writing porque a avaliação qualitativa nova não é comparável ao controle histórico. Nenhuma nova geração é necessária; somente a revisão das 6 saídas existentes.