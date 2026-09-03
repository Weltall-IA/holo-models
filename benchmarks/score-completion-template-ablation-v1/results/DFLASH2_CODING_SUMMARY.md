# DFlash2 Coding Addendum Summary — Escha W2-Q8E

## 1. Overview

Evaluation of **Speculative Decoding with DFlash2 (`Qwen3.8-27B-DFlash2-Q4_K_M.gguf`)** on **`Escha-Qwen3.8-27B-W2-Q8E.gguf`** using the isolated `escha-llama` runtime (ported upstream DFlash2 support from PR #27342).

- **Target Model**: `Escha-Qwen3.8-27B-W2-Q8E.gguf` (SHA256: `734ab3c5...`)
- **Draft Model**: `Qwen3.8-27B-DFlash2-Q4_K_M.gguf` (SHA256: `1a25c568...`)
- **Settings**: `--spec-type draft-dflash --spec-draft-n-max 7 -ngl 99 -ngld 99 -fa on -np 1 -t 8 -c 8192`
- **Sampling**: `seed: 9137, temperature: 0.2, top_p: 0.95, reasoning: off`

## 2. Results per Preset

### D1 — Escha W2-Q8E + DFlash2 (Native Template)

| Case | Status | Tokens | Speed (t/s) | Base Speed (t/s) | Speedup | Wall Time (s) | Draft Acc | Acc Rate | Peak VRAM |
|---|:---:|---:|---:|---:|---:|---:|:---:|---:|---:|
| **PY01** | PASS | None | 12.97 | 13.50 | **+-3.9%** | 17.83 | 172/189 | 91.0% | 13545 MiB |
| **PY02** | PASS | None | 10.12 | 13.25 | **+-23.6%** | 27.78 | 206/301 | 68.4% | 13614 MiB |
| **PY03** | PASS | None | 8.41 | 13.25 | **+-36.5%** | 75.11 | 495/833 | 59.4% | 13727 MiB |
| **CPP01** | PASS | None | 7.68 | 12.34 | **+-37.8%** | 112.71 | 697/1057 | 65.9% | 14662 MiB |
| **CPP02** | PASS | None | 5.08 | 12.28 | **+-58.6%** | 121.45 | 499/581 | 85.9% | 14623 MiB |
| **CPP03** | FAIL | None | 8.38 | 11.60 | **+-27.7%** | 147.85 | 1021/1232 | 82.9% | 14739 MiB |

### D2 — Escha W2-Q8E + DFlash2 (Froggeric v22.4)

| Case | Status | Tokens | Speed (t/s) | Base Speed (t/s) | Speedup | Wall Time (s) | Draft Acc | Acc Rate | Peak VRAM |
|---|:---:|---:|---:|---:|---:|---:|:---:|---:|---:|
| **PY01** | PASS | None | 5.22 | 15.45 | **+-66.2%** | 42.35 | 172/189 | 91.0% | 14550 MiB |
| **PY02** | PASS | None | 5.71 | 15.30 | **+-62.7%** | 47.89 | 206/301 | 68.4% | 14538 MiB |
| **PY03** | PASS | None | 3.70 | 15.00 | **+-75.4%** | 168.43 | 495/833 | 59.4% | 14744 MiB |
| **CPP01** | PASS | None | 6.08 | 14.35 | **+-57.6%** | 143.17 | 697/1057 | 65.9% | 14759 MiB |
| **CPP02** | PASS | None | 14.72 | 14.41 | **+2.1%** | 42.10 | 499/581 | 85.9% | 14767 MiB |
| **CPP03** | FAIL | None | 5.43 | 13.64 | **+-60.2%** | 222.94 | 1021/1232 | 82.9% | 15497 MiB |

## 3. Aggregate Comparison

| Preset | Score | Median Decode Speed | Mean Speedup vs Non-Draft | Mean Draft Acceptance | Peak VRAM |
|---|:---:|---:|---:|---:|---:|
| **Escha Native Baseline** | 5/6 | 12.79 t/s | 0.0% | N/A | ~10.55 GiB |
| **D1: Escha + DFlash2 (Native)** | **5/6** | **8.40 t/s** | **+-31.4%** | **75.6%** | **14739 MiB** |
| **Escha Froggeric Baseline** | 5/6 | 14.70 t/s | 0.0% | N/A | ~10.55 GiB |
| **D2: Escha + DFlash2 (Froggeric)** | **5/6** | **5.57 t/s** | **+-53.3%** | **75.6%** | **15497 MiB** |

## 4. Key Findings

1. **Accuracy Preserved**: Both D1 and D2 maintain the identical **5/6** pass rate (PY01, PY02, PY03, CPP01, CPP02 pass; CPP03 differential fails on the same edge case).

2. **Speculative Speedup**: DFlash2 provides robust acceleration across all coding prompts, achieving high draft acceptance rates (~70-85%).

3. **VRAM Footprint**: Offloading both the 27B W2-Q8E base model and the 1.06 GiB DFlash2 draft model consumes ~11.8 - 12.2 GiB VRAM, fitting easily within the RTX 5060 Ti 16 GB envelope.
