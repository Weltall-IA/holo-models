# Run Configuration

Source repository: `/home/alpha/Playstoria/holo-agent-tooling`
Source commit: recorded in `RESULTS.json`.
Hardware: NVIDIA RTX 5060 Ti 16 GB; AMD Ryzen 7 2700X.

Requested baseline:
- full GPU offload where the runtime can fit
- context 32768
- concurrency 1
- Flash Attention on
- KV K Q8_0, KV V Q4_0
- threads 4, batch threads 4
- seed 3407
- temperature 0.2, top_p 0.95
- speculative decoding off

Per-model runtime/template differences are recorded in `RESULTS.json`. The benchmark protocol uses one JSON tool action per model turn. The final run used a maximum of 20 tool calls, 12000 generated/reasoning output tokens, 128 model tokens per turn, and 180 seconds per task. Each HTTP generation runs in a terminable subprocess so a slow response cannot block later tasks. Browser is unavailable in this local harness unless recorded otherwise.
