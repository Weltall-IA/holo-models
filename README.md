# Holo Models

Repositório do Projeto Holo para governança, inventário, configuração, benchmark e operação de modelos locais.

## Escopo

- metadados e documentação de modelos;
- `Modelfile`, configurações e scripts operacionais;
- benchmarks reproduzíveis;
- inventário e blacklist;
- regras de armazenamento, runtimes e reflink;
- tarefas versionadas para colaboração entre agentes.

Os pesos não são publicados no GitHub. No checkout local, ficam nas categorias canônicas:

```text
text/
audio/
video/
image/
embed/
```

## Governança de agentes

Antes de atuar, leia:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `.ai/tasks/<task-id>/STATUS.yml`, quando existir.

A execução é direta e segue o estágio `X.Y.Z` registrado no estado da tarefa. Correções incrementam somente o patch `Z`. Toda resposta operacional termina com a linha de versão correspondente ao papel ativo.

## Regras essenciais

- não versionar pesos, tokens, caches, bancos ou segredos;
- não inventar resultados, versões ou hashes;
- revisar alterações e validações reais antes de concluir;
- respeitar o escopo e o estado da tarefa;
- não executar gate posterior nem chamar API paga sem autorização explícita.
