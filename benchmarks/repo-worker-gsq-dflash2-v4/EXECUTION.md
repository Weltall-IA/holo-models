# Executor contract — IQ2 DFlash2 + Froggeric v22.4

The local AI is an executor only. It must not redesign this round.

The previous Arch-package runtime attempt is invalid for DFlash2: Arch `llama-cpp 0.2.0-1` was built before upstream DFlash2 support landed and produces the known `expected 81, got 58` tensor-layout error.

Do not interpret that error as GSQ incompatibility.

Use only the official llama.app prebuilt runtime pinned by `PREPARE_LLAMA_APP.sh`:

- release `b10752`
- upstream commit `b96806d96061049a5b574269b049bf6241d63d46`
- installed binary `~/.local/bin/llama`
- server command is `llama serve`

Do not use `/usr/bin/llama-server`, the historical DeepGrove runtime, or any benchmark-specific source checkout. Do not compile llama.cpp locally.

Execution:

```bash
cd /home/alpha/Playstoria/models
git pull --ff-only origin master
git rev-parse HEAD

bash benchmarks/repo-worker-gsq-dflash2-v4/PREPARE_LLAMA_APP.sh
bash benchmarks/repo-worker-gsq-dflash2-v4/PREPARE_DFLASH2.sh
python3 benchmarks/repo-worker-gsq-dflash2-v4/runner/benchmark_orchestrator.py
```

Expected workload is only `2 profiles × 8 tasks = 16`:

- `iq2-dflash-frog-medium`
- `iq2-dflash-frog-medium-b256`

Do not rerun the old challenger-v2 IQ2_S OFF baseline. Do not add IQ3, Ornith, Qwen 9B, MTP or other profiles.

Do not alter context, threads, KV types, sampling, DFlash2 draft size, Froggeric template kwargs, reasoning effort, reasoning budget, evaluator, fixtures, timeouts or model files. Do not enable automatic fitting. Do not apply fallback if server loading fails. Preserve exact logs and failed traces. Do not rerun completed task JSONs to improve scores.

If `PREPARE_LLAMA_APP.sh` fails its release/commit/feature checks, stop and return the exact error. Do not switch to the Arch package and do not compile from source.

After a clean 16/16 run:

```bash
git add benchmarks/repo-worker-gsq-dflash2-v4/
git commit -m "bench(repo-worker): execute IQ2 DFlash2 Froggeric v22.4"
git push origin master
git rev-parse HEAD
```

Return:

```text
COMMIT=<sha>
SOURCE_REPO_HEAD=<sha>
SEED=<seed>
RUNS_COMPLETED=<n>/16
INFRA_ERRORS=<n>
RUNTIME_REVISION=<release/commit/version>
```

Then include the factual `RESULTS.md` table and the contents of `DFLASH_METRICS.json` and `CONTROLLED_CONFIG.json`. Do not rank or interpret the profiles.
