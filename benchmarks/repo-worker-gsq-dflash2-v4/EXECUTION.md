# Executor contract — IQ2 DFlash2 + Froggeric v22.4

The local AI is an executor only. It must not redesign this round.

The previous source-build instructions are cancelled. Do not run `UPDATE_LLAMA_CPP.sh` and do not compile llama.cpp locally.

Use the Arch Linux packages `llama-cpp` and `ggml-cuda`. The benchmark runner resolves `llama-server` from PATH and records the installed package/runtime version in `CONTROLLED_CONFIG.json`.

Before continuing, stop the cancelled CMake/build process and remove the incomplete `engines/llama.cpp-dflash2-v4` and `engines/llama.cpp` source/build trees created by the cancelled instructions. Do not touch `engines/deepgrove-llama.cpp`; it is historical only.

Verify that `llama-server` from the Arch package exposes DFlash2, Jinja, reasoning-effort, reasoning-budget, custom chat-template and `--fit` support. If any required feature is missing, stop and report it; do not compile from source and do not fall back to DeepGrove.

Then run `PREPARE_DFLASH2.sh` and `runner/benchmark_orchestrator.py` exactly as versioned.

The only profiles are `iq2-dflash-frog-medium` and `iq2-dflash-frog-medium-b256`, for 16 runs total. Do not change context, threads, KV types, sampling, DFlash2 draft size, Froggeric template, reasoning settings, evaluator, fixtures, timeouts or model files. Do not rerun completed task JSONs to improve scores.

After a clean 16/16 run, commit only generated artifacts under this benchmark directory with message `bench(repo-worker): execute IQ2 DFlash2 Froggeric v22.4`, push to master, and return COMMIT, SOURCE_REPO_HEAD, SEED, RUNS_COMPLETED, INFRA_ERRORS, RUNTIME_REVISION, RESULTS.md, DFLASH_METRICS.json and CONTROLLED_CONFIG.json. Do not rank or interpret the profiles.
