# INSTRUCTIONS v2.2.4 — candidates Nemotron e pipelines Qwen locais

Esta versão sucede a v2.2.3. O LFM2.5 já está concluído e não deve ser executado novamente.

## Objetivo

Materializar candidates canônicos a partir dos rankings top 50 já versionados nos dois artefatos de admissão Nemotron e executar exclusivamente o `Qwen/Qwen3-Reranker-0.6B` local sobre esses candidates.

Perfis desta etapa:

1. `nemotron_3_embed_1b_nvfp4`;
2. `nemotron_3_embed_1b_q4_k_m_gguf`.

Nenhum embedding será executado. Os candidates devem preservar apenas a ordem real dos rankings de admissão, usando `rank`; não devem inventar scores de embedding.

## Estado obrigatório

- Repositório: `Weltall-IA/holo-models`
- Worktree: `/home/alpha/Playstoria/models-embed-batch2-light`
- Branch: `exec/embed-rerank-batch2-light`
- PR: `#20`, aberto e draft
- Não fazer merge.

Leia integralmente, nesta ordem:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`;
6. este arquivo.

## Autoridade e proibições

A IA local está autorizada somente a inspecionar o estado, executar os testes e runners versionados, validar e fazer commit/push dos seis artefatos autorizados.

É proibido:

- editar `.py`, testes, schemas, YAML, JSON ou instruções manualmente;
- executar qualquer embedding;
- executar LFM, BitNet, Mixedbread, mxbai, Nemotron reranker ou outro modelo;
- chamar qualquer API Voyage;
- baixar pesos, tokenizers, configs ou runtimes;
- alterar CUDA, driver, Python, PyTorch, Transformers ou pacotes globais;
- sobrescrever `results/reranker/scores/qwen_local.json`;
- alterar `ALL_BENCHMARK_RESULTS.json` ou README;
- alterar os artefatos de admissão Nemotron;
- tocar nos arquivos não rastreados preexistentes;
- usar force-push;
- fazer merge.

## Retomada e preservação

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
test -f benchmark/embedding-v3/holo_benchmark/admission_candidate.py
test -f benchmark/embedding-v3/holo_benchmark/qwen_candidate_benchmark.py
test -f benchmark/embedding-v3/tests/test_admission_candidate.py
test -f benchmark/embedding-v3/tests/test_qwen_candidate_benchmark.py
```

Preserve sem adicionar ao Git, mover, apagar ou modificar:

- `rerank/`
- `run_bitnet_benchmark.py`
- `run_light_phase.py`
- `runtimes/`

Registre o status antes e depois.

## Caminhos e hashes de proteção

```bash
NV_PROFILE='nemotron_3_embed_1b_nvfp4'
Q4_PROFILE='nemotron_3_embed_1b_q4_k_m_gguf'

NV_SOURCE='benchmark/embedding-v3/results/nemotron_audit_1_0_5/admission_nvfp4_full_cached_20260723.json'
Q4_SOURCE='benchmark/embedding-v3/results/nemotron_audit_1_0_5/admission_gguf_full_20260723_attempt2.json'
GLOBAL_QWEN_SCORE='benchmark/embedding-v3/results/reranker/scores/qwen_local.json'

LFM_RESULT='benchmark/embedding-v3/results/gate3/lfm_25_embedding_350m_q4_k_m_official.json'
LFM_CANDIDATE='benchmark/embedding-v3/results/reranker/candidates/lfm_25_embedding_350m_q4_k_m_official.json'
LFM_SCORE='benchmark/embedding-v3/results/reranker/scores/qwen_local/lfm_25_embedding_350m_q4_k_m_official.json'
LFM_PIPELINE='benchmark/embedding-v3/results/reranker/pipelines/qwen_local/lfm_25_embedding_350m_q4_k_m_official.json'

for path in "$NV_SOURCE" "$Q4_SOURCE" "$GLOBAL_QWEN_SCORE" \
  "$LFM_RESULT" "$LFM_CANDIDATE" "$LFM_SCORE" "$LFM_PIPELINE"; do
  test -f "$path"
done

NV_SOURCE_SHA_BEFORE="$(sha256sum "$NV_SOURCE" | awk '{print $1}')"
Q4_SOURCE_SHA_BEFORE="$(sha256sum "$Q4_SOURCE" | awk '{print $1}')"
GLOBAL_SCORE_SHA_BEFORE="$(sha256sum "$GLOBAL_QWEN_SCORE" | awk '{print $1}')"
LFM_RESULT_SHA_BEFORE="$(sha256sum "$LFM_RESULT" | awk '{print $1}')"
LFM_CANDIDATE_SHA_BEFORE="$(sha256sum "$LFM_CANDIDATE" | awk '{print $1}')"
LFM_SCORE_SHA_BEFORE="$(sha256sum "$LFM_SCORE" | awk '{print $1}')"
LFM_PIPELINE_SHA_BEFORE="$(sha256sum "$LFM_PIPELINE" | awk '{print $1}')"

export NV_PROFILE Q4_PROFILE NV_SOURCE Q4_SOURCE GLOBAL_QWEN_SCORE
export NV_SOURCE_SHA_BEFORE Q4_SOURCE_SHA_BEFORE GLOBAL_SCORE_SHA_BEFORE
export LFM_RESULT LFM_CANDIDATE LFM_SCORE LFM_PIPELINE
export LFM_RESULT_SHA_BEFORE LFM_CANDIDATE_SHA_BEFORE
export LFM_SCORE_SHA_BEFORE LFM_PIPELINE_SHA_BEFORE
```

