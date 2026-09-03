# candidate-round-v1

Purpose: evaluate the new local candidates in one compact campaign, reusing the already-versioned benchmark cases/prompts. Do not invent new benchmark cases.

## Scope

Exactly 30 new generations:

- Coding: 4 candidate models × the existing 6 `coding-mini-v1` cases = 24 runs.
- Writing: 1 candidate model × the existing 2 `chat-writing-v1` prompts × 3 existing seeds = 6 runs.

Historical controls are reused from existing results and MUST NOT be rerun:

- Coding control: `Qwen3.8-27B GSQ-RCO IQ2_S + DFlash2`.
- Writing control: `Qwen3.8-27B Fable Distill Heretic ARA Q3_K_M`.

## Coding candidates

### C1 — Nanbeige4.2-3B Q4_K_M

Preferred repository:

`bartowski/Nanbeige_Nanbeige4.2-3B-GGUF`

Quant:

`Q4_K_M`

Expected weight file size: about 2.68 GB.

Use the existing stock `llama.cpp` runtime if it is b10380 or newer. The current benchmark runtime should be newer than that; verify before running.

### C2 — Ornith-1.5-9B existing local GGUF

Do NOT download another Ornith merely to normalize quantization.

Locate the existing local Ornith-1.5-9B GGUF and record its exact path, quantization, size, and SHA-256. If multiple copies exist, prefer the best already-downloaded quant in this order:

1. Q6_K
2. Q5_K_M
3. Q4_K_M

Do not use an older Ornith generation.

### C3 — Spark-X2.5-4B Q4_K_M

Preferred source model:

`XHToken/Spark-X2.5-4B`

Preferred GGUF quant:

`Q4_K_M`

If the official GGUF repository does not expose that exact file through the local downloader, use a verified Q4_K_M conversion pinned to the same source revision. Record repository, revision, file name and SHA-256.

Expected weight file size: about 2.60 GB.

### C4 — Qwen3.8-27B Escha-W2 GGUF

Repository:

`aj9o9/Qwen3.8-27B-Escha-W2-GGUF`

File:

`Escha-Qwen3.8-27B-W2-Q8E.gguf`

This is NOT a Q8 quantization of the whole 27B and MUST NOT be described as such. The Escha payload remains native mixed W2 (2.469 bpw); `Q8E` refers to the embedding/output-head storage choice.

Expected file size: about 10.31 GB.

Stock llama.cpp cannot load this model. Use the repository's required `escha-w2-dense` llama.cpp fork in a separate runtime directory. Do not replace or modify the normal benchmark llama.cpp runtime.

The Escha fork currently has no supported DFlash2 path for this model. Run Escha without DFlash2.

## Coding benchmark contract

Reuse exactly:

- `benchmarks/coding-mini-v1/CASES.md`
- the corrected evaluators already committed for `coding-mini-v1`
- the same prompts and max-token limits
- seed `9137`
- temperature `0.2`
- top_p `0.95`
- context `8192`
- 8 CPU threads
- Flash Attention on
- full GPU offload when supported
- K cache q8_0
- V cache q4_0 when supported by the runtime

Do not change case semantics, public tests, hidden tests, reference solutions or scoring.

For every candidate, capture:

- PASS/FAIL by case
- compile/syntax result
- public result
- hidden result
- predicted tok/s
- wall time
- peak VRAM MiB
- exact model file SHA-256
- runtime build/commit
- reasoning mode actually used

Primary coding comparison:

- C1 Nanbeige
- C2 Ornith
- C3 Spark
- C4 Escha
- historical GSQ + DFlash2 control

No composite score combining speed and correctness.

## Writing candidate

### W1 — Qwythos-9B-Claude-Mythos-5-1M Q4_K_M

Repository:

`empero-ai/Qwythos-9B-Claude-Mythos-5-1M-GGUF`

File:

`Qwythos-9B-Claude-Mythos-5-1M-Q4_K_M.gguf`

Expected file size: about 5.24 GiB / 5.63 GB.

Do not download Q8. Do not use the MTP variant in this round; this run is to establish writing quality first.

Qwythos is a reasoning model and may emit `<think>...</think>`. Use native reasoning parsing if supported so that `reasoning_content` is kept separate from user-visible story content. The qualitative review MUST judge only the final story content, not hidden reasoning. Record reasoning token/time overhead separately when available.

## Writing benchmark contract

Reuse exactly the existing `chat-writing-v1` prompts, seeds, target lengths, sampling settings and output checks used for the Fable writing run.

Run only Qwythos:

- neutral × repetitions 1–3
- adult × repetitions 1–3

Total: 6 writing generations.

Do not rerun Fable.

Capture the same speed, VRAM, refusal, word-count and behavior fields used by the existing writing benchmark, plus separated reasoning metrics if available.

After generation, perform the same qualitative review dimensions previously used for the writing benchmark. Fable's historical outputs remain the comparison control.

## Preflight

Before any model generation:

1. `git status` must be inspected; do not overwrite unrelated local changes.
2. Verify the corrected coding references still report:
   - `REFERENCE_PUBLIC_PASS=6/6`
   - `REFERENCE_HIDDEN_PASS=6/6`
   - `CPP03_DIFFERENTIAL_PASS=200/200`
3. Verify all four coding model files and the Qwythos file exist before starting their respective run. Download only missing files.
4. For Ornith, use the already-present local model as specified above.
5. Verify each runtime can load its model with a minimal warmup before launching the benchmark.
6. If one candidate has a runtime incompatibility, record it as an infrastructure blocker for that candidate; do not weaken or alter the benchmark to make it pass.

## Output artifacts

Create under:

`benchmarks/candidate-round-v1/results/`

At minimum:

- `CODING_RESULTS.jsonl`
- `CODING_SUMMARY.md`
- `WRITING_RESULTS.jsonl`
- `WRITING_QUALITATIVE_REVIEW.json`
- `WRITING_SUMMARY.md`
- `RUN_MANIFEST.json`

`CODING_SUMMARY.md` must compare the four new coding candidates against the historical GSQ+DFlash2 control without modifying the historical result files.

`WRITING_SUMMARY.md` must compare Qwythos against the historical Fable results without modifying the historical result files.

## Hard prohibitions

- Do not create new benchmark cases.
- Do not rerun the five-model `coding-mini-v1` suite.
- Do not rerun GSQ+DFlash2.
- Do not rerun Fable.
- Do not use Q8 for Nanbeige, Spark or Qwythos.
- Do not redownload Ornith if a valid Ornith-1.5-9B GGUF is already present.
- Do not silently substitute another model family/version.
- Do not alter old raw results.
