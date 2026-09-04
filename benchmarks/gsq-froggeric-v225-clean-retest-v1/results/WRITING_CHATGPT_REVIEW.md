# ChatGPT Writing Review — GSQ Froggeric v22.5 Clean Retest v1

## Basis

This review closes the `PENDING_CHATGPT_REVIEW` status from the clean retest without inventing a new rubric.

The clean-retetst Arm E (Native) and Arm F (Froggeric v22.5) produced byte-identical text for all 6 writing generations. Those same-seed clean-retetest texts also match the canonical historical `gsq_iq2s_base` outputs already audited in `benchmarks/chat-writing-v1/results/QUALITATIVE_REVIEW.json`.

Therefore the correct procedure is to reuse the existing canonical qualitative scores for those exact texts instead of rescoring them with a different heuristic.

## Canonical per-run scores reused

| Prompt | Rep | Seed | Historical canonical score | Native clean retest | Froggeric v22.5 clean retest |
|---|---:|---:|---:|---:|---:|
| neutral | 1 | 9137 | 3.50 / 5 | 3.50 / 5 | 3.50 / 5 |
| adult | 1 | 9137 | 3.25 / 5 | 3.25 / 5 | 3.25 / 5 |
| adult | 2 | 9138 | 3.25 / 5 | 3.25 / 5 | 3.25 / 5 |
| neutral | 2 | 9138 | 4.00 / 5 | 4.00 / 5 | 4.00 / 5 |
| neutral | 3 | 9139 | 4.00 / 5 | 4.00 / 5 | 4.00 / 5 |
| adult | 3 | 9139 | 3.25 / 5 | 3.25 / 5 | 3.25 / 5 |

## Aggregates

For both Native and Froggeric v22.5:

- Neutral: **3.83 / 5**
- Adult: **3.25 / 5**
- Overall: **3.54 / 5**

Result: **exact writing-quality parity** for the tested non-thinking condition.

## Interpretation

Froggeric v22.5 does not improve or degrade writing quality in this benchmark because the actual generated texts are identical to Native for all 6 writing runs.

The throughput deltas observed in the clean retest must be preserved as measurements from that session, but they should not be attributed causally to the template from this single sequential-arm run. The direction is inconsistent across workloads and even across individual writing pairs. The clean-GPU gate removes heavy external contention, but it does not remove run-order, clock, thermal, or power-state variance.

In particular, the earlier claim that the standalone coding slowdown is caused by Jinja parsing overhead is unsupported by these measurements. Jinja/template rendering occurs before generation and the recorded `predicted_per_second` metric is a decode throughput metric; the benchmark did not isolate template parsing cost.

The benchmark also does not test tool-calling behavior. Froggeric upstream advertises tool-calling support, but local tool-calling correctness must remain `N/A / not tested` until a dedicated local benchmark exists.

## Final decision

- Writing quality: **PARITY — 3.54 / 5 for both Native and Froggeric v22.5**.
- Coding correctness: **PARITY — 6/6 for both**.
- DFlash2 correctness/acceptance: **PARITY — 6/6 and 86.9% median acceptance**.
- Performance attribution: **INCONCLUSIVE for template effect**; preserve measured session values but do not treat them as causal template speedups/slowdowns.
- Recommended default: **Native embedded template**, because it produces the same tested outputs with the simplest deployment path.
- Froggeric v22.5: **validated as functionally compatible for this non-thinking chat/coding condition**, not as locally superior and not yet as locally validated for tool-calling.
