# Escha runtime microbenchmark v1

## Goal

Determine whether the observed Qwen3.8-27B Escha W2 decode speed on the RTX 5060 Ti 16 GB is caused by a runtime/configuration issue or is normal for the `llama.cpp-escha` port.

This is a **performance-only microbenchmark**. Do not change model weights, prompts, samplers, template behavior, or benchmark scope to improve results.

## Upstream reference

Target fork/branch:

- `https://github.com/Ajay9o9/llama.cpp-escha.git`
- branch: `escha-w2-dense`

Target GGUF:

- `Escha-Qwen3.8-27B-W2-Q8E.gguf`

The upstream author recommends full GPU offload, Flash Attention, one parallel slot, and Q8_0 for both K and V KV cache when serving.

## Local constraints

- GPU: RTX 5060 Ti 16 GB
- CPU threads: 8 maximum
- Use the already-built `escha-w2-dense` fork first. **Do not rebuild before Phase 1.**
- Do not download another model for this test.
- Do not use Froggeric or another chat template for the raw performance test.
- Do not use DFlash/speculative decoding.
- One server at a time.

## Preflight evidence

Record:

```bash
nvidia-smi --query-gpu=name,driver_version,memory.total,power.limit --format=csv,noheader
```

From the local Escha fork record:

```bash
git remote -v
git branch --show-current
git rev-parse HEAD
git status --short
```

Record the exact model path and SHA256:

```bash
sha256sum /exact/path/Escha-Qwen3.8-27B-W2-Q8E.gguf
```

Record the available benchmark/server flags from the actual built binaries before using them:

```bash
./build/bin/llama-bench --help | head -n 120
./build/bin/llama-server --help | grep -E 'cache-type|flash|jinja|threads|parallel|ctx|gpu-layers' -n
```

If the expected model or fork/branch is missing, stop and report; do not substitute another model or branch.

## Phase 1A — direct llama-bench reference shape

Run `llama-bench` with the Q8E GGUF, full GPU offload, one sequence/stream, 8 CPU threads, and the same basic test shape published upstream: prompt processing 512 tokens and token generation 128 tokens. Use 5 repetitions if supported by the installed binary.

Use the exact option names printed by this fork's `llama-bench --help`; do not guess unsupported flags.

Required semantic settings:

- model: Q8E GGUF above
- GPU layers: full offload (`99` or equivalent)
- Flash Attention: on, if exposed by `llama-bench`
- threads: 8
- prompt processing: 512 tokens
- token generation: 128 tokens
- repetitions: 5

Save the full command and raw output.

This phase exists to compare the local fork against the upstream author's published `pp512` / `tg128` benchmark shape without chat-template effects.

## Phase 1B — KV cache A/B through llama-server

Use raw `/completion`, not `/v1/chat/completions`, so chat templates cannot affect the comparison.

Common server settings for both profiles:

- model: Q8E GGUF
- `-ngl 99` or equivalent full offload
- Flash Attention: on
- parallel slots: 1
- threads: 8
- context: 8192
- no speculative decoder
- no external chat template
- bind localhost only

Profile A — current benchmark-style KV:

- K cache: `q8_0`
- V cache: `q4_0`

Profile B — upstream-recommended KV:

- K cache: `q8_0`
- V cache: `q8_0`

For each profile:

1. Start a fresh server.
2. Wait until model load is complete.
3. Record idle VRAM with `nvidia-smi`.
4. Send the exact same raw completion request 5 times sequentially, with exactly 256 predicted tokens each time.
5. Use deterministic sampling if supported (`temperature: 0`); the text itself is irrelevant, but output token count must be identical or the timing must be normalized by generated token count.
6. Record the server-reported prompt-eval and generation timing/tok/s for every repetition.
7. Record peak GPU memory during generation.
8. Stop the server completely before starting the other profile.

Raw prompt for every request:

```text
Write a long numbered sequence of concise software engineering observations. Continue until the generation limit. Do not stop early.
```

If the model emits EOS before 256 tokens, rerun using the server option/API field that ignores EOS **only if it is documented by the installed binary/API**. Otherwise report the actual generated-token count and compare normalized tok/s; do not alter the prompt between profiles.

## Phase 1C — sanity check for CUDA specialization

From server startup and/or benchmark logs, record the detected CUDA device and compute capability/kernel path if printed.

Do **not** rebuild merely because the current CMake build contains multiple architectures (`120;89;86;80;75`). A fat binary is not itself evidence of a slow runtime.

Only proceed to Phase 2 if one of these is true:

- logs suggest the intended Blackwell/CUDA kernel is not being selected;
- `llama-bench` performance is implausibly low relative to memory-bandwidth scaling;
- Profile B unexpectedly regresses badly or errors;
- the binary reports an architecture mismatch/fallback.

## Phase 2 — optional sm_120-only rebuild

Run only if Phase 1C provides a reason.

Keep the existing build intact and create a separate build directory, e.g. `build-sm120`, with:

```bash
cmake -S . -B build-sm120 -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=120
cmake --build build-sm120 --target llama-bench llama-server -j8
```

Then repeat only Phase 1A and the faster of the two Phase 1B KV profiles. Do not rerun unrelated model benchmarks.

## Required result artifact

Create:

`benchmarks/escha-runtime-micro-v1/RESULTS.md`

It must contain:

- date/time
- GPU/driver/power-limit evidence
- fork branch + commit
- model path + SHA256
- exact commands
- Phase 1A raw `llama-bench` results and median `pp512` / `tg128`
- Phase 1B five-run table for Q8/Q4 and Q8/Q8
- median generation tok/s for each KV profile
- percentage difference Q8/Q8 vs Q8/Q4
- idle/peak VRAM for each profile
- whether CUDA/kernel logs show an unexpected fallback
- whether Phase 2 was necessary; if run, its before/after numbers
- concise conclusion: `CONFIG_ISSUE`, `EXPECTED_PORT_LIMIT`, or `INCONCLUSIVE`, with evidence

Do not delete the Escha model or fork as part of this benchmark.
