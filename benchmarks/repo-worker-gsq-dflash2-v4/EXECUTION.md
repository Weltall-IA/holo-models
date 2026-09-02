# Executor contract — IQ2 DFlash2 + Froggeric v22.4

The local AI is an executor only. It must not redesign this round.

1. If the cancelled `PREPARE_RUNTIME.sh`/`llama.cpp-dflash2-v4` build is still running, stop that process first.
2. `git pull --ff-only origin master`.
3. Remove only the cancelled benchmark-specific runtime directory `/home/alpha/Playstoria/models/engines/llama.cpp-dflash2-v4` if it exists. Do not touch `deepgrove-llama.cpp`.
4. Run `UPDATE_LLAMA_CPP.sh` exactly as versioned. It makes `/home/alpha/Playstoria/models/engines/llama.cpp` the canonical official `ggml-org/llama.cpp` runtime for new GGUF work, pinned to the benchmark revision.
5. Run `PREPARE_DFLASH2.sh` exactly as versioned.
6. Run `runner/benchmark_orchestrator.py` exactly as versioned.
7. Expected workload is only `2 profiles × 8 tasks = 16` new runs.
8. Do not rerun the old challenger-v2 IQ2_S OFF baseline.
9. Do not add IQ3, Ornith, Qwen 9B, MTP or other profiles.
10. The only profiles are:
    - `iq2-dflash-frog-medium`
    - `iq2-dflash-frog-medium-b256`
11. The required runtime is `/home/alpha/Playstoria/models/engines/llama.cpp`, official upstream `ggml-org/llama.cpp`, revision `b96806d96061049a5b574269b049bf6241d63d46`.
12. `/home/alpha/Playstoria/models/engines/deepgrove-llama.cpp` is historical only. Do not update, delete or use it for this round.
13. Do not recreate `llama.cpp-dflash2-v4`.
14. Do not replace Froggeric v22.4 with another template version or Hugging Face `main`.
15. Do not alter context, threads, KV types, sampling, DFlash2 draft size, Froggeric template kwargs, reasoning effort, reasoning budget, evaluator, fixtures, timeout or model files.
16. Do not enable llama.cpp automatic fitting; the runner explicitly uses `--fit off`.
17. Do not apply context/CPU/GPU fallback if the runtime build or server load fails. Preserve and report the failure.
18. Do not rerun an already-written task JSON to improve a score.
19. Preserve all server logs and failed traces.
20. After all 16 runs complete with no infrastructure errors, commit only generated artifacts under `benchmarks/repo-worker-gsq-dflash2-v4/` and push to `master`.
21. Do not rank or interpret the profiles before ChatGPT audits the raw traces.

Execution:

```bash
cd /home/alpha/Playstoria/models

git pull --ff-only origin master
git rev-parse HEAD

# Clean up only the cancelled duplicate runtime after its build process is stopped.
rm -rf /home/alpha/Playstoria/models/engines/llama.cpp-dflash2-v4

bash benchmarks/repo-worker-gsq-dflash2-v4/UPDATE_LLAMA_CPP.sh
bash benchmarks/repo-worker-gsq-dflash2-v4/PREPARE_DFLASH2.sh
python3 benchmarks/repo-worker-gsq-dflash2-v4/runner/benchmark_orchestrator.py
```

If `UPDATE_LLAMA_CPP.sh` fails, stop and return the exact error. Do not patch it, switch runtime, checkout another commit or fall back to DeepGrove.

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
