# EMBED-RERANK-BATCH-2 — INSTRUCTIONS v2.2.13

## Objetivo

Executar, nesta ordem única:

1. selecionar definitivamente `Abiray/Nemotron-3-Embed-8B-GGUF` como mirror canônico;
2. executar Voyage Rerank 2.5 somente nas variantes Abiray auditadas em 4096 e 1024 dimensões;
3. excluir dos resultados publicáveis o mirror Aqua00 e os resultados legados ambíguos de Abiray/Aqua00;
4. preservar o artefato de auditoria integral que prova equivalência tensorial;
5. regenerar o consolidado e as duas tabelas canônicas da README;
6. validar, commitar e fazer push, sem merge.

## Decisão de mirror

O Hugging Face registrava aproximadamente:

- Abiray: 2,3 mil downloads;
- Aqua00: 733 downloads.

Os dois GGUF possuem conteúdo integral dos 308 tensores idêntico. Por decisão do operador, o mirror com maior adoção, Abiray, é o único perfil publicável.

## Estado Git obrigatório

- repositório: `Weltall-IA/holo-models`;
- worktree: `/home/alpha/Playstoria/models-embed-batch2-light`;
- branch: `exec/embed-rerank-batch2-light`;
- PR: `#20`, aberto, draft e sem merge;
- HEAD inicial: o SHA completo informado no handoff.

Execute:

```bash
set -euo pipefail
cd /home/alpha/Playstoria/models-embed-batch2-light

git remote get-url origin
git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse origin/exec/embed-rerank-batch2-light
```

Pare se branch ou HEAD divergirem, ou se houver alteração rastreada inesperada.

Preserve os não rastreados:

- `rerank/`
- `runtimes/`
- `run_bitnet_benchmark.py`
- `run_light_phase.py`

Não use stash, `reset --hard`, `clean`, checkout destrutivo ou force-push.

## Leitura obrigatória

Leia integralmente:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`;
6. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.12.1.md`;
7. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.12.2.md`;
8. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.12.3.md`;
9. este arquivo;
10. descrição atual e diff do PR #20.

## Responsabilidade da IA executora

Pode:

- executar testes e validações;
- chamar Voyage Rerank 2.5 para os dois candidates Abiray autorizados;
- executar o finalizador versionado;
- remover somente os artefatos explicitamente programados pelo finalizador;
- commitar resultados, consolidado e README;
- fazer push sem force.

Não pode:

- editar código, testes, instruções ou configuração;
- executar embeddings ou Qwen novamente;
- chamar Voyage para qualquer outro embedding;
- alterar manualmente métricas;
- apagar o artefato de identidade Abiray/Aqua00;
- fazer merge.

Falha de código deve ser reportada sem correção local.

## Python

Use:

```bash
PYTHON=/home/alpha/Playstoria/models/benchmarks/holo-embedding-benchmark-v3/.venv/bin/python
"$PYTHON" --version
```

## 1. Validação inicial

```bash
cd /home/alpha/Playstoria/models-embed-batch2-light/benchmark/embedding-v3

"$PYTHON" validate_governance.py
"$PYTHON" -m unittest discover -s tests -p 'test_*.py'
"$PYTHON" -m compileall -q .
"$PYTHON" validate_coverage.py
git diff --check
```

Critérios:

- pelo menos 235 testes;
- zero falhas e erros;
- todas as validações com exit 0.

Confirme também a existência de:

- `results/gate3/nemotron_8b_abiray_q4_audit_4096.json`;
- `results/gate3/nemotron_8b_abiray_q4_audit_1024.json`;
- candidates correspondentes;
- pipelines Qwen correspondentes;
- `results/reranker/nemotron_8b_abiray_aqua00_identity_audit.json` com status `IDENTICAL_ALL_TENSOR_CONTENT_METADATA_ONLY_CONTAINER_DIFFERENCE`.

## 2. Autorização Voyage

O operador autorizou explicitamente nesta rodada a execução Voyage para:

- `nemotron_8b_abiray_q4_audit_4096`;
- `nemotron_8b_abiray_q4_audit_1024`.

Nenhum outro perfil está autorizado.

Use a chave já existente:

`/home/alpha/Playstoria/models/.voyage4_token`

Antes da chamada, registre:

- arquivo de chave existe, sem imprimir seu conteúdo;
- número estimado de consultas: 150;
- candidate top-k: 50;
- rerank top-k: 20;
- variantes: exatamente 2;
- modelo API: `rerank-2.5`.

Se a API recusar por limite, saldo, cobrança ou autenticação, pare e reporte o erro exato. Não troque de conta, chave ou modelo.

## 3. Executar Voyage somente para Abiray

```bash
"$PYTHON" -m holo_benchmark.nemotron_8b_abiray_finalize voyage \
  --api-key-path /home/alpha/Playstoria/models/.voyage4_token \
  --request-interval 1.0
```

Se houver interrupção recuperável:

```bash
"$PYTHON" -m holo_benchmark.nemotron_8b_abiray_finalize voyage \
  --api-key-path /home/alpha/Playstoria/models/.voyage4_token \
  --request-interval 1.0 \
  --resume
```

A execução deve criar somente:

