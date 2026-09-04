# Qwen3.8-9B-Distill-uncensored-heretic.i1-Q4_K_M

## Identificação técnica

- Arquivo GGUF: `Qwen3.8-9B-Distill-uncensored-heretic.i1-Q4_K_M.gguf`
- Tamanho local registrado: `5,779,619,840` bytes (`5.38 GiB`)
- SHA256: `3a63c5b5c7c6af57d92437ed2610d524ea96a7ecf873ae7f8e470a024c047fa6`
- Origem: `petruhonk/Qwen3.8-9B-Distill-uncensored-heretic`
- Arquitetura: Qwen3.8 / `qwen35`, dense 9B distill
- Quantização: `i1-Q4_K_M`
- Variante: uncensored/heretic
- Status no workspace: **modelo rápido e leve; não é coder principal**

## Especialidade, pontos fortes e trade-offs

- Throughput alto e baixa latência para chat e tarefas simples.
- Pegada de VRAM pequena o bastante para coexistir melhor com desktop/navegador e outras cargas.
- No benchmark local de código perdeu lógica/robustez em tarefas mais difíceis: 3/6.
- Escrita é rápida, porém menos consistente e menos refinada que os 27B especializados.
- A descrição “uncensored/heretic” vem da variante; o benchmark local não deve ser interpretado como garantia universal de ausência de recusas.

## MEDIDO LOCALMENTE

Hardware: NVIDIA GeForce RTX 5060 Ti 16 GB.

Runtime de referência registrado nos benchmarks: llama.cpp `0.3.0-dev`, build `10752`, commit `b96806d96061049a5b574269b049bf6241d63d46`; 8 threads; full GPU offload; Flash Attention ON.

Última validação referenciada neste perfil: `2026-09-03`.

### Código — `coding-mini-v1`

Fonte: `benchmarks/coding-mini-v1/` e ranking consolidado em `benchmarks/score-completion-template-ablation-v1/results/CODING_SUMMARY.md`.

- Score: **3/6**
- Python: **2/3**
- C++20: **1/3**
- Mediana de decode: **50.66 tok/s**
- Pico de VRAM: **6,911 MiB**
- Falhas históricas: `PY03`, `CPP01` e `CPP03`

### Escrita — `chat-writing-v1`

- Score qualitativo geral: **3.15/5**
- Neutral: **3.25/5**
- Adult: **3.04/5**
- Velocidade de escrita: **~40 tok/s**
- Observação: prosa mais melodramática/explicativa que os melhores 27B da rodada.

### Speculative decoding

- DFlash2: **N/A / não testado como preset deste 9B**
- MTP: **N/A / não testado como preset deste 9B**

## DECLARADO PELO AUTOR/ORIGEM

A identificação distill + uncensored/heretic é proveniente da variante do modelo. Resultados externos não substituem os benchmarks locais deste arquivo.

## Preset recomendado

```bash
/home/alpha/.local/bin/llama serve \
  -m text/petruhonk-Qwen3.8-9B-Distill-uncensored-heretic/Qwen3.8-9B-Distill-uncensored-heretic.i1-Q4_K_M.gguf \
  -ngl 999 -fa on --fit off \
  -ctk q8_0 -ctv q4_0 \
  -c 8192 -np 1 -t 8 \
  --jinja --reasoning off
```

Template recomendado: nativo/embutido até existir evidência específica em contrário.

## Proveniência

- Código: `benchmarks/coding-mini-v1/`
- Escrita: `benchmarks/chat-writing-v1/`
- Ranking consolidado: `benchmarks/score-completion-template-ablation-v1/results/CODING_SUMMARY.md`
- Campo sem evidência versionada deve ser `N/A / não registrado`, nunca estimado.
