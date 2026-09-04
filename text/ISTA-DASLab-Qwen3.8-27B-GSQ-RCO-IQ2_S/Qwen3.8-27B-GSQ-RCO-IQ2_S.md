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

- Melhor resultado local preservado para código: **6/6** no `coding-mini-v1`.
- Relação qualidade/VRAM muito forte para um 27B.
- Compatibilidade validada com DFlash2, que elevou a mediana histórica de 24.70 para 46.00 tok/s sem reduzir o score local de código.
- Em escrita criativa fica abaixo do Fable; não é o modelo principal de narração.
- DFlash2 não é preset padrão para escrita: nos testes históricos de escrita a aceitação foi baixa e o overhead superou o ganho.
- **Template nativo permanece o preset recomendado.** O clean retest v22.5 mostrou paridade funcional total com Froggeric em non-thinking: mesmas saídas em todos os 18 pares testados, 6/6 em código e 3.54/5 em escrita para ambos.
- Os deltas de throughput do clean retest v22.5 são preservados como medições daquela sessão, mas não são tratados como efeito causal do template porque os braços foram executados sequencialmente e o sinal variou por workload.

## MEDIDO LOCALMENTE

Hardware: NVIDIA GeForce RTX 5060 Ti 16 GB.

Runtime de referência registrado nos benchmarks: llama.cpp `0.3.0-dev`, build `10752`, commit `b96806d96061049a5b574269b049bf6241d63d46`; 8 threads; full GPU offload; Flash Attention ON.

Última validação referenciada neste perfil: `2026-09-04`.

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
- Ganho sobre GSQ base nessa rodada histórica: **+86.26%**
- Wall time mediano: **13.63 s**
- Pico de VRAM: **14,086 MiB**
- Draft acceptance mediana: **86.9%**
- PY01: **58.44 tok/s**, acceptance **91.5%**, mean accepted length **7.41**

### Ablação Froggeric v22.5 — Clean Retest (2026-09-04)

Fonte: `benchmarks/gsq-froggeric-v225-clean-retest-v1/results/SUMMARY.md` e `WRITING_CHATGPT_REVIEW.md`.

- Condição de teste: clean-GPU gate validado antes de cada braço; sem processo externo sustentando carga pesada pelo critério do SPEC.
- Froggeric commit: `4ea21db90694e60d002500dae85ebff26e4b23ad`.
- Froggeric SHA256: `e57684bae4156211a55473c5a63be976a405a37ab5be5ae0e5abf1df5349c4b2`.
- Versão interna: `qwen3.8-froggeric-v22.5`.
- Integração usada: `--reasoning-format deepseek` + `--chat-template-kwargs '{"enable_thinking":false,"reasoning_effort":"none"}'`.
- Resultado funcional: **18/18 pares com saída final byte-idêntica** entre Native e Froggeric v22.5:
  - 6 coding sem draft;
  - 6 coding com DFlash2;
  - 6 writing/chat.
- Isso prova igualdade das saídas finais registradas, não igualdade do prefixo/tokenização renderizada, que não foi capturado diretamente.

#### Código sem draft — Arm A vs Arm B

- Native: **6/6**, mediana **21.02 tok/s**, pico **11,613 MiB**.
- Froggeric v22.5: **6/6**, mediana **15.51 tok/s**, pico **11,601 MiB**.
- Delta medido na sessão: **-26.2%**.
- Interpretação: medição preservada, mas **não atribuída causalmente ao template**. O benchmark não isolou custo de Jinja e foi um único passe sequencial por braço.

#### Código com DFlash2 n=7 — Arm C vs Arm D

- Native: **6/6**, mediana **33.63 tok/s**, pico **14,465 MiB**, draft acc **86.9%**.
- Froggeric v22.5: **6/6**, mediana **37.54 tok/s**, pico **14,508 MiB**, draft acc **86.9%**.
- Delta medido na sessão: **+11.6%**.
- Interpretação: mesma correção e mesma aceitação; o delta de velocidade é **observacional**, não prova que Froggeric acelera DFlash2.

#### Escrita/chat — Arm E vs Arm F

- Todas as 6 saídas Native/Froggeric foram byte-idênticas.
- As saídas também correspondem aos textos canônicos `gsq_iq2s_base` já avaliados em `chat-writing-v1`, então os scores históricos da mesma rubrica foram reutilizados, sem inventar nova avaliação.
- Native: **3.54/5** geral; Neutral **3.83/5**; Adult **3.25/5**.
- Froggeric v22.5: **3.54/5** geral; Neutral **3.83/5**; Adult **3.25/5**.
- Mediana medida de throughput na sessão: Native **13.92 tok/s**; Froggeric **17.77 tok/s**.
- O delta de throughput não é usado para afirmar vantagem do template porque o desenho não isolou run-order/clocks/estado térmico e os deltas mudaram de direção entre workloads.

