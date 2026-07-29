# INSTRUCTIONS v2.2.11 — consolidação canônica final do lote

## Estado e objetivo

A execução NVIDIA Nemotron da v2.2.10.1 está concluída no commit `8786f05cedbba45fc83a558774256b78b2f45789`:

- runtime isolado `vLLM 0.25.1`;
- modelo `nvidia/llama-nemotron-rerank-1b-v2` na revisão `d896ceda696c5c6fe0abf65f63a77c691bbf4548`;
- peso de `2471649792` bytes e SHA-256 `7d60ff24db62fe6a639c4c6f4aeac3a3b32ed20939ab72a0be4b019c2219e5e0`;
- template oficial e smoke semântico aprovados;
- seis scores e seis pipelines canônicos;
- `222/222` testes;
- servidor encerrado e porta liberada.

Esta é a etapa final obrigatória do lote. Ela deve:

1. validar novamente todo o repositório e os artefatos individuais já fechados;
2. regenerar `benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json` a partir dos artefatos versionados;
3. atualizar exclusivamente a data de revisão e as duas tabelas canônicas de `benchmark/embedding-v3/README.md`;
4. validar os totais, líderes, separação raw/reranked e portabilidade;
5. commitar exatamente esses dois arquivos gerados;
6. manter o PR aberto e draft, sem merge.

Esta etapa não executa benchmarks, não inicia servidores, não carrega modelos e não realiza downloads.

## Repositório, branch e PR

- repositório: `Weltall-IA/holo-models`;
- worktree: `/home/alpha/Playstoria/models-embed-batch2-light`;
- branch: `exec/embed-rerank-batch2-light`;
- PR: `#20`, aberto e draft;
- HEAD inicial: deve coincidir exatamente com o SHA completo informado no handoff;
- nenhum merge é autorizado.

## Leitura obrigatória

Leia integralmente, nesta ordem:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`;
6. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.10.1.md`;
7. esta instrução;
8. diff completo do PR #20.

A IA local pode somente inspecionar, executar testes e os dois geradores versionados, validar, commitar os dois arquivos autorizados e fazer push no mesmo branch.

A IA local não pode editar código, testes, configuração, instruções ou qualquer artefato individual.

## Proibições

- não executar embeddings ou rerankers;
- não iniciar vLLM, llama.cpp, Ollama, LM Studio ou qualquer servidor;
- não baixar pesos, arquivos de modelo ou pacotes;
- não chamar APIs;
- não alterar arquivos em `results/gate2/`, `results/gate3/` ou `results/reranker/`;
- não alterar candidates, scores ou pipelines;
- não alterar o artefato histórico `llama_nemotron_rerank_1b_v2_blocked.json`;
- não criar leaderboard, registry, blacklist, relatório ou resumo paralelo;
- não editar manualmente o consolidado ou a README;
- não usar `reset --hard`, `clean`, `checkout --`, stash automático ou force-push;
- não incluir arquivos não rastreados preexistentes;
- não fazer merge.

## 1. Atualização segura

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
printf 'HEAD após pull: %s\n' "$(git rev-parse HEAD)"
test -f .ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.11.md
```

Confirme que o remote corresponde inequivocamente a `Weltall-IA/holo-models` e que o HEAD coincide com o handoff. Em divergência, pare.

Preserve sem inclusão no commit:

- `rerank/`;
- `run_bitnet_benchmark.py`;
- `run_light_phase.py`;
- `runtimes/`.

Confirme que nenhum servidor do lote permanece ativo:

```bash
ps -eo pid,ppid,cmd | grep -E 'vllm|llama.*nemotron|rerank.*8099' | grep -v grep || true
ss -ltnp | grep ':8099' || true
```

A porta `8099` deve estar livre. Não inicie nem encerre processos nesta etapa.

## 2. Proteção integral dos artefatos individuais

Antes de executar os geradores, grave os hashes de todos os arquivos rastreados sob:

- `benchmark/embedding-v3/results/gate2/`;
- `benchmark/embedding-v3/results/gate3/`;
- `benchmark/embedding-v3/results/reranker/`.

```bash
find \
  benchmark/embedding-v3/results/gate2 \
  benchmark/embedding-v3/results/gate3 \
  benchmark/embedding-v3/results/reranker \
  -type f -print0 \
  | sort -z \
  | xargs -0 sha256sum \
  > /tmp/embed-rerank-v2211-individual-before.sha256

