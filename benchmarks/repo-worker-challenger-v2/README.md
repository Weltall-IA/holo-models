# Repo-Worker Challenger v2

Independent second-round benchmark for the four surviving local repo-worker operating points.

This suite deliberately does **not** reuse the six tasks from `repo-worker-final-short-v1`. It targets the failure modes exposed by the audit of v1:

- false PASS without a final `done`;
- string-oracle leakage from intermediate turns;
- public tests that can be weakened or left unchanged;
- "recovery" credited when the required failure never happened;
- semantic regressions hidden by shallow tests;
- architectural placement errors;
- contaminated server decode-TPS parsing.

## Candidates

Exactly four profiles are defined:

1. Qwen3.8-27B GSQ-RCO IQ2_S — Thinking OFF
2. Qwen3.8-27B GSQ-RCO IQ3_XXS — Thinking ON
3. Qwen3.8-9B Distill uncensored/heretic Q4_K_M — Thinking OFF
4. Ornith 1.5 9B Q5_K_M — Thinking OFF

All use 32K context, one slot, full GPU offload, FA ON, KV K=Q8_0 / V=Q4_0, four CPU threads and four batch threads.

## Run

From `/home/alpha/Playstoria/models`:

```bash
python3 benchmarks/repo-worker-challenger-v2/runner/benchmark_orchestrator.py
```

The runner is resumable: any existing `profiles/<profile>/taskNN.json` is preserved and skipped. It never reruns a completed task automatically.

A single fixed seed (`9137`) is used for all four profiles. Total planned work is 32 runs.

## Audit model

The agent can access only its isolated cloned worktree through the benchmark tool protocol. Hidden tests are bundled under `hidden/hidden_files.json`, outside the worktree, and are injected only **after** the agent has terminated. Shell execution from the agent is restricted to relative-path pytest commands, preventing hidden-test discovery through absolute-path shell access.

Generated results are factual only. The runner does not declare a winner or infer causal explanations.
