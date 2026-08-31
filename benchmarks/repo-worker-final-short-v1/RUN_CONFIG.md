# Run Configuration — Repo-Worker Short Final Comparison

## Host Environment
- **CPU**: AMD Ryzen 7 2700X Eight-Core Processor (4 threads allocated per candidate, 4 batch threads)
- **GPU**: NVIDIA GeForce RTX 5060 Ti 16GB (Full GPU offload)
- **OS**: Linux x86_64
- **Date**: 2026-08-31

## Evaluated Profiles
1. **O1: Ornith 1.5 9B Q5_K_M**
   - Context: 32768, KV Cache: Q8_0/Q4_0, Thinking: OFF
   - Runtime: Deepgrove (`8ce8ca6c6d370b6235dfa8e2a0611a9adb6d77d1`)
   - Sampling: `temperature=0.2, top_p=0.95`

2. **B4: Ternary Bonsai 27B**
   - Context: 8192, KV Cache: Q8_0/Q4_0, Thinking: ON, DSpark: ON
   - Runtime: PrismML (`9ca265a57f85f2117942490f421f64a226dd9847`)
   - Spec: `--spec-type draft-dspark --spec-draft-n-max 4`
   - Sampling: `temperature=0.7, top_p=0.95, top_k=20`

3. **M1: Qwen3.8-20B-Minitron IQ3_M**
   - Context: 16384, KV Cache: Q8_0/Q4_0, Thinking: OFF
   - Runtime: Deepgrove (`8ce8ca6c6d370b6235dfa8e2a0611a9adb6d77d1`)
   - Sampling: `temperature=0.2, top_p=0.95`

4. **V1: Vireqo-27B-Plus**
   - Context: 2048, KV Cache: Q8_0/Q8_0, Thinking: OFF
   - Runtime: Deepgrove (`8ce8ca6c6d370b6235dfa8e2a0611a9adb6d77d1`)
   - Sampling: `temperature=0.7, top_k=20, top_p=0.95, min_p=0, repeat_penalty=1.08, repeat_last_n=64`

## Task Suite (6 Representative Tasks)
- **T1 (`task01_nav_role_chain`)**: Navigation / repository architecture discovery.
- **T2 (`task02_fix_retry_loop`)**: Small algorithmic bugfix in retry loop bounds.
- **T3 (`task03_fix_ratelimit_math`)**: Harder bugfix in token bucket state transition.
- **T4 (`task04_multifile_timeout_rename`)**: Multi-file symbol & config rename across codebase.
- **T5 (`task05_recovery_missing_path`)**: Error recovery & fallback after missing file.
- **T6 (`task06_feature_router_prefix`)**: Incremental feature addition following existing codebase patterns.