Artefatos novos esperados:

```bash
NV_CANDIDATE="benchmark/embedding-v3/results/reranker/candidates/${NV_PROFILE}.json"
NV_SCORE="benchmark/embedding-v3/results/reranker/scores/qwen_local/${NV_PROFILE}.json"
NV_PIPELINE="benchmark/embedding-v3/results/reranker/pipelines/qwen_local/${NV_PROFILE}.json"
Q4_CANDIDATE="benchmark/embedding-v3/results/reranker/candidates/${Q4_PROFILE}.json"
Q4_SCORE="benchmark/embedding-v3/results/reranker/scores/qwen_local/${Q4_PROFILE}.json"
Q4_PIPELINE="benchmark/embedding-v3/results/reranker/pipelines/qwen_local/${Q4_PROFILE}.json"

for path in "$NV_CANDIDATE" "$NV_SCORE" "$NV_PIPELINE" \
  "$Q4_CANDIDATE" "$Q4_SCORE" "$Q4_PIPELINE"; do
  test ! -e "$path"
done

export NV_CANDIDATE NV_SCORE NV_PIPELINE Q4_CANDIDATE Q4_SCORE Q4_PIPELINE
```

Se qualquer artefato novo já existir, pare e reporte. Não sobrescreva evidência desconhecida.

## Identidade fixa dos embeddings admitidos

NVFP4:

- backend do artefato: `nvfp4`; runtime registrado: `vllm 0.25.0`;
- peso `model.safetensors`, `1027789672` bytes;
- SHA-256 `f2753954c89055eb679a45b7dfea27a3e05c04ecbdb1f4e6c086180fe8c32bc7`;
- licença `OpenMDW-1.1`; prefixes `passage: ` e `query: `.

GGUF:

- backend do artefato: `gguf`; runtime registrado: `llama.cpp 9972 (c92e806d1)`;
- peso `nemotron-3-embed-1b-q4_k_m.gguf`, `749352096` bytes;
- SHA-256 `9a74166f51dbc280073748fa199bea49283bd21f7f9280f2dec2b4d975ddfd1d`;
- licença `OpenMDW-1.1`; quantização `Q4_K_M`; prefixes `passage: ` e `query: `.

O materializador valida essas identidades, o corpus congelado, a ordem das 150 consultas, 50 IDs únicos por consulta e a reprodução das métricas recuperáveis a partir do top 50.

## Modelo Qwen fixo e offline

```bash
export QWEN_MODEL="$HOME/.cache/huggingface/hub/models--Qwen--Qwen3-Reranker-0.6B/snapshots/e61197ed45024b0ed8a2d74b80b4d909f1255473"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1

test -d "$QWEN_MODEL"
test "$(basename "$QWEN_MODEL")" = 'e61197ed45024b0ed8a2d74b80b4d909f1255473'
test -f "$QWEN_MODEL/model.safetensors"
test "$(stat -c '%s' "$QWEN_MODEL/model.safetensors")" = '1191588280'
test "$(sha256sum "$QWEN_MODEL/model.safetensors" | awk '{print $1}')" = \
  '27cd75a405b9c1b46b59abfd88aaa209e6fed2a1972cde9b70e7659537c5e65b'
```

