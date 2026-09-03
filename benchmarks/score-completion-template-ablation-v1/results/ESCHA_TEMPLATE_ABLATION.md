# Ablação de Template: Escha-W2 Native vs Froggeric v22.4

Comparação direta entre o template embutido nativo do `Escha-Qwen3.8-27B-W2-Q8E` e o `Froggeric v22.4` (`qwen3.8-froggeric-v22.4`, SHA256 `c47c82b0...`).
Ambos executados no runtime isolado `escha-llama` (commit `2940b80`) sob `reasoning off` com as mesmas sementes.

## 1. Código: Comparativo de Casos

| Caso | Escha Native | Escha + Froggeric v22.4 | Efeito do Template |
|---|:---:|:---:|---|
| **PY01** (`ttl_cache_injected_clock`) | **PASS** (13.50 t/s, 16.65s) | **PASS** (15.45 t/s, 14.51s) | Idêntico resultado funcional (+14% velocidade) |
| **PY02** (`retry_decorator_repair`) | **PASS** (13.25 t/s, 17.97s) | **PASS** (15.30 t/s, 15.28s) | Idêntico resultado funcional (+15% velocidade) |
| **PY03** (`deterministic_dependency_order`) | **PASS** (13.25 t/s, 48.11s) | **PASS** (15.00 t/s, 42.62s) | Idêntico resultado funcional (+13% velocidade) |
| **CPP01** (`normalize_int64_ranges`) | **PASS** (12.34 t/s, 80.90s) | **PASS** (14.35 t/s, 69.82s) | Idêntico resultado funcional (+16% velocidade) |
| **CPP02** (`sliding_window_statistics_repair`) | **PASS** (12.28 t/s, 49.89s) | **PASS** (14.41 t/s, 42.57s) | Idêntico resultado funcional (+17% velocidade) |
| **CPP03** (`lazy_segment_tree_affine`) | **FAIL** (11.60 t/s, 105.51s) | **FAIL** (13.64 t/s, 89.71s) | Ambos falharam no hidden test diferencial |

## 2. Escrita: Comparativo de Textos e Pontuação

| Prompt / Repetição | Escha Native (Palavras / Score) | Escha + Froggeric v22.4 (Palavras / Score) | Identidade Textual |
|---|:---:|:---:|---|
| **Neutral r1 (seed 9137)** | 436 palavras (3.88/5) | 436 palavras (3.88/5) | **Byte-idêntico** |
| **Adult r1 (seed 9137)** | 575 palavras (3.38/5) | 575 palavras (3.38/5) | **Byte-idêntico** |
| **Adult r2 (seed 9138)** | 483 palavras (3.38/5) | 483 palavras (3.38/5) | **Byte-idêntico** |
| **Neutral r2 (seed 9138)** | 503 palavras (3.88/5) | 503 palavras (3.88/5) | **Byte-idêntico** |
| **Neutral r3 (seed 9139)** | 594 palavras (3.88/5) | 594 palavras (3.88/5) | **Byte-idêntico** |
| **Adult r3 (seed 9139)** | 652 palavras (3.38/5) | 652 palavras (3.38/5) | **Byte-idêntico** |

## 3. Conclusão da Ablação

1. **Em Escrita (Reasoning OFF)**: O template Froggeric v22.4 e o template nativo embutido renderizam prefixos idênticos quando o raciocínio está desativado, produzindo exatamente as mesmas gerações textuais com nota média **3.63/5**.
2. **Em Código**: O Froggeric v22.4 manteve os mesmos **5/6** acertos do preset nativo, com uma ligeira vantagem de throughput (+13% a +17% de tok/s) devido ao formato mais enxuto de prefixo.