sha256sum benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json \
  > /tmp/embed-rerank-v2211-all-before.sha256
sha256sum benchmark/embedding-v3/README.md \
  > /tmp/embed-rerank-v2211-readme-before.sha256
```

Os artefatos individuais devem permanecer byte a byte idênticos até o final. Apenas consolidado e README podem mudar.

## 3. Ambiente Python e testes

Use o interpretador aprovado do benchmark:

```bash
PYTHON=/home/alpha/Playstoria/models/benchmarks/holo-embedding-benchmark-v3/.venv/bin/python
test -x "$PYTHON"
export PYTHONPATH="$PWD/benchmark/embedding-v3${PYTHONPATH:+:$PYTHONPATH}"

"$PYTHON" --version
"$PYTHON" - <<'PY'
import holo_benchmark
print(holo_benchmark.__file__)
PY
```

Execute antes da geração:

```bash
"$PYTHON" .ai/validate_governance.py

"$PYTHON" -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_consolidate_all_benchmark_results.py' -v

"$PYTHON" -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_update_canonical_readme_tables.py' -v

"$PYTHON" -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_artifact_portability.py' -v

"$PYTHON" -m unittest discover -s benchmark/embedding-v3/tests -v
"$PYTHON" -m compileall -q benchmark/embedding-v3

git diff --check
```

Resultados esperados:

- consolidação: `4/4` PASS;
- atualização README: `3/3` PASS;
- portabilidade: `7/7` PASS;
- suíte integral: pelo menos `229` testes, zero failures e zero errors;
- governance, compileall e diff check: exit code `0`.

Em qualquer falha, pare e reporte. Não edite código.

## 4. Regeneração do consolidado

Registre o SHA completo atual para proveniência:

```bash
SOURCE_COMMIT="$(git rev-parse HEAD)"
test "${#SOURCE_COMMIT}" = 40
```

Execute somente o gerador versionado:

```bash
"$PYTHON" benchmark/embedding-v3/tools/consolidate_all_benchmark_results.py \
  --source-commit "$SOURCE_COMMIT"
```

O comando deve terminar com `status: PASS` e produzir exatamente:

- 105 pipelines publicados;
- 36 embeddings com pipeline;
- 8 rerankers;
- 39 perfis raw;
- 144 registros totais.

Contagens obrigatórias por reranker:

```text
jina_reranker_v3_noncommercial: 12
kalm_reranker_v1_nano: 12
kalm_reranker_v1_small: 12
llama_nemotron_rerank_1b_v2: 6
mxbai_rerank_base_v2: 6
querit_reranker_4b: 12
qwen_local: 36
voyage_rerank_2_5: 9
```

Contagens obrigatórias dos perfis raw:

```text
gate2: 11
gate3: 19
voyage_raw: 2
nemotron_admission: 2
historical_raw_none: 5
```

O gerador deve usar `$.evaluation.reranked_metrics.summary` sempre que o pipeline possuir esse campo. Métricas base e reranqueadas não podem ser misturadas.

## 5. Atualização controlada das duas tabelas README

Execute somente:

```bash
"$PYTHON" benchmark/embedding-v3/tools/update_canonical_readme_tables.py \
  --revision 2026-07-29
