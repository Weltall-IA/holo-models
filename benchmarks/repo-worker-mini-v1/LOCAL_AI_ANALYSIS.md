# Local AI Analysis

This file is interpretation of the objective artifacts in `RESULTS.json`; it is not part of the raw measurement layer.

## Headline

Both models scored 0/5 on the five-task repo-worker battery with `MAX_TOKENS_PER_TURN = 1024`. Neither model produced a changed fixture file in any task, so neither completed an edit task end to end.

With 1024 tokens per turn, Ornith's reasoning model had enough space to produce complete reasoning traces and JSON tool calls without cutting off. It correctly identified the root cause of the `retry.py` bug in its internal reasoning (attempt count off-by-one and exception handling), but timed out during its multi-turn deliberation before successfully applying a patch. Bonsai made 4 patch attempts on `task03` with complete JSON output, but the patches failed to apply because `git apply` requires standard unified diff headers (`--- a/...`, `+++ b/...`) which the model omitted.

## Objective Results

| Model | Passes | Avg task time | Avg tool calls | Avg completion tokens | Total tokens | Patch attempts | Files changed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Bonsai | 0/5 | 180.03 s | 9.0 | 222.6 | 1113 | 4 | 0 |
| Ornith | 0/5 | 180.02 s | 8.6 | 1733.2 | 8666 | 0 | 0 |

Stop reasons:

- Bonsai: five `generation_timeout` stops (reached the 180s task time budget).
- Ornith: five `generation_timeout` stops (reached the 180s task time budget).

Ornith generated significantly more tokens per task (8,666 total vs 1,113 for Bonsai), reflecting its reasoning chain per turn. Peak sampled VRAM was 12,556-13,114 MiB for Bonsai and 11,424-11,859 MiB for Ornith.

## Task Patterns

- `task01` navigation: Bonsai searched `library` and read `routing/model-bindings.yaml`, mentioning `project-rw` in its search, but timed out before assembling the final answer. Ornith navigated through contracts, rules, and instructions, reading 4 files before the 180s budget expired.
- `task02` rename: Bonsai searched for `tool_timeout_s` and read settings. Ornith read `test_settings.py`, `settings.py`, `config.json`, and `README.md` (6 files total), but did not execute a patch before timing out.
- `task03` retry fix: Bonsai read the implementation and test, and attempted 4 unified diff patches. All 4 patch attempts failed at `git apply` due to missing `--- a/` and `+++ b/` file headers. Ornith accurately diagnosed the off-by-one loop (`range(attempts)`) in its reasoning trace, but deliberated across turns until task timeout.
- `task04` loader support: Bonsai searched and read loader files across 18 tool calls. Ornith read 6 files and explored `loader.py`, `loader.pyi`, and `test_loader.py`. Neither model emitted a complete patch adding `reasoning_budget`.
- `task05` capability investigation: Bonsai performed broad regex searches. Ornith read `AGENTS.md` and repository docs. Both timed out before emitting the final summary.

## Interpretation

Increasing `MAX_TOKENS_PER_TURN` to 1024 solved the token truncation issue that previously caused protocol syntax errors:
1. **Ornith**: The reasoning trace (`reasoning_content`) no longer exhausts the token budget, allowing valid tool calls. The model shows strong diagnostic capability in reasoning, but is slow to transition from reasoning to active modification.
2. **Bonsai**: With 1024 tokens, it successfully generates full diff payloads without JSON truncation. However, its generated diffs lack `git apply` header syntax (`--- a/fixture/retry.py`), demonstrating that raw diff formatting without standard file headers is a barrier for small/quantized models.

## Limitations

- Small five-task battery with deterministic seed (`3407`), concurrency 1, and 180s per-task timeout.
- Evaluated on RTX 5060 Ti 16 GB with PrismML runtime (Bonsai Q2_0) and deepgrove llama.cpp (Ornith Q5_K_M).
- Browser capability was evaluated from local repository documentation only.
- Raw transcripts and per-task objective checks in `benchmarks/repo-worker-mini-v1/` remain the source of truth for full auditability.
