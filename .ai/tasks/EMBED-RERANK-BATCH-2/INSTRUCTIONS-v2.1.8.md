# INSTRUCTIONS v2.1.8 — validação final da sanitização de caminhos

## Objetivo

Validar exclusivamente a correção de `_sanitize` implementada pelo gerente após o retorno v2.1.7.

Esta instrução não autoriza programação, edição de testes, alteração de schemas, alteração de resultados, reexecução de benchmarks BitNet, geração de candidates ou execução de rerankers.

## Repositório, branch e PR

- Repositório: `Weltall-IA/holo-models`
- Worktree: `/home/alpha/Playstoria/models-embed-batch2-light`
- Branch: `exec/embed-rerank-batch2-light`
- PR: `#20`
- Estado obrigatório: aberto e draft
- HEAD de referência anterior à instrução: `23ac7d91b08aa946597f668742b07c3907b801a8`

Não faça merge.

## Alterações implementadas pelo gerente

Foram alterados somente:

- `benchmark/embedding-v3/holo_benchmark/production_profile_runtime.py`;
- `benchmark/embedding-v3/tests/test_production_profile_runtime.py`.

A correção:

- remove o caminho completo baseado em `REPO`, `HOME`, `Path.home()` ou `USERPROFILE`;
- cobre separadores Linux e Windows;
- evita deixar expostos sufixos de workspace como `Playstoria/models`;
- redige o nome de usuário somente quando aparece como token isolado;
- preserva substrings legítimas, como `alphabet` e `alpha-1`;
- adiciona testes para home Linux, repositório atual, home Windows e limites de username.

O gerente executou 30 testes focados em ambiente isolado, todos aprovados. Isso não substitui a suíte integral na worktree real.

## Preservação obrigatória

A worktree contém arquivos e diretórios não rastreados preexistentes, incluindo itens como `rerank/`, `run_bitnet_benchmark.py`, `run_light_phase.py` e `runtimes/`.

Eles pertencem ao usuário. Não mova, não apague, não versione, não esconda e não faça stash.

## Proibições

- não edite nenhum arquivo;
- não use `git add`, `git commit` ou `git push`;
- não execute benchmark BitNet;
- não recrie candidates ou pipelines;
- não chame API Voyage;
- não baixe ou execute modelos;
- não altere Python, CUDA, driver, PyTorch ou pacotes;
- não use `reset --hard`, `clean`, `checkout --`, stash ou force-push;
- não faça merge.

Se houver falha, entregue o traceback integral sanitizado e pare. Não tente corrigir.

## Retomada

```bash
set -euo pipefail
cd /home/alpha/Playstoria/models-embed-batch2-light

git remote get-url origin
git branch --show-current
git status --short
git fetch origin --prune
git pull --ff-only origin exec/embed-rerank-batch2-light

test "$(git branch --show-current)" = "exec/embed-rerank-batch2-light"
test -f .ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.8.md
git rev-parse HEAD
```

Registre o HEAD completo e o `git status --short` antes dos testes.

## Validações obrigatórias

Execute exatamente e registre comando, exit code e resumo:

```bash
python .ai/validate_governance.py
python -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_production_profile_runtime.py' -v
python -m unittest discover -s benchmark/embedding-v3/tests -v
python -m compileall -q benchmark/embedding-v3
python benchmark/embedding-v3/validate_coverage.py
python benchmark/embedding-v3/reranker_benchmark.py --phase preflight
git diff --check
```

Confirme especificamente:

1. `test_sanitize_removes_home_path` passa;
2. `test_sanitize_removes_current_repo_path` passa;
3. `test_sanitize_removes_windows_home_path` passa;
4. `test_sanitize_preserves_username_substrings` passa;
5. a suíte integral possui zero failures e zero errors;
6. nenhum arquivo foi modificado pelos testes;
7. os dois resultados BitNet permanecem intactos;
8. candidates e pipelines Qwen dos BitNet continuam ausentes.

## Retorno obrigatório

Retorne:

1. HEAD completo;
2. worktree antes e depois;
3. todos os comandos e exit codes;
4. quantidade total de testes, passes, failures e errors;
5. resultado individual dos quatro testes de sanitização;
6. confirmação de que os resultados BitNet não foram alterados;
7. confirmação de ausência de Voyage, modelos, edição de código, commit e merge.

Termine exatamente com:

`Versão do retorno da IA local: 2.1.8 — Validação final da sanitização de caminhos`
