# Benchmark de embeddings e reranking v3

Implementação versionada dos Gates 0, 1 e 2 do benchmark do Projeto Holo.

## Segurança

- Gates 0 e 1 não baixam checkpoints nem executam embeddings;
- o Gate 2 usa somente modelos locais autorizados em `config/models.json`;
- snapshots são baixados para `embed/<model-id>` e permanecem fora do Git;
- revisões, tamanhos, licenças e hashes dos pesos são registrados nos resultados;
- nenhuma API paga é chamada no Gate 2;
- Gates 3 a 6 permanecem bloqueados até nova autorização;
- segredos e tokens não são gravados em relatórios.

## Estado das tarefas

O objetivo, o escopo, a etapa, os resultados, a auditoria e o próximo passo ficam concentrados em:

```text
.ai/tasks/EMBED-BENCH-V3-1.1/STATUS.yml
.ai/tasks/EMBED-BENCH-V3-1.2/STATUS.yml
```

A execução deve atualizar o `STATUS.yml` da atividade atual e terminar a resposta com a linha de versão definida em `.ai/WORKFLOW.yml`.

## CLI

```text
--gate
--dry-run
--resume
--models
--device
--batch-size
--max-documents
--max-queries
--skip-api
--only-api
--rerank-k
--force-recompute
```

`--force-recompute` exige confirmação interativa digitando `RECOMPUTAR`.

## Gate 1 e revisão semântica

A primeira execução gera o corpus candidato e `semantic_review_checklist.json`, retornando código 3. O executor revisa pelo menos 30 itens, cria `semantic_review.json` no schema indicado pela checklist e executa novamente com `--resume`. Qualquer rejeição bloqueia o congelamento e exige decisão sobre a correção.

## Gate 2 — modelos locais compactos

O dry-run resolve metadados oficiais dos modelos habilitados, incluindo revisão imutável, tamanho, licença, estado de acesso e destino canônico, sem baixar pesos.

A execução completa:

1. exige Gates 0 e 1 em `PASS`;
2. preserva o corpus congelado e seu hash conjunto;
3. baixa cada snapshot para `embed/<model-id>` na revisão resolvida;
4. executa os modelos sequencialmente no dispositivo solicitado;
5. calcula métricas globais, por tipo de consulta e por consulta;
6. registra dimensão, dtype, normalização, throughput, pico de VRAM e hashes dos pesos;
7. publica somente relatórios e resultados sanitizados.

Uma seleção parcial com `--models`, `--max-documents` ou `--max-queries` serve para diagnóstico e não pode concluir o Gate 2 como `PASS`. A execução final deve usar o conjunto completo de modelos e o corpus congelado completo.
