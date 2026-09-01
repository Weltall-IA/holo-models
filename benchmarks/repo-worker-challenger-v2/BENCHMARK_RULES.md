# Benchmark Rules

## Non-negotiable PASS rules

A task cannot PASS unless:

- the model emitted a valid final `done` action;
- the task did not end in timeout or request error;
- all task-specific mandatory criteria passed.

For coding tasks, public pytest success is not sufficient. Post-run hidden tests are authoritative.

## Hidden-test isolation

Hidden tests are versioned under `hidden/`, but are outside the cloned agent worktree. The agent tool surface is restricted to the worktree. The `run` action accepts only relative-path pytest commands and rejects absolute paths, parent traversal, shell pipelines and redirections.

Only after the agent terminates does the evaluator copy the relevant hidden test into the worktree, execute it, record output, and remove it.

## Recovery semantics

If a task requires an intentional failing action:

1. that exact action must actually be attempted;
2. the tool result must be `ok=false`;
3. a later useful tool action must succeed;
4. the final `done` answer must satisfy the task oracle.

Skipping the required failing action is not recovery.

## Protocol semantics

The agent must output one JSON object per turn. Prose mixed with the tool JSON is a protocol failure. The runner can send one corrective feedback turn after malformed output, but the error is retained in the trace.

## Performance semantics

`prompt eval time` and decode `eval time` are parsed in mutually exclusive branches. A prompt-eval line can never contribute to decode TPS.

Wall-clock workflow metrics and raw generation throughput are reported separately. No throughput metric can convert a functional FAIL into PASS.

## No causal claims

This benchmark compares selected operating points. It is not a controlled causal experiment for quantization level or thinking mode.
