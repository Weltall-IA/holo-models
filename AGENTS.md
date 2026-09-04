# AGENTS.md — Workspace models (Playstoria)

## Organização (regra central)

- Categoria canônica por tipo: `text/` (LLMs), `audio/`, `video/`, `image/`, `embed/`, `rerank/`.
- Pesos reais só na pasta canônica (nome = origem + quantização). Pastas de runtime (`runtimes/llama`, `runtimes/ollama`, `runtimes/lmstudio`, `runtimes/vllm`, `runtimes/comfyui`) contêm apenas links: symlink para `text/` (llama) ou blob/reflink (ollama). Nunca duplicar pesos.
- Trabalho pesado (quantização, GPU, checkouts de llama.cpp): pasta por tarefa em `tasks/` (ex.: `tasks/qwen38-ara-tq3/`); só o modelo final vai para a categoria canônica. `/home` e `/mnt/pool` são o mesmo volume (bcachefs).
- Remoção: apagar um modelo exige apagar também o symlink/reflink correspondente de cada runtime (`runtimes/llama`, `runtimes/lmstudio`, `runtimes/ollama`...) — a menos que o modelo continue em uso por outro runtime (ex.: está no ollama e no llama: manter só os links em uso). Nunca deixar link órfão apontando para modelo removido.
- Detalhes de governança: `gitmodels/docs/model-governance/MODEL_STORAGE.md`.

## Fluxo: adicionar modelo (obrigatório)

1. Identificar o tipo → categoria canônica (`text/`, `audio/`, `video/`, `image/`, `embed/`, `rerank/`).
2. Baixar do fonte oficial direto na pasta canônica: pasta nomeada `origem-quantizacao` (ex.: `text/Qwen3.8-27B-heretic-ara-TQ3_4S/`), sem espaços.
3. Criar obrigatoriamente dentro da pasta do modelo o arquivo de documentação `<nome-do-modelo>.md` (mesmo nome base do arquivo de pesos/GGUF, ex.: `Qwen3.8-27B-GSQ-RCO-IQ2_S.md`). O perfil é parte da identidade canônica do peso e deve ser atualizado quando houver nova validação, benchmark ou preset recomendado. Deve conter, no mínimo:
   - Identificação técnica: nome exato do arquivo, tamanho exato em bytes e GiB, SHA256, origem/autor, arquitetura e quantização;
   - Especialidade, pontos fortes, limitações e trade-offs;
   - Resultados de benchmarks locais realmente medidos no workspace: score, tok/s, wall time, pico de VRAM e speculative decoding/MTP quando houver;
   - Data da última validação local e hardware usado;
   - Runtime exato usado na validação, incluindo versão/build/commit quando disponível;
   - Proveniência dos números: caminho do benchmark/resultado e commit de referência quando disponível;
   - Comando/preset recomendado de execução: flags, contexto, KV cache, template, reasoning e draft quando aplicável;
   - Separação explícita entre `MEDIDO LOCALMENTE` e `DECLARADO PELO AUTOR/ORIGEM`.
   - É proibido inventar ou estimar benchmark ausente. Campo não medido ou não registrado deve ser marcado como `N/A / não testado` ou `N/A / não registrado`, com a pendência explícita.
4. Criar o link em cada runtime que vai usá-lo:
   - llama/lmstudio/vllm/comfyui: `ln -s ../text/<modelo>/<arquivo>.gguf runtimes/<runtime>/` (symlink);
   - ollama: importar para blob (reflink CoW obrigatório, sem cópia — ver MODEL_STORAGE.md).
5. Validar o modelo no runtime (boot + geração real) antes de considerar pronto e atualizar o `<nome-do-modelo>.md` com a validação efetivamente obtida.
6. Se o modelo deixar de ser usado por um runtime, remover só o link desse runtime; o físico na categoria canônica permanece até a remoção total.

## Fluxo: remover modelo (obrigatório)

1. Checar se o modelo está em uso por mais de um runtime (`runtimes/*`).
2. Remover o symlink/reflink de cada runtime que não vai mais usar o modelo (manter os dos runtimes em uso).
3. Remover blob do ollama somente após cruzar manifests/digests e provar que não é referenciado.
4. Remover a pasta canônica (`text/<modelo>/`).
5. Conferir que nenhum link órfão sobrou (`find . -xtype l` nas pastas de runtime).

## MCPs

- Preferir MCP quando o domínio tiver (github, context7, postgres-mcp-pro, sentry, n8n-mcp, playwright, jupyter, laravel-boost, grafana-cloud-mcp); read-only por padrão.

## Projeto

- Regras do projeto (fluxo, gates, benchmarks, padrão de atendimento): AGENTS.md canônico em `/home/alpha/Playstoria/infra-holoplay/AGENTS.md`.
