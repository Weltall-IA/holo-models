# Benchmark Results — Repo-Worker Short Final Candidates (v1)

## Resumo Executivo
Benchmark comparativo focado em capacidades reais de **repo-worker** (navegação em repositório, diagnóstico e bugfix algorítmico, refatoração multi-arquivo, recuperação de erros de ferramenta/testes e implementação incremental de features).

Avaliação com execução em 4 threads e offload completo em GPU (NVIDIA GeForce RTX 5060 Ti 16GB).

---

## 1. Avaliação Comparativa: Qwen 3.8 9B (Thinking OFF vs Thinking ON)

O **Qwen3.8-9B-Distill-uncensored-heretic Q4_K_M** foi testado de forma completa em ambos os modos operacionais nas 6 tarefas:

1. **Thinking OFF (`--reasoning off`)**:
   - **6 / 6 PASS (100.0%)**
   - **Tempo médio**: **43.6s** (mediana: **15.5s**)
   - **Throughput**: **82.57 tarefas com sucesso por hora**
   - **Comportamento**: Ações diretas e imediatas via chamadas de ferramenta JSON, com 100% de taxa de recuperação em erros.

2. **Thinking ON (`--reasoning on`)**:
   - **5 / 6 PASS (83.3%)**
   - **Tempo médio**: **110.1s** (mediana: **57.7s**)
   - **Throughput**: **27.26 tarefas com sucesso por hora**
   - **Comportamento**: Ganhou tempo na Task 1 de navegação (148.4s vs 168.7s), mas atingiu timeout de 360s na Task 6 por excesso de raciocínio encadeado antes de cada edição.

**Conclusão de Perfil**: O modo **Thinking OFF** é substancialmente superior para worker de repositório no Qwen 3.8 9B (100% de sucesso vs 83.3% e 3x mais rápido).

---

## 2. Tabela Comparativa Consolidada

| Métrica | Qwen3.8-9B (Thinking OFF) | Qwen3.8-9B (Thinking ON) | Ornith 1.5 9B (Thinking OFF) | Ternary Bonsai 27B (ON+DSpark) |
|---|---:|---:|---:|---:|
| **Tasks passed / 6** | **6 / 6** | 5 / 6 | **6 / 6** | 4 / 6 |
| **Pass rate** | **100.0%** | 83.3% | **100.0%** | 66.7% |
| **Successful edits** | 9 | 14 | 11 | 6 |
| **Tool errors** | 3 | 7 | 2 | 9 |
| **Recovery rate** | **100.0%** | 85.7% | **100.0%** | 55.6% |
| **Avg time** | **43.6s** | 110.1s | 115.8s | 216.4s |
| **Median time** | **15.5s** | 57.7s | 67.6s | 187.0s |
| **Decode tok/s** | **91.92 t/s** | 95.61 t/s | 38.52 t/s | 33.58 t/s |
| **Prompt tok/s** | **154.49 t/s** | 160.98 t/s | 64.56 t/s | 56.87 t/s |
| **Peak VRAM** | **7,313 MiB** | 7,468 MiB | 8,434 MiB | 13,631 MiB |
| **Successful tasks/hour** | **82.57** | 27.26 | 31.09 | 11.09 |

---

## 3. Ranking Final dos Melhores Modelos

```text
WINNER_REPO_WORKER=Qwen3.8-9B-Distill-uncensored-heretic Q4_K_M (Thinking OFF)
SECOND_PLACE=Ornith 1.5 9B Q5_K_M (Thinking OFF)
THIRD_PLACE=Qwen3.8-9B-Distill-uncensored-heretic Q4_K_M (Thinking ON)
```
