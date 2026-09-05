# Whittle16B Candidate v1 — Results Summary

Generated: 2026-09-04T22:55:17.379820

## Model

- Repo: `logic65/Qwen3.8-Whittle-16B`
- File: `Qwen3.8-Whittle-16B-v2-Q4_K_M.gguf`
- Size: `10142250656` bytes (`9.45 GiB`)
- SHA256: `335627718b0893a1b077728cd40b4a6b75e2850a6058eb564945f7a2b6265bd2`
- HF revision: `d18db969059b15423be91f5d4fd119c8c907801c`
- HF GGUF path: `gguf/Qwen3.8-Whittle-16B-v2-Q4_K_M.gguf`
- Runtime: `0.3.0-dev (build 10752, commit b96806d96) — GNU 16.2.1 for Linux x86_64`
- Hardware: RTX 5060 Ti 16 GB, 8 threads, full GPU offload, FA ON, ctx 8192, KV q8_0/q4_0
- Author recipe: `--jinja --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 4 --repeat-penalty 1.15 --repeat-last-n 512 --temp 0.7 --top-p 0.95 --min-p 0.05` + thinking ON, max_tokens 3072+ (AUTHOR_RECIPE)

## Important Note — Historical Controls vs AUTHOR_RECIPE

GSQ historical numbers were measured with protocol `temp=0.2, top_p=0.95, reasoning off` (same-protocol leaderboard). Whittle 16B AUTHOR_RECIPE uses `temp=0.7, top_p=0.95, min_p=0.05, DRY, repeat-penalty, thinking ON`. Throughput/wall times are **AUTHOR_RECIPE** and must **not** be merged as same-protocol leaderboard entries. Correctness on identical 6 canonical cases **can** be directly compared.

Previous Whittle-MoE-27B-A18B (tested and discarded) is a **different model** (27B MoE pruned) and is not comparable to Whittle 16B dense-pruned. The former scored `1/6, 19.39 tok/s, 15194 MiB` and must remain labelled as separate.

### Historical Controls (not rerun, reused for context)

- GSQ base: `6/6` @ 24.7 tok/s (same-protocol)
- GSQ + DFlash2 n=7: `6/6` @ 46.0 tok/s (same-protocol)
- GSQ agent native: `7/8` 70/80 (native template, temp 0.0)
- Whittle-MoE-27B-A18B old (different model): `1/6` 19.39 tok/s peak 15194 MiB

## STAGE A — Native Whittle 16B Coding (AUTHOR_RECIPE)

- Mode: native template, thinking ON, author DRY/repeat recipe, temp 0.7
- Cases: 6 canonical coding-mini-v1 (PY01 PY02 PY03 CPP01 CPP02 CPP03)
- Completion budget: ≥3072 (3072) per case, reasoning + final code
- Score: **0/6**
- Python: **0/3** | C++: **0/3**
- Median decode (AUTHOR_RECIPE): **19.83 tok/s**

### Per-Case Breakdown STAGE A

| Case | Status | Compile | Public | Hidden | tok/s | prompt tok/s | wall (s) | TTFT (s) | VRAM MiB | comp_len | trunc | loop | thinking_ok |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **PY01** | **FAIL** | PASS | PASS | FAIL | 22.11 | 339.25 | 34.57 | 15.25 | 11076 | 742 | NO | NO | YES |
| **PY02** | **FAIL** | FAIL | FAIL | FAIL | 19.94 | 212.36 | 85.55 | 34.39 | 11021 | 1670 | NO | NO | YES |
| **PY03** | **FAIL** | PASS | FAIL | FAIL | 21.73 | 326.57 | 41.91 | 19.77 | 11046 | 888 | NO | NO | YES |
| **CPP01** | **FAIL** | FAIL | FAIL | FAIL | 19.72 | 308.23 | 72.71 | 30.35 | 11067 | 1410 | NO | NO | YES |
| **CPP02** | **FAIL** | FAIL | FAIL | FAIL | 16.20 | 288.10 | 168.47 | 136.41 | 11047 | 2698 | NO | NO | YES |
| **CPP03** | **FAIL** | FAIL | FAIL | FAIL | 16.03 | 302.18 | 193.37 | 46.53 | 11062 | 3072 | YES | NO | NO |

Peak VRAM Stage A: **11076 MiB**

**GATE:** 0/6 → 0–4/6 = STOP. No DFlash2, no agent per SPEC.

## STAGE B — DFlash2

- **SKIPPED** (gate 0–4/6, per SPEC)

## STAGE C — Agent / Tool-Calling

- **SKIPPED** (requires 6/6 coding in stable config per SPEC)
  - Reason: Stage A was 0/6, not 6/6

## Classification

**WHITTLE16B_REJECT**

- Reason: ≤4/6 coding or serious instability. Not recommended.

## Provenance

- Profile: `text/logic65-Qwen3.8-Whittle-16B-v2-Q4_K_M/Qwen3.8-Whittle-16B-v2-Q4_K_M.md`
- Results: `benchmarks/whittle16b-candidate-v1/results/`
- Commit: see RUN_MANIFEST.json `git_commit`
- All numbers above are MEDIDO LOCALMENTE unless explicitly marked HISTORICAL / AUTHOR_RECIPE
