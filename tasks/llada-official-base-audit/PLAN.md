# LLaDA-Image Base oficial — Gate Plan (T01/T03/T06)

Status: PLANEJAMENTO. Nenhum peso baixado, nenhuma inferência executada.
Branch: `review/image-t2i-blind-v1`. Hardware: RTX 5060 Ti 16 GB, ~31 GB RAM, máx 8 CPU threads.

## 1. Motivação (por que o histórico anterior não basta)
- Turbo oficial uniform-v2 (reveal v3 congelado): corrigir `use_uniform_sigmas` melhorou o Turbo (+0.30 média, +0.9 em T01), mas NÃO resolveu a falha grave de composição/contagem em T06 (Turbo correto 1.4 vs community 1.8) e NÃO demonstrou vantagem global sobre o antigo community INT8+Q4.
- Turbo está encerrado; não repetir. O benchmark público alto corresponde ao **Base de 50 steps**, variante materialmente nova (modelo não-destilado, CFG 5.0) — mudança material que justifica o gate (AGENTS.md §4).
- Base community antigo (realrebelai INT8, MODEL_HISTORY) NÃO conta: era stack Q4/RealRebel.

## 2. Repos e revisions exatas
- Base FP8: `inclusionAI/LLaDA-Image-FP8` rev `7678c6071b139e1989565db41122b16d767cc585` (43 arquivos, 27635331569 bytes totais)
- Base BF16: `inclusionAI/LLaDA-Image` rev `e4e2703f410f7ddb6ee8d6b09dac6a8ec5093039` (39 arquivos, 49300950305 bytes totais)
- Código: `inclusionAI/LLaDA-Image` commit `e7c861b0aaa00d2f7ed49600a3a6f170e02a9d59` (já clonado em `tasks/llada-official-audit/LLaDA-Image/`)
- Venv: reutilizar `tasks/llada-official-audit/.venv` (Python 3.11.15, torch 2.8.0+cu128, transformers 4.57.6, diffusers 0.39.0)

## 3. Componentes e tamanhos (via metadata remoto, 2026-09-14)
Base FP8:
- `text_encoder/model-0000X-of-00009.safetensors` (9 shards, DIFERENTES do Turbo): total **17348461904 bytes (~16.16 GiB)**
- `transformer/diffusion_pytorch_model-0000X-of-00004.safetensors` (4 shards, Base não-destilado): total **6777040344 bytes (~6.31 GiB)** — ⚠️ NÃO carregável em diffusers público (mesmo `quant_method: fp8` + layout fundido do Turbo; manifest confirma `to_qkv`/`w13` fundidos)
- `queryformer/diffusion_pytorch_model.safetensors`: 101749704 bytes, sha `35cef6a3…` — DIFERENTE do Turbo (`0702ceeb…`)
- `text_projection/diffusion_pytorch_model.safetensors`: 652457384 bytes, sha `484e8061…` — DIFERENTE do Turbo (`5878406d…`)
- `vae/diffusion_pytorch_model.safetensors`: 168120872 bytes — IDENTICAL ao Turbo
- `tokenizer/tokenizer.json`: 15297062 bytes — IDENTICAL ao Turbo
- `sigvq/`: 2594014384 bytes — NÃO baixar (generation_mode=text não usa)
- `assets/`: ~14 MB — NÃO baixar
Base BF16 (somente transformer será usado):
- `transformer/diffusion_pytorch_model-0000X-of-00004.safetensors` (4 shards): total **13080492240 bytes (~12.18 GiB)**; config sem `quantization_config`, mesma arquitetura (dim 3840, 30 layers, in_channels 128) — carrega em diffusers público como o Turbo BF16

## 4. Carregabilidade com runtime público
- ✅ text_encoder FP8 Base: mesmo formato do Turbo FP8 (validado na Fase A do Turbo) — carregável via `AutoModel` + `device_map=auto`
- ✅ queryformer / text_projection Base: pesos densos BF16 padrão — carregáveis
- ✅ transformer BF16 Base: sem quant config — carregável com split como o Turbo BF16
- ❌ transformer FP8 Base: NÃO carregável (documentado; mesma limitação do Turbo FP8)
- Estratégia: encoder FP8 oficial + transformer BF16 oficial (mesma arquitetura/treino, precisão maior), idêntica à do Turbo staged

