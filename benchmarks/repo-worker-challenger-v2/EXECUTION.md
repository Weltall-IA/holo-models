# Execution

The suite is already defined. The local agent should only execute it and persist the generated artifacts.

From `/home/alpha/Playstoria/models`:

```bash
git pull --ff-only origin master
python3 benchmarks/repo-worker-challenger-v2/runner/benchmark_orchestrator.py
```

After all 32 traces exist and `INFRA_ERRORS=0`, inspect only that generated files are present, then commit them without rewriting the evaluator or interpreting the results:

```bash
git add benchmarks/repo-worker-challenger-v2/
git commit -m "bench(repo-worker): execute challenger v2 final four"
git push origin master
git rev-parse HEAD
```

Do not rerun a completed task to improve a score. The runner automatically skips existing task JSON files.

If an infrastructure error occurs, report it before any targeted retry. A targeted retry is allowed only after the infrastructure cause is identified; do not delete or overwrite the original INFRA_ERROR trace without preserving it.
