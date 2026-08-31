# Benchmark Results — Repo-Worker Short Final Candidates (v1)

## Resumo Executivo
Benchmark comparativo focado em capacidades reais de **repo-worker** (navegação em repositório, diagnóstico e bugfix algorítmico, refatoração multi-arquivo, recuperação de erros de ferramenta/testes e implementação incremental de features).

Avaliação de 4 perfis candidatos com execução em 4 threads e offload completo em GPU (NVIDIA GeForce RTX 5060 Ti 16GB).

---

## 1. Avaliação A/B de Thinking no Qwen3.8-20B-Minitron IQ3_M

Para determinar de forma justa o melhor modo operacional do **Qwen3.8-20B-Minitron IQ3_M**, foi executada uma bateria A/B dedicada (3 microtarefas agentic: navegação cega, bugfix e recuperação com pytest):

- **Microteste A/B (3 tasks)**:
  - **M-OFF (`--reasoning off`)**: 2 / 3 PASS (falhou na navegação cega de caminhos, mas executou bugfix e recovery com precisão rápida).
  - **M-ON (`--reasoning on`)**: 3 / 3 PASS (conseguiu passar as 3 tarefas, demonstrando raciocínio prévio útil em busca de caminhos).

- **Benchmark Completo de 6 Tasks (M-OFF vs M-ON)**:
  - **M-OFF**: **5 / 6 PASS (83.3%)** — 13 edições bem-sucedidas, completou refatorações multi-arquivo complexas (T4) com 25 turns, falhando apenas no recovery de caminho inexistente (T5).
  - **M-ON**: **4 / 6 PASS (66.7%)** — 4 edições bem-sucedidas; o modo ON perdeu o foco em tarefas de múltiplos arquivos devido à saturação de raciocínio antes de cada chamada de ferramenta.

- **Conclusão de Seleção**:
  - `MINITRON_SELECTED_MODE=OFF` (proporciona maior taxa de sucesso global de 83.3% vs 66.7% e maior capacidade de edições multi-file).

---

## 2. Tabela Comparativa Consolidada (Benchmark Final Curto)

| Métrica | Ornith OFF | Bonsai ON+DSpark | Qwen3.8-20B-Minitron IQ3_M (OFF) | Qwen3.8-20B-Minitron IQ3_M (ON) | Vireqo Corrected |
|---|---:|---:|---:|---:|---:|
| Tasks passed / 6 | 6 / 6 | 4 / 6 | 5 / 6 | 4 / 6 | 4 / 6 |
| Pass rate | 100.0% | 66.7% | 83.3% | 66.7% | 66.7% |
| Successful edits | 11 | 6 | 13 | 4 | 11 |
| Tool errors | 2 | 9 | 7 | 3 | 20 |
| Recovery rate | 100.0% | 55.6% | 71.4% | 33.3% | 40.0% |
| Avg time | 115.8s | 216.4s | 145.0s | 109.7s | 26.9s |
| Median time | 67.6s | 187.0s | 154.6s | 121.3s | 25.6s |
| Decode tok/s | 38.52 t/s | 33.58 t/s | 42.11 t/s | 50.86 t/s | 107.60 t/s |
| Prompt tok/s | 64.56 t/s | 56.87 t/s | 67.49 t/s | 85.62 t/s | 184.43 t/s |
| Peak VRAM | 8434 MiB | 13631 MiB | 10776 MiB | 10766 MiB | 9229 MiB |
| Successful tasks/hour | 31.09 | 11.09 | 20.69 | 21.88 | 89.16 |

---

## 3. Vencedores da Rodada Curta

```text
WINNER_SHORT_BENCH=Ornith 1.5 9B Q5_K_M (Thinking OFF)
SECOND_PLACE=Qwen3.8-20B-Minitron IQ3_M (Thinking OFF)
```
