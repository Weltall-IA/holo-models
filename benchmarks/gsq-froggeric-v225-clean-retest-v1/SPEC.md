# GSQ Froggeric v22.5 Clean Retest v1

Purpose: retest Froggeric under a clean GPU condition, using the current upstream-recommended llama.cpp integration and the current Froggeric release, while preserving direct paired controls.

## Why this retest exists

The previous `gsq-froggeric-ablation-v1` was executed while the user's GPU was under unrelated workload, so its throughput/VRAM comparisons must not be treated as a clean performance A/B. In addition, upstream Froggeric has since released v22.5, which specifically changes non-thinking prompt alignment and engine hardening.

Do not delete or overwrite the v22.4 historical artifacts. This is a new benchmark.

## Upstream Froggeric source of truth

Repository:

`froggeric/Qwen-Fixed-Chat-Templates`

Pinned release commit for this benchmark:

`4ea21db90694e60d002500dae85ebff26e4b23ad`

Expected template internal version:

`qwen3.8-froggeric-v22.5`

Use the root file:

`chat_template.jinja`

Do not use `chat_template_oneline.txt` as a separate variant.

Do not use the archived v22.4 template for this retest.

Download/store the pinned template separately under:

`text/froggeric-Qwen-Fixed-Chat-Templates-v22.5/chat_template.jinja`

Record its SHA256 in `RUN_MANIFEST.json` after download. Do not invent an expected SHA if it is not already versioned.

## Correct llama.cpp integration for Froggeric

Follow the current Froggeric README for llama.cpp:

- `--jinja`
- `--chat-template-file <path-to-chat_template.jinja>`
- `--reasoning-format deepseek`

For the non-thinking condition used by this benchmark, control thinking through Froggeric template kwargs, not through an ad-hoc template edit:

- `enable_thinking=false`
- `reasoning_effort="none"`

Pass both through the runtime's supported chat-template kwargs mechanism, e.g. current llama.cpp `--chat-template-kwargs` if present in `--help`.

Do not modify the template source to hardcode these benchmark values.

Do not rely only on `--reasoning off` as the Froggeric control. The benchmark must exercise the upstream-supported template kwargs path. If the current runtime exposes an additional reasoning-output flag, it may be used only if it does not replace the required template kwargs above.

Before generation, validate from server logs/rendering that:

- the external Froggeric file was loaded;
- internal version is `qwen3.8-froggeric-v22.5`;
- thinking is disabled for the benchmark condition;
- no reasoning text leaks into final content.

## Models

Target:

`/home/alpha/Playstoria/models/text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-IQ2_S/Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf`

Draft:

`/home/alpha/Playstoria/models/text/z-lab-Qwen3.8-27B-DFlash2-GGUF/Qwen3.8-27B-DFlash2-Q4_K_M.gguf`

Runtime:

`/home/alpha/.local/bin/llama`

## Clean-GPU gate

This retest is specifically intended to eliminate the prior unrelated GPU-load confound.

Before the first measured arm and again before each subsequent arm:

1. Record `nvidia-smi`.
2. Record at least 5 short `nvidia-smi pmon` samples (or an equivalent per-process GPU-utilization view).
3. Exclude the benchmark's own llama process when judging external load.
4. There must be no unrelated process sustaining heavy GPU compute. As a practical gate, no unrelated process may sustain >=25% SM in 3 or more of the sampled observations.
5. If the gate fails, wait for the unrelated workload to stop and sample again. Do not silently run through heavy contention.
6. Preserve the pre-arm GPU snapshots under `results/gpu-preflight/`.

Normal compositor/browser background activity is acceptable if it stays below the heavy-load gate. Do not change clocks, power limits, drivers, or other system tuning between arms.

## Shared runtime envelope

For all measured arms:

- `ctx=8192`
- `np=1`
- full target GPU offload
- Flash Attention ON
- `--fit off`
- target KV K `q8_0`
- target KV V `q4_0`
- max 8 CPU threads and 8 batch threads
- same runtime binary/version for all paired arms
- one server at a time
- same warmup policy for paired arms
- no unrelated model server running

Do not change quantization, context, KV types, sampler, prompt, seed, evaluator, or max tokens between paired controls.

## Coding generation contract

Reuse exactly the corrected 6 canonical cases from:

`benchmarks/coding-mini-v1/`

Settings:

- seed `9137`
- temperature `0.2`
- top_p `0.95`
- reasoning/thinking disabled as specified above
- same case-specific max tokens
- same evaluator

Record per case:

- compile/public/hidden
- PASS/FAIL
- tok/s
- wall time
- TTFT if available
- peak VRAM
- prompt/completion token counts if available

## Writing/chat generation contract

Reuse exactly the existing prompts, schedule and seeds from:

`benchmarks/chat-writing-v1/`

