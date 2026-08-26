# Local execution — Qwen3.8-27B uncensored round v1

Do not generate or redesign tests. The runner is already versioned in this directory and reuses the exact same fresh 30-case tie-break battery for direct comparability with previous results.

## 1. Update

```bash
git pull --ff-only origin master
python3 -m py_compile benchmarks/qwen38-27b-16gb-uncensored-round-v1/run_uncensored_round.py
```

## 2. Remove only the RVN benchmark baseline

Remove the RVN **Q3_K_M baseline downloaded for the benchmark**, including runtime symlinks/reflinks that point to that exact physical file, following the repository `AGENTS.md` removal rules. Verify `find . -xtype l` afterward.

Do **not** remove `RVN-IQ3_M-multilingual-mtp.gguf` or any unrelated pre-existing RVN variant unless explicitly instructed later.

## 3. Ensure these exact model artifacts exist under canonical `text/`

Check before downloading. Do not duplicate an existing physical GGUF.

### Ektome i1-IQ3_M

Repo:
`mradermacher/Ektome-Qwen3.8-27B-PristinelyUncensored-i1-GGUF`

Exact file:
`Ektome-Qwen3.8-27B-PristinelyUncensored.i1-IQ3_M.gguf`

Target size is about 12.8 GB.

### Heretic ARA i1-IQ3_M

Repo:
`mradermacher/Qwen3.8-27B-heretic-ara-i1-GGUF`

Exact file:
`Qwen3.8-27B-heretic-ara.i1-IQ3_M.gguf`

Target size is about 12.8 GB.

### ULTIMATE UNCENSORED Hybrid 16GB

Repo:
`lemonyins/Qwen3.8-27B-ULTIMATE-UNCENSORED-MTP-IQ4-GGUF-16GB`

Exact main model file:
`Qwen3.8-27B-ULTIMATE-UNCENSORED-MTP-IQ4-16GB.gguf`

Also download the tiny accompanying:
`chat_template.jinja`

Do not download `mmproj-BF16.gguf` and do not download the Windows TurboQuant ZIP for this first quality round.

Main GGUF size is about 13.2 GB.

For every new download, record repo revision if available, file size and SHA256.

## 4. Runtime fairness and desktop responsiveness

This round intentionally uses the same standard llama.cpp runtime for all three models at 16K. The runner hard-limits CPU work to 8 threads:

- `--threads 8`
- `--threads-batch 8`
- OMP/OpenBLAS/MKL/NumExpr thread envs = 8
- context = 16384
- full GPU offload when possible
- KV K/V = q4_0
- flash attention = on
- parallel = 1
- no MTP speculative decoding
- no vision/mmproj
- temperature = 0.2
- top_p = 0.95
- seeds = 42 and 1337

The ULTIMATE model advertises TurboQuant for its large-context memory claims. Do not switch only that model to TurboQuant in this quality round because that would make the runtime comparison non-uniform. If it cannot boot at 16K on the common runtime, preserve the exact failure and report it. A dedicated TurboQuant/context test can be done afterward.

## 5. Execute

Use the existing local llama-server path if it is not on PATH, for example:

```bash
LLAMA_SERVER=/home/alpha/Playstoria/models/engines/deepgrove-llama.cpp/build/bin/llama-server \
python3 benchmarks/qwen38-27b-16gb-uncensored-round-v1/run_uncensored_round.py
```

The runner loads one model once, executes all 30 cases with both seeds, then unloads it before moving to the next model.

If autodetection is ambiguous, set only the exact paths:

```bash
MODEL_EKTOME=/absolute/path/Ektome-Qwen3.8-27B-PristinelyUncensored.i1-IQ3_M.gguf \
MODEL_ULTIMATE=/absolute/path/Qwen3.8-27B-ULTIMATE-UNCENSORED-MTP-IQ4-16GB.gguf \
MODEL_ARA=/absolute/path/Qwen3.8-27B-heretic-ara.i1-IQ3_M.gguf \
LLAMA_SERVER=/absolute/path/llama-server \
python3 benchmarks/qwen38-27b-16gb-uncensored-round-v1/run_uncensored_round.py
```

## 6. Do not change the benchmark before first run

If there is a real execution bug, show the literal error and apply only the smallest compatibility fix. Do not generate new cases, change validators, alter sampling, or tune one model individually.

## 7. Return

Return the complete `leaderboard.md` plus:

- weighted score
- coding
- tools
- recovery
- benign non-refusal
- seed spread
- mean tok/s
- peak GPU MiB
- exact failed case IDs per model
- any runner errors
- any boot/OOM failure
- exact runtime command for each model
- any code diff that was required

Artifacts are written under:
`tasks/qwen38-27b-16gb-uncensored-round-v1/results/`
