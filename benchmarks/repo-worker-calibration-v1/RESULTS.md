# Calibration Benchmark Results (repo-worker-calibration-v1)

## Consolidated Results Table

| Métrica | B1 | B2 | B3 | B4 | O1 | O2 | Q1 22.62B | Q2 Vireqo Plus |
|---|---|---|---|---|---|---|---|---|
| **Tasks Passed** | 0 / 3 | 2 / 3 | 1 / 3 | 2 / 3 | **3 / 3** | 1 / 3 | 1 / 3 | 1 / 3 |
| **Task 1 (Navegação)** | FAIL | FAIL | FAIL | FAIL | **PASS** (201s) | FAIL | FAIL | FAIL |
| **Task 2 (Bugfix)** | FAIL | **PASS** (599s) | **PASS** (138s) | **PASS** (118s) | **PASS** (11s) | **PASS** (241s) | **PASS** (160s) | **PASS** (46s) |
| **Task 3 (Multi-file)** | FAIL | **PASS** (240s) | FAIL | **PASS** (264s) | **PASS** (51s) | FAIL | FAIL | FAIL |
| **Successful Edits** | 0 | 8 | 1 | 7 | 7 | 1 | 5 | 1 |
| **Tool Errors** | 25 | 6 | 4 | 0 | 0 | 3 | 1 | 43 |
| **Recovery Rate** | 40.0% | 66.7% | 25.0% | 100.0% | 100.0% | 33.3% | 100.0% | 9.3% |
| **Total Tool Calls** | 75 | 38 | 63 | 27 | 33 | 28 | 29 | 28 |
| **Reasoning Tokens** | 0 | 2678 | 0 | 1511 | 0 | 5523 | 1507 | 0 |
| **Output Tokens** | 1863 | 5519 | 1220 | 3373 | 1314 | 10030 | 3243 | 2031 |
| **Avg End-to-End Time** | 564.4s | 479.9s | 446.0s | 329.8s | 87.9s | 480.0s | 455.4s | 283.3s |
| **Avg Decode Throughput** | 10.28 t/s | 14.90 t/s | 11.14 t/s | 15.40 t/s | 31.53 t/s | 26.52 t/s | 5.41 t/s | 12.73 t/s |
| **Avg Prompt Throughput** | 24.30 t/s | 47.16 t/s | 30.07 t/s | 52.19 t/s | 193.58 t/s | 169.47 t/s | 36.11 t/s | 44.98 t/s |
| **Peak VRAM** | 10498 MiB | 10490 MiB | 13349 MiB | 13349 MiB | 9371 MiB | 9931 MiB | 15768 MiB | 10866 MiB |
| **Tasks / Hour** | 0.00 | 5.00 | 2.69 | 7.28 | **40.96** | 2.50 | 2.63 | 4.24 |

---

## Detailed Task Summaries

### Task 1: Navigation
- **Objetivo**: Descobrir o fluxo completo de roteamento do papel `project-rw` a partir de `model-bindings.yaml` até as instruções do agente e o contrato.
- **Resultados**:
  - `O1`: **PASS** (localizou os 4 arquivos em 9 tool calls, 201s).
  - Demais perfis: atingiram timeout de 600s explorando o repositório.

### Task 2: Bugfix
- **Objetivo**: Corrigir erro de contagem de tentativas em `fixture/retry.py` (`range(attempts + 1)` -> `range(attempts)`).
- **Resultados**:
  - `B2`: **PASS** (599s)
  - `B3`: **PASS** (138s)
  - `B4`: **PASS** (118s)
  - `O1`: **PASS** (11s)
  - `O2`: **PASS** (241s)
  - `Q1`: **PASS** (160s)
  - `Q2`: **PASS** (46s)

### Task 3: Multi-file Mechanical Rename
- **Objetivo**: Renomear chave `tool_timeout_seconds` para `tool_timeout_s` em 5 arquivos do fixture (`settings.py`, `settings.pyi`, `config.json`, `test_settings.py`, `README.md`) e validar com pytest.
- **Resultados**:
  - `B2`: **PASS** (240s)
  - `B4`: **PASS** (264s)
  - `O1`: **PASS** (51s)
  - Demais perfis: timeouts ou alterações parciais.
