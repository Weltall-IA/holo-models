# EMBED-RERANK-BATCH-2 — INSTRUCTIONS v2.2.13.1

## Objetivo

Concluir a seleção canônica do mirror Abiray mesmo com Voyage Rerank 2.5 bloqueado por rate limit externo.

Voyage não é pré-requisito para:

- remover Aqua00 dos artefatos publicáveis e rankings;
- remover os resultados legados ambíguos de Abiray/Aqua00;
- regenerar `ALL_BENCHMARK_RESULTS.json`;
- atualizar as duas tabelas canônicas da README;
- validar e commitar a deduplicação.

O bloqueio Voyage deve permanecer registrado como `BLOCKED_RATE_LIMIT`, sem métricas estimadas e sem pipeline fictício.

## Estado obrigatório

- repositório: `Weltall-IA/holo-models`;
- worktree: `/home/alpha/Playstoria/models-embed-batch2-light`;
- branch: `exec/embed-rerank-batch2-light`;
- PR: #20 aberto, draft e sem merge;
- HEAD inicial: SHA completo informado no handoff.

Preserve integralmente:

- `rerank/`;
- `runtimes/`;
- `run_bitnet_benchmark.py`;
- `run_light_phase.py`.

Não use stash, `reset --hard`, `clean`, checkout destrutivo ou force-push.

## Leitura obrigatória

Leia integralmente, nesta ordem:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`;
6. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.13.md`;
7. este arquivo;
8. descrição e diff atuais do PR #20.

## Responsabilidade

A IA executora pode apenas:

- atualizar a worktree por fast-forward;
- executar testes e validações;
- executar o finalizador opcional versionado;
- revisar os arquivos gerados e removidos;
- commitar e fazer push dos resultados autorizados.

Não pode:

- editar código, testes, instruções, configuração ou métricas;
- tentar Voyage novamente nesta etapa;
- executar embeddings ou rerankers;
- criar pipelines Voyage vazios ou estimados;
- remover o artefato de identidade Abiray/Aqua00;
- fazer merge.

Falha de código deve ser reportada ao gerente.

## 1. Atualização e validação inicial

```bash
set -euo pipefail
cd /home/alpha/Playstoria/models-embed-batch2-light

git remote get-url origin
git branch --show-current
git status --short
git rev-parse HEAD

git fetch origin --prune
git pull --ff-only origin exec/embed-rerank-batch2-light

test "$(git branch --show-current)" = "exec/embed-rerank-batch2-light"
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/exec/embed-rerank-batch2-light)"
```

Use:

```bash
PYTHON=/home/alpha/Playstoria/models/benchmarks/holo-embedding-benchmark-v3/.venv/bin/python
cd benchmark/embedding-v3

"$PYTHON" validate_governance.py
"$PYTHON" -m unittest -v tests.test_nemotron_8b_abiray_finalize_optional
"$PYTHON" -m unittest discover -s tests -p 'test_*.py'
"$PYTHON" -m compileall -q .
"$PYTHON" validate_coverage.py
git diff --check
```

Critérios:

- teste dedicado: 2/2;
- suíte integral: pelo menos 237 testes;
- zero falhas e erros;
- todas as validações com exit 0.

## 2. Confirmar o bloqueio Voyage

Não chamar a API novamente.

Confirme que não existem os dois pipelines completos:

- `results/reranker/pipelines/voyage_rerank_2_5/nemotron_8b_abiray_q4_audit_4096.json`;
- `results/reranker/pipelines/voyage_rerank_2_5/nemotron_8b_abiray_q4_audit_1024.json`.

Confirme o bloqueio observado anteriormente:

- `voyageai.error.RateLimitError`;
- conta gratuita;
- limite informado de 3 RPM e 10K TPM;
- duas tentativas;
- cooldown de cinco minutos;
- nenhum pipeline Voyage completo produzido.

Remova somente arquivos Voyage parciais desta tentativa quando forem claramente incompletos e não rastreados. Não remova nenhum dos nove pipelines Voyage históricos.

## 3. Finalizar sem Voyage

Obtenha o SHA de entrada:

```bash
SOURCE_COMMIT="$(git rev-parse HEAD)"
```

