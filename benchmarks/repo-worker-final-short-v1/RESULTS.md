# Benchmark Results — Repo-Worker Short Final Candidates (v1)

## Executive Summary
This short comparative benchmark evaluated 4 candidate profiles on 6 realistic software engineering agentic tasks (navigation, bugfixing, multi-file refactoring, error recovery, and feature implementation).

## Consolidated Metrics Table

| Métrica | Ornith OFF | Bonsai ON+DSpark | Mini-Me Q3 (Minitron 20B) | Vireqo Corrected |
|---|---:|---:|---:|---:|
| Tasks passed / 6 | 6 / 6 | 4 / 6 | 5 / 6 | 4 / 6 |
| Pass rate | 100.0% | 66.7% | 83.3% | 66.7% |
| Successful edits | 11 | 6 | 13 | 11 |
| Tool errors | 2 | 9 | 7 | 20 |
| Recovery rate | 100.0% | 55.6% | 71.4% | 40.0% |
| Avg time | 115.8s | 216.4s | 145.0s | 26.9s |
| Median time | 67.6s | 187.0s | 154.6s | 25.6s |
| Decode tok/s | 38.52 t/s | 33.58 t/s | 42.11 t/s | 107.60 t/s |
| Prompt tok/s | 64.56 t/s | 56.87 t/s | 67.49 t/s | 184.43 t/s |
| Peak VRAM | 8434 MiB | 13631 MiB | 10776 MiB | 9229 MiB |
| Successful tasks/hour | 31.09 | 11.09 | 20.69 | 89.16 |

## Final Ranking
- **1º Lugar (Vencedor Geral - Confiabilidade & Precisão)**: `Ornith 1.5 9B (Thinking OFF)` — 100% de taxa de acerto (6/6), 100% de taxa de recuperação, sem falhas de protocolo.
- **2º Lugar (Melhor Equilíbrio de Capacidade & Escopo)**: `Qwen3.8-20B-Minitron IQ3_M` — 83.3% de taxa de acerto (5/6), 13 edições bem sucedidas, execução robusta.
- **Destaque em Throughput Bruto**: `Vireqo-27B-Plus` — Altíssima velocidade em contexto 2048 (107.6 t/s decode), mas com maior taxa de erros de protocolo (20 erros) em raciocínios multi-turn.
- **3º/4º Lugar (Heavyweight & Reasoning)**: `Ternary Bonsai 27B` — 66.7% de taxa de acerto (4/6), mais lento devido ao overhead de reasoning tokens em tarefas curtas.
