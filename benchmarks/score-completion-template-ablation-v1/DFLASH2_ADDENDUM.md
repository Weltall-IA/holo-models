# DFlash2 addendum — score-completion-template-ablation-v1

This addendum is intentionally separate from `PLAN.md` because the original benchmark is already running. Do **not** restart, alter, or invalidate any currently running arm.

Run these extra DFlash2 arms only after the currently running work reaches a safe boundary / finishes. Reuse every existing canonical case and evaluator unchanged.

## Goal

Measure whether the existing Qwen3.8-27B DFlash2 draft improves the Escha W2-Q8E coding preset, including the already-canonical Froggeric v22.4 template.

No new coding cases. No new writing prompts. No native-baseline reruns.

## Fixed artifacts

Target:

`/home/alpha/Playstoria/models/text/aj9o9-Qwen3.8-27B-Escha-W2-GGUF/Escha-Qwen3.8-27B-W2-Q8E.gguf`

Draft:

`/home/alpha/Playstoria/models/text/z-lab-Qwen3.8-27B-DFlash2-GGUF/Qwen3.8-27B-DFlash2-Q4_K_M.gguf`

Froggeric template:

`/home/alpha/Playstoria/models/text/froggeric-Qwen-Fixed-Chat-Templates-v22.4/chat_template.jinja`

Froggeric expected SHA256:

`c47c82b0544752d454f4e427228d9d9d8c3df64c9e446cbd0229362f67948009`

Canonical coding cases/evaluators:

- `benchmarks/coding-mini-v1/CASES.md`
- corrected existing coding-mini evaluators

## Runtime requirement

Use only the isolated Escha runtime tree:

`/home/alpha/Playstoria/models/engines/escha-llama/`

Do not replace `/home/alpha/.local/bin/llama` and do not modify the DFlash2 GGUF to make it load.

The current Escha fork commit `2940b807c1562552ae3e152d73f6105f0ac0c98a` has the older DFlash implementation and previously failed on the official Qwen3.8 DFlash2 GGUF with `expected 81, got 58`.

For this addendum, that failure is **not** a terminal benchmark result. The runtime may be updated/patched inside the isolated Escha tree to port the official upstream DFlash2 support, while preserving the Escha target-model implementation.

Reference implementation: upstream llama.cpp PR `#27342` (`spec: add DFlash2 support (local convolution + candidate selector)`, merged commit `4a6ad487a6f7c615a5d5662be9248694a9ac1254`). Port the actual DFlash2 runtime support, not a tensor-count bypass.

After any runtime change, record:

- Escha base commit
- DFlash2 upstream commit/PR used
- resulting local commit or patch hash
- build command
- exact `llama-server --version`

Build `llama-server` only, CUDA enabled, max `-j8`.

## Gate before scoring

Before benchmark runs, prove the exact target + exact DFlash2 draft can:

1. load successfully;
2. complete one minimal generation;
3. report DFlash2 speculative counters/acceptance;
4. exit without model-load, tensor-shape, CUDA, or sampler errors.

Use DFlash2 via:

- `--spec-type draft-dflash`
- `--spec-draft-n-max 7`

Do not call the old 58-tensor DFlash path DFlash2.

If the runtime port itself fails, record the blocker and stop only these extra DFlash2 arms. Do not touch the already-running benchmark.

## Extra benchmark arms

Run exactly two additional coding presets.

### D1 — Escha W2-Q8E + DFlash2 + native template

Run the existing 6 corrected `coding-mini-v1` cases once each.

Keep the same coding controls already used by this benchmark:

- seed 9137
- temperature 0.2
- top_p 0.95
- reasoning off
- context 8192
- 8 CPU threads
- full GPU offload
- Flash Attention ON
- K cache q8_0
- V cache q4_0 when supported
- `--spec-type draft-dflash`
- `--spec-draft-n-max 7`

Total: **6 new generations**.

### D2 — Escha W2-Q8E + DFlash2 + Froggeric v22.4

Run the same 6 corrected coding cases once each with the same settings as D1, adding only:

- `--jinja`
- `--chat-template-file /home/alpha/Playstoria/models/text/froggeric-Qwen-Fixed-Chat-Templates-v22.4/chat_template.jinja`
- `--reasoning off`
- `--chat-template-kwargs '{"reasoning_effort":"none"}'`

Total: **6 new generations**.

## Generation budget

Additional work from this addendum only:

- D1: 6 coding generations
- D2: 6 coding generations

Total: **12 new generations**, plus one minimal compatibility smoke.

Do not rerun Escha native, Escha+Froggeric without DFlash2, GSQ+DFlash2, Fable, Spark, Nanbeige, or writing arms as part of this addendum.

## Metrics to record

For each generation retain the existing coding correctness result plus:

- output tokens
- decode tok/s
- wall time
- peak VRAM MiB
- speculative drafted tokens
- speculative accepted tokens
- acceptance rate / accepted tokens per draft block when exposed by runtime

Summarize D1 and D2 against the already-existing corresponding non-DFlash2 Escha results; do not rerun those controls.

## Output

Append/add DFlash2-specific artifacts under:

`benchmarks/score-completion-template-ablation-v1/results/`

At minimum:

- `DFLASH2_CODING_RESULTS.jsonl`
- `DFLASH2_CODING_SUMMARY.md`
- `DFLASH2_RUNTIME_PORT.md`

Do not overwrite historical result rows. If integrating into a combined ranking, preserve provenance and mark these as addendum runs.

## Hard prohibitions

- Do not interrupt or restart the benchmark already running.
- Do not invent new cases.
- Do not change prompts/evaluators to accommodate DFlash2.
- Do not delete or alter DFlash2 tensors.
- Do not silently fall back to ordinary DFlash.
- Do not replace the global stock llama runtime.
- Do not use more than 8 build/runtime CPU threads.
