# INSTRUCTIONS v2.2.6.1 — correções de bootstrap e proveniência da v2.2.6

## Autoridade e escopo

Esta versão é a instrução ativa e corrige o bootstrap operacional e a prova de revisão do modelo na `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.6.md`.

Leia e execute integralmente a v2.2.6, aplicando obrigatoriamente todas as substituições abaixo. As demais regras, proteções, execuções, validações, arquivos autorizados e formato de retorno da v2.2.6 permanecem vigentes.

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

Todas as invocações `-m holo_benchmark...` devem ser executadas na raiz da worktree com esse `PYTHONPATH`.

## Correção 3 — testes focados

Substitua o comando focado inválido da seção 4 por:

```bash
"$PYTHON" -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_mxbai_panel_benchmark.py' -v

"$PYTHON" -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_mxbai_panel_execution.py' -v

"$PYTHON" -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_bitnet_artifact_finalize.py' -v
```

Resultados esperados:

- runner Mixedbread: `5/5` PASS;
- wrapper de revisão: `2/2` PASS;
- finalizador BitNet: `3/3` PASS.

Em seguida execute a suíte integral da v2.2.6 e reporte a contagem real.

## Correção 4 — revisão Mixedbread provada localmente

A revisão `2cae013cb0d1dc0d16409ebd405e35875576d78e` citada na v2.2.6 identifica uma revisão histórica conhecida do peso, mas não deve ser registrada automaticamente como revisão do diretório local completo.

Antes da execução, determine a revisão real exclusivamente por metadados locais, sem rede.

Procure SHAs em:

- `rerank/mxbai_rerank_base_v2/.cache/huggingface/download/*.metadata`;
- `$HOME/.cache/huggingface/hub/models--mixedbread-ai--mxbai-rerank-base-v2/refs/main`, quando existir.

Exemplo somente leitura:

```bash
REVISION_FILE="/tmp/mxbai-v226-revisions.txt"
: > "$REVISION_FILE"

if [ -d "$MXBAI_MODEL/.cache/huggingface/download" ]; then
  while IFS= read -r -d '' metadata; do
    head -n 1 "$metadata" || true
  done < <(find "$MXBAI_MODEL/.cache/huggingface/download" -type f -name '*.metadata' -print0) \
    >> "$REVISION_FILE"
fi

HF_REF="$HOME/.cache/huggingface/hub/models--mixedbread-ai--mxbai-rerank-base-v2/refs/main"
if [ -f "$HF_REF" ]; then
  cat "$HF_REF" >> "$REVISION_FILE"
fi

mapfile -t MXBAI_REVISIONS < <(
  { grep -E '^[0-9a-fA-F]{40}$' "$REVISION_FILE" || true; } \
    | tr 'A-F' 'a-f' | sort -u
)

printf 'Revisões Mixedbread encontradas:\n'
printf '%s\n' "${MXBAI_REVISIONS[@]}"
```

Se não houver revisão, pare e reporte. Se houver mais de uma revisão distinta, não escolha silenciosamente pela ordem: correlacione os arquivos `.metadata` de `model.safetensors`, `config.json` e `tokenizer.json`. Todos os arquivos usados devem pertencer a uma única revisão comprovada. Se isso não puder ser provado, pare e reporte.

Depois da correlação:

```bash
MXBAI_REVISION="<SHA_UNICO_COMPROVADO>"
test "${#MXBAI_REVISION}" -eq 40
printf 'Mixedbread revision local: %s\n' "$MXBAI_REVISION"
```

`MXBAI_REVISION` deve ser um SHA hexadecimal completo obtido dos metadados, nunca `main`, tag ou SHA curto.

O SHA-256 obrigatório do peso continua:

`c01649fe56b3fe32e52da43c69e084dff7c2252cf231a38c56d5a291a674338f`

## Correção 5 — módulo de execução

Substitua todas as invocações da seção 8:

```bash
-m holo_benchmark.mxbai_panel_benchmark
```

por:

```bash
-m holo_benchmark.mxbai_panel_execution
```

E acrescente em cada comando:

```bash
--model-revision "$MXBAI_REVISION"
```

O wrapper rejeita `main`, tags, SHAs curtos e qualquer valor que não tenha exatamente 40 caracteres hexadecimais. A revisão comprovada é registrada no score e no pipeline.

## Correção 6 — interpretação de falhas

- Falha de importação antes de definir `PYTHONPATH` não conta como falha do runner; use o bootstrap corrigido.
- Falha após o bootstrap corrigido conta como falha real e deve ser reportada sem edição local de código.
- Não pule um perfil Mixedbread após falha não resolvida pelas reduções de batch autorizadas.
- Não registre a revisão histórica padrão quando os metadados locais apontarem para outra revisão.

## Retorno

Use o mesmo título e o mesmo conteúdo obrigatório da v2.2.6:

`Retorno v2.2.6 — Painel Mixedbread canônico e portabilidade BitNet`

Inclua adicionalmente:

- confirmação de que a v2.2.6.1 foi aplicada;
- valor efetivo de `PYTHONPATH`;
- caminho importado de `holo_benchmark`;
- todos os arquivos de metadados consultados;
- revisão local completa comprovada e método de correlação.
