# HANDOFF — Estado atual do benchmark de imagem

Atualizado em 2026-09-09.

## Repositório e hardware

- Repositório: `Weltall-IA/holo-models`
- Branch atual de trabalho: `review/image-t2i-blind-v1`
- HEAD anterior a este handoff: `5fa42b500ea8816e579dc0a99a63905e29a66923`
- Raiz local: `/home/alpha/Playstoria/models/`
- SO: Arch Linux
- GPU: RTX 5060 Ti 16 GB
- RAM: ~31 GB
- Limite prático: no máximo 8 CPU threads
- Não usar `/tmp` ou `/dev/shm` para artifacts/pesos grandes: `/tmp` é tmpfs e já causou pressão de RAM/swap severa.

## Regra de trabalho

- O ChatGPT define semântica do benchmark, critérios, comparações e próximos testes.
- A IA local executa, mede, baixa/compila runtime quando explicitamente autorizado e não deve mudar prompts/evaluator/presets para “fazer passar”.
- Preservar sempre logs, manifests, PNGs e resultados históricos antes de remover pesos.
- Não usar `git add .` nem `git add -A`.
- Pesos nunca devem ser staged.

---

# 1. Benchmark T2I principal — finalistas atuais

Campanha final:

`benchmarks/image-t2i-final-v1/`

Prompts canônicos herdados de:

`benchmarks/image-t2i-16gb-v1/PROMPTS.json`

Seeds:

- T01 = 51001
- T02 = 51002
- T03 = 51003
- T04 = 51004
- T05 = 51005
- T06 = 51006
- T07 = 51007
- T08 = 51008

Resolução: 1024x1024.

Sem LoRA/ControlNet/upscale/prompt enhancement no benchmark base, exceto a variante Ideogram especializada explicitamente documentada abaixo.

## Finalistas testados

### FLUX.2 Klein 9B stock KV-INT8 ConvRot

Checkpoint local usado:

`wraps/FLUX.2-klein-9B-KV-INT8-ConvRot-ComfyUI`

- rev: `686016cf4a324e5c5a1a8855b11446533f0eef5f`
- peso: `flux-2-klein-9b-kv-int8-convrot.safetensors`
- bytes: 9,439,891,920
- SHA256: `b446f68e990a43f78887a6d15fc52ba84ea6cf1d2d9ca89d7f5e6d113240c886`
- encoder: `qwen_3_8b_fp8mixed.safetensors`
- VAE: `flux2-vae.safetensors`
- preset consolidado: 20 steps, Euler + Flux2Scheduler, CFG 5
- warm median histórico: 42.822 s/img

### Krea 2 Turbo INT8 ConvRot

IMPORTANTE: foi Krea **2**, não Krea 1. Qualquer menção antiga a “Krea 1” é erro de rótulo, não de checkpoint.

- repo: `Comfy-Org/Krea-2`
- rev: `e5ea8b4dd7f38f348b138eb0fe29f92c0e367e96`
- peso: `krea2_turbo_int8_convrot.safetensors`
- bytes: 13,492,686,496
- SHA256: `8e4eeda70dd5037ab1ba2bef6b417f9f901e26093117cf397f741fc1fdaaf3f1`
- encoder: `qwen3vl_4b_fp8_scaled.safetensors`
- VAE: `qwen_image_vae.safetensors`
- preset: 8 steps, Euler/simple, CFG 1
- warm median histórico: 17.880 s/img

### Z-Image Turbo NVFP4

- repo: `Comfy-Org/z_image_turbo`
- rev: `08d04455279082882deaabc8d0d09fc914c071e1`
- peso: `z_image_turbo_nvfp4.safetensors`
- bytes: 4,509,509,600
- SHA256: `a553c889dbcb910de4c98293237573219a37007c1074a3f04576646a088bd5c8`
- encoder: `qwen_3_4b_fp4_mixed.safetensors`
- VAE: `ae.safetensors`
- preset: 8 steps, res_multistep/simple, CFG 1, ModelSamplingAuraFlow shift=3.0
- warm median histórico: 6.124 s/img

### Ideogram 4 Realism Fused A2

A variante stock do Ideogram 4 teve falsos positivos graves do safety banner.

Evolução:

