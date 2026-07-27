# Resumos de benchmark substituídos

Esta pasta preserva documentos históricos que foram retirados da raiz para evitar múltiplas fontes concorrentes.

Fonte canônica para inventário, ranking e comparação:

`benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json`

Fontes autoritativas das métricas:

`benchmark/embedding-v3/results/reranker/pipelines/**/*.json`

Arquivos preservados:

- `BENCHMARK_RESULTS.json` — primeiro registro consolidado;
- `BENCHMARK_RESULTS_REGISTRY.json` — registry intermediário append-only;
- `RERANKER_TOP5_REPORT.md` — relatório da sessão Top-5;
- `OPERATIONAL_COMPARISON_REPORT.md` — comparação operacional do PR #12.

Estes arquivos não devem ser usados para escolher o líder atual. Permanecem somente para auditoria histórica e rastreabilidade.
