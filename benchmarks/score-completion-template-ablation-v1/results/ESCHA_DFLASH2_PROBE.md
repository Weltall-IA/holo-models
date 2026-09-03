# Probe de Compatibilidade: Escha-W2 + DFlash2

**Data**: 2026-09-03
**Target**: `/home/alpha/Playstoria/models/text/aj9o9-Qwen3.8-27B-Escha-W2-GGUF/Escha-Qwen3.8-27B-W2-Q8E.gguf`
**Draft Model**: `/home/alpha/Playstoria/models/text/z-lab-Qwen3.8-27B-DFlash2-GGUF/Qwen3.8-27B-DFlash2-Q4_K_M.gguf`
**Runtime**: `/home/alpha/Playstoria/models/engines/escha-llama/build/bin/llama-server` (commit `2940b80`)

## 1. Resultado do Probe

```text
ESCHA_DFLASH2_STATUS=BLOCKED_RUNTIME_UNSUPPORTED
ESCHA_DFLASH2_CODE_SCORE=N/A
```

## 2. Diagnóstico Técnico e Log de Erro

Ao inicializar o `llama-server` do fork `escha-w2-dense` com `--spec-type draft-dflash -md .../Qwen3.8-27B-DFlash2-Q4_K_M.gguf`, o servidor abortou imediatamente com o erro:
```text
0.00.845.321 E llama_model_load: error loading model: done_getting_tensors: wrong number of tensors; expected 81, got 58
0.00.845.326 E llama_model_load_from_file_impl: failed to load model
0.23.820.797 E llama_model_load: error loading model: done_getting_tensors: wrong number of tensors; expected 81, got 58
0.23.820.812 E common_speculative_init_result: failed to load draft model
0.23.833.517 E srv  llama_server: exiting due to model loading error
```

## 3. Causa Raiz

- O fork `Ajay9o9/llama.cpp-escha` (branch `escha-w2-dense`) foi baseado em um commit anterior à introdução do suporte ao checkpoint Qwen3.8 DFlash2 oficial (que contém 81 tensores com convoluções e seletores adicionais).
- Conforme estipulado no `PLAN.md`, nenhum tensor foi removido e o benchmark não foi forçado. O preset Escha+DFlash2 permanece catalogado como `BLOCKED_RUNTIME_UNSUPPORTED`.