- plain-text stock: 1/8 imagens válidas
- JSON oficial validado: 4/8 válidas
- `Winnougan/Ideogram_Instant_NSFW` INT8 ConvRot: 8/8 válidas
- `mrjackspade/Ideogram4-Natural-Language-Text-Encoder` step 5000 + stock Quality: 8/8 válidas
- Realism Engine V5 como LoRA dinâmico: runtime inviável por centenas de patches/offload
- solução final: fundir o Realism Engine V5 offline nos dois diffusion models e usar o NL encoder step 5000

Pesos derivados locais:

- conditional: `ideogram4_realism-v5-s055_fp8.safetensors`
  - SHA256 `914ed111d4baeed487b30619fd5df200262416f214d32b249a710982449f38d9`
  - 9,280,745,925 bytes
- unconditional: `ideogram4_unconditional_realism-v5-s055_nvfp4.safetensors`
  - SHA256 `6ed937cfb3557e60132b66e57348c48eec25eb375e15d9b5b644a8411db34101`
  - 5,490,554,845 bytes
- Realism Engine V5 strength = 0.55
- encoder: `qwen3vl_8b_ideogram4_nl_s020_v1_step_00005000_fp8_scaled.safetensors`
- VAE: `flux2-vae.safetensors`

Merge foi feito out-of-core/streaming em:

`benchmarks/image-t2i-final-v1/fuse_realism_v5.py`

Sem LoRA dinâmico durante inferência (`dynamic_lora_patches = 0`).

Gate de steps:

- A1 12 steps: 4/4 PASS, ~89.9 s/img
- A2 20 steps: 4/4 PASS, ~99.7 s/img
- A3 48 steps: 4/4 PASS, ~163.1 s/img

Blind gate interno congelado antes do reveal:

- T01: A2 > A3 > A1
- T02: A1 > A3 > A2
- T03: A2 > A3 > A1
- T06: A1 > A2 > A3

Pontuação ordinal simples 3/2/1:

- A2 = 9
- A1 = 8
- A3 = 7

A2/20 steps escolhido para a final.

Config A2:

- 20 steps
- Euler
- `Ideogram4Scheduler(mu=0.5, std=1.75)`
- `DualModelGuider(cfg=7.0)`
- `CFGOverride(cfg=3.0, start_percent=0.7)`
- natural language via NL encoder step 5000

---

# 2. Final cega Krea vs Z vs FLUX vs Ideogram

Review:

`benchmarks/image-t2i-final-v1/review-final-ideogram-a2-v1/`

32/32 imagens válidas, 8/8 por modelo, zero placeholders e zero safety banners.

Mapping revelado após congelar ranking visual.

Ranking cego congelado por caso:

- T01: D > B > C > A
- T02: A > D > B > C
- T03: B > C > D > A
- T04: C > B > D > A
- T05: A > C > B > D
- T06: A > B > C > D
- T07: A > D > C > B
- T08: A > B > C > D

Mapping final:

- T01: A=FLUX, B=Krea, C=Z, D=Ideogram
- T02: A=FLUX, B=Krea, C=Z, D=Ideogram
- T03: A=Z, B=FLUX, C=Krea, D=Ideogram
- T04: A=Krea, B=Z, C=FLUX, D=Ideogram
- T05: A=Ideogram, B=FLUX, C=Krea, D=Z
- T06: A=Krea, B=FLUX, C=Z, D=Ideogram
- T07: A=FLUX, B=Ideogram, C=Z, D=Krea
- T08: A=FLUX, B=Krea, C=Z, D=Ideogram

Pontuação ordinal 4/3/2/1:

- FLUX.2 Klein stock: 26
- Krea 2 Turbo: 22
- Ideogram Realism A2: 18
- Z-Image Turbo: 14

Vitórias por caso:

- FLUX: T02, T03, T04, T07, T08 = 5/8
- Ideogram A2: T01, T05 = 2/8
- Krea: T06 = 1/8
- Z: 0/8

Interpretação provisória correta:

- FLUX é o vencedor geral em qualidade visual desta suíte.
- Krea fica forte como renderer rápido de alta qualidade.
- Z continua relevante principalmente pela classe de velocidade (~6.1 s/img warm), não por vencer qualidade nesta final.
- Ideogram só deve ser mantido se sua vantagem em certos tipos de cena justificar o custo/complexidade; não inventar papel apenas para “aproveitar” o modelo.

---

# 3. Variantes derrotadas/removidas

Já foram removidas após pairwise:

