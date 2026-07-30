# EMBED-RERANK-BATCH-2 — INSTRUCTIONS v2.2.14

## Objetivo

Concluir os dois pipelines Voyage Rerank 2.5 do Nemotron 8B Abiray por meio da Voyage Batch API, substituir o estado provisório `BLOCKED_RATE_LIMIT`, regenerar o consolidado e atualizar a README.

A API síncrona não deve ser utilizada nesta etapa.

## Estado esperado

- repositório: `Weltall-IA/holo-models`;
- worktree: `/home/alpha/Playstoria/models-embed-batch2-light`;
- branch: `exec/embed-rerank-batch2-light`;
- PR: `#20`, aberto, draft e sem merge;
- HEAD inicial: SHA completo informado no handoff;
- Abiray é o único mirror canônico;
- Aqua00 e os resultados legados ambíguos já foram removidos;
- consolidado atual: 105 pipelines, 36 embeddings, 39 raws, 9 Voyage;
- bloqueio provisório existente: `results/reranker/voyage_rerank_2_5_nemotron_8b_abiray_blocked.json`.

## Leitura obrigatória

Leia integralmente, nesta ordem:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`;
6. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.13.md`;
7. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.13.1.md`;
8. este arquivo;
9. descrição e diff atuais do PR #20.

## Proteções

Não:

- editar código, testes, instruções ou configuração;
- executar embedding ou Qwen novamente;
- usar o endpoint síncrono `/v1/rerank` diretamente;
- chamar outro modelo Voyage;
- chamar Voyage para outro embedding;
- imprimir ou versionar a chave;
- apagar o artefato de identidade Abiray/Aqua00;
- usar stash, `reset --hard`, `clean` ou force-push;
- fazer merge.

Preserve os não rastreados:

- `rerank/`;
- `runtimes/`;
- `run_bitnet_benchmark.py`;
- `run_light_phase.py`.

## Python e chave

```bash
set -euo pipefail
cd /home/alpha/Playstoria/models-embed-batch2-light

PYTHON=/home/alpha/Playstoria/models/benchmarks/holo-embedding-benchmark-v3/.venv/bin/python
KEY=/home/alpha/Playstoria/models/.voyage4_token

"$PYTHON" --version
test -s "$KEY"
```

Não exiba o conteúdo da chave.

## 1. Confirmar estado Git

```bash
git remote get-url origin
git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse origin/exec/embed-rerank-batch2-light
```

Pare diante de branch, HEAD ou alterações rastreadas inesperadas.

## 2. Validação inicial

```bash
cd benchmark/embedding-v3

"$PYTHON" validate_governance.py
"$PYTHON" -m unittest discover -s tests -p 'test_*.py'
"$PYTHON" -m compileall -q .
"$PYTHON" validate_coverage.py
git diff --check
```

Critérios:

- pelo menos 242 testes;
- zero falhas e erros;
- todos os comandos com exit 0.

Confirme a existência de:

- `results/gate3/nemotron_8b_abiray_q4_audit_4096.json`;
- `results/gate3/nemotron_8b_abiray_q4_audit_1024.json`;
- candidates correspondentes;
- pipelines Qwen correspondentes;
- artefato de auditoria integral;
- bloqueio provisório Voyage.

## 3. Submeter o Batch Voyage

O runner cria exatamente 150 requisições JSONL, uma por consulta. Cada requisição contém a união dos candidates top 20 das duas dimensões. O mapeamento de saída usa `custom_id`, nunca a ordem das linhas.

Execute:

```bash
"$PYTHON" -m holo_benchmark.voyage_abiray_batch submit \
  --api-key-path "$KEY"
```

O comando deve:

1. gerar o JSONL apenas em diretório temporário;
2. fazer upload pela Files API com `purpose=batch`;
3. criar um batch com:
   - endpoint `/v1/rerank`;
   - modelo `rerank-2.5`;
   - `completion_window=12h`;
   - `top_k=20`;
   - `return_documents=false`;
   - `truncation=true`;
4. gravar o checkpoint:
   - `results/raw/reranker/voyage_rerank_2_5_nemotron_8b_abiray_batch.json`.

Registre o `batch_id`, `input_file_id`, status inicial e contagem de 150 requisições. Não use `--force` salvo se o checkpoint não possuir `batch_id` válido e houver evidência de que nenhuma submissão foi criada.

## 4. Consultar o Batch

Consulte com:

```bash
"$PYTHON" -m holo_benchmark.voyage_abiray_batch status \
  --api-key-path "$KEY"
