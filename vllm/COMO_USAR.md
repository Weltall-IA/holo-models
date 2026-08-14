# vLLM — Guia de execução nesta máquina (NÃO ESQUECER)

Data: 2026-08-11. Máquina: 31 GB RAM, RTX 5060 Ti 16 GB (sm_120/Blackwell),
kernel 7.1.6-cachyos. vLLM **0.26.0** instalado no venv
`/home/alpha/Playstoria/models/.venv` (permanente — não usar /tmp).

---

## ⚠️ PROBLEMA RESOLVIDO: OOM de RAM no startup

**Sintoma:** RAM sobe de ~8 GB para 29-31 GB em 60-120s e o processo morre.
Log mostra `flashinfer.jit: [Autotuner]: Autotuning process starts` antes do crash.

**Causa raiz (diagnóstico K3 + arbitragem Sol, 2026-08-11):**
- O vLLM 0.26 liga `enable_flashinfer_autotune` por padrão (nível -O3).
- No sm_120 (RTX 5060 Ti), o kernel NVFP4 selecionado é
  `FlashInferCutlassNvFp4LinearKernel`, cujo GEMM b12x é CuTe-DSL `@cute.jit`
  (compilação MLIR→PTX in-process via nvidia-cutlass-dsl).
- O autotuner perfila **TODAS as táticas válidas** num dummy run cobrindo
  todos os batch sizes → tempestade de compilações, cada uma com pico de
  centenas MB a >1 GB de RAM no engine-core → OOM.
- O auto-skip de fp4_gemm só vale para kernel CuteDSL (família 10.x), não
  para o sm_120 (120//10=12 → não dispara).
- vLLM 0.6.x NÃO suporta sm_120 (CUDA_SUPPORTED_ARCHS até 9.0) — downgrade
  inviável. Suporte Blackwell entra na 0.8.0.

## ✅ SOLUÇÃO (config que funciona)

```bash
export LD_LIBRARY_PATH=/usr/lib/ollama/cuda_v13:$LD_LIBRARY_PATH
export MALLOC_ARENA_MAX=2
export TORCHINDUCTOR_COMPILE_THREADS=1
export MAX_JOBS=2
export NVCC_THREADS=1

vllm serve /home/alpha/Playstoria/models/embed/texto/Nemotron-3-Embed-1B-NVFP4 \
  --trust-remote-code \
  --max-model-len 2048 \
  --max-num-seqs 2 \
  --gpu-memory-utilization 0.5 \
  -O1 \
  --kernel-config '{"enable_flashinfer_autotune":false}' \
  --compilation-config '{"cudagraph_capture_sizes":[1,2,4,8]}' \
  --port 8001
```

**Por que funciona:**
- `--kernel-config '{"enable_flashinfer_autotune":false}'` — desliga o
  autotuner (causa raiz) SEM desligar CUDA graphs (PIECEWISE ativos, log:
  `Capturing CUDA graphs (mixed prefill-decode, PIECEWISE)`).
- `-O1` — mantém torch.compile JIT + CUDA graphs (piecewise).
- `MALLOC_ARENA_MAX=2 TORCHINDUCTOR_COMPILE_THREADS=1 MAX_JOBS=2
  NVCC_THREADS=1` — limita concorrência/pico do heap e do nvcc.
- Tempo de boot: ~3-5 min (torch.compile ~18s + captura CUDA graphs).

**Logs de confirmação (procurar no output):**
- `Skipping FlashInfer autotune because it is disabled.` ✅
- `Using FlashInferCutlassNvFp4LinearKernel for NVFP4 GEMM` ✅
- `Capturing CUDA graphs (mixed prefill-decode, PIECEWISE)` ✅

## ⚠️ Variáveis que NÃO funcionam (não repetir)

| Tentativa | Resultado |
|---|---|
| `--enforce-eager` | Evita OOM mas DESLIGA CUDA graphs (não queremos) |
| `-O0` | Desliga tudo (autotune + compile + cudagraphs) |
| `--attention-backend FLASH_ATTN` sozinho | Não resolve (autotuner roda para outros kernels) |
| `VLLM_USE_FLASHINFER_SAMPLER=False` (string) | Crash: espera `0`/`1` inteiro |
| `--swap-space 0` | Flag não existe na 0.26 |
| vLLM 0.6.x | Não suporta sm_120/Blackwell |
| swapfile em btrfs | btrfs não suporta swapfile (falha "Invalid argument") |
| swapfile em bcachefs | bcachefs não suporta swapfile (falha "Invalid argument") |
| zram >15.6 GB | `echo 32G > disksize` falha "Device or resource busy" |

## API de embedding (vLLM 0.26 — endpoint mudou!)

O endpoint NÃO é `/v1/embeddings` (404). É **`/v2/embed`** (formato
Cohere-compatível):

```bash
curl -X POST http://localhost:8001/v2/embed \
  -H "Content-Type: application/json" \
  -d '{"model":"/home/alpha/Playstoria/models/embed/texto/Nemotron-3-Embed-1B-NVFP4",
       "texts":["passage: texto aqui"],
       "input_type":"document"}'
```

- `input_type`: `document` ou `query` (NÃO `search_document` — dá 400).
- `model`: caminho completo do diretório do modelo (served_model_name).
- Resposta: `{"embeddings": {"float": [[...]]}}` (dict com tipo, não lista).
- Prefixos: `query: ` para queries, `passage: ` para documentos.

## Consumo medido (2026-08-11, benchmark 240 queries)

| Métrica | NVFP4 (vLLM) | Q4_K_M (llama.cpp) |
|---|---:|---:|
| VRAM pico (GPU) | 1356 MiB | 1218 MiB |
| RAM do processo | 4.47 GB | 1.11 GB |
| Tempo 2240 requests | 60.2s | 27.0s |
| Throughput | ~37 req/s | ~83 req/s |
| MRR@10 (240q) | 0.7056 | 0.7054 |

**Conclusão:** NVFP4 usa 11% mais VRAM, 4× mais RAM e é ~2.2× mais lento
(overhead HTTP por request) — com qualidade IDÊNTICA ao Q4_K_M (Δ 0.0002).
Q4_K_M (llama.cpp) é a escolha clara; vLLM/NVFP4 só compensa para servido
concorrente de alta throughput em lote.

## Env vars úteis (0.26)

| Var | Valor | Efeito |
|---|---|---|
| `VLLM_FLASHINFER_AUTOTUNE_SKIP_OPS` | `fp4_gemm` | Pula só a tempestade fp4 (mantém resto) |
| `VLLM_FLASHINFER_AUTOTUNE_CACHE_DIR` | `$HOME/.cache/vllm/fi_autotune` | Cache do autotune (inútil com autotune off) |
| `VLLM_USE_FLASHINFER_SAMPLER` | `0` | Desliga sampler flashinfer (irrelevante p/ embedding) |
| `VLLM_DISABLED_KERNELS` | — | Existe mas não ataca o DSL JIT |

## Outras notas

- `LD_LIBRARY_PATH=/usr/lib/ollama/cuda_v13` — necessário pós-restart
  (llama-cpp compilado com CUDA 13; o torch cu128 instala a .12).
- Ollama segura modelos na GPU com keep_alive; descarregar com:
  `curl -X POST http://localhost:11434/api/generate -d '{"model":"<nome>","keep_alive":0}'`
- Cache de kernels: `~/.cache/vllm/` (torch_compile_cache + flashinfer).
  A troca de versão do vLLM invalida (hash inclui versão/config).
