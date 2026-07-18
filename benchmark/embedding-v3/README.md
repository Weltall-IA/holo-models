# Benchmark de embeddings e reranking v3

Implementação versionada dos Gates 0 e 1 do benchmark do Projeto Holo.

## Segurança

- não baixa checkpoints nos Gates 0 e 1;
- não carrega modelos;
- não chama Voyage;
- não lê banco do Holo;
- não grava segredos;
- Gates 2 a 6 retornam bloqueio até nova autorização.

## Execução pelo agente local

O fluxo canônico está em:

```text
.ai/tasks/EMBED-BENCH-V3-1.1/REQUEST.md
.ai/tasks/EMBED-BENCH-V3-1.1/STATUS.yml
```

Comandos são executados no checkout da feature branch e registrados em `EXECUTION.md`.

## CLI

```text
--gate
--dry-run
--resume
--models
--device
--max-documents
--max-queries
--skip-api
--only-api
--rerank-k
--force-recompute
```

`--force-recompute` exige confirmação interativa digitando `RECOMPUTAR`.

## Gate 1 e revisão semântica

A primeira execução gera o corpus candidato e `semantic_review_checklist.json`, retornando código 3. O executor revisa pelo menos 30 itens, cria `semantic_review.json` no schema indicado pela checklist e executa novamente com `--resume`. Qualquer rejeição bloqueia o congelamento e exige decisão do diretor.
