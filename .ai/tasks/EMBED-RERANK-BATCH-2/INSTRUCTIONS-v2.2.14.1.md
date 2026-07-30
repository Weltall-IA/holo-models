# EMBED-RERANK-BATCH-2 — INSTRUCTIONS v2.2.14.1

## Objetivo

Coletar o batch Voyage já concluído, usando o parser corrigido para respostas `top_k=20` sobre uniões de até 33 candidatos; gerar os dois pipelines Voyage Abiray; atualizar o consolidado de 105 para 107 pipelines; atualizar a README; validar, commitar e fazer push sem merge.

Não submeta novo batch. Não chame o endpoint síncrono. Reutilize exclusivamente o `batch_id`, `input_file_id` e `output_file_id` já registrados no checkpoint existente.

## Estado Git obrigatório

- repositório: `Weltall-IA/holo-models`;
- worktree: `/home/alpha/Playstoria/models-embed-batch2-light`;
- branch: `exec/embed-rerank-batch2-light`;
- PR: #20, aberto, draft e sem merge;
- HEAD inicial: o SHA completo informado no handoff.

Preserve os não rastreados `rerank/`, `runtimes/`, `run_bitnet_benchmark.py` e `run_light_phase.py`.

Não use stash, `reset --hard`, `clean`, force-push ou merge.

## Leitura obrigatória

Leia integralmente:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.14.md`;
6. este arquivo;
7. `benchmark/embedding-v3/holo_benchmark/voyage_abiray_batch.py`;
8. `benchmark/embedding-v3/holo_benchmark/voyage_abiray_batch_collect.py`;
9. `benchmark/embedding-v3/holo_benchmark/nemotron_8b_abiray_finalize.py`;
10. descrição e diff atuais do PR #20.

## Correção aplicada

A API retorna somente `min(top_k, union_size)` resultados. Com `top_k=20`, uniões de 21 a 33 candidatos deixam candidatos intencionalmente sem score.

O coletor corrigido:

- exige exatamente 20 resultados quando a união possui mais de 20 candidatos;
- valida índices únicos e dentro da união;
- não inventa scores para candidatos omitidos;
- usa a ordem Voyage para os candidatos retornados;
- anexa candidatos não retornados na ordem base estável de cada embedding;
- registra `partial_union_scoring=true` e a política de fallback no score e nos pipelines.

## Python

```bash
PYTHON=/home/alpha/Playstoria/models/benchmarks/holo-embedding-benchmark-v3/.venv/bin/python
cd /home/alpha/Playstoria/models-embed-batch2-light/benchmark/embedding-v3
```

## 1. Validação inicial

```bash
"$PYTHON" validate_governance.py
"$PYTHON" -m unittest discover -s tests -p 'test_*.py'
"$PYTHON" -m compileall -q .
"$PYTHON" validate_coverage.py
git diff --check
```

Exija zero falhas. Confirme que o checkpoint Batch possui:

- status `completed` ou equivalente já atualizado;
- 150 requisições concluídas;
- zero falhas;
- `batch_id`;
- `input_file_id`;
- `output_file_id`.

Não imprima a chave API.

## 2. Coletar o batch concluído

Execute uma única vez:

```bash
"$PYTHON" -m holo_benchmark.voyage_abiray_batch_collect \
  --api-key-path /home/alpha/Playstoria/models/.voyage4_token
```

A coleta deve:

- baixar o output já existente;
- processar 150/150 respostas;
- gerar `results/reranker/scores/voyage_rerank_2_5_nemotron_8b_abiray.json`;
- gerar os pipelines Voyage de Abiray 4096 e 1024;
- remover o artefato provisório `voyage_rerank_2_5_nemotron_8b_abiray_blocked.json`;
- atualizar o checkpoint para `COLLECTED`;
- não criar novo batch nem novo input file.

Valide programaticamente:

- cada resposta contém exatamente `min(20, union_size)` scores;
- índices únicos, válidos e pertencentes à união;
- 150 queries presentes;
- zero respostas com erro;
- os dois pipelines contêm 150 linhas de `per_query` em base e reranked;
- `partial_union_scoring` é verdadeiro;
- `unscored_policy` é `append in stable base-embedding order`;
- nenhum score sintético foi gravado.

## 3. Regenerar o consolidado final

Use o finalizador existente agora que os dois pipelines Voyage existem:

```bash
SOURCE_COMMIT="$(git rev-parse HEAD)"
"$PYTHON" -m holo_benchmark.nemotron_8b_abiray_finalize finalize \
  --source-commit "$SOURCE_COMMIT" \
  --revision 2026-07-30
```

O resultado obrigatório é:

- pipelines publicados: 107;
- embeddings únicos: 36;
- raw profiles: 39;
- Voyage: 11;
- Qwen: 36;
- Abiray 4096 e 1024 presentes em raw, Qwen e Voyage;
- Aqua00 ausente dos rankings e artefatos publicáveis;
- auditoria integral Abiray/Aqua00 preservada;
- consolidado `PASS`;
- README atualizada.

## 4. Validação final

```bash
"$PYTHON" validate_governance.py
"$PYTHON" -m unittest discover -s tests -p 'test_*.py'
"$PYTHON" -m compileall -q .
"$PYTHON" validate_coverage.py
"$PYTHON" tools/consolidate_all_benchmark_results.py --validate-only
"$PYTHON" tools/update_canonical_readme_tables.py --validate-only --revision 2026-07-30
git diff --check
```

Se o validador histórico falhar exclusivamente por constantes 105/9, registre o defeito antigo; a validação interna do finalizador deve passar em 107/11.

## 5. Git

Revise todos os arquivos antes do commit. Não inclua chave, pesos, caches ou não rastreados protegidos.

```bash
git add -A -- benchmark/embedding-v3/results benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json benchmark/embedding-v3/README.md
git commit -m "Collect Voyage batch and publish Abiray rerank results"
git push origin exec/embed-rerank-batch2-light
```

Não faça merge.

## Retorno obrigatório

Informe:

1. HEAD inicial e final completos;
2. batch_id, input_file_id e output_file_id parcialmente mascarados;
3. confirmação de que nenhum batch novo foi submetido;
4. requests concluídas/falhas;
5. distribuição de tamanhos das uniões e quantidade média de scores retornados;
6. métricas Voyage 4096 e 1024: MRR@10, HR@1, HR@10, nDCG@10 e hard-negative error;
7. comparação raw/Qwen/Voyage;
8. arquivos adicionados, alterados e removidos;
9. contagens 107/36/39, Voyage 11 e Qwen 36;
10. testes e validações;
11. PR draft, sem merge e não rastreados preservados.

Versão esperada:

`2.2.14.1 — Voyage Batch coletado com top-k parcial, pipelines Abiray publicados e consolidado 107/11`