```

Enquanto o status for `validating`, `in_progress` ou `finalizing`, aguarde cinco minutos e consulte novamente. Não crie outro batch.

Estados terminais aceitos para coleta:

- somente `completed` permite gerar resultados;
- `partially_completed`, `failed`, `expired`, `cancelled` ou `canceled` devem ser reportados com `request_counts`, `error_file_id` e erro exato, sem consolidar resultados parciais.

## 5. Coletar resultados

Quando o batch estiver `completed`, execute:

```bash
"$PYTHON" -m holo_benchmark.voyage_abiray_batch collect \
  --api-key-path "$KEY"
```

O comando deve:

- baixar o output JSONL pela Files API;
- exigir 150 `custom_id` únicos;
- exigir status HTTP 200 em todas as respostas;
- rejeitar qualquer linha com `error`;
- exigir score para todos os candidates da união;
- gerar:
  - `results/reranker/scores/voyage_rerank_2_5_nemotron_8b_abiray.json`;
  - `results/reranker/pipelines/voyage_rerank_2_5/nemotron_8b_abiray_q4_audit_4096.json`;
  - `results/reranker/pipelines/voyage_rerank_2_5/nemotron_8b_abiray_q4_audit_1024.json`;
- remover o artefato provisório `BLOCKED_RATE_LIMIT`;
- atualizar o checkpoint para `COLLECTED`.

Não versionar o JSONL temporário baixado. Os scores e pipelines portáveis são a evidência versionada.

## 6. Regenerar consolidado e README

Depois da coleta bem-sucedida:

```bash
SOURCE_COMMIT="$(git rev-parse HEAD)"

"$PYTHON" -m holo_benchmark.nemotron_8b_abiray_finalize finalize \
  --source-commit "$SOURCE_COMMIT" \
  --revision 2026-07-30
```

O finalizador deve detectar automaticamente os dois pipelines Voyage e produzir:

- 107 pipelines publicados;
- 36 embeddings únicos;
- 39 perfis raw;
- 11 pipelines Voyage;
- 36 pipelines Qwen;
- status canônico `PASS`;
- README com os dois perfis Abiray e sem Aqua00/IDs legados.

## 7. Validação final

```bash
"$PYTHON" validate_governance.py
"$PYTHON" -m unittest discover -s tests -p 'test_*.py'
"$PYTHON" -m compileall -q .
"$PYTHON" validate_coverage.py
git diff --check
```

Valide programaticamente:

- todos os JSON parseiam;
- nenhum segredo ou path absoluto foi versionado;
- checkpoint contém `batch_id`, `input_file_id` e `output_file_id`;
- request count total 150, completed 150, failed 0;
- os dois pipelines usam `$.evaluation.reranked_metrics.summary` no consolidado;
- contagens 107/36/39 e Voyage 11/Qwen 36;
- bloqueio provisório removido;
- Aqua00 ausente dos rankings e artefatos publicáveis;
- artefato de identidade preservado;
- não rastreados protegidos intactos.

## 8. Git

Revise:

```bash
git status --short
git diff --stat
git diff --check
git diff -- ALL_BENCHMARK_RESULTS.json README.md
```

O commit pode conter somente:

- checkpoint Batch sanitizado;
- score Voyage Abiray;
- dois pipelines Voyage Abiray;
- remoção do bloqueio provisório;
- `ALL_BENCHMARK_RESULTS.json`;
- `README.md`.

```bash
git add -A -- \
  results/raw/reranker/voyage_rerank_2_5_nemotron_8b_abiray_batch.json \
  results/reranker/voyage_rerank_2_5_nemotron_8b_abiray_blocked.json \
  results/reranker/scores/voyage_rerank_2_5_nemotron_8b_abiray.json \
  results/reranker/pipelines/voyage_rerank_2_5/nemotron_8b_abiray_q4_audit_4096.json \
  results/reranker/pipelines/voyage_rerank_2_5/nemotron_8b_abiray_q4_audit_1024.json \
  ALL_BENCHMARK_RESULTS.json \
  README.md

git commit -m "Complete Abiray reranking through Voyage Batch API"
git push origin exec/embed-rerank-batch2-light
```

Não faça merge.

## 9. Retorno obrigatório

Informe:

1. HEAD inicial e final completos;
2. `batch_id`, `input_file_id`, `output_file_id` e status final;
3. timestamps de criação, início, finalização e conclusão;
4. request counts total/completed/failed;
5. tokens e custo quando fornecidos pela API; não estimar como cobrança real;
6. arquivos adicionados, alterados e removidos;
7. métricas Voyage dos perfis 4096 e 1024:
   - MRR@10;
   - HR@1;
   - HR@10;
   - nDCG@10;
   - hard-negative error;
8. comparação raw, Qwen e Voyage;
9. ranking global atualizado;
10. contagens finais 107/36/39, Voyage 11 e Qwen 36;
11. testes e validações;
12. PR aberto, draft, sem merge e não rastreados preservados.

Versão esperada do retorno:

`2.2.14 — Voyage Batch concluído para Abiray 4096/1024 e consolidado regenerado`
