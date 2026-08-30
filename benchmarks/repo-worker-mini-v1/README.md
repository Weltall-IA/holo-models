# Repo Worker Mini Benchmark v1

Objective facts only. This benchmark compares two local models as repository workers across five small tasks. Each model/task runs in an isolated disposable worktree from the same source commit.

The runner records prompts, raw model turns, tool calls/results, patches, tests, token usage, timings, and VRAM samples. Browser access is recorded as unavailable unless explicitly enabled by the runner.

Models:
- Bonsai: local Ternary Bonsai Q2_0 through the PrismML llama.cpp runtime.
- Ornith: `bartowski/Ornith-1.5-9B-GGUF`, `Ornith-1.5-9B-Q5_K_M.gguf`.

The first results commit contains objective measurements only. Subjective analysis is stored separately in `LOCAL_AI_ANALYSIS.md` in the second commit.
