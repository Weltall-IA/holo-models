# score-completion-template-ablation-v1 — Writing Summary

Avaliação qualitativa e de velocidade dos candidatos de escrita contra o controle histórico **Qwen3.8-27B Fable Distill Heretic ARA Q3_K_M**.
Configuração: seed 9137/9138/9139, temperature 0.8, top_p 0.95, min_p 0.05, repeat_penalty 1.05, max_tokens 1536, ctx 8192, 8 threads, full GPU offload, Flash Attention ON.

## 1. Ranking Consolidado de Escrita / Narração (Ordenado por Nota Descendente)

| Posição | Modelo / Preset | Qualidade Geral (1–5) | Neutral (1–5) | Adult (1–5) | tok/s mediano | Peak VRAM | Status / Observações |
|:---:|---|:---:|:---:|:---:|:---:|:---:|---|
| **1º** | **[Controle] Qwen3.8-27B Fable Heretic Q3_K_M** | **4.92** | 4.92 | 4.92 | ~15.8 tok/s | 15696 MiB | Topo absoluto em qualidade literária |
| **2º** | **[Controle] Qwen3.8-27B Heretic RVN IQ3_M** | **4.38** | 4.50 | 4.25 | ~17.5 tok/s | 14930 MiB | Prosa densa e sensorial |
| **3º** | **[Controle] Qwen3.8-27B Uncensored YMQ S-Pro** | **4.27** | 4.17 | 4.38 | ~17.5 tok/s | 14111 MiB | Excelente ritmo e erotismo maduro |
| **4º** | **Qwen3.8-27B Escha-W2 (Q8E) Native** | **3.63** | 3.88 | 3.38 | 14.63 tok/s | 13444 MiB | Prosa sólida; ecoa restrições no fim |
| **4º** | **Qwen3.8-27B Escha-W2 (Q8E) + Froggeric v22.4** | **3.63** | 3.88 | 3.38 | 14.56 tok/s | 13444 MiB | Saída idêntica à Native sob reasoning off |
| **5º** | **[Controle] Qwen3.8-27B GSQ IQ2_S Base** | **3.54** | 3.83 | 3.25 | ~20.4 tok/s | 10985 MiB | Estável e econômico em VRAM |
| **6º** | **Nanbeige4.2-3B Q4_K_M** | **3.25** | 3.38 | 3.12 | 18.68 tok/s | 4519 MiB | Bom fluxo PT-BR; insere títulos markdown |
| **7º** | **[Controle] Qwen3.8-9B Distill Heretic Q4_K_M** | **3.15** | 3.25 | 3.04 | ~40.0 tok/s | 6950 MiB | Fluente, porém melodramático e explicativo |
| **8º** | **Spark-X2.5-4B Q4_K_M** | **2.94** | 3.00 | 2.88 | 34.52 tok/s | 4520 MiB | Rápido, mas textos curtos (<400w) com títulos |
| **9º** | **[Controle] Qwythos-9B-Mythos Q4_K_M** | **2.23** | 2.20 | 2.25 | ~36.8 tok/s | 7912 MiB | Prolixo em reasoning, truncado e suavizado |

