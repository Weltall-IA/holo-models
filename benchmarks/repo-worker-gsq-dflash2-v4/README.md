# Repo Worker GSQ DFlash2 + Froggeric v22.4

Focused follow-up for the surviving Qwen3.8-27B GSQ-RCO IQ2_S operating point.

This round deliberately does **not** repeat IQ3, Ornith, Qwen 9B, or the already-run IQ2_S no-spec baseline. The challenger-v2 IQ2_S OFF trace remains the practical reference operating point.

## Runtime requirement

The `wrong number of tensors; expected 81, got 58` failure was **not evidence that GSQ-RCO is incompatible with DFlash2**. It is the known signature of trying to load a DFlash2 checkpoint with a llama.cpp runtime that only understands the older DFlash tensor layout.

The DFlash2 model card explicitly requires llama.cpp DFlash2 support from PR #27342. That support reached upstream master on 2026-08-27 in commit `b10f9ca58c89ccfc3653ac01e979dd085d582b76` via #27816. The Arch Linux `llama-cpp 0.2.0-1` package was built on 2026-08-22, before that integration, so it is too old for this round even though its CLI exposes `draft-dflash`.

For this benchmark we use the official prebuilt llama.cpp runtime from `llama.app`, pinned to release:

`b10752`

Release `b10752` targets upstream commit:

`b96806d96061049a5b574269b049bf6241d63d46`

That commit contains the DFlash2 local-convolution and candidate-selector implementation, together with the Jinja/reasoning controls required by Froggeric v22.4. `PREPARE_LLAMA_APP.sh` downloads the official CUDA-capable prebuilt binary; it does not run CMake or compile llama.cpp locally.

The historical DeepGrove runtime remains untouched for reproduction of older results. The stale Arch `llama-server` is not used by this round.

## Why the GSQ target remains valid

The GSQ-RCO repository states that its files are standard GGUFs that run unmodified in llama.cpp. The IQ2_S target remains the same model already validated in challenger-v2. DFlash2 is a separate draft model; the target still verifies the speculative tokens.

The DFlash2 repository documents the pairing as a Qwen3.8-27B target plus the DFlash2 sidecar with `--spec-type draft-dflash --spec-draft-n-max 7`. Its published evaluation uses a Q4_K_M target, but the loader failure we observed happened before inference and was caused by the stale runtime tensor schema, not by GSQ quantization.

## Why Froggeric v22.4

As of 2026-09-02, `froggeric/Qwen-Fixed-Chat-Templates` v22.4 is the newest published v22 release on Hugging Face. It is pinned here to revision `e649070` so later `main` changes cannot silently alter the benchmark.

The template identifies itself as:

`qwen3.8-froggeric-v22.4`

For Qwen3.8, v22.4 changes the unsafe default reasoning baseline from `xhigh` to `medium`, supports explicit `reasoning_effort`, fixes historical empty-think/tool-loop issues, preserves chronological reasoning for KV-cache reuse, and is intended for llama.cpp through custom Jinja plus reasoning extraction.

## Question

Test only two new operating points:

| profile | target | speculative decoding | chat template / reasoning |
|---|---|---|---|
| `iq2-dflash-frog-medium` | GSQ-RCO IQ2_S | DFlash2 Q4_K_M | Froggeric v22.4, `medium`, no hard budget |
| `iq2-dflash-frog-medium-b256` | GSQ-RCO IQ2_S | DFlash2 Q4_K_M | Froggeric v22.4, `medium` + hard budget 256 |

Expected run count: `2 profiles × 8 tasks = 16`.

## Models

Target:

`/home/alpha/Playstoria/models/text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-IQ2_S/Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf`

Target SHA256:

`16c9802111aa9ef3acde465188d6d601f8db128ee3d828ad983a5caca4135ecb`

Draft:

`/home/alpha/Playstoria/models/text/z-lab-Qwen3.8-27B-DFlash2-GGUF/Qwen3.8-27B-DFlash2-Q4_K_M.gguf`

Draft SHA256:

`1a25c56858e1ebe93f2718ac1d49d1151f9323325c1bbfd6209370f4db131ebd`

The current z-lab and incoai Q4_K_M mirror files have the same 1.14 GB artifact and SHA256 above.

Froggeric template:

- repository: `froggeric/Qwen-Fixed-Chat-Templates`
- release revision: `e649070`
- file: `chat_template.jinja`
- expected embedded version: `qwen3.8-froggeric-v22.4`

## Controlled envelope

- seed `9137`
- context `32768`
- temperature `0.2`
- top_p `0.95`
- threads/batch threads `2/2`
- KV cache `Q8_0/Q4_0`
- full target GPU offload
- full draft GPU offload
- flash attention ON
- automatic runtime fitting OFF
- one slot
- task timeout `480 s`
- request timeout ceiling `240 s`
- DFlash2 draft width `7`
- Froggeric v22.4
- native `--reasoning-effort medium`
- `enable_thinking = true`
- `preserve_thinking = true`
- `--reasoning-format deepseek`

Only the second profile adds native `--reasoning-budget 256`.

Because the old challenger-v2 baseline used a different runtime, original model template and no DFlash2, it remains a practical reference rather than a single-variable A/B control. The within-round comparison between the two new profiles is controlled except for the hard reasoning budget.

## Suite

The same eight challenger-v2 tasks, public fixtures, hidden tests and strict `done` protocol are reused. T7 includes the evaluator correction from the independent audit: a correct policy-layer-only implementation is allowed and an unnecessary service edit is no longer required.

## Execution

```bash
cd /home/alpha/Playstoria/models
git pull --ff-only origin master
bash benchmarks/repo-worker-gsq-dflash2-v4/PREPARE_LLAMA_APP.sh
bash benchmarks/repo-worker-gsq-dflash2-v4/PREPARE_DFLASH2.sh
python3 benchmarks/repo-worker-gsq-dflash2-v4/runner/benchmark_orchestrator.py
```

Do not use `/usr/bin/llama-server` for this round. Do not compile llama.cpp locally. Do not alter or fallback any runtime/model parameter if the pinned official runtime fails to load. Preserve and report the failure.

The runner verifies release `b10752`, upstream commit `b96806d96061049a5b574269b049bf6241d63d46`, DFlash2/custom-Jinja/reasoning features, model/template hashes, and writes per-task traces, server logs, corrected prompt/decode TPS, DFlash acceptance metrics, runtime provenance, VRAM and factual result tables. It does not rank the profiles.
