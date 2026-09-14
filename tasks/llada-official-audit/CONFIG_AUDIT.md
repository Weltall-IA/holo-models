# LLaDA Official Staged Turbo — Configuration Audit

Data: 2026-09-11. Sem nova inferência, sem download de pesos grandes, sem remoção de pesos.

## Identity
- branch: `review/image-t2i-blind-v1`
- HEAD auditado: `8a81390a6e7d8f25612fd5d9dd4317c344bbc4b8`
- upstream code: `inclusionAI/LLaDA-Image` commit `e7c861b0aaa00d2f7ed49600a3a6f170e02a9d59`
- FP8 repo/rev: `inclusionAI/LLaDA-Image-Turbo-FP8` / `664a975e4b4980fb750fd47b2f87e1874bb14bd7` (36 arquivos, 25001206121 bytes)
- BF16 repo/rev: `inclusionAI/LLaDA-Image-Turbo` / `f4afc52d925bbac4e22a1c947111fc1f127e37e5` (somente `transformer/*` baixado, ~13.08 GB)
- venv isolado: Python 3.11.15, torch 2.8.0+cu128, transformers 4.57.6, diffusers 0.39.0

## Scheduler audit
Config efetiva do snapshot (`scheduler/scheduler_config.json`):
- `_class_name`: FlowMatchEulerDiscreteScheduler, `_diffusers_version`: 0.40.0.dev0
- `num_train_timesteps`: 1000, `shift`: 3.0, `base_shift`: 0.5, `max_shift`: 1.15
- `use_uniform_sigmas`: **true**
- `stochastic_sampling`: **true** (default do repo)
- `time_shift_type`: exponential; beta/dynamic/exponential/karras sigmas: false (só uniform true)

Código oficial (`pipeline_llada_image.py:552-562`): se `use_uniform_sigmas` true → rota A
(`linspace(1.0, 0.0, steps+1)[:-1]`, p.ex. 4 steps = `[1.0, 0.75, 0.5, 0.25]`);
senão rota B (Kumaraswamy `(1-(1-s)**1.17)**0.8)**1.1`, sigmas = `1-schedule`).

Rota executada pelo `run_staged.py` (linhas 199-203): sempre rota B (Kumaraswamy),
ignorando o config.

- `use_uniform_sigmas` real: **true**
- `stochastic_sampling` real em runtime: **false** (override via `register_to_config`
  aplicado antes de qualquer `step()`; diffusers 0.39 `step()` lê
  `self.config.stochastic_sampling` em runtime — efeito real, não só documentado;
  logs registram `stochastic_sampling=False`)
- Schedule executada == correta? **Não.** Verdict: **MATERIAL_MISMATCH**
  (sigmas uniformes vs Kumaraswamy produzem timesteps materialmente diferentes).

## FP8 vs BF16 component equivalence
Comparação SHA256 local (MANIFEST_Turbo-FP8.json) vs LFS oid remoto (BF16 rev f4afc52d):

| component | FP8 hash (local) | BF16 remote hash | verdict |
|---|---|---|---|
| queryformer/diffusion_pytorch_model.safetensors | 0702ceeb… | 0702ceeb… | IDENTICAL |
| text_projection/diffusion_pytorch_model.safetensors | 5878406d… | 5878406d… | IDENTICAL |
| vae/diffusion_pytorch_model.safetensors | 19874383… | 19874383… | IDENTICAL |
| tokenizer/tokenizer.json | 2197aedd… | 2197aedd… | IDENTICAL |
| queryformer/config.json | b16e24de… | b16e24de… | IDENTICAL |
| text_projection/config.json | 4e4b2955… | 4e4b2955… | IDENTICAL |
| scheduler/scheduler_config.json | 45282ce7… | 45282ce7… | IDENTICAL |
| vae/config.json | 7948580b… | 7948580b… | IDENTICAL |
| tokenizer/tokenizer_config.json | 501830d0… | 501830d0… | IDENTICAL |
| tokenizer/special_tokens_map.json | 15064b08… | 15064b08… | IDENTICAL |

(JSONs comparados byte-a-byte e semanticamente — iguais nos dois critérios.)
Somente `transformer/` e `text_encoder/` diferem (variantes quantizadas, esperado).
Nenhum POSSIBLE_MATERIAL_MISMATCH: hipótese de componentes divergentes **fechada sem download adicional**.

