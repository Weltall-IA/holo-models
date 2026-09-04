# Qwen3.8-27B-Fable-Distill-Heretic-ara-Q3_K_M

## Identificação técnica

- Arquivo GGUF: `Qwen3.8-27B-Fable-Distill-Heretic-ara-Q3_K_M.gguf`
- Tamanho local registrado: `14,153,250,816` bytes (`13.18 GiB`)
- SHA256: `44e786a11380bba9cdcd1b40649afee79d6cf78152f9fb014f731209a67044d3`
- Origem: `armand0e/Qwen3.8-27B-Fable-Distill-Heretic-ara-Q3_K_M`
- Arquitetura: Qwen3.8 / `qwen35`, dense 27B
- Quantização: `Q3_K_M`
- Variante: Fable Distill + Heretic/ARA
- Status no workspace: **modelo principal de escrita/narração**

## Especialidade, pontos fortes e trade-offs

- Melhor resultado qualitativo local de escrita entre os modelos preservados.
- Forte em narrativa, diálogos, subtexto, atmosfera e português natural.
- Nos prompts avaliados não apresentou recusas; isso não deve ser generalizado como garantia de “zero recusas” fora do benchmark.
- Código é competente, mas inferior ao GSQ: 5/6 contra 6/6.
- Ocupa muito mais VRAM que GSQ base e opera próximo do limite da RTX 5060 Ti 16 GB em escrita longa.
- Não há speculative decoding recomendado/validado para este preset no workspace.

## MEDIDO LOCALMENTE

Hardware: NVIDIA GeForce RTX 5060 Ti 16 GB.

Runtime de referência registrado nos benchmarks: llama.cpp `0.3.0-dev`, build `10752`, commit `b96806d96061049a5b574269b049bf6241d63d46`; 8 threads; full GPU offload; Flash Attention ON.

Última validação referenciada neste perfil: `2026-09-03`.

### Escrita criativa — `chat-writing-v1`

Fonte: `benchmarks/chat-writing-v1/` e revisão qualitativa versionada.

- Score geral: **4.92/5**
- Neutral: **4.92/5**
- Adult: **4.92/5**
- Throughput de escrita: **~15.8 tok/s**
- Pico de VRAM registrado no benchmark de escrita: **15,696 MiB**
- Commit da análise qualitativa histórica: `53b53e870d7c4f83902db740995ef04634bdb218`

### Código — `coding-mini-v1`

Fonte: `benchmarks/coding-mini-v1/` e ranking consolidado em `benchmarks/score-completion-template-ablation-v1/results/CODING_SUMMARY.md`.

- Score: **5/6**
- Python: **3/3**
- C++20: **2/3**
- Mediana de decode: **17.35 tok/s**
- Pico de VRAM no benchmark de código: **14,561 MiB**

### Speculative decoding

- DFlash2: **N/A / não testado como preset recomendado para Fable**
- MTP: **N/A / não testado como preset recomendado para Fable**

## DECLARADO PELO AUTOR/ORIGEM

A identificação Fable Distill + Heretic/ARA vem da variante/origem do modelo. Qualquer alegação externa de qualidade ou ausência de recusas deve ser tratada separadamente dos resultados medidos localmente acima.

## Preset recomendado

```bash
/home/alpha/.local/bin/llama serve \
  -m text/armand0e-Qwen3.8-27B-Fable-Distill-Heretic-ara-Q3_K_M/Qwen3.8-27B-Fable-Distill-Heretic-ara-Q3_K_M.gguf \
  -ngl 999 -fa on --fit off \
  -ctk q8_0 -ctv q4_0 \
  -c 8192 -np 1 -t 8 \
  --jinja --reasoning off
```

Template recomendado: **nativo/embutido** até que uma ablação específica prove vantagem de outro template.

## Proveniência

- Escrita: `benchmarks/chat-writing-v1/`
- Código: `benchmarks/coding-mini-v1/`
- Ranking consolidado de código: `benchmarks/score-completion-template-ablation-v1/results/CODING_SUMMARY.md`
- Campo sem evidência versionada deve ser `N/A / não registrado`, nunca estimado.