Qualquer divergência é bloqueio. Não baixe nem substitua nada.

## Testes prévios

```bash
python .ai/validate_governance.py
PYTHONPATH=benchmark/embedding-v3 python -m unittest discover \
  -s benchmark/embedding-v3/tests -p 'test_admission_candidate.py' -v
PYTHONPATH=benchmark/embedding-v3 python -m unittest discover \
  -s benchmark/embedding-v3/tests -p 'test_qwen_candidate_benchmark.py' -v
PYTHONPATH=benchmark/embedding-v3 python -m unittest discover \
  -s benchmark/embedding-v3/tests -v
python -m compileall -q benchmark/embedding-v3
git diff --check
```

Esperado para os testes novos: `7/7` PASS. A suíte integral deve retornar código 0. Se houver falha, pare e reporte o traceback integral sanitizado. Não corrija código.

## Materialização dos candidates

```bash
PYTHONPATH=benchmark/embedding-v3 python -m holo_benchmark.admission_candidate \
  --profile-id "$NV_PROFILE"
PYTHONPATH=benchmark/embedding-v3 python -m holo_benchmark.admission_candidate \
  --profile-id "$Q4_PROFILE"
```

Valide ambos com o loader canônico:

```bash
PYTHONPATH=benchmark/embedding-v3 python - <<'PY'
import reranker_execution

profiles = [
    "nemotron_3_embed_1b_nvfp4",
    "nemotron_3_embed_1b_q4_k_m_gguf",
]
loaded = reranker_execution.load_candidate_payloads(profiles, 50)
assert set(loaded) == set(profiles)
for profile in profiles:
    payload = loaded[profile]
    assert payload["schema_version"] == "1.0"
    assert payload["variant"] == profile
    assert payload["candidate_top_k"] == 50
    assert len(payload["ranking_sha256"]) == 64
    assert payload["ranking_source"]["score_semantics"] == "rank_only"
    assert len(payload["queries"]) == 150
    for row in payload["queries"]:
        candidates = row["candidates"]
        assert len(candidates) == 50
        assert [item["rank"] for item in candidates] == list(range(1, 51))
        ids = [item["chunk_id"] for item in candidates]
        assert len(ids) == len(set(ids))
print({profile: loaded[profile]["ranking_sha256"] for profile in profiles})
PY
```

Registre os dois `ranking_sha256` e os SHA-256 dos candidates. Os artefatos de admissão devem permanecer byte a byte inalterados.

## Execução Qwen — NVFP4

Registre RAM e VRAM livres. Não encerre processos não relacionados.

```bash
PYTHONPATH=benchmark/embedding-v3 python -m holo_benchmark.qwen_candidate_benchmark \
  --profile-id "$NV_PROFILE" \
  --model-path "$QWEN_MODEL" \
  --candidate "$NV_CANDIDATE" \
  --score-output "$NV_SCORE" \
  --pipeline-output "$NV_PIPELINE" \
  --batch-size 8
```

Deve pontuar exatamente 7.500 pares em CUDA. Se falhar, pare antes do segundo perfil e reporte. Não edite nem repita automaticamente.

Após sucesso, confirme que o processo terminou, registre RAM e VRAM livres e não mate processos não relacionados.

## Execução Qwen — GGUF

```bash
PYTHONPATH=benchmark/embedding-v3 python -m holo_benchmark.qwen_candidate_benchmark \
  --profile-id "$Q4_PROFILE" \
  --model-path "$QWEN_MODEL" \
  --candidate "$Q4_CANDIDATE" \
  --score-output "$Q4_SCORE" \
  --pipeline-output "$Q4_PIPELINE" \
  --batch-size 8
```

Também deve pontuar exatamente 7.500 pares em CUDA.

## Validação dos scores e pipelines

Para cada score, valide:

1. schema 1.0, `reranker_id=qwen_local` e identidade Qwen fixada;
2. corpus 600/150 e SHA-256 congelado;
3. variant e ranking SHA-256 idênticos ao candidate;
4. 150 consultas, 50 IDs e 50 scores finitos por consulta;
5. CUDA, 7.500 pares e VRAM positiva;
6. ausência de caminhos absolutos ou identificadores do host.

