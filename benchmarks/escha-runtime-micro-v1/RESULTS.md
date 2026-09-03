# Escha Runtime Microbenchmark v1 Results

## Metadata
- **Date/Time**: 2026-09-03 16:35 UTC
- **GPU**: NVIDIA GeForce RTX 5060 Ti (16311 MiB Total, 15866 MiB CUDA visible)
- **Driver Version**: 610.57.04
- **Power Limit**: 150.00 W
- **CPU**: AMD Ryzen 7 2700X Eight-Core Processor (8 threads used)
- **Fork Remote**: `https://github.com/Ajay9o9/llama.cpp-escha.git`
- **Fork Branch**: `escha-w2-dense`
- **Fork Commit**: `2940b807c1562552ae3e152d73f6105f0ac0c98a`
- **Model Path**: `text/aj9o9-Qwen3.8-27B-Escha-W2-GGUF/Escha-Qwen3.8-27B-W2-Q8E.gguf`
- **Model SHA256**: `734ab3c53a468869e4eaf8544c3fe4e4bed5f1f0a47c363750eed29be87ccbab`

---

## Phase 1A — llama-bench Reference Shape

### Command
```bash
./engines/escha-llama/build/bin/llama-bench \
  -m text/aj9o9-Qwen3.8-27B-Escha-W2-GGUF/Escha-Qwen3.8-27B-W2-Q8E.gguf \
  -ngl 99 -fa on -t 8 -p 512 -n 128 -r 5 -o json
```

### Raw llama-bench Output
| Test | Run 1 (t/s) | Run 2 (t/s) | Run 3 (t/s) | Run 4 (t/s) | Run 5 (t/s) | Mean ± StdDev (t/s) | Median (t/s) |
|---|---|---|---|---|---|---|---|
| **pp512** | 479.98 | 476.60 | 497.44 | 496.32 | 491.01 | 488.27 ± 9.50 | **491.01** |
| **tg128** | 16.34 | 16.34 | 16.27 | 16.34 | 16.24 | 16.30 ± 0.05 | **16.34** |

---

## Phase 1B — KV Cache A/B via llama-server (256 tokens)

### Common Configuration
- Model: `Escha-Qwen3.8-27B-W2-Q8E.gguf`
- Offload: `-ngl 99` (full offload)
- Flash Attention: `-fa on`
- Parallel Slots: `-np 1`
- Context: `-c 8192`
- Threads: `-t 8`
- Endpoint: `/completion` (raw prompt, deterministic `temperature: 0.0`, `ignore_eos: true`, `n_predict: 256`)

### Profile A: Current Benchmark-Style KV (`ctk=q8_0, ctv=q4_0`)
- **Idle VRAM**: 10,875 MiB
- **Peak VRAM**: 10,898 MiB

| Run | Prompt Eval (t/s) | Generation Eval (t/s) | Gen Time (ms) | Tokens |
|---|---|---|---|---|
| 1 | 34.76 | 13.51 | 18,948.39 | 256 |
| 2 | 12.48 | 13.46 | 19,012.68 | 256 |
| 3 | 13.35 | 13.63 | 18,786.33 | 256 |
| 4 | 12.83 | 13.73 | 18,650.79 | 256 |
| 5 | 13.57 | 13.55 | 18,893.61 | 256 |
| **Median** | **13.35** | **13.55** | **18,893.61** | **256** |

### Profile B: Upstream-Recommended KV (`ctk=q8_0, ctv=q8_0`)
- **Idle VRAM**: 11,222 MiB
- **Peak VRAM**: 11,344 MiB

| Run | Prompt Eval (t/s) | Generation Eval (t/s) | Gen Time (ms) | Tokens |
|---|---|---|---|---|
| 1 | 34.86 | 15.91 | 16,094.38 | 256 |
| 2 | 12.22 | 15.28 | 16,758.43 | 256 |
| 3 | 13.49 | 15.12 | 16,927.98 | 256 |
| 4 | 13.56 | 15.61 | 16,404.28 | 256 |
| 5 | 13.55 | 15.40 | 16,624.37 | 256 |
| **Median** | **13.49** | **15.40** | **16,624.37** | **256** |

---

## Comparison Summary

| Metric | Profile A (Q8/Q4) | Profile B (Q8/Q8) | Delta |
|---|---|---|---|
| **Median Generation Speed** | 13.55 t/s | 15.40 t/s | **+13.65% (+1.85 t/s)** |
| **Mean Generation Speed** | 13.58 ± 0.11 t/s | 15.46 ± 0.30 t/s | **+13.84%** |
| **llama-bench tg128** | — | — | 16.34 t/s |
| **Idle VRAM** | 10,875 MiB | 11,222 MiB | +347 MiB |
| **Peak VRAM** | 10,898 MiB | 11,344 MiB | +446 MiB |

---

## Phase 1C — CUDA Specialization & Fallback Analysis
- **Detected Device**: `Device 0: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15866 MiB`.
- **Kernel Compilation**: Compiled targeting `CMAKE_CUDA_ARCHITECTURES=120a;89;86;80;75`. Native Blackwell SM120 code was selected and executed without runtime recompilation or JIT overhead.
- **CUDA Fallbacks / Errors**: None. Zero warnings or fallback notices in server/benchmark logs.
- **Phase 2sm_120 Rebuild Requirement**: Not needed, as CUDA capability 12.0 is already natively compiled and fully offloaded.

---

## Conclusion

**`EXPECTED_PORT_LIMIT`** (with actionable KV cache configuration gain)

1. **Port Limit**: The raw kernel dequantization and execution throughput of `llama.cpp-escha` for Qwen3.8-27B W2 on the RTX 5060 Ti 16 GB naturally sits at ~16.3 t/s in `llama-bench` (tg128) and ~15.4 t/s in continuous HTTP `/completion` serving. This is inherent to the custom W2 unpacking kernels in the upstream branch `escha-w2-dense`.
2. **Configuration Gain**: Switching from `q8_0/q4_0` KV cache to the upstream-recommended `q8_0/q8_0` KV cache improves decoding throughput by **+13.65%** (13.55 -> 15.40 t/s) for a modest +446 MiB VRAM cost (11.34 GB peak), comfortably within the 16 GB hardware budget.