- Z-Image Base INT8 ConvRot
- Z-Image Turbo INT8 ConvRot challenger
- Krea Raw INT8 ConvRot
- FLUX True-V3 int8mixedrow

Foram recuperados ~58.75 GiB nessa limpeza.

LLaDA community antigo também foi removido anteriormente, mas os resultados históricos foram preservados.

---

# 4. Reabertura do LLaDA — motivo

O usuário questionou corretamente o resultado ruim porque o benchmark público do `inclusionAI/LLaDA-Image` mostra desempenho muito melhor do que vimos localmente.

O resultado antigo NÃO deve mais ser usado para condenar a família inteira.

Reclassificação do antigo:

`LLADA_COMMUNITY_LOW_MEMORY_STACK`

Stack antiga:

- transformer INT8 comunitário
- text encoder Q4_K_M
- RealRebel ComfyUI/custom node

Essa stack ficou ruim no benchmark visual e lenta/instável no Base, mas não reproduz a stack oficial.

---

# 5. Auditoria oficial LLaDA atual

Diretório:

`tasks/llada-official-audit/`

GitHub oficial:

`inclusionAI/LLaDA-Image`

Commit:

`e7c861b0aaa00d2f7ed49600a3a6f170e02a9d59`

Turbo-FP8:

- repo `inclusionAI/LLaDA-Image-Turbo-FP8`
- rev `664a975e4b4980fb750fd47b2f87e1874bb14bd7`
- 36 arquivos
- 25,001,206,121 bytes
- manifest: `tasks/llada-official-audit/MANIFEST_Turbo-FP8.json`

Base-FP8 ainda NÃO baixado:

- rev `7678c6071b139e1989565db41122b16d767cc585`

Base BF16 rev conhecido:

- `e4e2703f410f7ddb6ee8d6b09dac6a8ec5093039`

Venv isolado:

`tasks/llada-official-audit/.venv`

Versões:

- Python 3.11.15
- torch 2.8.0+cu128
- transformers 4.57.6
- diffusers 0.39.0

## Problema do transformer FP8 oficial

O transformer FP8 oficial não é carregável corretamente pelo Diffusers público atual testado:

- `quant_method=fp8` não é suportado como esperado
- layout publicado usa `to_qkv`/`w13` fundidos, enquanto o código público espera splits `to_q/to_k/to_v`, `w1/w3`
- bypass silencioso foi rejeitado porque poderia randomizar/pular pesos

Portanto o teste oficial staged usou:

- text encoder FP8 oficial (~17.3 GB, 9 shards, split GPU/CPU)
- transformer BF16 oficial (~13.08 GB, split 22 blocos GPU / 8 CPU)
- pipeline oficial `LLaDAImagePipeline`

Isto é MAIS fiel em precisão que o antigo INT8/Q4, embora não seja “full FP8”.

Nome correto da variante atual:

`LLADA_OFFICIAL_STAGED_TURBO`

Não chamá-la de “full FP8”.

## Runner staged

Arquivo:

`tasks/llada-official-audit/run_staged.py`

Estratégia:

1. Fase A: carregar encoder/queryformer/text projection oficiais, calcular embeddings, liberar completamente.
2. Fase B: carregar transformer BF16 + VAE e gerar usando embeddings pré-computados.

Isso evitou OOM sem recorrer ao encoder Q4.

Memória observada:

- Fase A: 64–84 s por caso
- RSS <2.3 GB
- GPU pico ~11.5–11.8 GB
- após free GPU ~3.7–4.0 GB
- Fase B: RSS pico ~10 GB
- GPU pico 14133–14304 MiB
- MemAvailable mínimo ~15.8 GB
- swap ~8→11 GB durante loads, sem thrashing

Config Turbo:

- 1024x1024
- 4 steps
- guidance_scale 1.0
- generation_mode text
- `stochastic_sampling=false`

Resultados:

- smoke 63001: PASS
- T01/51001: PASS — Fase A 68.4 s + Fase B 59.8 s
- T03/51003: PASS — Fase A 74.7 s + Fase B 54.9 s
- T06/51006: PASS — Fase A 64.0 s + Fase B 37.6 s

Outputs:

`tasks/llada-official-audit/outputs/llada-official-turbo-fp8/`

Base oficial ainda NÃO executado. A decisão depende de avaliação visual humana do Turbo oficial staged.

---

# 6. Comparação cega LLaDA atual — PRÓXIMO PASSO IMEDIATO