#### Decisão do clean retest

- Correção de código: **PARITY**.
- Qualidade de escrita: **PARITY**.
- DFlash2 acceptance: **PARITY**.
- Efeito de performance do template: **INCONCLUSIVE**.
- Preset padrão: **KEEP_NATIVE**, por simplicidade de deployment e ausência de ganho funcional medido.
- Froggeric v22.5: **compatível e corretamente integrado para o modo non-thinking testado**.
- Tool-calling local: **N/A / não testado** neste benchmark. O upstream anuncia suporte, mas não há validação local deste comportamento nesta rodada.

### Ablação Froggeric v22.4 — código sem DFlash2 (Histórico)

Fonte: `benchmarks/gsq-froggeric-ablation-v1/results/SUMMARY.md`.

- Score: **6/6**
- Mediana de decode: **19.78 tok/s**
- Delta histórico reportado contra o template nativo: **-19.9%**
- Pico de VRAM: **12,213 MiB**
- A rodada tinha carga de GPU não controlada; usar como histórico de compatibilidade/correção, não como A/B limpo de performance.

### Ablação Froggeric v22.4 — código com DFlash2 `n_max=7`

Fonte: `benchmarks/gsq-froggeric-ablation-v1/results/SUMMARY.md`.

- Score: **6/6**
- Mediana de decode: **46.38 tok/s**
- Controle histórico: **46.00 tok/s**
- Delta: **+0.8%**
- Pico de VRAM: **14,374 MiB** versus **14,086 MiB** no controle histórico
- Draft acceptance mediana: **86.9%**
- Mean accepted draft length: **7.08**
- Rodada preservada como histórico; havia carga de GPU não controlada.

### Escrita — template nativo

Fonte: `benchmarks/chat-writing-v1/`.

- Score qualitativo geral: **3.54/5**
- Neutral: **3.83/5**
- Adult: **3.25/5**

### Escrita — Froggeric v22.4

Fonte de geração: `benchmarks/gsq-froggeric-ablation-v1/results/WRITING_FROGGERIC_RESULTS.jsonl`.

- Mediana de throughput registrada: **21.30 tok/s**
- Pico de VRAM: **11,700 MiB**
- 5/6 gerações ficaram fora da faixa de 425–575 palavras.
- O score automático `3.52/5` produzido pelo runner **não é canônico** porque não reproduziu a auditoria qualitativa histórica.
- Não usar esse `3.52` em ranking.

### Compatibilidade especulativa

- DFlash2 Q4_K_M: **VALIDADO**
- `--spec-draft-n-max 7`: **VALIDADO e recomendado para código**
- MTP: há benchmarks históricos separados; não é o preset recomendado atual deste peso.

## DECLARADO PELO AUTOR/ORIGEM

Metadados externos do autor/origem não substituem os resultados locais acima. Scores externos não são usados neste perfil para escolher o preset do workspace.

Froggeric upstream declara suporte a tool-calling, thinking e múltiplos runtimes. Neste workspace, o clean retest v22.5 validou apenas o comportamento non-thinking de chat/writing/coding coberto pelo SPEC; tool-calling permanece não testado localmente.

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

**Não adicionar `--chat-template-file` Froggeric neste preset padrão.** O clean retest mostrou paridade de saída, não superioridade funcional.

Para rodar sem speculative decoding, remover `-md`, `--spec-type`, `--spec-draft-n-max` e `-ngld`.

## Proveniência

- Código corrigido: `benchmarks/coding-mini-v1/`
- GSQ + DFlash2: `benchmarks/coding-mini-v1/results/GSQ_DFLASH2_COMPARISON.md`
- Escrita canônica: `benchmarks/chat-writing-v1/`
- Froggeric v22.4 histórico: `benchmarks/gsq-froggeric-ablation-v1/`
- Froggeric v22.5 clean retest: `benchmarks/gsq-froggeric-v225-clean-retest-v1/`
- Review final de writing v22.5: `benchmarks/gsq-froggeric-v225-clean-retest-v1/results/WRITING_CHATGPT_REVIEW.md`
- Campo sem evidência versionada deve ser `N/A / não registrado`, nunca estimado.
