# Repo Worker GSQ DFlash2 v4

Focused follow-up for the surviving Qwen3.8-27B GSQ-RCO IQ2_S operating point.

This round deliberately does **not** repeat IQ3, Ornith, Qwen 9B, or the already-run IQ2_S no-spec baseline. The challenger-v2 IQ2_S OFF trace is the reference operating point.

## Question

Test only two new operating points:

| profile | target | speculative decoding | reasoning |
|---|---|---|---|
| `iq2-dflash-off` | GSQ-RCO IQ2_S | DFlash2 Q4_K_M | OFF |
| `iq2-dflash-b256` | GSQ-RCO IQ2_S | DFlash2 Q4_K_M | native hard budget 256 |

Expected run count: `2 profiles × 8 tasks = 16`.

The target GGUF is exactly the same IQ2_S file already used by challenger-v2:

`/home/alpha/Playstoria/models/text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-IQ2_S/Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf`

Target SHA256:

`16c9802111aa9ef3acde465188d6d601f8db128ee3d828ad983a5caca4135ecb`

The draft is the current z-lab Qwen3.8-27B DFlash2 Q4_K_M GGUF:

`Qwen3.8-27B-DFlash2-Q4_K_M.gguf`

Expected SHA256:

`1a25c56858e1ebe93f2718ac1d49d1151f9323325c1bbfd6209370f4db131ebd`

DFlash2 is loaded as a separate draft model with `-md`, `--spec-type draft-dflash`, full draft GPU offload, and `--spec-draft-n-max 7`, matching its trained block size of 8.

## Controlled envelope

To make the DFlash2 OFF profile directly comparable to the already-run IQ2_S OFF profile, this round intentionally preserves the actual challenger-v2 IQ2 envelope:

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

The only difference between the old IQ2_S OFF baseline and `iq2-dflash-off` is the DFlash2 speculative path.

The `iq2-dflash-b256` profile keeps the same DFlash2 configuration and enables native `--reasoning on --reasoning-budget 256` while keeping sampling unchanged.

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

The runner writes per-task traces, server logs, corrected prompt/decode TPS, DFlash draft/acceptance metrics, VRAM and factual result tables. It does not rank the profiles.
