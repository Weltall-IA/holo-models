# Run Configuration — Repo-Worker Challenger v2

- Seed: `9137`
- Planned runs: `4 profiles × 8 tasks = 32`
- Task timeout: `480 s`
- Per-request timeout ceiling: `240 s`
- Maximum turns: `40`
- Context: `32768`
- Parallel slots: `1`
- GPU layers: `999` (full offload target)
- Flash attention: `ON`
- KV K: `Q8_0`
- KV V: `Q4_0`
- CPU threads: `4`
- Batch threads: `4`
- Runtime: `/home/alpha/Playstoria/models/engines/deepgrove-llama.cpp/build/bin/llama-server`
- Expected runtime Git SHA: `8ce8ca6c6d370b6235dfa8e2a0611a9adb6d77d1`

| Profile ID | Model | Expected SHA256 | Thinking | temp | top_p |
|---|---|---|---|---:|---:|
| `gsq-iq2s-off` | Qwen3.8-27B GSQ-RCO IQ2_S | `16c9802111aa9ef3acde465188d6d601f8db128ee3d828ad983a5caca4135ecb` | OFF | 0.2 | 0.95 |
| `gsq-iq3xxs-on` | Qwen3.8-27B GSQ-RCO IQ3_XXS | `fdfcb6a29b11188956dfbfd904223588a6c1b77eb250c3e8a36e1bd269df91f7` | ON | 0.6 | 0.95 |
| `qwen38-9b-heretic-off` | Qwen3.8-9B Distill uncensored/heretic Q4_K_M | `3a63c5b5c7c6af57d92437ed2610d524ea96a7ecf873ae7f8e470a024c047fa6` | OFF | 0.2 | 0.95 |
| `ornith-15-9b-off` | Ornith 1.5 9B Q5_K_M | `b50e44fd4e4dc2a14e5b864cbc296885d111e772c07286efbac9a20c1f1c63ab` | OFF | 0.2 | 0.95 |

Thinking configurations are the selected operating points from the previous round. Temperature therefore remains part of each operating point; this v2 must not be interpreted as an isolated ON/OFF experiment.
