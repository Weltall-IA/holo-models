# Whittle16B Candidate v1 — compact historical summary

Evaluation date: 2026-09-04

## Identity

- Repo: `logic65/Qwen3.8-Whittle-16B`
- GGUF tested: `Qwen3.8-Whittle-16B-v2-Q4_K_M.gguf`
- Size: `10142250656` bytes (`9.45 GiB`)
- SHA256: `335627718b0893a1b077728cd40b4a6b75e2850a6058eb564945f7a2b6265bd2`
- HF revision: `d18db969059b15423be91f5d4fd119c8c907801c`
- Runtime: llama.cpp `0.3.0-dev`, build `10752`, commit `b96806d96`
- Hardware: RTX 5060 Ti 16 GB; 8 threads; full GPU offload; FA ON; ctx 8192; KV q8_0/q4_0

## Measured configuration

The candidate was tested with the upstream author recipe rather than the historical GSQ sampling protocol:

`--jinja --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 4 --repeat-penalty 1.15 --repeat-last-n 512`, temperature `0.7`, top_p `0.95`, min_p `0.05`, thinking ON, seed `9137`, completion budget `3072`.

Therefore throughput is labelled **AUTHOR_RECIPE** and must not be merged into the same-protocol GSQ leaderboard. Correctness is directly comparable because the exact same six canonical `coding-mini-v1` cases/evaluator were used.

## Result

- Coding: **0/6** (`0/3` Python, `0/3` C++20)
- Median decode: **19.83 tok/s** (`AUTHOR_RECIPE`)
- Peak VRAM: **11076 MiB**
- PY01: FAIL hidden; 22.11 tok/s
- PY02: FAIL compile; 19.94 tok/s
- PY03: FAIL public; 21.73 tok/s
- CPP01: FAIL compile; 19.72 tok/s
- CPP02: FAIL compile; 16.20 tok/s
- CPP03: FAIL compile/truncated at 3072; 16.03 tok/s

Gate result: `0/6` → Stage B DFlash2 and Stage C agent were correctly skipped.

Classification: **`WHITTLE16B_REJECT`**.

Historical controls, not rerun: GSQ base `6/6 @ 24.70 tok/s`; GSQ + DFlash2 n=7 `6/6 @ 46.00 tok/s`; GSQ native agent `7/8, 70/80`. The older Whittle-MoE-27B-A18B is a different model and previously scored `1/6 @ 19.39 tok/s`, peak `15194 MiB`.

## Compact-history state

The model weights and runtime symlink were removed after rejection. The inactive profile was also removed from `text/` so active model categories do not retain historical-only model folders.

Under the workspace compact-history policy, the current branch preserves:

- `benchmarks/whittle16b-candidate-v1/SPEC.md`
- this `SUMMARY.md`
- `benchmarks/whittle16b-candidate-v1/results/RUN_MANIFEST.json`
- the central `MODEL_HISTORY.md` ledger entry

Bulky raw JSONL, server log, GPU preflight snapshot and the benchmark-specific runner were removed from the current branch. They remain recoverable from Git history at the original execution commit:

`c9823c3952666ae054610a404b3d4a2cafd4e553`

The subsequent weight-removal/documentation commit was:

`5563f043c6e4b99a6f937399f76975508350bed8`

Note: the original `RUN_MANIFEST.json` field `git_commit` records the pre-execution benchmark/spec HEAD, not the commit that later added the results. For provenance of the complete raw run, use `c9823c3952666ae054610a404b3d4a2cafd4e553`.

Do not redownload/retest this exact v2 Q4_K_M candidate automatically. Consult `MODEL_HISTORY.md` first; require explicit user confirmation unless a materially new revision/configuration justifies a new evaluation.
