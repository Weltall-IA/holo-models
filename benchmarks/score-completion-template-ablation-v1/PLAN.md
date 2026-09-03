# score-completion-template-ablation-v1

Purpose: complete missing coding/writing scores for the remaining local candidates, evaluate the current Froggeric template on Escha, and empirically probe Escha+DFlash2 compatibility without weakening any benchmark.

## Historical anchors

Reuse, do not modify or rerun unless explicitly listed below:

- `benchmarks/coding-mini-v1/CASES.md`
- corrected coding evaluators/results
- `benchmarks/chat-writing-v1/` prompts, seeds and qualitative rubric
- `benchmarks/candidate-round-v1/` results at commit `9c08ccf4f52b261b7ac569d96fc24fd00211e75d`

Historical control results remain authoritative:

- Fable Heretic Q3_K_M: coding 5/6, writing 4.92/5
- GSQ IQ2_S + DFlash2: coding 6/6
- GSQ IQ2_S base: coding 6/6, writing 3.54/5
- Qwen3.8 9B Heretic: coding 3/6, writing 3.15/5
- Nanbeige4.2-3B Q4_K_M: coding 5/6
- Escha Qwen3.8-27B W2-Q8E native: coding 5/6
- Spark-X2.5-4B: prior coding attempt is BLOCKED/NOT SCORED because the stock runtime did not support `spark2_5`

## Cleanup requested by user

The following model weights are no longer needed and may be deleted from local storage after confirming the historical benchmark artifacts are committed and untouched:

1. `/home/alpha/Playstoria/models/text/empero-ai-Qwythos-9B-Claude-Mythos-5-1M-GGUF/`
2. `/home/alpha/Playstoria/models/text/bartowski-Ornith-1.5-9B-Q5_K_M/`

Do NOT delete their historical benchmark results.
Do NOT delete shared blobs unless exclusivity is proven.
Report physical GiB reclaimed.

## Froggeric template — canonical choice

Use exactly the restored current template:

`/home/alpha/Playstoria/models/text/froggeric-Qwen-Fixed-Chat-Templates-v22.4/chat_template.jinja`

Pinned revision:

`e649070`

Expected SHA256:

`c47c82b0544752d454f4e427228d9d9d8c3df64c9e446cbd0229362f67948009`

Expected internal version:

`qwen3.8-froggeric-v22.4`

For llama.cpp / llama.cpp-escha, use the root `.jinja` file with:

- `--jinja`
- `--chat-template-file <path-above>`

Do NOT treat `chat_template_oneline.txt` as a separate quality variant: it is the minified/equivalent form intended for embedding/engines that need one-line text.
Do NOT benchmark archived v22/v22.1/v22.2/v22.3 templates unless a later regression investigation explicitly asks for them.

### Non-reasoning benchmark controls

For the coding and writing benchmarks in this plan, keep reasoning disabled so template is the only behavioral variable:

- `--reasoning off`
- `--chat-template-kwargs '{"reasoning_effort":"none"}'`

Do not enable Froggeric's default `medium` reasoning in these ablations.

## Runtime isolation

### Stock models

Use the existing known-good stock runtime:

`/home/alpha/.local/bin/llama`

for Nanbeige and other already-supported stock architectures.

### Escha

Use only the already-built isolated Escha runtime:

`/home/alpha/Playstoria/models/engines/escha-llama/build/bin/llama-server`

from Ajay9o9 `llama.cpp-escha`, branch `escha-w2-dense`.
Record its exact current git commit before running.
Do not replace the stock runtime.

### Spark

The current upstream stock runtime does not yet support `spark2_5`. Build a second isolated runtime only for Spark from the implementation branch/PR that adds Spark2_5 support.

Pin the implementation used for this round to commit:

`fe158c6c4db8b0cb8d74c7cfe23401f7c21a45fe`

Keep it under:

`/home/alpha/Playstoria/models/engines/spark-llama/`

Compile CUDA for the local GPU and `llama-server` only, max `-j8`.
Do not overwrite `/home/alpha/.local/bin/llama` or the Escha runtime.

Before scoring Spark, verify a minimal warmup loads the existing local GGUF:

`/home/alpha/Playstoria/models/text/sizzlebop-Spark-X2.5-4B-GGUF/Spark-X2.5-4B-Q4_K_M.gguf`

If the pinned runtime cannot load it, record an infrastructure blocker and do not change the benchmark or silently substitute a different Spark model.

## Required new scoring runs

### A. Complete missing writing scores

