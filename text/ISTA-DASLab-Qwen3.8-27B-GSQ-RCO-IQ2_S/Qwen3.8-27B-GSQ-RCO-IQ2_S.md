# Qwen3.8-27B-GSQ-RCO-IQ2_S

## Identificação técnica

- Arquivo GGUF: `Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf`
- Tamanho local registrado: `9,255,432,192` bytes (`8.62 GiB`)
- SHA256: `16c9802111aa9ef3acde465188d6d601f8db128ee3d828ad983a5caca4135ecb`
- Origem: `ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-IQ2_S`
- Arquitetura: Qwen3.8 / `qwen35`, dense 27B
- Quantização: GSQ-RCO `IQ2_S` (~2.15 bpw, conforme metadado registrado no workspace)
- Status no workspace: **coder local principal**

## Especialidade, pontos fortes e trade-offs

- Melhor resultado local preservado para código: 6/6 no `coding-mini-v1`.
- Relação qualidade/VRAM muito forte para um 27B.
- Compatibilidade validada com DFlash2, que quase dobra o throughput sem reduzir o score local de código.
- Em escrita criativa fica abaixo do Fable; não é o modelo principal de narração.
- DFlash2 não é preset padrão para escrita: nos testes de escrita a aceitação foi baixa e o overhead superou o ganho.
- Alterações de chat template devem ser tratadas como variável separada. A ablação Froggeric v22.4 está em `benchmarks/gsq-froggeric-ablation-v1/`.

## MEDIDO LOCALMENTE

Hardware: NVIDIA GeForce RTX 5060 Ti 16 GB.

Runtime de referência registrado nos benchmarks: llama.cpp `0.3.0-dev`, build `10752`, commit `b96806d96061049a5b574269b049bf6241d63d46`; 8 threads; full GPU offload; Flash Attention ON.

Última validação referenciada neste perfil: `2026-09-03`.

### Código — GSQ base

Fonte: `benchmarks/coding-mini-v1/results/SUMMARY_CORRECTED.md` e artefatos correlatos.

- Score: **6/6**
- Python: **3/3**
- C++20: **3/3**
- Mediana de decode: **24.70 tok/s**
- Pico de VRAM: **11,216 MiB**
- Commit histórico da reavaliação corrigida: `8293e8b30b5b73e07a81ef7c8607dd132804593e`

### Código — GSQ + DFlash2 Q4_K_M, `n_max=7`

Fonte: `benchmarks/coding-mini-v1/results/GSQ_DFLASH2_COMPARISON.md`.

- Score: **6/6**
- Python: **3/3**
- C++20: **3/3**
- Mediana de decode: **46.00 tok/s**
- Ganho sobre GSQ base: **+86.26%**
- Wall time mediano: **13.63 s**
- Pico de VRAM: **14,086 MiB**
- Draft acceptance mediana: **86.9%**
- PY01: **58.44 tok/s**, acceptance **91.5%**, mean accepted length **7.41**

### Escrita — template nativo

Fonte: `benchmarks/chat-writing-v1/`.

- Score qualitativo geral: **3.54/5**
- Neutral: **3.83/5**
- Adult: **3.25/5**

### Compatibilidade especulativa

- DFlash2 Q4_K_M: **VALIDADO**
- `--spec-draft-n-max 7`: **VALIDADO e recomendado para código**
- MTP: há benchmarks históricos separados; não é o preset recomendado atual deste peso.

## DECLARADO PELO AUTOR/ORIGEM

Metadados externos do autor/origem não substituem os resultados locais acima. Scores externos não são usados neste perfil para escolher o preset do workspace.

## Preset recomendado — código

```bash
/home/alpha/.local/bin/llama serve \
  -m text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-IQ2_S/Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf \
  -md text/z-lab-Qwen3.8-27B-DFlash2-GGUF/Qwen3.8-27B-DFlash2-Q4_K_M.gguf \
  --spec-type draft-dflash \
  --spec-draft-n-max 7 \
  -ngl 999 -ngld 999 \
  -fa on --fit off \
  -ctk q8_0 -ctv q4_0 \
  -c 8192 -np 1 -t 8 -tb 8 \
  --jinja --reasoning off
```

Para rodar sem speculative decoding, remover `-md`, `--spec-type`, `--spec-draft-n-max` e `-ngld`.

## Proveniência

- Código corrigido: `benchmarks/coding-mini-v1/`
- GSQ + DFlash2: `benchmarks/coding-mini-v1/results/GSQ_DFLASH2_COMPARISON.md`
- Escrita: `benchmarks/chat-writing-v1/`
- Ablação de template: `benchmarks/gsq-froggeric-ablation-v1/`
- Campo sem evidência versionada deve ser `N/A / não registrado`, nunca estimado.