Já criada e pronta:

`tasks/llada-official-audit/review/`

Casos:

- T01
- T03
- T06

Cinco candidatos por caso:

1. `LLADA_OFFICIAL_STAGED_TURBO`
   - encoder FP8 oficial
   - transformer BF16 oficial
   - pipeline oficial
   - Turbo 4 steps
   - stochastic_sampling=false

2. LLaDA community antigo
   - transformer INT8
   - encoder Q4_K_M
   - RealRebel ComfyUI

3. Krea 2 Turbo INT8 ConvRot

4. Z-Image Turbo NVFP4

5. FLUX.2 Klein 9B stock KV-INT8 ConvRot

Grids:

- `tasks/llada-official-audit/review/grids/T01.png`
- `tasks/llada-official-audit/review/grids/T03.png`
- `tasks/llada-official-audit/review/grids/T06.png`
- contact sheet: `tasks/llada-official-audit/review/grids/ALL.png`

15 PNGs cegos:

`tasks/llada-official-audit/review/blind/T01/A.png ... E.png`
`tasks/llada-official-audit/review/blind/T03/A.png ... E.png`
`tasks/llada-official-audit/review/blind/T06/A.png ... E.png`

Mapping:

`tasks/llada-official-audit/review/BLIND_MAPPING.json`

NÃO foi revelado ainda.

Nenhuma nova inferência foi feita para montar essa review.

## Próxima ação obrigatória

O próximo ChatGPT deve PRIMEIRO avaliar cegamente `ALL.png` ou, preferencialmente, `T01.png`, `T03.png` e `T06.png`, congelar o ranking A–E de cada caso e SÓ ENTÃO pedir/revelar `BLIND_MAPPING.json`.

Objetivo da comparação:

1. medir quanto o LLaDA oficial staged melhorou sobre o LLaDA INT8+Q4 antigo;
2. ver se o oficial staged encosta em Krea/Z/FLUX;
3. decidir se vale gastar tempo/disco com o `LLaDA-Image Base` oficial de 50 steps.

NÃO baixar nem executar Base antes desse julgamento visual.

---

# 7. Incidentes e proteções importantes

## tmpfs / RAM

Um merge anterior de Ideogram congelou o desktop porque:

- tempfile foi para `/tmp` (tmpfs/RAM)
- o código reteve `orig_tensors` integralmente
- RAM acabou e ~15 GB foram empurrados para swap

Correção consolidada:

- nunca usar `/tmp`, `/dev/shm` ou filesystem RAM-backed para artifacts grandes
- merges out-of-core/streaming tensor a tensor
- guardas de MemAvailable/swap/disco/processos
- `.partial` + rename atômico

## Watchdog final

Runner final foi corrigido para:

- máximo 8 CPUs via `sched_setaffinity`
- `OMP/MKL/OPENBLAS/NUMEXPR/VECLIB/BLIS = 8`
- `torch.set_num_threads(8)`
- `torch.set_num_interop_threads(1)`
- RLIMIT_NPROC herdado do sistema, sem limite artificial de 512
- ComfyUI isolado por caso
- `/interrupt`
- SIGTERM/SIGKILL + wait
- cleanup em finally

RLIMIT_NPROC efetivo observado:

`(127567, 127567)`

---

# 8. Instrução explícita para o próximo ChatGPT

LEIA ESTE ARQUIVO INTEIRO ANTES DE RESPONDER OU DAR NOVA ORDEM PARA A IA LOCAL.

Depois:

1. Leia `AGENTS.md`.
2. NÃO recomece o benchmark.
3. NÃO remova mais pesos antes de verificar o estado atual.
4. NÃO conclua que LLaDA é ruim com base apenas no antigo INT8+Q4.
5. NÃO diga que Krea usado era Krea 1; foi Krea 2 Turbo INT8 ConvRot.
6. Avalie cegamente agora as grids LLaDA em `tasks/llada-official-audit/review/grids/`.
7. Congele rankings A–E de T01/T03/T06 antes de revelar mapping.
8. Só depois decida se o Base LLaDA oficial 50-step merece teste.
9. Continue separando qualidade visual de performance.
10. Não invente papel para todo modelo apenas para justificá-lo; só manter modelos que tenham vantagem prática real.

Estado esperado imediatamente após ler este handoff: **avaliar a comparação cega LLaDA oficial staged vs community antigo vs Krea vs Z vs FLUX**.
