# INSTRUCTIONS v2.1.7 — validação operacional após correção do gerente

## Objetivo

Validar exclusivamente as correções implementadas pelo gerente após o retorno v2.1.6. Esta instrução não autoriza programação, alteração de testes, alteração de schemas, reexecução dos benchmarks BitNet completos ou edição manual de artefatos.

## Repositório, branch e PR

- Repositório: `Weltall-IA/holo-models`
- Worktree: `/home/alpha/Playstoria/models-embed-batch2-light`
- Branch: `exec/embed-rerank-batch2-light`
- PR: `#20`
- Estado obrigatório: aberto e draft
- Não faça merge.

## Alterações feitas pelo gerente

O gerente corrigiu diretamente:

- telemetria residual de VRAM para não invalidar embeddings CPU quando `nvidia-smi` estiver ausente, incompatível ou interceptado por mock;
- comando versionado sanitizado, sem caminhos absolutos do binário, GGUF ou arquivo temporário;
- remoção automática de candidate obsoleto quando o perfil termina com gate FAIL;
- validação da identidade antes de remover qualquer candidate;
- validação do loader canônico quando `--candidate-output` aponta para diretório alternativo;
- testes específicos da limpeza de candidates obsoletos.

Também foram removidos do branch, porque o BitNet 270M terminou com gate FAIL:

- `benchmark/embedding-v3/results/reranker/candidates/bitnet_270m_current.json`;
- `benchmark/embedding-v3/results/reranker/pipelines/qwen_local/bitnet_270m_current.json`.

Os resultados reais abaixo devem permanecer preservados e não devem ser reexecutados:

- `benchmark/embedding-v3/results/gate3/bitnet_06b_current.json`;
- `benchmark/embedding-v3/results/gate3/bitnet_270m_current.json`.

A alegação anterior de ausência de `dataset` nesses dois arquivos estava incorreta. Ambos registram corpus, SHA-256, 600 documentos e 150 consultas.

## Proibições

- não edite Python;
- não edite testes;
- não edite JSON ou YAML manualmente;
- não reexecute os benchmarks BitNet completos;
- não recrie candidate para BitNet 0.6B ou 270M;
- não execute Qwen para BitNet;
- não chame API Voyage;
- não baixe ou execute modelos pesados;
- não altere CUDA, driver, Python, PyTorch ou pacotes globais;
- não faça commit vazio;
- não faça merge.

Se houver falha de código, preserve a saída integral sanitizada e reporte ao gerente. Não tente corrigir.

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
test -f .ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.7.md
```

Registre o HEAD completo após o pull e confirme worktree limpa antes dos testes.

## Testes obrigatórios

Execute e registre comando, exit code e resumo:

```bash
python .ai/validate_governance.py
python -m unittest \
  benchmark.embedding-v3.tests.test_bitnet_parser \
  benchmark.embedding-v3.tests.test_bitnet_gate_cleanup -v
python -m unittest discover -s benchmark/embedding-v3/tests -v
python -m compileall -q benchmark/embedding-v3
git diff --check
```

Se a forma de módulo com hífen no caminho não funcionar, execute os dois arquivos focados por discovery sem editar nada:

```bash
python -m unittest discover -s benchmark/embedding-v3/tests -p 'test_bitnet*.py' -v
```

## Validação dos resultados e limpeza

Execute validação somente de leitura confirmando:

1. os dois resultados BitNet têm `schema_version = 1.0`;
2. `dataset.combined_sha256` corresponde ao corpus congelado;
3. `dataset.documents = 600` e `dataset.queries = 150`;
4. `metrics.per_query` contém 150 entradas;
5. `metrics.by_query_type` não está vazio;
6. não há NaN ou infinito;
7. ambos possuem `gate_result = FAIL`;
8. `bitnet_06b_current` mantém `HitRate@50 = 0.7666666666666667`;
9. `bitnet_270m_current` mantém `HitRate@50 = 0.8466666666666667`;
10. não existe candidate BitNet 0.6B;
11. não existe candidate BitNet 270M;
12. não existe pipeline Qwen para nenhum dos dois BitNet.

Use Python de leitura para validar. Não regrave os arquivos.

## Falha `test_sanitize_removes_repo_path`

Se esse teste ainda falhar, o retorno deve incluir obrigatoriamente:

- caminho completo do arquivo de teste dentro do repositório;
- nome completo do módulo e da classe;
- traceback integral sanitizado;
- valor esperado;
- valor efetivamente recebido;
- função de produção chamada pelo teste;
- `git blame` das linhas do teste e da função, sem editar nada.

Não classifique como “pré-existente” sem essas evidências.

## Git e retorno

Após os testes:

- confirme `git status --short`;
- não faça commit se nenhum artefato foi legitimamente alterado;
- não faça push de arquivos gerados por testes;
- mantenha o PR #20 draft;
- não faça merge.

Retorne:

1. HEAD completo;
2. estado da worktree antes e depois;
3. comandos e exit codes;
4. total de testes, passes, failures e errors;
5. validação dos 12 itens dos resultados;
6. traceback completo de qualquer falha remanescente;
7. confirmação de que nenhum código foi editado;
8. confirmação de ausência de Voyage, modelos pesados e merge.

Termine exatamente com:

`Versão do retorno da IA local: 2.1.7 — Validação operacional após correção do gerente`