Execute:

```bash
"$PYTHON" -m holo_benchmark.nemotron_8b_abiray_finalize_optional \
  --source-commit "$SOURCE_COMMIT" \
  --revision 2026-07-30
```

Resultado esperado:

- status `PASS_WITH_EXTERNAL_BLOCKER`;
- mirror selecionado: `Abiray/Nemotron-3-Embed-8B-GGUF`;
- Voyage: `BLOCKED_RATE_LIMIT`;
- pipelines totais: 105;
- embeddings únicos: 36;
- raw profiles: 39;
- pipelines Voyage publicados: 9;
- pipelines Qwen publicados: 36.

O finalizador deve:

- manter os dois raw Abiray auditados, 4096 e 1024;
- manter os dois candidates Abiray;
- manter os dois pipelines Qwen Abiray;
- remover raw, candidates e pipelines Qwen Aqua00;
- remover os resultados legados ambíguos Abiray/Aqua00;
- preservar `results/reranker/nemotron_8b_abiray_aqua00_identity_audit.json`;
- criar `results/reranker/voyage_rerank_2_5_nemotron_8b_abiray_blocked.json`;
- regenerar `ALL_BENCHMARK_RESULTS.json` com validação PASS;
- atualizar a README;
- retirar os IDs legados Abiray/Aqua00 da blacklist canônica;
- inserir Abiray 4096 e 1024 na tabela de reutilizáveis;
- registrar explicitamente que Voyage ficou bloqueado por rate limit externo.

## 4. Validação final

Execute:

```bash
"$PYTHON" validate_governance.py
"$PYTHON" -m unittest -v tests.test_nemotron_8b_abiray_finalize_optional
"$PYTHON" -m unittest discover -s tests -p 'test_*.py'
"$PYTHON" -m compileall -q .
"$PYTHON" validate_coverage.py
git diff --check
```

Valide programaticamente:

- todos os JSON parseiam;
- `ALL_BENCHMARK_RESULTS.json` possui status PASS;
- 105 pipelines;
- 36 embeddings;
- 39 raw profiles;
- Voyage 9;
- Qwen 36;
- os rankings não contêm Aqua00 nem os IDs legados ambíguos;
- os dois perfis Abiray auditados estão presentes;
- o artefato de auditoria integral está presente;
- o artefato de bloqueio Voyage está presente;
- nenhum pipeline Voyage novo foi inventado;
- os nove pipelines Voyage históricos permanecem byte a byte idênticos;
- nenhum path absoluto, token ou segredo foi publicado.

O `tools/consolidate_all_benchmark_results.py --validate-only` histórico volta a ser compatível, pois as contagens publicadas permanecem 105 pipelines e 9 Voyage.

## 5. Git

Revise:

```bash
git status --short
git diff --stat
git diff --check
git diff -- benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json benchmark/embedding-v3/README.md
```

O commit deve conter somente:

- remoções explícitas de Aqua00 e resultados legados ambíguos;
- artefato de bloqueio Voyage;
- `ALL_BENCHMARK_RESULTS.json`;
- `README.md`.

Não inclua checkpoint parcial, token, pesos, caches, `rerank/`, `runtimes/` ou outros não rastreados.

```bash
git add -A -- \
  benchmark/embedding-v3/results \
  benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json \
  benchmark/embedding-v3/README.md

git commit -m "Select Abiray mirror and record Voyage rate limit"
git push origin exec/embed-rerank-batch2-light
```

Não faça merge.

## 6. Retorno obrigatório

Informe:

1. HEAD inicial e final completos;
2. arquivos removidos, adicionados e alterados;
3. confirmação de Aqua00 removido dos rankings;
4. confirmação dos dois perfis Abiray preservados;
5. métricas raw e Qwen de 4096 e 1024;
6. Voyage como `BLOCKED_RATE_LIMIT`, sem pipeline publicado;
7. contagens 105/36/39, Voyage 9 e Qwen 36;
8. resultados de testes e validações;
9. não rastreados preservados;
10. PR draft, aberto, sem merge.

Versão esperada:

`2.2.13.1 — Abiray canônico, Aqua00 removido, Voyage bloqueado e consolidação concluída`
