# Qwen3.8-27B-DFlash2-Q4_K_M

## Identificação técnica

- Arquivo GGUF: `Qwen3.8-27B-DFlash2-Q4_K_M.gguf`
- Tamanho local registrado: `1,138,229,248` bytes (`1.06 GiB`)
- SHA256: `1a25c56858e1ebe93f2718ac1d49d1151f9323325c1bbfd6209370f4db131ebd`
- Origem: `z-lab/Qwen3.8-27B-DFlash2-GGUF`
- Arquitetura: `dflash` / DFlash2 para targets Qwen3.8-27B
- Quantização: `Q4_K_M`
- Status no workspace: **draft especulativo ativo do GSQ IQ2_S**
- Uso isolado: **não aplicável**; este GGUF é um draft/helper, não um modelo de chat standalone.

## Especialidade, pontos fortes e trade-offs

- Draft de speculative decoding usado para acelerar Qwen3.8-27B compatíveis.
- Com o GSQ IQ2_S preservou 6/6 no benchmark de código e elevou a mediana de 24.70 para 46.00 tok/s.
- O ganho depende fortemente da aceitação do target e do tipo de workload; não deve ser generalizado para qualquer modelo Qwen3.8-27B.
- Em escrita criativa o DFlash2 não é preset recomendado: a aceitação observada foi baixa e o overhead superou o ganho.
- `n_max=7` é o maior valor permitido pelo bloco usado no checkpoint/runtime atual; é também o ponto validado no GSQ, não uma regra universal para outros targets.

## MEDIDO LOCALMENTE

Hardware: NVIDIA GeForce RTX 5060 Ti 16 GB.

Runtime de referência: llama.cpp `0.3.0-dev`, build `10752`, commit `b96806d96061049a5b574269b049bf6241d63d46`; 8 threads; full GPU offload; Flash Attention ON.

Última validação referenciada neste perfil: `2026-09-03`.

### GSQ IQ2_S + DFlash2 — `coding-mini-v1`

Fonte: `benchmarks/coding-mini-v1/results/GSQ_DFLASH2_COMPARISON.md`.

- Target: `Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf`
- Score: **6/6**
- Mediana target base: **24.70 tok/s**
- Mediana com DFlash2: **46.00 tok/s**
- Ganho: **+86.26%**
- Wall time mediano com DFlash2: **13.63 s**
- Pico de VRAM do conjunto target+draft: **14,086 MiB**
- Draft acceptance mediana: **86.9%**
- PY01: **58.44 tok/s**, acceptance **91.5%**, mean accepted length **7.41**
- Integridade de qualidade: **6/6 antes e 6/6 depois**

### Escrita

Fonte: `benchmarks/chat-writing-v1/`.

- Aceitação observada em escrita: aproximadamente **10–12%** nas execuções históricas.
- Resultado prático: overhead maior que o ganho; **não usar como padrão para writing**.

### Outros targets

- Compatibilidade/performance com outro target deve ser medida antes de adoção.
- Resultados históricos do Escha permanecem apenas como histórico; o target/runtime Escha foi removido do armazenamento ativo.

## DECLARADO PELO AUTOR/ORIGEM

A descrição de arquitetura DFlash2/candidate selector é metadado da origem/checkpoint. Os ganhos e taxas de aceitação listados acima são somente os medidos localmente com o GSQ IQ2_S.

## Preset recomendado — com GSQ IQ2_S

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

## Proveniência

- Comparação principal: `benchmarks/coding-mini-v1/results/GSQ_DFLASH2_COMPARISON.md`
- Código consolidado: `benchmarks/score-completion-template-ablation-v1/results/CODING_SUMMARY.md`
- Escrita: `benchmarks/chat-writing-v1/`
- Histórico DFlash2/port: `benchmarks/score-completion-template-ablation-v1/DFLASH2_ADDENDUM.md` e respectivos resultados.
- Campo sem evidência versionada deve ser `N/A / não registrado`, nunca estimado.
