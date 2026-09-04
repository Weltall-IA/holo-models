# Qwen3.8-Whittle-16B Candidate Evaluation v1

## Purpose

Evaluate `logic65/Qwen3.8-Whittle-16B` as a possible local coding/agent candidate on the current RTX 5060 Ti 16 GB workspace.

This model is **not** the previously tested `Qwen3.8-Whittle-MoE-27B-A17.8B`. Treat it as a separate candidate.

The upstream card describes this model as a 27B pruned down to ~16.8B, then healed. The current recommended GGUF is the **v2 Q4_K_M**.

## Upstream target

Repository:

`logic65/Qwen3.8-Whittle-16B`

Required GGUF:

`Qwen3.8-Whittle-16B-v2-Q4_K_M.gguf`

Canonical local directory:

`text/logic65-Qwen3.8-Whittle-16B-v2-Q4_K_M/`

Canonical local GGUF path:

`text/logic65-Qwen3.8-Whittle-16B-v2-Q4_K_M/Qwen3.8-Whittle-16B-v2-Q4_K_M.gguf`

Canonical profile path required by workspace governance:

`text/logic65-Qwen3.8-Whittle-16B-v2-Q4_K_M/Qwen3.8-Whittle-16B-v2-Q4_K_M.md`

Before benchmarking, record:
- exact downloaded byte size;
- SHA256;
- Hugging Face repo/revision if available from the download metadata;
- GGUF architecture/quantization metadata;
- llama.cpp runtime version/build/commit.

Do not download safetensors unless required to recover from a real GGUF problem. Prefer the single v2 Q4_K_M GGUF.

## Important upstream execution notes

The upstream author explicitly recommends the anti-loop settings below as part of the serving recipe:

- `--dry-multiplier 0.8`
- `--dry-base 1.75`
- `--dry-allowed-length 4`
- `--repeat-penalty 1.15`
- `--repeat-last-n 512`
- `--temp 0.7`
- `--top-p 0.95`
- `--min-p 0.05`
- `--jinja`

The author also describes the model as a **thinking model**. Therefore the primary candidate arm in this benchmark must test the model in its intended upstream configuration rather than disabling reasoning merely to force historical protocol parity.

Because this differs from the historical `coding-mini-v1` sampling/reasoning protocol, its speed numbers must **not** be merged into the strict historical leaderboard as if they were same-protocol measurements. Correctness on the exact same canonical cases may still be compared directly, while throughput/wall-time should be labelled `AUTHOR_RECIPE`.

## Runtime baseline

Use the known workspace runtime:

`/home/alpha/.local/bin/llama`

Expected known reference before execution:
- llama.cpp `0.3.0-dev`
- build `10752`
- commit `b96806d96061049a5b574269b049bf6241d63d46`

If the local wrapper now points to a newer runtime, record the actual runtime and continue only if the model loads correctly and Qwen3.5-series support is present. Do not silently switch to an unrelated fork.

Hardware/runtime constraints:
- RTX 5060 Ti 16 GB
- 8 CPU threads
- full GPU offload when it fits
- Flash Attention ON
- fit OFF
- `ctx=8192`
- `np=1`
- K cache `q8_0`
- V cache `q4_0`

## GPU preflight

Before each benchmark stage, capture:
- one `nvidia-smi` snapshot;
- five 1-second `nvidia-smi pmon -s u` samples.

Do not begin a measured stage if an unrelated process sustains >=25% SM in at least 3 of the 5 samples. Wait and retry the preflight instead of changing system settings.

Do not change clocks, power limits, driver settings, compositor settings, or benchmark parameters between cases.

## Stage A — Native Whittle 16B coding gate

Use the exact 6 canonical cases from:

`benchmarks/coding-mini-v1/`

Cases:
- PY01
- PY02
- PY03
- CPP01
- CPP02
- CPP03

Do not modify prompts, evaluator, public tests, hidden tests, code extraction, or case expectations.

Use the upstream author recipe for generation:

- `--jinja`
- thinking/reasoning enabled using the model/runtime native mechanism;
- do **not** force `--reasoning off`;
- `--dry-multiplier 0.8`
- `--dry-base 1.75`
- `--dry-allowed-length 4`
- `--repeat-penalty 1.15`
- `--repeat-last-n 512`
- temperature `0.7`
- top_p `0.95`
- min_p `0.05`
- seed `9137`

Give each case a sufficiently large completion budget for thinking plus final code. Use at least 2048 completion tokens unless an existing canonical case has a larger requirement. Do not truncate hidden reasoning merely to make runtime shorter.

Evaluate only the final answer/code using the existing `coding-mini-v1` evaluator. Reasoning text is not itself scored except if it leaks into or corrupts the final code/protocol.

Record per case:
- compile pass;
- public pass;
- hidden pass;
- overall PASS/FAIL;
- decode tok/s;
- prompt tok/s;
- wall time;
- TTFT when available;
- peak VRAM;
- completion length;
- whether output looped/truncated;
- whether reasoning completed cleanly before final answer.

Stage A gate:
- `0–4/6`: stop candidate expansion. Do not run DFlash2 or agent stage.
- `5/6`: allow Stage B DFlash2 compatibility/quality check, but skip Stage C agent benchmark unless Stage B reaches 6/6.
- `6/6`: run Stage B, then Stage C according to the gates below.

## Stage B — DFlash2 compatibility and coding gate

Only run if Stage A >=5/6.

Draft model:

