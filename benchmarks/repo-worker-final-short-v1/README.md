# Repo-Worker Short Final Candidate Benchmark (v1)

This directory contains the short, focused comparative benchmark of top repo-worker candidates for the Weltall-IA / Holoplay stack:

- **Ornith 1.5 9B Q5_K_M** (Thinking OFF)
- **Ternary Bonsai 27B** (Thinking ON + DSpark ON)
- **Qwen3.8-20B-Minitron IQ3_M** (Thinking OFF)
- **Vireqo-27B-Plus** (Corrected reference config, Thinking OFF)

## Execution Structure
- `runner/benchmark_orchestrator.py`: Python master test runner executing all agent loops against isolated clean worktrees.
- `PREFLIGHT.md`: Detailed preflight validation, hashes, runtimes, and sanity check results.
- `RUN_CONFIG.md`: Exact model and server runtime parameters.
- `RESULTS.json`: Complete turn-by-turn trace, timing, VRAM, and evaluation payload.
- `RESULTS.md`: Formatted metrics comparison and executive summary.
- `profiles/`: Subdirectory per candidate storing per-task JSON traces and server output logs.