- `results/reranker/scores/voyage_rerank_2_5_nemotron_8b_abiray.json`;
- `results/reranker/pipelines/voyage_rerank_2_5/nemotron_8b_abiray_q4_audit_4096.json`;
- `results/reranker/pipelines/voyage_rerank_2_5/nemotron_8b_abiray_q4_audit_1024.json`;
- checkpoint separado sob `results/raw/reranker/` quando necessário.

Não pode sobrescrever os nove pipelines Voyage anteriores nem o score histórico genérico.

Registre no retorno:

- requests;
- tokens, quando fornecidos pelo runtime;
- elapsed time;
- resume usado ou não;
- MRR@10, HR@1, HR@10, nDCG@10 e hard-negative error de cada pipeline.

## 4. Finalização canônica e remoção do Aqua00

Depois de Voyage passar, obtenha o HEAD atual completo:

```bash
SOURCE_COMMIT="$(git rev-parse HEAD)"
```

Execute:

```bash
"$PYTHON" -m holo_benchmark.nemotron_8b_abiray_finalize finalize \
  --source-commit "$SOURCE_COMMIT" \
  --revision 2026-07-30
```

O finalizador deve:

- manter Abiray 4096 e 1024;
- remover os resultados legados ambíguos Abiray/Aqua00;
- remover todos os resultados raw, candidates e pipelines Qwen do Aqua00 auditado;
- preservar `results/reranker/nemotron_8b_abiray_aqua00_identity_audit.json`;
- preservar os dois resultados Abiray auditados;
- preservar os pipelines Qwen Abiray;
- preservar os dois novos pipelines Voyage Abiray;
- regenerar `ALL_BENCHMARK_RESULTS.json`;
- atualizar as duas tabelas da README;
- retirar Abiray e Aqua00 antigos da blacklist provisória;
- inserir os dois perfis Abiray auditados na tabela de reutilizáveis;
- publicar 107 pipelines totais;
- publicar 36 embeddings únicos;
- publicar 39 perfis raw;
- registrar 11 pipelines Voyage;
- manter 36 pipelines Qwen.

Pare se qualquer contagem divergir.

## 5. Verificações obrigatórias após finalização

Confirme ausência nos rankings e artefatos publicáveis de:

- `nemotron_8b_aqua00_q4`;
- `nemotron_8b_aqua00_q4_audit_4096`;
- `nemotron_8b_aqua00_q4_audit_1024`;
- `nemotron_8b_abiray_q4` legado.

Confirme presença de:

- `nemotron_8b_abiray_q4_audit_4096` raw, Qwen e Voyage;
- `nemotron_8b_abiray_q4_audit_1024` raw, Qwen e Voyage;
- artefato de auditoria integral Abiray/Aqua00.

Execute:

```bash
"$PYTHON" validate_governance.py
"$PYTHON" -m unittest discover -s tests -p 'test_*.py'
"$PYTHON" -m compileall -q .
"$PYTHON" validate_coverage.py
"$PYTHON" tools/consolidate_all_benchmark_results.py --validate-only
"$PYTHON" tools/update_canonical_readme_tables.py --validate-only --revision 2026-07-30
git diff --check
```

Valide programaticamente:

- todos os JSON parseiam;
- zero path absoluto ou segredo;
- consolidado com status PASS;
- pipelines 107;
- embeddings 36;
- raw 39;
- Voyage 11;
- Qwen 36;
- os dois novos Voyage usam `$.evaluation.reranked_metrics.summary`;
- README contém os dois perfis Abiray auditados;
- README não contém linhas canônicas de Aqua00 ou dos IDs legados ambíguos;
- arquivos não rastreados protegidos permanecem intactos.

Observação: o `--validate-only` do consolidador histórico possui constantes antigas. Se ele falhar exclusivamente por esperar 105 pipelines ou 9 Voyage, reporte essa divergência como defeito do validador antigo; não edite código. O consolidado gerado pelo finalizador deve possuir suas próprias verificações PASS com 107/11.

## 6. Git

Revise:

```bash
git status --short
git diff --stat
git diff --check
git diff -- benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json benchmark/embedding-v3/README.md
```

O commit pode conter somente:

- dois pipelines Voyage Abiray;
- score/checkpoint Voyage Abiray necessários;
- remoções explícitas de resultados legados/Aqua00;
- `ALL_BENCHMARK_RESULTS.json`;
- `README.md`.

Não inclua pesos, caches, token, `rerank/`, `runtimes/` ou outros não rastreados.

Commit:

```bash
git add -A -- benchmark/embedding-v3/results benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json benchmark/embedding-v3/README.md
git commit -m "Select Abiray mirror and add Voyage rerank results"
git push origin exec/embed-rerank-batch2-light
```

Não faça merge.

## 7. Retorno obrigatório

Informe:

1. HEAD inicial e final completos;
2. arquivos adicionados, alterados e removidos;
3. identidade Abiray preservada;
4. confirmação de remoção Aqua00 dos rankings;
5. uso Voyage: requests, tokens, tempo, custo/cobrança observada;
6. métricas raw, Qwen e Voyage para 4096 e 1024;
7. ranking global atualizado dos pipelines principais;
8. contagens finais 107/36/39 e Voyage 11/Qwen 36;
9. validações e testes;
10. confirmação de PR draft, sem merge e não rastreados preservados.

Versão esperada do retorno:

`2.2.13 — Abiray canônico, Aqua00 removido, Voyage executado e consolidado regenerado`
