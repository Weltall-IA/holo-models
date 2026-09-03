# coding-mini-v1 — Evaluator Corrections

Status: canonical correction to the local evaluator implementation. The case specifications in `CASES.md` are unchanged.

Source cases commit: `8233069c88f5b6e463186ba1a383130342689277`
Original results commit: `4e9bbb962e55ce92c61bd41dabb141482769af15`

Do not rerun any model. Re-evaluate the already-generated `extracted_code` from `results/RAW_RESULTS.jsonl` after applying only the corrections below.

## PY01 — TTL cache

The canonical contract says `ttl` must be strictly positive and the hidden requirements include invalid TTL preserving the old value. It does **not** define mandatory coercion/type-validation behavior for non-numeric objects.

The local harness incorrectly broadened the task by requiring `ValueError` for string and `None` TTL values.

Correct the invalid-TTL hidden loop to use only numeric non-positive values:

```python
for bad_ttl in [0, -1, -0.001]:
    try:
        c.set("k1", "bad", bad_ttl)
        assert False, f"Expected ValueError for ttl={bad_ttl}"
    except ValueError:
        pass
```

Do not test `"5"`, `None`, or other non-numeric values unless the canonical case specification is explicitly revised in a future benchmark version.

All other PY01 public/hidden tests remain unchanged.

## PY02 — retry decorator

The canonical contract requires `ValueError` when `max_attempts <= 0`. It does **not** specify that strings, booleans, floats, or other non-integer types must be rejected with a particular exception type.

The local harness incorrectly broadened the task by testing `"3"` and `False` as mandatory `ValueError` cases.

Correct the hidden validation loop to:

```python
for bad_n in [0, -1, -5]:
    try:
        retry(max_attempts=bad_n)
        assert False, f"Expected ValueError for max_attempts={bad_n}"
    except ValueError:
        pass
```

All other PY02 tests remain unchanged, including:

- exact call counts;
- exhaustion re-raises the last eligible exception;
- per-invocation state isolation;
- metadata preservation;
- tuple and single exception-class handling;
- `max_attempts=1`.

## CPP03 — lazy affine segment tree

The canonical public example has exactly one correct output. After:

- initial `[1, 2, 3]`;
- `SUM 0 2` => `6`;
- `ADD 0 1 5` => `[6, 7, 3]`, sum `16`;
- `MUL 1 2 2` => `[6, 14, 6]`, sum `26`;
- `SUM 1 1` => `14`.

The local evaluator temporarily accepted either `26` or `28`. Remove that compatibility allowance.

The public output must be exactly:

```text
6
16
26
14
```

The 200 randomized differential scenarios and large-scale test remain unchanged.

## Re-evaluation procedure

Do not call any LLM and do not start any model server.

1. Apply the three evaluator corrections above.
2. Keep `results/RAW_RESULTS.jsonl` unchanged as the historical raw-generation artifact.
3. For each of its 30 rows, take the already stored `extracted_code` and run the corrected evaluator.
4. Create:
   - `results/RAW_RESULTS_REEVALUATED.jsonl`
   - `results/SUMMARY_CORRECTED.md`
5. Preserve generation metrics (`predicted_per_second`, wall time, VRAM) from the original rows; only evaluator outcomes may change.
6. Report which rows changed PASS/FAIL and the exact corrected reason.
7. Validate the six reference solutions again under the corrected evaluators before re-evaluating model outputs.

Required final checks:

```text
MODELS_EXECUTED=0
ROWS_REEVALUATED=30/30
REFERENCE_PUBLIC_PASS=6/6
REFERENCE_HIDDEN_PASS=6/6
CPP03_DIFFERENTIAL_PASS=200/200
```

Do not change the case prompts, generation parameters, model outputs, or original raw-results file.
