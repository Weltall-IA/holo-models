# Pre-flight Validation Report — Repo-Worker Short Final Candidates

## Date: 2026-08-31
## Host & GPU: AMD Ryzen 7 2700X / NVIDIA GeForce RTX 5060 Ti 16GB / CUDA 12.0

---

## 1. Minitron 20B IQ3_M (Substituted for broken 23B)
- **Model Path**: `text/mradermacher-Qwen3.8-20B-Minitron-i1-IQ3_M/Qwen3.8-20B-Minitron.i1-IQ3_M.gguf`
- **Original SHA256**: `253f542604f42433cf9fad806b30c0d1243418c5b543eca56ad62c0761b12bbd`
- **Final SHA256**: `253f542604f42433cf9fad806b30c0d1243418c5b543eca56ad62c0761b12bbd` (Intact, unmodified)
- **File Size**: 9,143,500,032 bytes
- **Runtime Path**: `engines/deepgrove-llama.cpp/build/bin/llama-server`
- **Runtime SHA**: `8ce8ca6c6d370b6235dfa8e2a0611a9adb6d77d1` (v1-8ce8ca6)
- **Context Selected**: 16384 (Full GPU offload, ~10.9 GB VRAM, 5.4 GB headroom)
- **Thinking Mode Selected**: `OFF` (clean direct JSON generation and instant arithmetic)
- **Sanity Results**:
  - `17 * 23` -> `391` (PASS)
  - `Capital of France` -> `Paris` (PASS)
  - Tool Protocol -> `{"action":"list","path":"."}` (PASS)
- **Llama-Bench Performance**:
  - PP512: `307.84 ± 60.98 t/s`
  - TG128: `32.84 ± 0.40 t/s`
- **Status**: `MINIME_READY=YES`

---

## 2. Vireqo-27B-Plus (Corrected Reference)
- **Model Path**: `text/Vireqo-27B-Plus-260816/Vireqo-27B-Plus-260816.gguf`
- **SHA256**: `a32a8ec286a11c6534bf29d1ee20bd4c02064032b51ae8310bb1216e2de17e03`
- **Context Selected**: 2048 (Author target operating point)
- **KV Cache**: `K=Q8_0, V=Q8_0`
- **Sampling**: `temp=0.7, top_k=20, top_p=0.95, min_p=0, repeat_penalty=1.08, repeat_last_n=64`
- **Thinking**: `OFF`
- **Sanity Results**:
  - `17 * 23` -> `391` (PASS)
  - `Capital of France` -> `Paris` (PASS)
- **Decode Speed**: `~27.02 t/s`
- **Status**: `VIREQO_READY=YES`

---

## 3. Ornith 1.5 9B Q5_K_M
- **Model Path**: `text/bartowski-Ornith-1.5-9B-Q5_K_M/Ornith-1.5-9B-Q5_K_M.gguf`
- **SHA256**: `b50e44fd4e4dc2a14e5b864cbc296885d111e772c07286efbac9a20c1f1c63ab`
- **Context Selected**: 32768
- **Thinking**: `OFF`
- **Sanity Results**: PASS (391, Paris, 0 tool errors)
- **Decode Speed**: `~45.5 t/s`
- **Status**: `ORNITH_READY=YES`

---

## 4. Ternary Bonsai 27B
- **Model Path**: `text/Ternary-Bonsai-27B-Abliterated-LowDeg/Ternary-Bonsai-27B-Abliterated-LowDeg-Q2_0.gguf`
- **DSpark Draft**: `text/Ternary-Bonsai-27B-Abliterated-LowDeg/Ternary-Bonsai-27B-dspark-Q4_1.gguf`
- **Context Selected**: 8192
- **DSpark Specs**: `--spec-type draft-dspark --spec-draft-n-max 4`
- **Thinking**: `ON`
- **Sanity Results**: PASS (391, reasoning + tool protocol valid)
- **Llama-Bench Throughput**:
  - Base TG128: `44.31 t/s`
  - DSpark TG128: `46.0 t/s`
- **Status**: `BONSAI_READY=YES`
