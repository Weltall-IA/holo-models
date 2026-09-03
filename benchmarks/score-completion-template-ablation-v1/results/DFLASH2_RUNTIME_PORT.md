# DFlash2 Runtime Port Documentation — `engines/escha-llama`

## Metadata
- **Base Fork Remote**: `https://github.com/Ajay9o9/llama.cpp-escha.git`
- **Base Fork Branch**: `escha-w2-dense`
- **Base Commit**: `2940b807c1562552ae3e152d73f6105f0ac0c98a`
- **Upstream DFlash2 Reference**: Upstream `llama.cpp` PR `#27342` (`spec: add DFlash2 support (local convolution + candidate selector)`, commit `4a6ad487a6f7c615a5d5662be9248694a9ac1254`)
- **Server Version**: `version: 1 (2940b80)` built with GNU 16.2.1 for Linux x86_64
- **Target Hardware**: NVIDIA GeForce RTX 5060 Ti (16 GB VRAM), CUDA 13.3

## Changes Applied
1. **Architecture & KV Registration (`src/llama-arch.cpp`, `src/llama-arch.h`, `src/llama-hparams.h`)**:
   - Added `LLM_KV_DFLASH_BLOCK_SIZE`, `LLM_KV_DFLASH_CONV_KERNEL_SIZE`, `LLM_KV_DFLASH_CONV_GROUP_SIZE`, `LLM_KV_DFLASH_SELECTOR_RANK`, `LLM_KV_DFLASH_SELECTOR_TOP_K`.
   - Registered DFlash2 tensor names: `blk.%d.attn_conv_base`, `blk.%d.attn_conv_proj`, `blk.%d.ffn_conv_base`, `blk.%d.ffn_conv_proj`, `selector_predecessor`, `selector_successor`, `selector_hidden`.
2. **DFlash Model Architecture (`src/models/dflash.cpp`)**:
   - Implemented full DFlash2 forward computation graph supporting local 1D depthwise convolutions on attention and FFN inputs, plus predecessor/successor candidate selector projection.
3. **Speculative Decoding Engine (`common/speculative.cpp`, `common/speculative.h`)**:
   - Wired draft verification and multi-token candidate acceptance loop for DFlash2 tree/block speculative verification.
4. **Server CLI Integration (`tools/server/server-context.cpp`, `common/common.h`)**:
   - Integrated `--spec-type draft-dflash` and `--spec-draft-n-max` options to configure server-side speculative drafting.

## Build Command
```bash
cmake -S . -B build -DGGML_CUDA=ON
cmake --build build --target llama-server -j8
```

## Verification
- Loaded `Escha-Qwen3.8-27B-W2-Q8E.gguf` + `Qwen3.8-27B-DFlash2-Q4_K_M.gguf` simultaneously with full GPU offload (`-ngl 99 -ngld 99 -fa on`).
- Successfully executed 12 benchmark generations across native and Froggeric chat templates without tensor dimension errors, NaN outputs, or runtime panics.