Use exactly the existing `chat-writing-v1` contract: same neutral/adult prompts, seeds 9137/9138/9139, temperature 0.8, top_p 0.95, min_p 0.05, repeat_penalty 1.05, max_tokens 1536, ctx 8192, 8 threads, full GPU offload, Flash Attention ON.

Run 6 writing generations for each:

1. Nanbeige4.2-3B Q4_K_M — native/embedded template
2. Escha-Qwen3.8-27B-W2 Q8E — native/embedded template
3. Spark-X2.5-4B Q4_K_M — native/embedded template

Total: 18 generations.

Apply the same qualitative dimensions already used in `chat-writing-v1`, producing a directly comparable 1–5 writing score.

### B. Complete Spark coding score

Run Spark-X2.5-4B Q4_K_M through exactly the 6 existing corrected `coding-mini-v1` cases.

Configuration:

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

Total: 6 generations.

This replaces the prior `BLOCKED` entry with a real score only if all six generations are actually executable.

### C. Escha + Froggeric v22.4

Evaluate one additional Escha preset:

`Escha W2-Q8E + Froggeric v22.4`

Use the Escha runtime plus the canonical Froggeric root Jinja template specified above.

Run:

- 6 existing coding cases
- 6 existing writing generations (2 prompts x 3 seeds)

Total: 12 generations.

Coding and writing settings must otherwise match the historical native Escha runs exactly.

The purpose is to isolate the chat-template effect. Do not change sampling, reasoning, context, KV quantization or model weights at the same time.

## Escha + DFlash2 compatibility probe

The Escha GGUF port's author documents that the current `escha-w2-dense` fork does NOT implement the full Qwen3.8 DFlash2 checkpoint path: DFlash2 has additional convolution/selector tensors beyond the older DFlash implementation.

Therefore do NOT claim an Escha+DFlash2 benchmark variant exists unless the local Escha runtime proves it can load the exact existing DFlash2 file.

Existing draft file:

`/home/alpha/Playstoria/models/text/z-lab-Qwen3.8-27B-DFlash2-GGUF/Qwen3.8-27B-DFlash2-Q4_K_M.gguf`

Perform one isolated startup/warmup compatibility probe using:

- Escha W2-Q8E as target
- the exact DFlash2 file above as draft
- `--spec-type draft-dflash`
- `--spec-draft-n-max 7`

Do not run benchmark cases unless target + draft both load and at least one minimal generation succeeds with draft counters/acceptance visible.

If it fails because DFlash2 tensors/modules are unsupported, record:

`ESCHA_DFLASH2_STATUS=BLOCKED_RUNTIME_UNSUPPORTED`

and stop that arm. Do not strip tensors, requantize, patch benchmark prompts, or call the older 58-tensor DFlash path "DFlash2".

If it unexpectedly succeeds, record the exact runtime commit and then run the same 6 coding cases. Do not run writing until coding confirms stable operation.

## Generation budget

Expected normal new generations:

- missing writing scores: 18
- Spark coding: 6
- Escha + Froggeric: 12

Total normal: 36 new generations.

Escha+DFlash2 adds zero benchmark generations if blocked; at most 6 coding generations if the compatibility probe genuinely succeeds.

## Output artifacts

Create:

`benchmarks/score-completion-template-ablation-v1/results/`

At minimum:

- `CODING_RESULTS.jsonl`
- `CODING_SUMMARY.md`
- `WRITING_RESULTS.jsonl`
- `WRITING_QUALITATIVE_REVIEW.json`
- `WRITING_SUMMARY.md`
- `ESCHA_TEMPLATE_ABLATION.md`
- `ESCHA_DFLASH2_PROBE.md`
- `RUN_MANIFEST.json`
- `CLEANUP_REPORT.md`

The final summaries must show two separate rankings, both sorted by score descending:

1. Coding ranking — PASS/6
2. Writing ranking — qualitative score /5

Use `N/A` only for configurations that genuinely have no score; never turn an infrastructure blocker into 0/6.

## Hard prohibitions

- Do not invent new coding cases or writing prompts.
- Do not alter historical outputs.
- Do not rerun already-scored native presets except where this plan explicitly asks for the missing writing score.
- Do not substitute archived Froggeric templates for v22.4.
- Do not call the oneline Froggeric file a separate quality variant.
- Do not force DFlash2 into the Escha fork by deleting unsupported tensors or modifying the checkpoint.
- Do not replace any known-good runtime globally.
- Do not use more than 8 CPU build/runtime threads.
