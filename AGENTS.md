# Regras para agentes de IA

## Leitura inicial

Antes de executar uma tarefa, leia:

1. `.ai/PROJECT.yml`;
2. `.ai/WORKFLOW.yml`;
3. `.ai/tasks/<task-id>/STATUS.yml`, quando existir.

Não interrompa o trabalho apenas para informar que esses arquivos foram lidos.

## Execução

Execute diretamente as ações necessárias para concluir a tarefa.

Não peça confirmação para inspecionar, editar, testar, validar, corrigir, repetir comandos, incrementar patches ou atualizar o estado da tarefa.

Solicite uma decisão somente quando não for tecnicamente possível continuar sem informação externa ou quando a tarefa exigir uma escolha que altere seu objetivo.

## Proteção de edição

Antes de modificar qualquer arquivo existente:

1. crie uma cópia temporária;
2. edite o arquivo original;
3. gere um diff entre a cópia e o arquivo editado;
4. revise o diff;
5. mantenha a alteração quando estiver correta;
6. restaure o original quando estiver incorreta;
7. remova a cópia temporária.

Procedimento:

```bash
arquivo="caminho/do/arquivo"
temporario="$(mktemp)"

cp --preserve=mode,timestamps -- "$arquivo" "$temporario"
micro "$arquivo"

diff -u \
  --label "$arquivo — antes" \
  --label "$arquivo — depois" \
  "$temporario" \
  "$arquivo"
```

Para manter a alteração:

```bash
rm -f -- "$temporario"
```

Para restaurar:

```bash
cp --preserve=mode,timestamps -- "$temporario" "$arquivo"
rm -f -- "$temporario"
```

Arquivos novos não exigem cópia temporária, mas devem ter seu conteúdo completo revisado.

## Validações

Execute as validações aplicáveis definidas em `.ai/PROJECT.yml`.

Registre somente resultados realmente obtidos. Quando uma validação não puder ser executada, informe o motivo.

## Correções

Quando uma validação ou auditoria encontrar um erro dentro do escopo:

1. incremente o patch;
2. aplique a correção;
3. revise o diff;
4. repita as validações;
5. atualize o `STATUS.yml`;
6. continue sem pedir confirmação.

## Comunicação

Informe somente:

- trabalho realizado;
- arquivos alterados;
- validações e resultados;
- bloqueios reais;
- próximo passo.

Toda resposta operacional deve terminar com a linha de versão definida em `.ai/WORKFLOW.yml`.

Nenhum texto pode aparecer depois dessa linha.