```

O resultado deve informar:

- `table1_rows`: 30;
- `table2_rows`: 9;
- `revision`: `2026-07-29`;
- `status`: `PASS`.

O diff da README pode conter somente:

1. a linha `Revisão desta classificação`;
2. a Tabela 1;
3. a Tabela 2.

Nenhum outro parágrafo, seção, link ou regra pode mudar.

## 6. Validação semântica do consolidado

Execute:

```bash
"$PYTHON" - <<'PY'
import json
from pathlib import Path

path = Path('benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json')
data = json.loads(path.read_text(encoding='utf-8'))

assert data['schema_version'] == '2.0.0'
assert data['validation']['status'] == 'PASS'
assert all(data['validation']['checks'].values())
assert data['canonical_scope']['published_pipeline_artifacts'] == 105
assert data['canonical_scope']['unique_embeddings'] == 36
assert data['canonical_scope']['rerankers'] == 8
assert data['canonical_scope']['raw_embedding_profiles'] == 39
assert data['canonical_scope']['benchmark_records_total'] == 144

expected = {
    'jina_reranker_v3_noncommercial': 12,
    'kalm_reranker_v1_nano': 12,
    'kalm_reranker_v1_small': 12,
    'llama_nemotron_rerank_1b_v2': 6,
    'mxbai_rerank_base_v2': 6,
    'querit_reranker_4b': 12,
    'qwen_local': 36,
    'voyage_rerank_2_5': 9,
}
assert data['inventory']['published_pipeline_count_by_reranker'] == expected

leader = data['leaders_published']['best_by_mrr_at_10']
assert leader['pipeline_id'] == (
    'qwen3_embedding_4b_q8_0__llama_nemotron_rerank_1b_v2'
)
assert leader['metric_summary_path'] == '$.evaluation.reranked_metrics.summary'
assert leader['metrics']['mrr_at_10'] == 0.8325555555555556
assert leader['metrics']['ndcg_at_10'] == 0.8361353976752077

raw = data['raw_embedding_profiles_by_id']
for profile in (
    'lfm_25_embedding_350m_q4_k_m_official',
    'bitnet_06b_current',
    'bitnet_270m_current',
    'nemotron_3_embed_1b_nvfp4',
    'qwen3_embedding_8b_gguf',
):
    assert profile in raw

assert raw['lfm_25_embedding_350m_q4_k_m_official']['metrics']['mrr_at_10'] == 0.6085343915343916
assert raw['bitnet_06b_current']['metrics']['mrr_at_10'] == 0.20891534391534392
assert raw['bitnet_270m_current']['metrics']['mrr_at_10'] == 0.301457671957672

serialized = json.dumps(data, ensure_ascii=False)
assert '/home/alpha/' not in serialized
assert 'C:\\Users\\' not in serialized

nvidia = [
    item
    for item in data['published_pipelines_ranked_by_mrr_at_10']
    if item['reranker'] == 'llama_nemotron_rerank_1b_v2'
]
assert len(nvidia) == 6
assert all(item['metadata']['runtime']['endpoint'] == '/rerank' for item in nvidia)
assert all(item['metadata']['runtime']['backend_version'] == '0.25.1' for item in nvidia)
assert all(item['metadata']['runtime']['semantic_smoke']['status'] == 'PASS' for item in nvidia)

print('CANONICAL_VALIDATION_PASS')
print('leader', leader['pipeline_id'], leader['metrics']['mrr_at_10'])
print('raw_profiles', len(raw))
PY
```

Se qualquer asserção falhar, pare e reporte. Não edite manualmente o JSON.

## 7. Validação das tabelas README

Execute:

```bash
"$PYTHON" - <<'PY'
from pathlib import Path

text = Path('benchmark/embedding-v3/README.md').read_text(encoding='utf-8')
assert text.count('### Tabela 1 — embeddings bons ou reutilizáveis') == 1
assert text.count('### Tabela 2 — blacklist de artefatos e configurações') == 1
assert 'Revisão desta classificação: **2026-07-29**.' in text

