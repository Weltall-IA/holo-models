# EMBED-RERANK-BATCH-2 — INSTRUCTIONS v2.2.14.2

## Objetivo

Corrigir exclusivamente o estado canônico residual do Voyage Nemotron 8B após a coleta Batch concluída no commit `38528f83fe187c0e6eb8cd4f7b5042f5cff1b10a`.

O benchmark já está executado e publicado com 107 pipelines e 11 pipelines Voyage. Não executar API, batch, embedding ou reranker novamente.

## Estado obrigatório

- repositório: `Weltall-IA/holo-models`;
- worktree: `/home/alpha/Playstoria/models-embed-batch2-light`;
- branch: `exec/embed-rerank-batch2-light`;
- PR: #20, aberto, draft, sem merge;
- HEAD inicial: SHA completo informado no handoff.

Leia integralmente `AGENTS.md`, `.ai/PROJECT.yml`, `.ai/WORKFLOW.yml`, `benchmark/embedding-v3/AGENTS.md`, as instruções v2.2.14 e v2.2.14.1, este arquivo e o diff atual do PR.

Preserve os não rastreados `rerank/`, `runtimes/`, `run_bitnet_benchmark.py` e `run_light_phase.py`. Não use stash, clean, reset destrutivo ou force-push.

## Defeito confirmado

`benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json` já registra:

- 107 pipelines publicados;
- 11 pipelines `voyage_rerank_2_5`;
- dois pipelines Voyage Abiray existentes;

mas o bloco `voyage_nemotron_8b_status` ainda contém:

- `status: BLOCKED_RATE_LIMIT`;
- referência ao artefato `voyage_rerank_2_5_nemotron_8b_abiray_blocked.json`, que foi removido;
- `published_pipeline_count: 0`.

Isso é inconsistente e deve ser corrigido na fonte de geração, não apenas manualmente no JSON.

## Alterações obrigatórias

1. Ajustar `benchmark/embedding-v3/holo_benchmark/nemotron_8b_abiray_finalize.py` para, após confirmar os dois pipelines Voyage, substituir no documento consolidado o bloco `voyage_nemotron_8b_status` por um estado concluído contendo pelo menos:
   - `status: COMPLETED_BATCH`;
   - `backend: voyage_batch_api`;
   - `model: rerank-2.5`;
   - `published_pipeline_count: 2`;
   - IDs das duas variantes Abiray;
   - caminho do score Voyage Abiray;
   - caminho do checkpoint Batch;
   - `partial_union_scoring: true`;
   - `top_k: 20`;
   - política dos não pontuados: anexar em ordem base estável.
2. Remover qualquer referência canônica ao arquivo bloqueado inexistente.
3. Atualizar a descrição da variante Abiray 1024 na README para não dizer apenas “comparar Qwen e Voyage”; a comparação já ocorreu. Registrar objetivamente que Qwen e Voyage empataram em MRR@10 arredondado (~0,7907), enquanto 4096 + Voyage atingiu ~0,8267.
4. Regenerar `ALL_BENCHMARK_RESULTS.json` e `README.md` usando o finalizador corrigido, sem alterar métricas ou artefatos individuais.
5. Adicionar teste que falhe se:
   - existem 11 pipelines Voyage e o status ainda é bloqueado;
   - o bloco aponta para artefato inexistente;
   - `published_pipeline_count` diverge de 2 para o escopo Nemotron 8B.

## Validação

Executar:

```bash
PYTHON=/home/alpha/Playstoria/models/benchmarks/holo-embedding-benchmark-v3/.venv/bin/python
cd /home/alpha/Playstoria/models-embed-batch2-light/benchmark/embedding-v3

"$PYTHON" validate_governance.py
"$PYTHON" -m unittest discover -s tests -p 'test_*.py'
"$PYTHON" -m compileall -q .
"$PYTHON" validate_coverage.py
"$PYTHON" tools/consolidate_all_benchmark_results.py --validate-only
git diff --check
```

Validar programaticamente:

- consolidado `validation.status == PASS`;
- pipelines 107;
- embeddings 36;
- raw profiles 39;
- Voyage 11;
- Qwen 36;
- `voyage_nemotron_8b_status.status == COMPLETED_BATCH`;
- `voyage_nemotron_8b_status.published_pipeline_count == 2`;
- nenhuma referência a `voyage_rerank_2_5_nemotron_8b_abiray_blocked.json`;
- os dois pipelines Voyage Abiray presentes;
- Aqua00 ausente dos rankings;
- identity audit preservado.

## Git

O commit pode conter somente:

- correção do finalizador;
- teste de regressão;
- `ALL_BENCHMARK_RESULTS.json`;
- `README.md`.

Commit sugerido:

```bash
git add benchmark/embedding-v3/holo_benchmark/nemotron_8b_abiray_finalize.py \
  benchmark/embedding-v3/tests \
  benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json \
  benchmark/embedding-v3/README.md
git commit -m "Close Voyage batch status for canonical Abiray results"
git push origin exec/embed-rerank-batch2-light
```

Não fazer merge.

## Retorno obrigatório

Informar HEAD inicial/final, arquivos alterados, bloco canônico final, métricas Abiray raw/Qwen/Voyage, contagens 107/36/39/11/36, testes, PR draft e ausência de merge.

Versão esperada:

`2.2.14.2 — estado Voyage Batch fechado e consolidado canônico consistente`
