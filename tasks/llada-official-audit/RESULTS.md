# Auditoria oficial LLaDA-Image — resultados (2026-09-09)

## Configuração executada
- Pipeline oficial `LLaDAImagePipeline`, semântica preservada (scheduler, template, QueryFormer, projection, transformer math, VAE, sampling)
- Runner staged `tasks/llada-official-audit/run_staged.py` (Fase A encode → free → Fase B diffuse)
- stochastic_sampling=false forçado para Turbo (default do repo é true)
- 1024x1024, 4 steps, guidance 1.0, seeds oficiais
- Mistura documentada: encoder = oficial FP8 (`...Turbo-FP8` rev 664a975e), transformer = oficial BF16 (`...Turbo` rev f4afc52d, mesma arquitetura/treino), pois o transformer FP8 não carrega em nenhum diffusers público (quant_method `fp8` desconhecido + layout fundido vs split)

## Fase A (encoder oficial FP8, split ~9 camadas GPU / resto CPU)
- Smoke: embeds (1,290,2560) em 83.5 s; pico GPU total (nvidia-smi) ~11.7 GB na config final (split 8GiB), liberado p/ ~3882 MiB. Nota: 15742 MiB registrado em tentativa descartada com split 12GiB (encoder lotou a VRAM e o run falhou no queryformer por OOM); não é métrica da config final. Todos os valores GPU aqui são totais nvidia-smi incluindo ~3.7 GB de baseline do desktop, salvo indicação contrária.
- T01: embeds (1,351,2560) em 68.4 s
- T03: embeds (1,352,2560) em 74.7 s
- T06: embeds (1,368,2560) em 64.0 s
- Após cada Fase A: encoder removido, GPU volta a ~3.7–4.0 GB, RSS < 2 GB

## Fase B (transformer BF16 split 22 GPU / 8 CPU + VAE CUDA, transformer liberado antes do decode)
- Smoke 63001: PASS 1024x1024 RGB, 14.0 s, peak VRAM 14133 MiB
- T01/51001: PASS 1024x1024 RGB, 59.8 s, peak VRAM 14237 MiB
- T03/51003: PASS 1024x1024 RGB, 54.9 s, peak VRAM 14297 MiB
- T06/51006: PASS 1024x1024 RGB, 37.6 s, peak VRAM 14304 MiB
- Outputs: `tasks/llada-official-audit/outputs/llada-official-turbo-fp8/`

## Memória/swap
- RSS Fase B pico: ~10 GB (transformer load); após free < 2 GB
- MemAvailable mínimo observado: ~15.8 GB; swap cresceu de ~8 para ~11 GB durante loads (offload CPU do accelerate), sem thrashing; zero OOM após o split
- Warnings preservados: `transformer.to("cpu")` recusa em modelo com hooks (del + empty_cache libera mesmo assim); `use_uniform_sigmas` ignorado pelo diffusers 0.39 (runner usa grid explícita como o código oficial prevê)

## CPU offload genérico
- Declarado no código: `model_cpu_offload_seq = "text_encoder->queryformer->text_projection->sigvq->transformer->vae"`
- Teste de smoke com `enable_model_cpu_offload()` na stack inteira NÃO executado (carregaria ~25 GB de uma vez = OOM por construção, foi exatamente a falha anterior)
- Risco de device mismatch: `__call__` usa `self.transformer.device` / `self.vae.device` diretamente; com hooks do accelerate esses atributos não refletem o streaming — o runner staged evita o problema por construção (cada fase com devices explícitos)
- Nenhum patch local na matemática foi necessário; apenas gerenciamento de memória + bypass do loader FP8 (documentado acima)

## Base FP8
- NÃO executado. O gate Turbo passou tecnicamente (4/4 PNGs válidos), mas qualidade visual promissora vs fraca é decisão humana — sem julgamento visual local, conforme instrução.

## Rodada uniform-v2 (schedule oficial correta)
- Status da rodada original (Kumaraswamy): INVALID_FOR_OFFICIAL_QUALITY_COMPARISON por schedule mismatch; preservada apenas como evidência histórica em `outputs/llada-official-turbo-fp8/`.
- Runner corrigido para respeitar `scheduler.config["use_uniform_sigmas"]` (uniforme p/ este snapshot).
- Smoke 63001: PASS, 1024x1024 RGB, Fase A 83.1 s, Fase B 37.3 s, peak VRAM 12239 MiB, sigmas `[1000.0, 900.0, 750.0, 500.0]`, stochastic_sampling=false.
- T01/51001: PASS, Fase A 82.6 s, Fase B 31.4 s, peak VRAM 12181 MiB.
- T03/51003: PASS, Fase A 86.9 s, Fase B 32.0 s, peak VRAM 12349 MiB.
- T06/51006: PASS, Fase A 83.4 s, Fase B 30.9 s, peak VRAM 12694 MiB.
- Outputs: `tasks/llada-official-audit/outputs/llada-official-turbo-uniform-v2/` (SHA256 distintos dos antigos).
- Review cega v2 (6 candidatos, labels A–F, shuffle independente): `tasks/llada-official-audit/review-uniform-v2/`.
- Nenhum vencedor declarado; somente julgamento visual cego poderá decidir qualidade.
