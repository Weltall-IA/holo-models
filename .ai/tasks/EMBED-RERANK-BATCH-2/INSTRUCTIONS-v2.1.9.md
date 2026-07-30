# INSTRUCTIONS v2.1.9 — regeneração portátil do preflight

## Objetivo

Validar a correção implementada pelo gerente em `reranker_preflight.py`, regenerar `results/reranker/preflight.json` pelo gerador real sem caminhos absolutos do host e versionar exclusivamente esse artefato gerado.

Esta instrução não autoriza edição de código, testes, schemas, métricas, candidates ou pipelines.

## Repositório e escopo

- Repositório: `Weltall-IA/holo-models`
- Worktree: `/home/alpha/Playstoria/models-embed-batch2-light`
- Branch: `exec/embed-rerank-batch2-light`
- PR: `#20`
- Estado obrigatório: aberto e draft
- Não faça merge.

O gerente já implementou:

- serialização de caminhos relativos ao repositório;
- redação de caminhos externos como `<external>/<nome-do-arquivo>`;
- sanitização de caminhos Windows;
- sanitização de `qwen_candidates` e de `qwen_model_path_requested`;
- cinco testes focados do preflight.

## Preservação obrigatória

Os itens não rastreados preexistentes pertencem ao usuário e não podem ser adicionados, apagados, movidos ou modificados:

- `rerank/`
- `run_bitnet_benchmark.py`
- `run_light_phase.py`
- `runtimes/`

Não use `git clean`, `reset --hard`, stash automático ou force-push.

## Atualização segura

```bash
set -euo pipefail
cd /home/alpha/Playstoria/models-embed-batch2-light

git remote get-url origin
git branch --show-current
git status --short
git fetch origin --prune
git pull --ff-only origin exec/embed-rerank-batch2-light

test "$(git branch --show-current)" = "exec/embed-rerank-batch2-light"
test -f .ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.9.md
```

Se o pull for recusado porque `preflight.json` está modificado, não descarte o arquivo. Registre o SHA-256 da cópia local, salve somente esse arquivo em `/tmp/holo-preflight-v2.1.8.json`, restaure apenas `benchmark/embedding-v3/results/reranker/preflight.json` para o conteúdo do HEAD e repita o pull. Não toque nos não rastreados.

## Testes antes da regeneração

Execute:

```bash
python .ai/validate_governance.py
python -m unittest discover -s benchmark/embedding-v3/tests -p 'test_reranker_preflight.py' -v
python -m unittest discover -s benchmark/embedding-v3/tests -v
python -m compileall -q benchmark/embedding-v3
git diff --check
```

Todos devem retornar código 0. Não corrija nenhuma falha; reporte ao gerente.

## Regeneração real

Execute uma vez:

```bash
python benchmark/embedding-v3/reranker_benchmark.py --phase preflight
```

Código 0 indica que o comando executou corretamente; o campo `status` do JSON pode continuar `BLOCKED` por dependências ausentes.

Valide programaticamente, sem regravar o arquivo:

1. JSON parseia e termina com newline;
2. `schema_version == "1.0"`;
3. corpus continua 600/150 com SHA-256 congelado;
4. nenhum valor em `paths[*].path` é absoluto;
5. nenhum `qwen_candidates[*].path` é absoluto;
6. nenhum caminho contém `/home/`, `/Users/`, `Playstoria`, `models-embed-batch2-light` ou o username do host;
7. caminhos internos usam formato relativo, por exemplo `embed/...`, `benchmark/...` ou `rerank/...`;
8. caminhos externos, se existirem, usam `<external>/<basename>`;
9. nenhuma API Voyage foi chamada;
10. nenhum benchmark de embedding ou reranking foi executado.

## Git

Revise:

```bash
git status --short
git diff -- benchmark/embedding-v3/results/reranker/preflight.json
git diff --check
```

O único arquivo rastreado modificado deve ser:

`benchmark/embedding-v3/results/reranker/preflight.json`

Depois:

```bash
git add -- benchmark/embedding-v3/results/reranker/preflight.json
git diff --cached --check
git diff --cached --name-only
```

Confirme que a saída contém exatamente um arquivo. Então faça:

```bash
git commit -m "Regenerate portable reranker preflight"
git push origin exec/embed-rerank-batch2-light
```

Não adicione os arquivos não rastreados. Não faça merge.

## Retorno

Retorne:

- HEAD inicial e final completos;
- status antes e depois;
- comandos e exit codes;
- total da suíte integral;
- conteúdo resumido de `status` e `blockers` do preflight;
- lista completa dos caminhos persistidos;
- confirmação de ausência de caminhos absolutos e identificadores do host;
- SHA-256 do `preflight.json` versionado;
- nome exato do único arquivo commitado;
- confirmação de ausência de Voyage, benchmarks de modelos, edição de código, arquivos não rastreados no commit e merge.

Termine exatamente com:

`Versão do retorno da IA local: 2.1.9 — Preflight portátil regenerado pelo gerador canônico`
