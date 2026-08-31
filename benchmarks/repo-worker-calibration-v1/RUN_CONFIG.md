# Run Configuration & Runtime Metadata

## Runtimes & Git SHAs
- **PrismML (Bonsai B1-B4)**:
  - Binary: `engines/prism-llama/llama-prism-b9599-9ca265a/llama-server`
  - Real Git SHA: `9ca265a57f85f2117942490f421f64a226dd9847`
  - Build: `b9599-9ca265a57`
  - CUDA Backend: CUDA 12 Vendor libs

- **Deepgrove (Ornith O1-O2, Qwen22B Q1, Vireqo Plus Q2)**:
  - Binary: `engines/deepgrove-llama.cpp/build/bin/llama-server`
  - Real Git SHA: `8ce8ca6c6d370b6235dfa8e2a0611a9adb6d77d1`
  - Build: `b1-8ce8ca6`
  - CUDA Backend: CUDA 12.0

## Model Hashes & Files
- **Bonsai Base**: `text/Ternary-Bonsai-27B-Abliterated-LowDeg/Ternary-Bonsai-27B-Abliterated-LowDeg-Q2_0.gguf`
  - SHA256: `527f276ddf047b3494de964985b5529b9fc3ecf739ea64d8fab3a6ef8403e81d` (7,165,121,600 bytes)
- **Bonsai DSpark Draft**: `text/Ternary-Bonsai-27B-Abliterated-LowDeg/Ternary-Bonsai-27B-dspark-Q4_1.gguf`
  - SHA256: `c4810091d244eddc61a0cc4966e584b0959f141e3c66c0d371a6652d9f647da9` (1,946,393,568 bytes)
- **Ornith**: `text/bartowski-Ornith-1.5-9B-Q5_K_M/Ornith-1.5-9B-Q5_K_M.gguf`
  - SHA256: `b50e44fd4e4dc2a14e5b864cbc296885d111e772c07286efbac9a20c1f1c63ab` (6,852,928,384 bytes)
- **Q1 (Qwen3.8-22.62b-v3)**: `text/Qwen3.8-22.62b-v3-Q4_K_M/qwen3.8-22.62b-v3-Q4_K_M.gguf`
  - SHA256: `66cd29c7d7f98b566f6098cbab580cae381809b2c10a31587577d6dc82baa84e` (13,957,089,952 bytes)
- **Q2 (Vireqo-27B-Plus)**: `text/Vireqo-27B-Plus-260816/Vireqo-27B-Plus-260816.gguf`
  - SHA256: `a32a8ec286a11c6534bf29d1ee20bd4c02064032b51ae8310bb1216e2de17e03` (7,585,332,288 bytes)

## Llama-Bench Sanity (Bonsai Baseline vs DSpark)
- **Bonsai Baseline (No DSpark)**:
  - TG128: 44.31 ± 0.32 t/s
  - PP512: 1026.60 ± 11.71 t/s
- **Bonsai DSpark (Draft Q4_1, block_size 4)**:
  - TG128: 46.0 t/s
  - PP512: 1026.60 t/s
