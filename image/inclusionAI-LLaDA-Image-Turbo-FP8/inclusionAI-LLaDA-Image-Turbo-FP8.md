# inclusionAI / LLaDA-Image-Turbo-FP8 (oficial)

## Identificação técnica
- Repo upstream: `inclusionAI/LLaDA-Image-Turbo-FP8`
- Revisão/commit: `664a975e4b4980fb750fd47b2f87e1874bb14bd7`
- Pasta canônica: `image/inclusionAI-LLaDA-Image-Turbo-FP8/`
- Total: 36 arquivos, 25001206121 bytes (~23.29 GiB)
- Licença: Apache-2.0 (repo upstream)
- Arquitetura: LLaDA-Image Turbo 4-step distilled, transformer FP8 block128 + text encoder LLaDA2-MoE FP8
- Quantização: FP8 E4M3 (transformer 6.71 GB em 4 shards; text encoder 17.3 GB em 9 shards)
- Exclusões locais: `assets/*` e `sigvq/*` (SigVQ não usado em generation_mode="text"; 2.6 GB economizados)
- Manifest completo: `tasks/llada-official-audit/MANIFEST_Turbo-FP8.json` (bytes + SHA256 por arquivo)
- Runtime validado: venv isolado `tasks/llada-official-audit/.venv` — Python 3.11.15, torch 2.8.0+cu128, transformers 4.57.6, diffusers 0.39.0
- Código oficial: `inclusionAI/LLaDA-Image` commit `e7c861b0aaa00d2f7ed49600a3a6f170e02a9d59`, classe `LLaDAImagePipeline`
- Scheduler: `stochastic_sampling=false` forçado (default do repo é true; upstream recomenda false para Turbo)

## MEDIDO LOCALMENTE
- FASE A (encoder oficial FP8, device_map split 10×GPU/10×CPU): embeds pos=(1,290,2560) em 83.5 s; GPU 11685 MiB no pico; após free GPU volta a ~3882 MiB
- Smoke 63001 (4 steps, CFG 1.0, seed 63001): PASS, 1024x1024 RGB, Phase B 14.0 s, peak VRAM 14133 MiB
- T01/seed 51001: PASS, 1024x1024 RGB
- T03/seed 51003: PASS, 1024x1024 RGB
- T06/seed 51006: PASS, 1024x1024 RGB
- Outputs: `tasks/llada-official-audit/outputs/llada-official-turbo-fp8/`
- Runner: `tasks/llada-official-audit/run_staged.py` (staged A/B, sem stack inteira, sem RealRebel/ComfyUI, sem Q4/INT8)

## DECLARADO PELO AUTOR/ORIGEM
- Turbo = 4 steps, guidance_scale 1.0, `stochastic_sampling=false` pode dar detalhes mais nítidos
- Requer Python 3.11, PyTorch 2.8, Transformers 4.57.6, Diffusers 0.39.0

## Limitação documentada
- O transformer FP8 oficial usa `quantization_config` quant_method `fp8` (config salva com diffusers 0.40.0.dev0) que nenhum diffusers público (0.39.0, 0.40.0, 0.41.0.dev0 testados) reconhece; além disso o layout fundido (to_qkv/w13) não casa com o split do código (to_q/to_k/to_v, w1/w3). Carregá-lo sem o fork interno do autor exigiria reimplementação de loader — fora do escopo mínimo. Por isso a Fase B usa o transformer BF16 oficial (`inclusionAI/LLaDA-Image-Turbo` rev `f4afc52d925bbac4e22a1c947111fc1f127e37e5`, 13 GB), mesma arquitetura/treino, precisão maior. Fase A (encoder, o componente suspeito do Q4) é 100% oficial FP8.
