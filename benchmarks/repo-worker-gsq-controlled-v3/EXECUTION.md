# Executor contract

The local executor must execute the versioned benchmark, not redesign it.

1. `git pull --ff-only origin master`.
2. Run `PREPARE_MODELS.sh` exactly once; do not substitute files.
3. Run `runner/benchmark_orchestrator.py`.
4. Do not alter context, KV types, threads, sampling, reasoning budget, MTP settings, evaluator, fixtures, timeout or profiles.
5. Do not auto-fallback context if a server fails to load.
6. Do not rerun completed task JSONs to improve scores.
7. Preserve server logs and all failed traces.
8. After a complete run, commit only generated artifacts under this benchmark directory and push to `master`.
9. Do not write a subjective ranking before ChatGPT audits the traces.
