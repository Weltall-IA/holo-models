# Benchmark Results — Repo-Worker Short Final Candidates (v1)

## Resumo Executivo
Benchmark comparativo focado em capacidades reais de **repo-worker** (navegação em repositório, diagnóstico e bugfix algorítmico, refatoração multi-arquivo, recuperação de erros de ferramenta/testes e implementação incremental de features).

Avaliação com execução em 4 threads e offload completo em GPU (NVIDIA GeForce RTX 5060 Ti 16GB).

---

## 1. Avaliação do Qwen3.8-9B-Distill-uncensored-heretic Q4_K_M
O **Qwen3.8-9B Uncensored** obteve desempenho impecável:
- **Taxa de acerto**: **6 / 6 PASS (100.0%)**
- **Tempo médio por tarefa**: **43.6s** (mediana: **15.5s**) — quase 3x mais rápido que Ornith 1.5 9B e 5x mais rápido que Bonsai 27B.
- **Taxa de recuperação**: **100.0%** (recuperou imediatamente dos 3 erros de navegação/busca sem travar).
- **VRAM**: Apenas **7,313 MiB** com contexto de 32K tokens.
- **Throughput real de decode em servidor**: **91.92 t/s**.

---

## 2. Tabela Comparativa Consolidada

| Métrica | Ornith 1.5 9B (OFF) | Qwen3.8-9B Uncensored (OFF) | Ternary Bonsai 27B (ON+DSpark) | Qwen3.8-20B-Minitron (OFF) | Vireqo-27B-Plus (Corrected) |
|---|---:|---:|---:|---:|---:|
| Tasks passed / 6 | 6 / 6 | 6 / 6 | 4 / 6 | 5 / 6 | 4 / 6 |
| Pass rate | 100.0% | 100.0% | 66.7% | 83.3% | 66.7% |
| Successful edits | 11 | 9 | 6 | 13 | 11 |
| Tool errors | 2 | 3 | 9 | 7 | 20 |
| Recovery rate | 100.0% | 100.0% | 55.6% | 71.4% | 40.0% |
| Avg time | 115.8s | 43.6s | 216.4s | 145.0s | 26.9s |
| Median time | 67.6s | 15.5s | 187.0s | 154.6s | 25.6s |
| Decode tok/s | 38.52 t/s | 91.92 t/s | 33.58 t/s | 42.11 t/s | 107.60 t/s |
| Prompt tok/s | 64.56 t/s | 154.49 t/s | 56.87 t/s | 67.49 t/s | 184.43 t/s |
| Peak VRAM | 8434 MiB | 7313 MiB | 13631 MiB | 10776 MiB | 9229 MiB |
| Successful tasks/hour | 31.09 | 82.57 | 11.09 | 20.69 | 89.16 |

---

## 3. Ranking Final e Conclusão

```text
WINNER_SHORT_BENCH=Qwen3.8-9B-Distill-uncensored-heretic (Thinking OFF)
RUNNER_UP=Ornith 1.5 9B Q5_K_M (Thinking OFF)
THIRD_PLACE=Qwen3.8-20B-Minitron IQ3_M (Thinking OFF)
```

- **Qwen3.8-9B Uncensored** demonstrou ser o melhor candidato para worker de repositório: 100% de precisão (6/6), tempo de resolução ultrarrápido (15.5s de mediana), 82.5 tarefas com sucesso por hora e baixíssimo consumo de VRAM (7.3 GB em 32K de contexto).
