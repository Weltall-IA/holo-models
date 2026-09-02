# Executor contract — IQ2 DFlash2 + Froggeric v22.4

The local AI is an executor only. It must not redesign this round.

1. `git pull --ff-only origin master`.
2. Run `PREPARE_RUNTIME.sh` exactly as versioned. It prepares a separate pinned upstream llama.cpp runtime for DFlash2/Froggeric and must not modify the historical DeepGrove runtime.
3. Run `PREPARE_DFLASH2.sh` exactly as versioned. It prepares DFlash2 and the pinned Froggeric v22.4 template.
4. Run `runner/benchmark_orchestrator.py` exactly as versioned.
5. Expected workload is only `2 profiles × 8 tasks = 16` new runs.
6. Do not rerun the old challenger-v2 IQ2_S OFF baseline.
7. Do not add IQ3, Ornith, Qwen 9B, MTP or other profiles.
8. The only profiles are:
   - `iq2-dflash-frog-medium`
   - `iq2-dflash-frog-medium-b256`
9. The required benchmark runtime is the dedicated upstream checkout at `/home/alpha/Playstoria/models/engines/llama.cpp-dflash2-v4`, pinned to `b96806d96061049a5b574269b049bf6241d63d46`.
10. Do not use or update `/home/alpha/Playstoria/models/engines/deepgrove-llama.cpp` for this round.
11. Do not replace Froggeric v22.4 with another template version or with Hugging Face `main`.
12. Do not alter context, threads, KV types, sampling, DFlash2 draft size, Froggeric template kwargs, reasoning effort, reasoning budget, evaluator, fixtures, timeout or model files.
13. Do not enable llama.cpp automatic fitting; the runner explicitly uses `--fit off`.
14. Do not apply context/CPU/GPU fallback if the runtime build or server load fails. Preserve and report the failure.
15. Do not rerun an already-written task JSON to improve a score.
16. Preserve all server logs and failed traces.
17. After all 16 runs complete with no infrastructure errors, commit only generated artifacts under `benchmarks/repo-worker-gsq-dflash2-v4/` and push to `master`.
18. Do not rank or interpret the profiles before ChatGPT audits the raw traces.

Execution:

```bash
cd /home/alpha/Playstoria/models
git pull --ff-only origin master

git rev-parse HEAD

bash benchmarks/repo-worker-gsq-dflash2-v4/PREPARE_RUNTIME.sh
bash benchmarks/repo-worker-gsq-dflash2-v4/PREPARE_DFLASH2.sh
python3 benchmarks/repo-worker-gsq-dflash2-v4/runner/benchmark_orchestrator.py
```

If the runtime preparation/build fails, stop and return the exact build error. Do not patch, checkout a different commit, reduce CUDA features, or use the old DeepGrove binary.

After a clean 16/16 run:

```bash
git add benchmarks/repo-worker-gsq-dflash2-v4/
git commit -m "bench(repo-worker): execute IQ2 DFlash2 Froggeric v22.4"
git push origin master
git rev-parse HEAD
```

Return only:

```text
COMMIT=<sha>
SOURCE_REPO_HEAD=<sha>
SEED=<seed>
RUNS_COMPLETED=<n>/16
INFRA_ERRORS=<n>
RUNTIME_REVISION=<sha>
```

Then include the factual `RESULTS.md` table and the contents of `DFLASH_METRICS.json` and `CONTROLLED_CONFIG.json`. Do not add a subjective winner.
