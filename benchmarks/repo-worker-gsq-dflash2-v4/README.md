# Repo Worker GSQ DFlash2 + Froggeric v22.4

Focused follow-up for the surviving Qwen3.8-27B GSQ-RCO IQ2_S operating point.

This round deliberately does **not** repeat IQ3, Ornith, Qwen 9B, or the already-run IQ2_S no-spec baseline. The challenger-v2 IQ2_S OFF trace remains the practical reference operating point.

## Why Froggeric v22.4

As of 2026-09-02, `froggeric/Qwen-Fixed-Chat-Templates` v22.4 is the newest published v22 release on Hugging Face. It supersedes v22.3/v22.2 and is pinned here to the v22.4 template release commit `e649070` so later `main` changes cannot silently alter the benchmark.

The template identifies itself as:

`qwen3.8-froggeric-v22.4`

For Qwen3.8, v22.4 changes the unsafe default reasoning baseline from `xhigh` to `medium`, supports explicit `reasoning_effort`, fixes historical empty-think/tool-loop issues, preserves chronological reasoning for KV-cache reuse, and is intended for llama.cpp through `--jinja --chat-template-file ... --reasoning-format deepseek`.

## Question

Test only two new operating points:

| profile | target | speculative decoding | chat template / reasoning |
|---|---|---|---|
| `iq2-dflash-frog-medium` | GSQ-RCO IQ2_S | DFlash2 Q4_K_M | Froggeric v22.4, `medium`, no hard budget |
| `iq2-dflash-frog-medium-b256` | GSQ-RCO IQ2_S | DFlash2 Q4_K_M | Froggeric v22.4, `medium` + hard budget 256 |

Expected run count: `2 profiles × 8 tasks = 16`.

This answers a practical question without another broad rerun: is Froggeric's safer `medium` reasoning enough for agent work, or is the additional native `--reasoning-budget 256` guard still useful?

## Models

Target GGUF, identical to the challenger-v2 IQ2_S target:

`/home/alpha/Playstoria/models/text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-IQ2_S/Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf`

Target SHA256:

`16c9802111aa9ef3acde465188d6d601f8db128ee3d828ad983a5caca4135ecb`

Draft:

`Qwen3.8-27B-DFlash2-Q4_K_M.gguf`

Expected draft SHA256:

`1a25c56858e1ebe93f2718ac1d49d1151f9323325c1bbfd6209370f4db131ebd`

DFlash2 is loaded separately with `-md`, `--spec-type draft-dflash`, full draft GPU offload, and `--spec-draft-n-max 7`, matching its trained block size of 8.

Froggeric template:

- repository: `froggeric/Qwen-Fixed-Chat-Templates`
- release revision: `e649070`
- file: `chat_template.jinja`
- expected embedded version: `qwen3.8-froggeric-v22.4`

`PREPARE_DFLASH2.sh` fetches both the draft and the pinned template and refuses to continue if the expected target/draft SHA or template version marker does not match.

## Controlled envelope

The round preserves the actual challenger-v2 IQ2 runtime envelope wherever possible:

- seed `9137`
- context `32768`
- temperature `0.2`
- top_p `0.95`
- threads/batch threads `2/2`
- KV cache `Q8_0/Q4_0`
- full target GPU offload
- full draft GPU offload
- flash attention ON
- one slot
- task timeout `480 s`
- request timeout ceiling `240 s`

Both new profiles use:

- Froggeric v22.4
- `reasoning_effort = medium`
- `enable_thinking = true`
- `preserve_thinking = true`
- `--reasoning-format deepseek`
- DFlash2 speculative decoding

Only the second profile adds native `--reasoning-budget 256`.

Because the old challenger-v2 baseline used the model's original template and no DFlash2, it is a practical reference rather than a single-variable A/B control. The within-round comparison between the two new profiles is controlled except for the hard reasoning budget.

## Suite

The same eight challenger-v2 tasks, public fixtures, hidden tests and strict `done` protocol are reused. T7 includes the evaluator correction from the independent audit: a correct policy-layer-only implementation is allowed and an unnecessary service edit is no longer required.

## Execution

```bash
cd /home/alpha/Playstoria/models
git pull --ff-only origin master
bash benchmarks/repo-worker-gsq-dflash2-v4/PREPARE_DFLASH2.sh
python3 benchmarks/repo-worker-gsq-dflash2-v4/runner/benchmark_orchestrator.py
```

Do not alter or fallback any runtime parameter if a profile fails to load. Preserve the failure and report it.

The runner verifies that the local runtime exposes DFlash2, custom Jinja template, chat-template kwargs, reasoning-format, and reasoning-budget support before executing tasks. It writes per-task traces, server logs, corrected prompt/decode TPS, DFlash draft/acceptance metrics, template SHA, VRAM and factual result tables. It does not rank the profiles.
