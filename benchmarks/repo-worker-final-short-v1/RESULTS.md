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

---

## 4. Avaliação dos Qwen3.8-27B GSQ-RCO (IQ2_S e IQ3_XXS)

Ambos os modelos **ISTA-DASLab/Qwen3.8-27B-GSQ-RCO** foram avaliados nas 6 tarefas nos dois modos (Thinking OFF e Thinking ON), com contexto 32768, KV Q8_0/Q4_0, FA ON, 4 threads e full GPU offload.

### Preflight
| Modelo | SHA256 | Tamanho | PP512 | TG128 | Peak VRAM |
|---|---|---:|---:|---:|---:|
| GSQ-RCO IQ2_S | `16c9802111aa9ef3acde465188d6d601f8db128ee3d828ad983a5caca4135ecb` | 9,259,510,912 B | 210.09 t/s | 31.14 t/s | 11,901 MiB |
| GSQ-RCO IQ3_XXS | `fdfcb6a29b11188956dfbfd904223588a6c1b77eb250c3e8a36e1bd269df91f7` | 10,094,357,632 B | 212.99 t/s | 29.93 t/s | 13,700 MiB |

Sanidade: `17*23=391` PASS, `Paris` PASS em ambos.

### Resultados das 6 Tasks

| Métrica | GSQ IQ2_S (OFF) | GSQ IQ2_S (ON) | GSQ IQ3_XXS (OFF) | GSQ IQ3_XXS (ON) | Qwen 9B Heretic (OFF) | Ornith 1.5 9B (OFF) |
|---|---:|---:|---:|---:|---:|---:|
| **Tasks passed / 6** | 5 / 6 | 5 / 6 | **6 / 6** | **6 / 6** | **6 / 6** | **6 / 6** |
| **Successful edits** | 8 | 10 | 8 | 10 | 9 | 11 |
| **Tool errors** | 2 | 2 | 2 | 3 | 3 | 2 |
| **Recovery rate** | 50.0% | 50.0% | 50.0% | 66.7% | **100.0%** | **100.0%** |
| **Avg time** | **80.4s** | 111.9s | 132.2s | 121.0s | **43.6s** | 115.8s |
| **Median time** | 64.8s | 79.9s | 35.2s | 73.9s | **15.5s** | 67.6s |
| **Decode tok/s (server)** | — | 49.84 t/s | 45.18 t/s | 46.61 t/s | **91.92 t/s** | 38.52 t/s |
| **Prompt tok/s (server)** | — | 81.11 t/s | 71.57 t/s | 76.37 t/s | **154.49 t/s** | 64.56 t/s |
| **Peak VRAM** | 11,901 MiB | 11,388 MiB | 13,700 MiB | 12,050 MiB | **7,313 MiB** | 8,434 MiB |
| **Contexto usado** | 32768 | 32768 | 32768 | 32768 | 32768 | 32768 |
| **Tasks/hour** | **37.32** | 26.80 | 27.23 | 29.74 | **82.57** | 31.09 |

### Conclusões GSQ-RCO
1. **IQ3_XXS é o melhor dos dois GSQ**: 6/6 PASS em ambos os modos (OFF e ON), enquanto o IQ2_S falhou consistentemente na T1 (navegação) nos dois modos — indício de perda de capacidade de recuperação de contexto longo na quantização mais agressiva.
2. **Thinking ON no IQ3_XXS** melhora levemente a taxa de recuperação (66.7% vs 50.0%) sem perder tasks, mas custa ~10% mais tempo médio.
3. **Nenhum GSQ-RCO supera o Qwen 9B Heretic**: o modelo de 9B mantém 100% de acerto com 2x o throughput (82.57 vs ~29 tasks/hour) e metade da VRAM.
