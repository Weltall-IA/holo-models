# inclusionAI / LLaDA-Image-Turbo BF16 transformer (oficial, suporte à auditoria)

## Identificação técnica
- Repo upstream: `inclusionAI/LLaDA-Image-Turbo`
- Revisão/commit: `f4afc52d925bbac4e22a1c947111fc1f127e37e5`
- Pasta canônica: `image/inclusionAI-LLaDA-Image-Turbo/` (somente `transformer/*` + `model_index.json`; scheduler/vae/tokenizer/queryformer/text_projection reutilizados do snapshot Turbo-FP8)
- Transformer: 4 shards, ~13.08 GB
- Licença: Apache-2.0
- Motivo: o transformer FP8 oficial não carrega em diffusers público (quant_method `fp8` desconhecido + layout fundido vs split). Este BF16 é o mesmo treino/arquitetura, precisão maior, e isola a variável suspeita (encoder Q4) mantendo o encoder 100% oficial FP8.

## MEDIDO LOCALMENTE
- Load via `LLaDAImageTransformer2DModel.from_pretrained` com `device_map=auto` (22 camadas GPU + 8 CPU): OK
- Smoke 63001 Phase B: 4 steps em ~10 s de difusão, peak VRAM 14133 MiB
- VAE decode após liberar transformer da GPU: OK

## DECLARADO PELO AUTOR/ORIGEM
- Turbo = 4 steps, guidance_scale 1.0
