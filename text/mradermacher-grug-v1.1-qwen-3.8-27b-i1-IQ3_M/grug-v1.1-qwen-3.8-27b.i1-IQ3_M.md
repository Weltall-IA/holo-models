# grug-v1.1-qwen-3.8-27b.i1-IQ3_M

## Identificação técnica

- Arquivo GGUF: `grug-v1.1-qwen-3.8-27b.i1-IQ3_M.gguf`
- Caminho local esperado pelo `Modelfile`: `/home/alpha/Playstoria/models/text/mradermacher-grug-v1.1-qwen-3.8-27b-i1-IQ3_M/grug-v1.1-qwen-3.8-27b.i1-IQ3_M.gguf`
- Tamanho exato local: **N/A / não registrado em artefato versionado**
- SHA256 local registrado: `b345f97dbb26f4c4256df21d0959dec598685ec4f5ae59fc1c9b75a89706618e`
- Origem: `mradermacher/grug-v1.1-qwen-3.8-27b-i1-GGUF`
- Arquitetura: Qwen3.8 / `qwen35`, dense 27B
- Quantização: `i1-IQ3_M`
- Status no workspace: **modelo preservado, mas template-sensitive; não é preset principal atual**

## Especialidade, pontos fortes e trade-offs

- Variante 27B voltada a chat/escrita com comportamento menos restritivo.
- O modelo demonstrou boa capacidade de escrita em algumas gerações, porém a avaliação inicial foi contaminada por reasoning não solicitado no template embutido.
- A principal limitação prática conhecida é justamente o chat template: `--reasoning off` sozinho não garantiu non-thinking na rodada inicial.
- Para qualquer uso comparável, deve-se forçar `reasoning_effort=none` no template kwargs.
- Não há score canônico de código preservado suficiente neste perfil para classificá-lo como coder principal.

## MEDIDO LOCALMENTE

Hardware: NVIDIA GeForce RTX 5060 Ti 16 GB.

Runtime registrado: llama.cpp `0.3.0-dev`, build `10752`, commit `b96806d96061049a5b574269b049bf6241d63d46`.

Última validação referenciada neste perfil: `2026-09-02`.

### Escrita — rodada inicial

Fonte: `benchmarks/chat-writing-v1/results/GRUG_REASONING_AUDIT.md` e artefatos de `chat-writing-v1`.

- Resultado qualitativo inicial: **INVÁLIDO para comparar qualidade pura do modelo**.
- Motivo: o template nativo manteve `reasoning_effort="medium"` e vazou blocos de reasoning apesar de `--reasoning off`.
- Leakage observado: **6/6 gerações** na rodada afetada.
- Scores afetados registrados historicamente: Neutral **1.46/5**, Adult **3.63/5**, Overall **2.54/5**.
- Esses números devem ser tratados como diagnóstico de template, não como score final do modelo.
- Commit do audit histórico: `2c7a54986f266356447ea06accb9c6f1e19f0b9b`.

### Smoke non-thinking corrigido

Fonte: audit/smoke do `chat-writing-v1`.

- Configuração-chave: `--chat-template-kwargs '{"reasoning_effort":"none"}'`
- Reasoning tokens: **0**
- Throughput observado: **17.22 tok/s**
- Pico de VRAM observado: **14,242 MiB**
- Resultado: confirma que o modelo pode operar sem leakage quando o template é configurado explicitamente.
- Commit do smoke histórico: `e44489bd5cf9b88a5ed02acbb4e0528cd6eae2ba`

### Código

- Score canônico atual: **N/A / não registrado neste perfil com evidência suficiente para classificação**

### Speculative decoding

- DFlash2: **N/A / não validado como preset recomendado deste target**
- MTP: **N/A / não validado como preset recomendado deste target**

## DECLARADO PELO AUTOR/ORIGEM

- Repositório de origem da quantização: `mradermacher/grug-v1.1-qwen-3.8-27b-i1-GGUF`.
- Tamanho publicado do GGUF é aproximadamente `12.6 GB`; isso **não substitui** o tamanho exato local, que permanece `N/A / não registrado` até ser medido e versionado.
- Licença publicada pela origem: Apache-2.0.

## Preset recomendado

Usar o template nativo, mas desabilitar explicitamente reasoning também via template kwargs:

```bash
/home/alpha/.local/bin/llama serve \
  -m text/mradermacher-grug-v1.1-qwen-3.8-27b-i1-IQ3_M/grug-v1.1-qwen-3.8-27b.i1-IQ3_M.gguf \
  -ngl 999 -fa on --fit off \
  -ctk q8_0 -ctv q4_0 \
  -c 8192 -np 1 -t 8 \
  --jinja \
  --reasoning off \
  --chat-template-kwargs '{"reasoning_effort":"none"}'
```

Não remover o `--chat-template-kwargs` acima em execuções non-thinking comparáveis sem nova validação.

## Proveniência

- `text/mradermacher-grug-v1.1-qwen-3.8-27b-i1-IQ3_M/Modelfile`
- `benchmarks/chat-writing-v1/results/GRUG_REASONING_AUDIT.md`
- `benchmarks/chat-writing-v1/results/PREFLIGHT.json`
- Commits históricos: `2c7a54986f266356447ea06accb9c6f1e19f0b9b`, `e44489bd5cf9b88a5ed02acbb4e0528cd6eae2ba`
- Campo sem evidência versionada deve ser `N/A / não registrado`, nunca estimado.