required = (
    '| `nemotron_3_embed_1b_nvfp4` | 0.7753 | 0.8318 |',
    '| `voyage-context-4` | 0.7433 | 0.7887 |',
    '| `nomic_embed_text_v2_moe_q4` | 0.7420 | 0.8320 |',
    '| `embeddinggemma` | 0.7562 | 0.8299 |',
    '| `qwen3_embedding_4b_q8_0` | 0.7010 | 0.8326 |',
    '| `colibri_ptbr` | 0.6966 | 0.8305 |',
    '| `granite_embedding_311m_r2` | 0.6709 | 0.8185 |',
    '| `lfm_25_embedding_350m_q4_k_m_official` | 0.6085 | 0.7768 |',
    '| `bitnet_270m_current` | 0.3015 | `GATE_FAIL` |',
    '| `bitnet_06b_current` | 0.2089 | `GATE_FAIL` |',
)
for fragment in required:
    assert fragment in text, fragment

assert '| `bitnet_270m` | — | `BLOCKED` |' not in text
assert '| `bitnet_06b` | — | `BLOCKED` |' not in text
print('README_TABLES_VALIDATION_PASS')
PY
```

## 8. Proteções e diff final

Confirme que os artefatos individuais não mudaram:

```bash
sha256sum -c /tmp/embed-rerank-v2211-individual-before.sha256
```

O status deve mostrar somente os arquivos não rastreados preexistentes e os dois arquivos autorizados modificados:

```bash
git status --short
git diff --name-only
```

Arquivos rastreados modificados esperados, exatamente:

```text
benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json
benchmark/embedding-v3/README.md
```

Valide:

```bash
test "$(git diff --name-only | sort)" = "$(printf '%s\n' \
  benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json \
  benchmark/embedding-v3/README.md \
  | sort)"

git diff --check
"$PYTHON" -m unittest discover -s benchmark/embedding-v3/tests -v
"$PYTHON" .ai/validate_coverage.py
```

A suíte final deve continuar com pelo menos `229` testes e zero falhas.

Revise o diff completo dos dois arquivos. Não aceite:

- redução ou desaparecimento de pipelines existentes;
- líder calculado com métricas base;
- ausência dos seis pipelines Mixedbread ou NVIDIA;
- ausência de LFM oficial ou BitNet current nos perfis raw;
- caminhos absolutos locais;
- alteração de texto da README fora da data e das duas tabelas;
- criação de fonte canônica paralela.

## 9. Commit e push

Somente após todas as validações:

```bash
git add \
  benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json \
  benchmark/embedding-v3/README.md

git diff --cached --name-only
```

O índice deve conter exatamente os dois arquivos autorizados.

Commit:

```text
Regenerate canonical benchmark results and README tables
```

Depois:

```bash
git commit -m "Regenerate canonical benchmark results and README tables"
git push origin exec/embed-rerank-batch2-light
```

Não faça merge e não marque o PR como ready.

## 10. Retorno obrigatório

Título:

```text
Retorno v2.2.11 — consolidação canônica final do lote
```

Inclua:

1. HEAD inicial e SHA completo do commit final;
2. status antes e depois, incluindo não rastreados preservados;
3. interpretador e versão Python;
4. todos os comandos relevantes e exit codes;
5. contagens dos testes focados e da suíte completa;
6. SHA-256 anterior e novo de `ALL_BENCHMARK_RESULTS.json` e README;
7. contagens 105 pipelines, 36 embeddings, 8 rerankers, 39 raw e 144 totais;
8. contagem por reranker e por fonte raw;
9. pipeline líder e suas métricas completas;
10. melhores pipelines dos perfis alterados na Tabela 1;
11. métricas e estado dos dois BitNet current;
12. comprovação de que os artefatos individuais permaneceram idênticos;
13. comprovação de que somente consolidado e README foram commitados;
14. confirmação de ausência de benchmark, servidor, download, API, edição manual e merge;
15. estado do PR #20, que deve permanecer aberto e draft.