## 5. Scheduler config do Base (lida do repo, não assumida do Turbo)
`scheduler/scheduler_config.json` do Base FP8 (487 bytes):
- FlowMatchEulerDiscreteScheduler, `num_train_timesteps` 1000, `shift` **1.0** (Turbo: 3.0)
- **SEM chave `use_uniform_sigmas`** → `config.get("use_uniform_sigmas", False)` = False → rota oficial Kumaraswamy (a mesma que o runner antigo hardcodava; o runner atual já respeita o config, então está correto para o Base sem alteração)
- **`stochastic_sampling: false`** (default do repo; Turbo era true) → NÃO aplicar override de Turbo; usar o default oficial do Base
- demais campos iguais ao Turbo (base_shift 0.5, max_shift 1.15, exponential, resto false)

## 6. Recipe oficial completa (README upstream, exemplo Base)
- `generation_mode="text"`, 1024x1024, `num_inference_steps=50`, `guidance_scale=5.0`
- `negative_prompt=""` (vazio, default oficial), `generator=torch.Generator("cuda").manual_seed(42)` (gate usará seeds 51001/51003/51006)
- `pipe = LLaDAImagePipeline.from_pretrained("inclusionAI/LLaDA-Image", torch_dtype=torch.bfloat16, device="cuda")` — substituído pelo runner staged (gerenciamento de memória; matemática idêntica)

## 7. Estimativas
- Disco livre atual: ~1706905907200 bytes (~1.59 TiB). Novos bytes necessários: **~31183161232 bytes (~29.05 GiB)** = encoder FP8 17.35 GB + queryformer 0.10 GB + text_projection 0.65 GB + transformer BF16 13.08 GB (+ KBs de configs/py). Reutilizáveis byte-identicamente do Turbo: vae, tokenizer.*, model_index.json. Margem: folgada.
- RAM/VRAM (extrapolado do Turbo medido): Fase A ~70–90 s, pico GPU ~11.7 GB; Fase B 50 steps com CFG (batch cond+uncond duplica o forward) ≈ 8–15 min/imagem; timeout proposto 900 s/case. pico VRAM estimado ≤ 14.5 GB (split 22 GPU/8 CPU + VAE CUDA).
- Swap: Turbo variou 8→13 GB durante loads sem thrashing; mesmo perfil esperado.

## 8. Estratégia Phase A / Phase B (mesmo runner, novos paths)
- Reutilizar `tasks/llada-official-audit/run_staged.py` SEM alterar matemática; apenas novos `--model-dir` (Base FP8) e `--transformer-dir` (Base BF16).
- Fase A (guidance 5.0 → calcula pos + neg embeddings; neg = prompt vazio oficial).
- Fase B (50 steps, CFG 5.0, scheduler do Base sem override de stochastic; rota Kumaraswamy via respeito ao config).
- NÃO reutilizar `stochastic_sampling=false` forçado do Turbo como regra — no Base o default já é false; registrar o valor efetivo em log.
- NÃO carregar stack inteira; mesmo watchdog (processo isolado, /interrupt, SIGTERM/SIGKILL, cleanup).
- Gate: somente T01/T03/T06, seeds 51001/51003/51006, prompts canônicos. Outputs em `tasks/llada-official-base-audit/outputs/`.

## 9. Reutilização byte-identical do Turbo (SHA256 confirmados)
- `vae/diffusion_pytorch_model.safetensors` (19874383…) — symlink, NÃO baixar
- `tokenizer/tokenizer.json` (2197aedd…) + `tokenizer_config.json` + `special_tokens_map.json` — symlink/cópia, NÃO baixar
- Todo o resto do Base (encoder, queryformer, projection, transformer) DIFERE do Turbo — download novo obrigatório (lista §3).

## 10. Riscos de OOM
- Text encoder Base FP8 17.35 GB > Turbo 17.3 GB equivalente: mesmo split 8GiB GPU deve servir; se OOM, reduzir para 6GiB antes de qualquer outra mudança.
- Transformer BF16 Base 13.08 GB ≈ Turbo BF16 13.08 GB: mesmo split 10GiB GPU; Fase B com CFG dobra ativações por step — monitorar pico; se OOM no decode, liberar transformer antes do VAE (já implementado).
- 50 steps × ~2 (CFG) ≈ 100 forwards no transformer split CPU/GPU: risco de tempo >900 s, não de OOM adicional.

## 11. Critérios de abandono do gate
- Falha técnica persistente após 1 retry idêntica (OOM não contornável por split, erro de loader).
- Qualquer case >900 s sem conclusão.
- Qualidade visual (julgamento humano posterior) sem melhora material sobre Turbo uniform-v2/community — decide após o gate, não durante.
- Ao abandonar: registrar em MODEL_HISTORY.md, preservar logs, remover SOMENTE pesos exclusivos do Base.

## 12. Após o gate
- Comparação cega contra Turbo uniform-v2 + community + Krea/Z/FLUX somente se ≥1 case PASS.
- NÃO apagar Turbo/community/Krea/Z/FLUX antes da avaliação humana.
