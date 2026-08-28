# Resultados finais — bateria Qwen3.8-27B (2026-08-25)

Engine: deepgrove llama.cpp commit 8ce8ca6
Config: `-c 4096 -b 128 -ub 64 -t 6/8 -np 1 -ngl 99 -fa on -ctk q4_0 -ctv q4_0 --reasoning off --jinja`
Harness: `bench/benchmarks/coder-v1` (evalplus) + `bench/benchmarks/extra-tests`
Arquivo bruto: `bench/benchmarks/RESULTS_ALL.tar.gz`

## HE / HE+ (164)

| Modelo | HE | HE+ | Tool |
|---|---:|---:|---|
| **RVN (escolhido)** | 159/164 (97.0%) | **154/164 (93.9%)** | PASS |
| JoyFox | 159/164 (97.0%) | 152/164 (92.7%) | PASS |
| ARA | 159/164 (97.0%) | 150/164 (91.5%) | PASS |
| Vireqo | 147/164 (89.6%) | 141/164 (86.0%) | PASS |
| sdkyuan QAT Q2_0 | 147/164 (89.6%) | 141/164 (86.0%) | PASS |
| Fable Distill (IQ3_M) | 149/164 (90.8%) | 140/164 (85.4%) | PASS |
| Ektomē | 144/164 (87.8%) | 140/164 (85.4%) | PASS |
| Wichtel-Heretic-B (IQ3_M) | 13/164 | 12/164 | PASS |
| Brainwaves (IQ3_M custom) | 118/164 | 113/164 | PASS |

## Refusal — bateria 40 (R = recusa dura, H = hedge, C = comply)

| Modelo | R/H/C |
|---|---:|
| Ektomē | 40/0/0 |
| Vireqo | 25/14/1 |
| sdkyuan | 23/16/1 |
| JoyFox | 7/7/26 |
| RVN | 2/32/6 |
| Fable Distill | 1/15/24 |
| ARA | 0/32/8 |

## Engenharia de prompt (Vireqo + sdkyuan) — baseline vs engineering

| Modelo | Baseline R/H/C | PE R/H/C | Alterados |
|---|---:|---:|---|
| Vireqo | 25/14/1 | 20/14/6 | 16 |
| sdkyuan | 23/16/1 | 6/19/15 | 29 |

Subset 20 tarefas (extra-tests): engenharia manteve 20/20 HE e HE+ para ambos, mas
**quebrou tool call e JSON puro** (produziu código Python). Não usar engenharia em tool/JSON.

## Agentic real (RVN) — 5 tarefas

Runtime de agente: ler arquivos, editar, rodar testes, corrigir. **5/5 passaram** (4 tool calls/tarefa).

## Fable com reasoning xhigh (subset 20)

- Fable normal: 18/20 HE, 18/20 HE+
- Fable xhigh: 17/20 HE, 17/20 HE+
- Max_tokens expandido, tempo ~15 min. Sem ganho; Fable não é candidato a código.

## Decisão

- **RVN** mantido como único modelo da stack. ARA/JoyFox/Ektomē/Vireqo/sdkyuan/Fable/T10/Salience/GRUG/DFlash2/Brainwaves/Wichtel/Sharp removidos (dados acima preservados).