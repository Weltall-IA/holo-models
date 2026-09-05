# AGENTS.md — Workspace models (Playstoria)

## Organização (regra central)

- Categoria canônica por tipo: `text/` (LLMs), `audio/`, `video/`, `image/`, `embed/`, `rerank/`.
- Pesos reais só na pasta canônica (nome = origem + quantização). Pastas de runtime (`runtimes/llama`, `runtimes/ollama`, `runtimes/lmstudio`, `runtimes/vllm`, `runtimes/comfyui`) contêm apenas links: symlink para `text/` (llama) ou blob/reflink (ollama). Nunca duplicar pesos.
- Trabalho pesado (quantização, GPU, checkouts de llama.cpp): pasta por tarefa em `tasks/` (ex.: `tasks/qwen38-ara-tq3/`); só o modelo final vai para a categoria canônica. `/home` e `/mnt/pool` são o mesmo volume (bcachefs).
- Remoção: apagar um modelo exige apagar também o symlink/reflink correspondente de cada runtime (`runtimes/llama`, `runtimes/lmstudio`, `runtimes/ollama`...) — a menos que o modelo continue em uso por outro runtime. Nunca deixar link órfão apontando para modelo removido.
- Modelos totalmente removidos não devem permanecer como pastas históricas dentro das categorias ativas. O histórico compacto de modelos testados/removidos vive em `MODEL_HISTORY.md` e nos summaries/commits de benchmark.
- Detalhes de governança: `gitmodels/docs/model-governance/MODEL_STORAGE.md`.

## Histórico e proteção contra reteste (obrigatório)

1. **Antes de qualquer download, conversão, quantização ou benchmark de modelo**, consultar `MODEL_HISTORY.md` e procurar summaries/benchmarks existentes pelo nome do modelo, origem, revisão e variante.
2. Se o mesmo modelo/revisão/quantização, ou uma variante materialmente equivalente, já tiver sido testado, **não baixar nem retestar automaticamente**.
3. Antes de qualquer novo download nesse caso, informar ao usuário:
   - qual variante já foi testada;
   - resultado principal;
   - status/classificação;
   - evidência/benchmark existente.
4. Repetir download/teste somente com confirmação explícita do usuário ou quando houver mudança material capaz de alterar o resultado: nova revisão/peso treinado, quantização substancialmente diferente, correção relevante de runtime/template, benchmark que mede capacidade diferente ou mudança relevante de hardware. Documentar no novo benchmark por que o histórico anterior não basta.
5. Ao concluir avaliação de um modelo rejeitado/removido, adicionar ou atualizar sua entrada em `MODEL_HISTORY.md` antes de encerrar a remoção.
6. O ledger é um índice, não substitui resultados canônicos de modelos ativos nem summaries de benchmark.

## Fluxo: adicionar modelo (obrigatório)

1. Identificar o tipo → categoria canônica (`text/`, `audio/`, `video/`, `image/`, `embed/`, `rerank/`).
2. Executar obrigatoriamente a checagem de histórico acima. **Nenhum download começa antes dessa checagem.**
3. Se liberado pela checagem, baixar da fonte oficial direto na pasta canônica: pasta nomeada `origem-quantizacao` (ex.: `text/Qwen3.8-27B-heretic-ara-TQ3_4S/`), sem espaços.
4. Criar obrigatoriamente dentro da pasta do modelo o arquivo de documentação `<nome-do-modelo>.md` (mesmo nome base do arquivo de pesos/GGUF). O perfil é parte da identidade canônica do peso e deve ser atualizado quando houver nova validação, benchmark ou preset recomendado. Deve conter, no mínimo:
   - Identificação técnica: nome exato do arquivo, tamanho exato em bytes e GiB, SHA256, origem/autor, arquitetura e quantização;
   - Especialidade, pontos fortes, limitações e trade-offs;
   - Resultados de benchmarks locais realmente medidos no workspace: score, tok/s, wall time, pico de VRAM e speculative decoding/MTP quando houver;
   - Data da última validação local e hardware usado;
   - Runtime exato usado na validação, incluindo versão/build/commit quando disponível;
   - Proveniência dos números: caminho do benchmark/resultado e commit de referência quando disponível;
   - Comando/preset recomendado de execução: flags, contexto, KV cache, template, reasoning e draft quando aplicável;
   - Separação explícita entre `MEDIDO LOCALMENTE` e `DECLARADO PELO AUTOR/ORIGEM`;
   - Campo não medido ou não registrado deve ser `N/A / não testado` ou `N/A / não registrado`. É proibido inventar ou estimar benchmark ausente.
5. Criar o link em cada runtime que vai usá-lo:
   - llama/lmstudio/vllm/comfyui: symlink para o peso canônico;
   - ollama: importar para blob/reflink CoW conforme `MODEL_STORAGE.md`.
6. Validar o modelo no runtime (boot + geração real) antes de considerar pronto e atualizar o perfil com a validação efetivamente obtida.
7. Se o modelo deixar de ser usado por um runtime, remover só o link desse runtime; o físico na categoria canônica permanece até a remoção total.

## Fluxo: remover modelo (obrigatório)

1. Checar se o modelo está em uso por mais de um runtime (`runtimes/*`).
2. Antes da remoção total, garantir que `MODEL_HISTORY.md` registre identidade/revisão/quantização, resultado principal, status, data/hardware, benchmark e commit da execução quando disponível.
3. Remover o symlink/reflink de cada runtime que não vai mais usar o modelo.
4. Remover blob do ollama somente após cruzar manifests/digests e provar que não é referenciado.
5. Remover a pasta canônica inteira (`text/<modelo>/`, `embed/<modelo>/`, etc.) quando os pesos forem totalmente removidos. Não manter perfil histórico isolado em categoria ativa; o registro passa para `MODEL_HISTORY.md`.
6. Conferir que nenhum link órfão sobrou (`find . -xtype l` nas pastas de runtime).
7. Para candidato decisivamente rejeitado, pode compactar o histórico no branch atual conforme `MODEL_HISTORY.md`: preservar `SPEC.md`, `SUMMARY.md`, `RUN_MANIFEST.json` quando útil e o SHA do commit original; raw JSONL volumoso, logs, snapshots e runner exclusivo podem ser removidos. Não aplicar essa compactação automaticamente a modelos aceitos, próximos do gate ou campanhas ainda em análise.

## MCPs

- Preferir MCP quando o domínio tiver (github, context7, postgres-mcp-pro, sentry, n8n-mcp, playwright, jupyter, laravel-boost, grafana-cloud-mcp); read-only por padrão.

## Projeto

- Regras do projeto (fluxo, gates, benchmarks, padrão de atendimento): AGENTS.md canônico em `/home/alpha/Playstoria/infra-holoplay/AGENTS.md`.