Para cada pipeline, valide:

1. schema 1.0 e `pipeline_id=<profile>__qwen_local`;
2. identidade e SHA-256 do embedding corretos;
3. ranking SHA-256 idêntico ao candidate;
4. `candidate_top_k=50`, `rerank_top_k=20` e score relativo específico do perfil;
5. `base_metrics.per_query`, `reranked_metrics.per_query` e `per_query_effect` com 150 entradas;
6. ambos os `by_query_type` com os sete tipos;
7. ausência de NaN, infinito, paths absolutos ou identificadores do host;
8. registrar summaries base/reranked, rescue, damage e melhorias de rank.

## Proteções após a execução

```bash
test "$(sha256sum "$NV_SOURCE" | awk '{print $1}')" = "$NV_SOURCE_SHA_BEFORE"
test "$(sha256sum "$Q4_SOURCE" | awk '{print $1}')" = "$Q4_SOURCE_SHA_BEFORE"
test "$(sha256sum "$GLOBAL_QWEN_SCORE" | awk '{print $1}')" = "$GLOBAL_SCORE_SHA_BEFORE"
test "$(sha256sum "$LFM_RESULT" | awk '{print $1}')" = "$LFM_RESULT_SHA_BEFORE"
test "$(sha256sum "$LFM_CANDIDATE" | awk '{print $1}')" = "$LFM_CANDIDATE_SHA_BEFORE"
test "$(sha256sum "$LFM_SCORE" | awk '{print $1}')" = "$LFM_SCORE_SHA_BEFORE"
test "$(sha256sum "$LFM_PIPELINE" | awk '{print $1}')" = "$LFM_PIPELINE_SHA_BEFORE"
```

## Validações posteriores

```bash
python .ai/validate_governance.py
PYTHONPATH=benchmark/embedding-v3 python -m unittest discover \
  -s benchmark/embedding-v3/tests -v
python -m compileall -q benchmark/embedding-v3
python benchmark/embedding-v3/validate_coverage.py
git diff --check
```

Todos devem retornar código 0.

## Commit e push

Os únicos caminhos autorizados no commit são:

- `benchmark/embedding-v3/results/reranker/candidates/nemotron_3_embed_1b_nvfp4.json`;
- `benchmark/embedding-v3/results/reranker/scores/qwen_local/nemotron_3_embed_1b_nvfp4.json`;
- `benchmark/embedding-v3/results/reranker/pipelines/qwen_local/nemotron_3_embed_1b_nvfp4.json`;
- `benchmark/embedding-v3/results/reranker/candidates/nemotron_3_embed_1b_q4_k_m_gguf.json`;
- `benchmark/embedding-v3/results/reranker/scores/qwen_local/nemotron_3_embed_1b_q4_k_m_gguf.json`;
- `benchmark/embedding-v3/results/reranker/pipelines/qwen_local/nemotron_3_embed_1b_q4_k_m_gguf.json`.

```bash
git add -- \
  "$NV_CANDIDATE" "$NV_SCORE" "$NV_PIPELINE" \
  "$Q4_CANDIDATE" "$Q4_SCORE" "$Q4_PIPELINE"
git diff --cached --check
git diff --cached --name-only
```

Pare se houver qualquer outro caminho staged.

```bash
git commit -m 'Materialize Nemotron candidates and Qwen pipelines'
git push origin exec/embed-rerank-batch2-light
```

Mantenha o PR #20 aberto e draft. Não faça merge.

## Retorno obrigatório

Retorne:

1. HEAD inicial e final completos;
2. worktree antes e depois;
3. comandos e exit codes;
4. total de testes, passes, failures e errors;
5. SHA-256 dos artefatos de admissão antes e depois;
6. identidade e SHA-256 do Qwen;
7. ranking SHA-256 e SHA-256 de cada candidate;
8. runtime de cada execução: segundos, pares, RAM e VRAM;
9. summaries base e reranked completos dos dois pipelines;
10. rescue/damage e melhorias de rank dos dois pipelines;
11. SHA-256 dos scores e pipelines;
12. arquivos exatos commitados;
13. confirmação de ausência de downloads, embeddings, Voyage, outros modelos, edição de código, alterações LFM e merge.

Termine exatamente com:

`Versão do retorno da IA local: 2.2.4 — Candidates Nemotron e pipelines Qwen locais`
