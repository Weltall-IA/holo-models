# Local AI Analysis

This file is interpretation of the objective artifacts in `RESULTS.json`; it is not part of the raw measurement layer.

## Headline

Both models scored 0/5 on the five-task repo-worker battery. Neither model produced a changed fixture file in any task, so neither completed an edit task end to end.

Under this protocol, Ornith was the stronger executor: it read more, generated substantially more tokens, and completed more tool turns before stopping. It still failed the benchmark because exploration did not turn into valid patches and it reached either the tool-call cap or a generation timeout.

## Objective Results

| Model | Passes | Avg task time | Avg tool calls | Avg completion tokens | Patch attempts | Files changed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Bonsai | 0/5 | 116.34 s | 8.6 | 212.0 | 1 | 0 |
| Ornith | 0/5 | 99.24 s | 14.4 | 1266.6 | 0 | 0 |

Stop reasons:

- Bonsai: five `generation_timeout` stops.
- Ornith: three `generation_timeout` stops and two `max_tool_calls` stops.

The runtime's sampled generation rates were higher for Ornith on every task: Bonsai ranged from 0.58 to 3.78 tokens/s, while Ornith ranged from 1.89 to 20.17 tokens/s. Peak sampled VRAM was 12,556-13,114 MiB for Bonsai and 11,424-11,859 MiB for Ornith.

## Task Patterns

- `task01` navigation: Bonsai found the routing file and mentioned two of the required markers, but timed out before producing the complete required answer. Ornith read four relevant files but also timed out before completing the answer.
- `task02` rename: both models discovered or emitted the new key in some form, but left `tool_timeout_seconds` present and changed no fixture files. Bonsai stopped on a generation timeout after seven tool calls; Ornith used all 20 tool calls without a valid patch.
- `task03` retry fix: the focused test remained failing for both models with four calls instead of the required three. Bonsai attempted one patch, but the fixture was unchanged afterward. Ornith made no patch attempt and stopped at the tool-call limit.
- `task04` loader support: the focused test passed because the original test already passed, but neither model added `reasoning_budget`, the environment variable, the typed surface, documentation, or the required file set. Both therefore failed the feature-specific oracle.
- `task05` capability investigation: Bonsai mentioned three of the required markers but missed `browser` and timed out. Ornith read only `AGENTS.md`, missed all required markers in its final answer, and timed out.

## Interpretation

The benchmark separates repository exploration from repository-worker completion. Ornith demonstrated better throughput and broader exploration, but the zero patch count indicates that its extra turns were not converted into repository changes. Bonsai generated much more slowly under the selected PrismML configuration; its short runs ended before it could finish even when it had started the right investigation. The observed winner for practical repo-worker throughput is therefore Ornith, but neither model is reliable enough for unattended edit tasks under this configuration.

The main failure mode was completion control, not server startup. Both servers passed the startup/smoke stage. Bonsai consistently ran into generation timeouts. Ornith had enough generation capacity to consume the action budget on two edit tasks, which points to inefficient tool-loop behavior or failure to commit to a patch after inspection.

## Limitations

- This is a small five-task battery with one deterministic seed and one concurrency slot; it is directional, not a general model ranking.
- The models used different runtimes: PrismML llama.cpp for Bonsai and deepgrove llama.cpp for Ornith. Runtime behavior is part of this comparison and limits model-only attribution.
- Browser access was unavailable, so browser capability was evaluated from local repository documentation only.
- The benchmark used 128 generated model tokens per turn, a 20-tool-call cap, and a 180-second task timeout. A different turn budget or prompting policy could materially change completion rates.
- The raw transcripts and per-task objective checks are the source of truth for auditability; this document should not be used without them.
