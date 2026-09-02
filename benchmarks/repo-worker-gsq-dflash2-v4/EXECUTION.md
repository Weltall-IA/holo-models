# Executor contract — IQ2 DFlash2 + Froggeric v22.4

The local AI is an executor only. It must not redesign this round.

1. `git pull --ff-only origin master`.
2. Run `PREPARE_DFLASH2.sh` exactly as versioned. It prepares both DFlash2 and the pinned Froggeric v22.4 template.
3. Run `runner/benchmark_orchestrator.py` exactly as versioned.
4. Expected workload is only `2 profiles × 8 tasks = 16` new runs.
5. Do not run `repo-worker-gsq-controlled-v3` as part of this round.
6. Do not rerun the old challenger-v2 IQ2_S OFF baseline.
7. Do not add IQ3, Ornith, Qwen 9B, MTP or other profiles.
8. The only profiles are:
   - `iq2-dflash-frog-medium`
   - `iq2-dflash-frog-medium-b256`
9. Do not replace Froggeric v22.4 with another template version or with Hugging Face `main`. The runner expects the pinned v22.4 revision and embedded version marker.
10. Do not alter context, threads, KV types, sampling, DFlash2 draft size, Froggeric template kwargs, reasoning effort, reasoning budget, evaluator, fixtures, timeout or model files.
11. Do not apply context/CPU/GPU fallback if a server fails to load. Preserve and report the failure.
12. Do not rerun an already-written task JSON to improve a score.
13. Preserve all server logs and failed traces.
14. After all 16 runs complete with no infrastructure errors, commit only generated artifacts under `benchmarks/repo-worker-gsq-dflash2-v4/` and push to `master`.
15. Do not rank or interpret the profiles before ChatGPT audits the raw traces.

Execution:

```bash
cd /home/alpha/Playstoria/models
git pull --ff-only origin master
bash benchmarks/repo-worker-gsq-dflash2-v4/PREPARE_DFLASH2.sh
python3 benchmarks/repo-worker-gsq-dflash2-v4/runner/benchmark_orchestrator.py
```

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
```

Then include the factual `RESULTS.md` table and the contents of `DFLASH_METRICS.json`. Do not add a subjective winner.
