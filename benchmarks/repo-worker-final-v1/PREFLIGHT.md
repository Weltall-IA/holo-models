# Preflight Validation Report: Mini-Me Q3 vs Vireqo Plus Corrected

## 1. Summary Table

| Métrica | Mini-Me Q3 (Original) | Vireqo Plus (Corrected) |
|---|---:|---:|
| **Load Status** | ❌ GGUF Incompatible (`blk.52.attn_norm.weight` missing) | ✅ OK (Ready in 6s) |
| **Integrity Preserved** | ✅ 100% Intact / No manual binary edit | ✅ 100% Intact |
| **Basic Response** | ❌ None (Runtime Abort / Missing Layer) | ✅ PASS ("Paris", "391") |
| **Tool Call Protocol** | ❌ N/A | ✅ PASS (`list`, `read`, `edit`, `done`) |
| **Edit & Test** | ❌ N/A | ✅ PASS (Exact string edit verified) |
| **Error Recovery** | ❌ N/A | ✅ PASS (Immediate fallback on error) |
| **Context Length** | 2048 / 32768 | **2048** (Author reference operating point) |
| **KV Cache Type** | Q8_0 / Q4_0 | **Q8_0 / Q8_0** |
| **GPU Offload** | Full GPU attempted | **Full GPU (100% layers in VRAM)** |
| **Peak VRAM** | N/A | **10.103 MiB** |
| **Decode Throughput** | 16.91 tok/s (raw bench) | **27.02 tok/s** (real server) |
| **Prompt Throughput** | 655.64 tok/s (raw bench) | **150.71 tok/s** (real server) |
| **READY** | **NO** (`MINIME_RUNTIME_INCOMPATIBLE`) | **YES** (`READY`) |

---

## 2. Technical Findings on Mini-Me Original GGUF

- **Repository**: `torchsnow/Qwen3.8-23B-Mini-Me-bf16-Q3_K_M-GGUF`
- **File**: `qwen3.8-23b-mini-me-bf16-q3_k_m.gguf`
- **Size**: `11107125856` bytes (10.34 GiB)
- **SHA256**: `5c284bbc65b662a2d015943262b724fdf7199d80e4b8909a3b37a35136f47f57`
- **Root Cause**:
  - A conversão automática GGUF registrou `qwen35.block_count = 53` e `qwen35.nextn_predict_layers = 1`.
  - No entanto, o pruning de 12 camadas realizado no modelo base eliminou as camadas MTP/nextn do final, gerando tensores apenas até o bloco 51 (`blk.0` até `blk.51`).
  - Todos os runtimes atuais (`deepgrove`, `prism-llama`, `geo-llama`, `lmstudio-2.29.1`) rejeitam o carregamento por falta do tensor `blk.52.attn_norm.weight`.
  - Conforme as regras estritas de integridade estabelecidas, o arquivo GGUF não foi modificado.
  - **Status do Mini-Me**: Marcado como `MINIME_RUNTIME_INCOMPATIBLE`. Não participará do benchmark final de 12 tasks para não fabricar dados.

---

## 3. Findings on Vireqo-27B-Plus (Corrected Reference Profile)

- **Repository**: `Vita0818/Vireqo-27B-Plus-260816`
- **File**: `Vireqo-27B-Plus-260816.gguf`
- **Size**: `7585332288` bytes (7.06 GiB)
- **SHA256**: `a32a8ec286a11c6534bf29d1ee20bd4c02064032b51ae8310bb1216e2de17e03`
- **Configuração Validada**:
  - Context: 2048
  - KV Cache: Q8_0 / Q8_0
  - GPU Offload: Full GPU (`-ngl 999`)
  - Flash Attention: ON
  - Reasoning / Thinking: OFF
  - Sampling: `temp=0.7`, `top_k=20`, `top_p=0.95`, `repeat_penalty=1.08`, `repeat_last_n=64`
- **Status do Vireqo**: **100% READY** para o benchmark final.
