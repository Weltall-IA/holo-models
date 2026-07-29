# INSTRUCTIONS v2.2.6.1 — correção de bootstrap da v2.2.6

## Autoridade e escopo

Esta versão é a instrução ativa e corrige somente o bootstrap operacional da `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.6.md`.

Leia e execute integralmente a v2.2.6, aplicando obrigatoriamente as substituições abaixo. Todas as demais regras, proteções, execuções, validações, arquivos autorizados e formato de retorno da v2.2.6 permanecem vigentes.

A IA local não pode editar código ou qualquer arquivo de instrução.

## Correção 1 — verificação do HEAD

Na seção 1 da v2.2.6, não execute a linha com o placeholder:

```bash
test "$(git rev-parse HEAD)" = "<HEAD_COMPLETO_ESPERADO_DO_HANDOFF>"
```

Depois de `git pull --ff-only`, execute:

```bash
ACTUAL_HEAD="$(git rev-parse HEAD)"
printf 'HEAD após pull: %s\n' "$ACTUAL_HEAD"
```

Compare `ACTUAL_HEAD` com o SHA completo informado na mensagem de handoff. Se divergir, pare e reporte. Não altere o arquivo para preencher o SHA.

## Correção 2 — importação do pacote do benchmark

Imediatamente depois de resolver `PYTHON`, ainda na raiz da worktree, execute:

```bash
export PYTHONPATH="$PWD/benchmark/embedding-v3${PYTHONPATH:+:$PYTHONPATH}"

"$PYTHON" - <<'PY'
import holo_benchmark
print("holo_benchmark", holo_benchmark.__file__)
PY
```

Todas as invocações `-m holo_benchmark...` da v2.2.6 dependem desse `PYTHONPATH` e devem ser executadas na raiz da worktree.

## Correção 3 — testes focados

Substitua o comando focado inválido da seção 4 por dois comandos `discover`:

```bash
"$PYTHON" -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_mxbai_panel_benchmark.py' -v

"$PYTHON" -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_bitnet_artifact_finalize.py' -v
```

Resultados esperados dos testes focados:

- Mixedbread: `5/5` PASS;
- finalizador BitNet: `3/3` PASS.

Em seguida execute a suíte integral exatamente como definido na v2.2.6 e reporte a contagem real.

## Correção 4 — interpretação de falhas

- Falha de importação de `holo_benchmark` antes de definir `PYTHONPATH` não conta como falha do runner; use o bootstrap corrigido acima.
- Falha após o bootstrap corrigido conta como falha real e deve ser reportada sem edição local de código.
- Não pule um perfil Mixedbread após falha não resolvida pelas reduções de batch autorizadas.

## Retorno

Use o mesmo título e o mesmo conteúdo obrigatório da v2.2.6:

`Retorno v2.2.6 — Painel Mixedbread canônico e portabilidade BitNet`

Inclua adicionalmente:

- confirmação de que a v2.2.6.1 foi aplicada;
- valor efetivo de `PYTHONPATH`;
- caminho importado de `holo_benchmark`.