- prompts: `neutral`, `adult`
- schedule: AB / BA / AB
- seeds: `9137`, `9138`, `9139`
- temperature `0.8`
- top_p `0.95`
- min_p `0.05`
- repeat_penalty `1.05`
- max_tokens `1536`
- reasoning/thinking disabled as specified above

Record full raw outputs, objective behavior flags, word count, tok/s, wall time, TTFT and peak VRAM.

Do NOT create a new heuristic writing-quality score. The previous local heuristic is not comparable to `chat-writing-v1`'s historical qualitative review.

For this retest, produce an anonymized review packet and mark qualitative writing status `PENDING_CHATGPT_REVIEW` unless the exact historical qualitative review procedure is reproduced without heuristic substitution.

## Arms

Run all arms in one uninterrupted benchmark cycle after preflight. Do not ask for confirmation between arms.

### Arm A — GSQ native coding control

6 coding cases, embedded/native GGUF chat template, no DFlash2.

### Arm B — GSQ + Froggeric v22.5 coding

6 coding cases, external Froggeric v22.5 using the integration above, no DFlash2.

### Arm C — GSQ + DFlash2 native coding control

6 coding cases, embedded/native target chat template, DFlash2 enabled with:

- `--spec-type draft-dflash`
- `--spec-draft-n-max 7`
- full draft GPU offload

Record draft acceptance, accepted/generated and mean accepted length.

### Arm D — GSQ + DFlash2 + Froggeric v22.5 coding

Same as Arm C, changing only the target chat template to Froggeric v22.5 and applying the required non-thinking kwargs.

### Arm E — GSQ native writing/chat control

6 writing generations using the embedded/native GGUF template.

### Arm F — GSQ + Froggeric v22.5 writing/chat

6 writing generations using Froggeric v22.5 and the same generation settings as Arm E.

Total new measured generations: 36.

The paired controls are intentionally rerun because this benchmark's purpose is clean same-session performance comparison after the previous GPU-contention confound.

## DFlash2 metrics

For Arms C and D, record per case:

- draft acceptance ratio
- accepted draft tokens
- generated draft tokens
- mean accepted draft length
- target tok/s
- wall time
- peak VRAM

Use `n_max=7`; do not perform an n_max sweep.

## Required outputs

Write under:

`benchmarks/gsq-froggeric-v225-clean-retest-v1/results/`

At minimum:

- `RUN_MANIFEST.json`
- `GPU_PREFLIGHT_SUMMARY.md`
- `CODING_NATIVE_RESULTS.jsonl`
- `CODING_FROGGERIC_V225_RESULTS.jsonl`
- `CODING_DFLASH2_NATIVE_RESULTS.jsonl`
- `CODING_DFLASH2_FROGGERIC_V225_RESULTS.jsonl`
- `WRITING_NATIVE_RESULTS.jsonl`
- `WRITING_FROGGERIC_V225_RESULTS.jsonl`
- `WRITING_REVIEW_PACKET.md`
- `SUMMARY.md`

`RUN_MANIFEST.json` must contain:

- target SHA256
- draft SHA256
- Froggeric HF repo
- Froggeric pinned commit
- Froggeric template SHA256
- Froggeric internal template version
- llama runtime version/build/commit
- exact server flags for native/Froggeric/DFlash2 arms
- GPU model
- clean-GPU gate outcome for each arm

## Comparison rules

Primary coding comparisons are same-session paired comparisons:

- Arm B vs Arm A
- Arm D vs Arm C

Primary writing speed comparison:

- Arm F vs Arm E

Historical numbers may be shown as context only, not used as the primary performance baseline for this clean retest.

Coding correctness must remain 6/6 to claim no quality regression.

A <3% throughput delta should be treated as practical parity unless repeated evidence supports a real effect.

Do not claim writing-quality improvement until the raw outputs receive the historical qualitative review procedure.

## Final classification

`SUMMARY.md` must classify coding/template behavior as one of:

- `FROGGERIC_V225_CODING_PREFERRED`
- `FROGGERIC_V225_CODING_PARITY`
- `KEEP_NATIVE_CODING`

Writing quality must remain:

- `PENDING_CHATGPT_REVIEW`

unless exact historical qualitative review is reproduced.

Do not collapse these into one global recommendation before writing review is valid.

## Governance

- Do not overwrite historical v22.4 results.
- Do not invent missing metrics.
- Do not alter canonical prompts/evaluators to improve the Froggeric result.
- Do not rerun an arm merely because its result is unfavorable.
- If a run is contaminated by a clean-GPU gate failure during the arm, mark that arm invalid and rerun only that invalid arm after the load clears.
- Preserve all valid raw results and server logs.
- Update model profile Markdown only after the benchmark is complete and only with measured, versioned facts.
