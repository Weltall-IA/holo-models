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

## Fonte de verdade

Leia antes de atuar:

1. `AGENTS.md`;
2. `.ai/WORKFLOW.yml`;
3. `docs/ai-collaboration/ROLES.md`;
4. `docs/ai-collaboration/PROTOCOL.md`;
5. `docs/ai-collaboration/LOCAL_EXECUTOR.md`, quando aplicável;
6. `.ai/tasks/<task-id>/STATUS.yml` e `REQUEST.md`;
7. `docs/model-governance/MODEL_STORAGE.md`.

## Regras essenciais

- nunca trabalhar diretamente em `master`;
- não versionar pesos, tokens, caches, bancos ou segredos;
- não fazer force push, merge, publicação ou remoção de modelos sem autorização humana;
- resultados e validações devem ser reais e vinculados ao SHA executado;
- no modo `dual`, o ChatGPT é o autor remoto e a IA local executa, valida e coleta evidências.