`text/z-lab-Qwen3.8-27B-DFlash2-GGUF/Qwen3.8-27B-DFlash2-Q4_K_M.gguf`

Use:
- `--spec-type draft-dflash`
- `--spec-draft-n-max 7`
- full target and draft GPU offload if it fits.

Because Whittle 16B is structurally pruned relative to the original 27B, DFlash2 compatibility is **not assumed**.

First run a single compatibility smoke on PY01 using otherwise identical Stage A settings.

If the server fails to load, tokenizer/vocab compatibility fails, speculative decoding errors, output becomes invalid, or VRAM OOM occurs:
- record `DFLASH2_INCOMPATIBLE_OR_UNUSABLE`;
- preserve logs;
- do not retry with arbitrary architecture hacks;
- skip the rest of Stage B.

If PY01 completes correctly, run all 6 canonical coding cases with DFlash2.

Record additionally:
- draft acceptance ratio;
- accepted/generated draft tokens;
- mean accepted draft length;
- target+draft peak VRAM.

Stage B interpretation:
- compare correctness to Stage A;
- do not accept acceleration if correctness regresses;
- DFlash2 is considered useful only if it preserves at least the Stage A PASS count and materially improves median wall/decode performance without unsafe VRAM pressure.

## Stage C — Agent/tool-calling mini benchmark

Only run if the candidate reaches **6/6 coding** in the best non-speculative or speculative configuration that is stable and suitable for serving.

Reuse the exact 8 canonical agent/tool cases from:

`benchmarks/gsq-froggeric-agent-tools-v1/CASES.json`

Do not invent new cases or edit schemas/stubs/expected sequences.

Use the model's **native embedded template** with `--jinja` and no Froggeric override.

Use OpenAI-compatible `/v1/chat/completions` with real structured `tools` payloads and stubbed tool results exactly as defined by the existing agent benchmark.

For agent sampling, preserve the upstream Whittle anti-loop recipe unless the API layer requires sampling fields in the request rather than server flags. Keep thinking enabled unless the runtime's tool protocol demonstrably requires otherwise; if a protocol-specific change is required, document it before execution and do not silently change it case-by-case.

Score using the existing 8-case agent rubric:
- tool selection/sequence;
- arguments/schema;
- grounded final answer;
- protocol hygiene.

Record STRICT PASS /8 and total /80.

## Historical controls to report, not rerun

For context in the final summary, reuse preserved historical results only:

- GSQ IQ2_S base coding: `6/6`, 24.70 tok/s historical same-protocol result.
- GSQ IQ2_S + DFlash2 n=7 coding: `6/6`, 46.00 tok/s historical same-protocol result.
- GSQ native agent/tool benchmark: `7/8`, 70/80.
- Previous Whittle MoE 27B A18B: `1/6`, 19.39 tok/s, peak 15194 MiB. This is a different model and must be labelled as such.

Do not rerun these controls for this candidate gate.

## Required outputs

Create:

`benchmarks/whittle16b-candidate-v1/results/WHITTLE16B_NATIVE_CODING.jsonl`

If Stage B runs:

`benchmarks/whittle16b-candidate-v1/results/WHITTLE16B_DFLASH2_CODING.jsonl`

If Stage C runs:

`benchmarks/whittle16b-candidate-v1/results/WHITTLE16B_AGENT_RESULTS.jsonl`

Always create:

- `benchmarks/whittle16b-candidate-v1/results/SUMMARY.md`
- `benchmarks/whittle16b-candidate-v1/results/RUN_MANIFEST.json`
- `benchmarks/whittle16b-candidate-v1/results/gpu-preflight/`
- relevant server logs.

The summary must clearly separate:
1. `AUTHOR_RECIPE` measurements for Whittle 16B;
2. historical same-protocol GSQ controls;
3. DFlash2 compatibility status;
4. agent status if Stage C ran.

## Required profile update

Create/update:

`text/logic65-Qwen3.8-Whittle-16B-v2-Q4_K_M/Qwen3.8-Whittle-16B-v2-Q4_K_M.md`

Follow `AGENTS.md` exactly. Separate `MEDIDO LOCALMENTE` from `DECLARADO PELO AUTOR/ORIGEM`. Do not invent any absent metric.

At minimum include:
- exact GGUF filename;
- bytes/GiB;
- SHA256;
- origin/revision;
- architecture/quantization;
- upstream recommended recipe;
- Stage A coding score and metrics;
- Stage B DFlash2 status if run;
- Stage C agent score if run;
- recommended serving command based only on the measured result;
- limitations.

## Final classification

Use exactly one:

- `WHITTLE16B_REJECT`
- `WHITTLE16B_INTERESTING`
- `WHITTLE16B_STRONG_CANDIDATE`
- `WHITTLE16B_PRIMARY_CODER_CANDIDATE`

Guidance:
- `REJECT`: <=4/6 coding or serious runtime/protocol instability.
- `INTERESTING`: 5/6 coding with useful efficiency/VRAM characteristics.
- `STRONG_CANDIDATE`: 6/6 coding, stable runtime, but not clearly better overall than current GSQ+DFlash2.
- `PRIMARY_CODER_CANDIDATE`: 6/6 coding plus compelling efficiency/performance and no meaningful agent/runtime regression relative to current needs.

Do not promote solely from upstream claims.

## Git workflow

After execution:
- validate generated files;
- update only the candidate model profile and benchmark-specific files/scripts;
- preserve all historical results;
- commit and push to `origin/master`;
- report the final commit SHA.
