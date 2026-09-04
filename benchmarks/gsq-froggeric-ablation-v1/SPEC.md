# GSQ Froggeric Ablation v1

Purpose: determine whether the canonical Froggeric v22.4 chat template improves the current GSQ IQ2_S operating point without reducing coding correctness or DFlash2 performance.

## Historical controls — reuse only

Do not rerun these controls:

- GSQ IQ2_S native coding: 6/6, median 24.70 tok/s.
- GSQ IQ2_S + DFlash2 n_max=7 coding: 6/6, median 46.00 tok/s.
- GSQ IQ2_S native writing: 3.54/5.

Use the committed historical artifacts as the comparison source.

## Target model

Use the existing local GSQ target:

`/home/alpha/Playstoria/models/text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-IQ2_S/Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf`

Use the existing DFlash2 draft when required:

`/home/alpha/Playstoria/models/text/z-lab-Qwen3.8-27B-DFlash2-GGUF/Qwen3.8-27B-DFlash2-Q4_K_M.gguf`

## Canonical Froggeric template

Use exactly:

`/home/alpha/Playstoria/models/text/froggeric-Qwen-Fixed-Chat-Templates-v22.4/chat_template.jinja`

Expected revision: `e649070`

Expected SHA256:

`c47c82b0544752d454f4e427228d9d9d8c3df64c9e446cbd0229362f67948009`

Expected internal version: `qwen3.8-froggeric-v22.4`

Use:

- `--jinja`
- `--chat-template-file <canonical path>`

Do not use archived Froggeric versions or `chat_template_oneline.txt` as a separate variant.

## Runtime envelope

Use the existing known-good stock runtime `/home/alpha/.local/bin/llama`.

For all new runs:

- full GPU offload
- Flash Attention ON
- `--fit off`
- one slot (`np=1`)
- max 8 CPU threads
- context 8192
- reasoning OFF
- `--chat-template-kwargs '{"reasoning_effort":"none"}'`
- K cache `q8_0`
- V cache `q4_0`

Do not close or otherwise alter the user's normal desktop/application environment solely for this benchmark. Record any obvious abnormal concurrent GPU load if observed.

## Arm A — GSQ + Froggeric coding

Run exactly the 6 corrected canonical cases from `benchmarks/coding-mini-v1/`.

Use the same settings as the historical coding control:

- seed 9137
- temperature 0.2
- top_p 0.95
- reasoning off
- context 8192
- threads 8

Only the chat template may differ from the historical GSQ native control.

Record per case:

- compile/public/hidden status
- final PASS/FAIL
- tok/s
- wall time
- peak VRAM

## Arm B — GSQ + Froggeric writing

Run exactly the existing `benchmarks/chat-writing-v1/` prompts and seeds.

Use the historical writing contract unchanged:

- 2 prompts: neutral and adult
- seeds 9137, 9138, 9139
- temperature 0.8
- top_p 0.95
- min_p 0.05
- repeat_penalty 1.05
- max_tokens 1536
- context 8192
- threads 8
- reasoning off

Total: 6 writing generations.

Apply the same qualitative rubric already used by `chat-writing-v1`; do not invent a new writing rubric.

## Arm C — GSQ + DFlash2 n=7 + Froggeric coding

Run exactly the same 6 corrected `coding-mini-v1` cases with:

- same target GSQ IQ2_S
- same canonical Froggeric template
- same coding settings as Arm A
- `--spec-type draft-dflash`
- `--spec-draft-n-max 7`
- `-ngld 999` or equivalent full draft GPU offload supported by the current runtime

Record per case in addition to normal coding metrics:

- draft acceptance ratio
- accepted/generated draft tokens
- mean accepted draft length
- tok/s
- wall time
- peak VRAM

## Generation budget

New generations only:

- Arm A: 6 coding
- Arm B: 6 writing
- Arm C: 6 coding

Total: 18 new generations.

Do not rerun GSQ native controls.

## Required outputs

Write results under:

`benchmarks/gsq-froggeric-ablation-v1/results/`

At minimum:

- `CODING_FROGGERIC_RESULTS.jsonl`
- `WRITING_FROGGERIC_RESULTS.jsonl`
- `DFLASH2_FROGGERIC_RESULTS.jsonl`
- `SUMMARY.md`
- `RUN_MANIFEST.json`

`SUMMARY.md` must compare:

1. GSQ native coding historical control
2. GSQ + Froggeric coding
3. GSQ + DFlash2 n=7 historical control
4. GSQ + DFlash2 n=7 + Froggeric coding
5. GSQ native writing historical control
6. GSQ + Froggeric writing

## Decision rules

Classify the outcome explicitly:

- `FROGGERIC_GLOBAL_DEFAULT` only if coding remains 6/6, writing improves materially over 3.54/5, and DFlash2 coding remains 6/6 without a material performance regression.
- `SPLIT_PRESETS` if Froggeric improves writing but native remains preferable for coding/DFlash2.
- `KEEP_NATIVE` if Froggeric does not provide a material benefit or causes regressions.

Do not weaken coding evaluators, change prompts, alter seeds, enable reasoning, or change model weights to improve the result.
