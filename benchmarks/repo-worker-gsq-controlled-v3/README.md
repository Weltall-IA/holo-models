# Repo Worker GSQ Controlled v3

Focused experiment for the two surviving Qwen3.8-27B GSQ-RCO quantizations.

This round answers two separate questions with controlled within-quant comparisons:

1. Does the native Qwen MTP head improve repo-worker throughput without reducing task correctness?
2. With MTP held ON, does a hard reasoning budget recover useful thinking without the long `reasoning=on` stalls seen in challenger-v2?

## Models

Use the official ISTA-DASLab `-mtp` builds, not community-grafted files:

- `Qwen3.8-27B-GSQ-RCO-IQ2_S-mtp.gguf`
- `Qwen3.8-27B-GSQ-RCO-IQ3_XXS-mtp.gguf`

`PREPARE_MODELS.sh` downloads both into `/home/alpha/Playstoria/models/text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-MTP/` and records their SHA256 values.

## Six profiles

| profile | reasoning | MTP |
|---|---|---|
| iq2-off-nospec | OFF | OFF |
| iq2-off-mtp | OFF | `draft-mtp`, n-max 3 |
| iq2-budget256-mtp | ON, hard budget 256 | `draft-mtp`, n-max 3 |
| iq3-off-nospec | OFF | OFF |
| iq3-off-mtp | OFF | `draft-mtp`, n-max 3 |
| iq3-budget256-mtp | ON, hard budget 256 | `draft-mtp`, n-max 3 |

All six use the same sampling and runtime envelope:

- seed `27183`
- temperature `0.2`
- top_p `0.95`
- context `32768`
- threads/batch threads `4/4`
- full GPU offload
- flash attention ON
- KV cache `Q4_0/Q4_0`
- one slot
- task timeout `480 s`

The budgeted profiles use `--reasoning-budget 256` and a short budget-exhaustion message. They are not unrestricted Thinking ON profiles.

## Suite

The eight tasks, public fixtures and hidden tests are intentionally reused from `repo-worker-challenger-v2`. This is a controlled operating-point experiment, so changing the workload would add an unnecessary variable.

One evaluator defect discovered during the independent v2 audit is corrected: T7 no longer requires an unnecessary edit to `service/profile_service.py`. The correct implementation may edit only `policy/access.py`; the evaluator still requires the service to consume the policy and forbids duplicating the `reserved:` rule in the service.

## Execution

```bash
cd /home/alpha/Playstoria/models
git pull --ff-only origin master
bash benchmarks/repo-worker-gsq-controlled-v3/PREPARE_MODELS.sh
python3 benchmarks/repo-worker-gsq-controlled-v3/runner/benchmark_orchestrator.py
```

Do not modify the runner if a profile fails preflight or does not fit. Preserve the failure and report it.

Expected run count: `6 profiles × 8 tasks = 48`.

The runner stores per-task traces, server logs, corrected prompt/decode TPS, MTP draft-acceptance statistics, VRAM and factual result tables. It does not choose a winner.