## Pipeline equivalence (generation_mode="text")
| # | etapa | verdict | nota |
|---|---|---|---|
| 1 | formatação do prompt | EXACT | mesmo template + `.strip()` |
| 2 | tokenizer (special/pad/trunc/2048) | EXACT | mesmos args |
| 3 | text encoder embeddings | EXACT | |
| 4 | QueryFormer | EXACT | |
| 5 | concat query embeddings | EXACT | |
| 6 | attention mask | EXACT | |
| 7 | position_ids | EXACT | |
| 8 | backbone attention mask | EXACT | |
| 9 | text_encoder.model | EXACT | |
| 10 | text_projection | SEMANTICALLY_EQUIVALENT | mask retornada em CPU vs device dos embeds; valores idênticos, transferida p/ device na Fase B |
| 11 | initial latent shape | EXACT | lsf=16 confirmado via `vae.config.block_out_channels` (4 blocos → 2³=8, ×2=16) |
| 12 | dtype dos latents | EXACT | randn float32 → `.to(transformer.dtype).float()` |
| 13 | RNG/device/seed | SEMANTICALLY_EQUIVALENT | `torch.Generator("cuda").manual_seed(seed)` |
| 14 | schedule/sigmas | MATERIAL_MISMATCH | executado Kumaraswamy; oficial com este checkpoint usa grid uniforme |
| 15 | timestep normalization | EXACT | `ts/num_train_timesteps` expand |
| 16 | chamada transformer (x/t/cap_feats/glm None/source None) | EXACT | |
| 17 | sinal negativo no output | EXACT | |
| 18 | CFG desativado (guidance 1.0) | EXACT | `guidance > 1.0` nos dois |
| 19 | scheduler.step | EXACT | mesmos args |
| 20 | denormalização | EXACT | mesma ordem (denorm → unpatchify) após correção |
| 21 | unpatchify | EXACT | reshape/permute idênticos ao `_unpatchify_latents` |
| 22 | VAE decode | EXACT | |
| 23 | postprocess | EXACT | `VaeImageProcessor(vae_scale_factor=16)` = `latent_scale_factor` oficial |

Gerenciamento de memória/staging (split device_map, transformer liberado antes do
decode, `@torch.no_grad`) não conta como divergência: matemática efetiva idêntica.

## Documentation corrections
1. `run_staged.py` docstring: dizia "transformer FP8" na Fase B — corrigido para
   BF16 oficial com motivo documentado.
2. `run_staged.py` print: dizia "max_memory cuda 12GiB" — corrigido para 8GiB
   (valor efetivo do dict; 12GiB foi só a tentativa descartada que OOMou).
3. VRAM Fase A (15742 vs ~11685 MiB): 15742 = total nvidia-smi (inclui ~3.7 GB
   baseline desktop) da tentativa descartada com split 12GiB; ~11.5–11.8 GB =
   total nvidia-smi das runs finais com split 8GiB. Métricas distintas, ambas
   preservadas com explicação em RESULTS.md e no perfil.
4. Blind mapping: `tasks/llada-official-audit/review/BLIND_MAPPING.json` está
   versionado no commit 8a81390 — portanto NÃO é "local-only". A validade cega
   veio do julgamento A–E congelado antes de qualquer revelação; avaliadores
   futuros com acesso ao branch podem ler o mapping (documentado aqui, sem
   revelar conteúdo).

## Remaining uncertainties
- Nenhuma variável crítica pendente de verificação. O transformer FP8 oficial
  permanece descarregável-mas-não-carregável em diffusers público (limitação de
  loader, não de auditoria).

## Final technical verdict
**C) OFFICIAL_TURBO_RETEST_JUSTIFIED** — existe exatamente uma divergência
material (schedule Kumaraswamy executada vs grid uniforme oficial). Para um
reteste fiel: ler `scheduler.config["use_uniform_sigmas"]` em runtime e
selecionar a rota A/B como o código oficial, mantendo todo o resto idêntico.
Reexecutar somente T01/T03/T06 após a correção. Nenhuma inferência foi
executada nesta auditoria.

## Retest uniform-v2 (executado após esta auditoria)
- Runner corrigido (respeita `use_uniform_sigmas`; log confirma
  `use_uniform_sigmas=True sigmas=[1000.0, 900.0, 750.0, 500.0]`).
- Smoke + T01/T03/T06: 4/4 PASS, 1024x1024 RGB, stochastic_sampling=false,
  mesmos prompts/seeds/encoder/transformer/VAE.
- Rodada original reclassificada: INVALID_FOR_OFFICIAL_QUALITY_COMPARISON
  (evidência histórica preservada).
- Review cega v2 com 6 candidatos em `review-uniform-v2/` (mapping novo,
  independente, não revelado).

## Reveal v3 e encerramento do Turbo (2026-09-14)
- Médias congeladas: FLUX 4.53 > Krea 4.30 > Z 4.00 > community 3.57 > Turbo uniform correto 3.43 > Turbo wrong-schedule 3.13.
- Correção da schedule: +0.30 média, +0.9 em T01; T06 segue grave (1.4). Turbo encerrado sem vantagem global sobre o community.
- Gate do Base planejado em `tasks/llada-official-base-audit/PLAN.md` (nenhum peso baixado, nenhuma inferência executada).

## Decisão sobre o próximo teste (Fase 6)
- NÃO repetir o Turbo em nenhuma configuração (nem correta nem incorreta).
- O próximo candidato LLaDA materialmente novo continua sendo o Base oficial
  de 50 steps (FP8 rev `7678c6071b139e1989565db41122b16d767cc585` / BF16 rev
  `e4e2703f410f7ddb6ee8d6b09dac6a8ec5093039`), mas download SOMENTE após
  decisão explícita — nenhum download foi feito nesta fase.
