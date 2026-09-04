# GSQ Froggeric v22.5 Clean Retest v1 — Summary

## 1. Overview

Clean-GPU retest of **Froggeric v22.5** (`chat_template.jinja`, upstream commit `4ea21db90694e60d002500dae85ebff26e4b23ad`, internal version `qwen3.8-froggeric-v22.5`) against fresh paired Native controls on `Qwen3.8-27B GSQ-RCO IQ2_S`.

- Target: `Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf`
- Draft: `Qwen3.8-27B-DFlash2-Q4_K_M.gguf`
- Froggeric SHA256: `e57684bae4156211a55473c5a63be976a405a37ab5be5ae0e5abf1df5349c4b2`
- Runtime: llama.cpp `0.3.0-dev`, build `10752`, commit `b96806d96`
- Froggeric integration: `--jinja --chat-template-file ... --reasoning-format deepseek --chat-template-kwargs '{"enable_thinking":false,"reasoning_effort":"none"}'`
- Clean-GPU gate: passed before all 6 arms; snapshots are preserved under `results/gpu-preflight/`.

## 2. Primary paired results

| Arm | Configuration | Workload | Score / PASS | Median tok/s | Measured delta | Peak VRAM | Draft acceptance | Mean accepted length |
|---|---|---|:---:|---:|---:|---:|:---:|:---:|
| A | GSQ Native | Coding | **6/6** | 21.02 | baseline | 11613 MiB | N/A | 1.00 |
| B | GSQ + Froggeric v22.5 | Coding | **6/6** | 15.51 | -26.2% | 11601 MiB | N/A | 1.00 |
| C | GSQ + DFlash2 n=7 Native | Coding | **6/6** | 33.63 | baseline | 14465 MiB | 86.9% | 7.08 |
| D | GSQ + DFlash2 n=7 + Froggeric v22.5 | Coding | **6/6** | 37.54 | +11.6% | 14508 MiB | 86.9% | 7.08 |
| E | GSQ Native | Writing | **3.54/5** | 13.92 | baseline | 11710 MiB | N/A | N/A |
| F | GSQ + Froggeric v22.5 | Writing | **3.54/5** | 17.77 | +27.7% | 11958 MiB | N/A | N/A |

The throughput deltas above are preserved as measurements from this session. They are **not** interpreted as causal template speedups/slowdowns; see §5.

## 3. Correctness and output identity

### Coding

- Arm A vs B: both **6/6 PASS**.
- Arm C vs D: both **6/6 PASS**.
- For all 6 A/B coding pairs, the final raw response and extracted code were byte-identical.
- For all 6 C/D DFlash2 coding pairs, the final raw response and extracted code were byte-identical.
- DFlash2 acceptance was identical case-by-case between C and D; median acceptance was **86.9%** and mean accepted length aggregate was **7.08**.

This proves equality of the recorded final outputs for these benchmark requests. It does **not** by itself prove that the rendered prompt/prefix token streams were byte-identical, because the benchmark did not record and compare the fully rendered tokenized prompts.

### Writing

All 6 Arm E/F writing pairs were byte-identical. In addition, those same-seed clean-retest texts match the canonical historical `gsq_iq2s_base` outputs already audited in `benchmarks/chat-writing-v1/results/QUALITATIVE_REVIEW.json`.

Therefore no new subjective rubric was introduced. The existing canonical scores for the exact same texts were reused:

| Prompt | Rep | Score |
|---|---:|---:|
| neutral | 1 | 3.50/5 |
| adult | 1 | 3.25/5 |
| adult | 2 | 3.25/5 |
| neutral | 2 | 4.00/5 |
| neutral | 3 | 4.00/5 |
| adult | 3 | 3.25/5 |

Aggregates for both Native and Froggeric v22.5:

- Neutral: **3.83/5**
- Adult: **3.25/5**
- Overall: **3.54/5**

Canonical review closure: `results/WRITING_CHATGPT_REVIEW.md`.

## 4. Case-by-case coding throughput

| Case | A Native | B Froggeric | C DF2 Native | D DF2 Froggeric | D acceptance |
|---|---:|---:|---:|---:|:---:|
| PY01 | 20.60 | 20.66 | 41.44 | 36.51 | 173/189 (91.5%) |
| PY02 | 22.48 | 13.10 | 44.39 | 52.98 | 129/147 (87.8%) |
| PY03 | 21.81 | 15.82 | 30.72 | 32.31 | 437/784 (55.7%) |
| CPP01 | 21.44 | 16.35 | 26.60 | 30.91 | 617/1064 (58.0%) |
| CPP02 | 20.44 | 15.20 | 28.85 | 45.09 | 412/455 (90.5%) |
| CPP03 | 14.28 | 13.77 | 36.54 | 38.57 | 1019/1183 (86.1%) |

## 5. Performance interpretation

The clean-GPU gate successfully removed the previous heavy external-GPU-load confound. However, this benchmark used one sequential pass per arm, so it does not isolate template cost from run-order, GPU clocks, thermal state, power state, or other within-session variance.

The measured direction is also inconsistent:

- standalone coding: Froggeric measured slower;
- DFlash2 coding: Froggeric measured faster;
- writing: Froggeric measured faster overall, while the first neutral pair was slower.

Because the generated outputs were identical for every paired request, these speed differences should be treated as **session observations**, not evidence that Froggeric itself causes a ±N% decode-speed change.

The earlier attribution of the standalone slowdown to "Jinja parsing overhead" is unsupported. Template rendering happens before generation and this benchmark did not separately measure Jinja rendering cost. The primary throughput metric is `timings.predicted_per_second`, a decode throughput metric.

No extra rerun is required for the model-selection decision: output quality and correctness are already resolved. A separate interleaved/repeated performance microbenchmark would only be necessary if exact template-overhead attribution becomes important.

## 6. Final decision

- Coding correctness: **PARITY** — 6/6 Native and 6/6 Froggeric.
- Writing quality: **PARITY** — 3.54/5 Native and 3.54/5 Froggeric.
- DFlash2 correctness/acceptance: **PARITY** — 6/6 and 86.9% median acceptance.
- Performance effect of the template: **INCONCLUSIVE** from this sequential single-pass design.
- Default deployment: **KEEP_NATIVE** because it produces the same tested outputs with the simplest deployment path.
- Froggeric v22.5 status: **functionally compatible and correctly integrated for the tested non-thinking chat/coding condition**.
- Tool-calling: upstream Froggeric advertises tool-calling support, but this benchmark did not test local tool-calling correctness; local status remains **N/A / not tested**.
