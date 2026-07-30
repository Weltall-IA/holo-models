# INSTRUCTIONS v2.2.3 — finalização portátil do LFM e pipeline Qwen canônico

Esta versão sucede a v2.2.2. Não repita o embedding LFM2.5.

## Objetivo

1. sanitizar deterministicamente o bloco `hardware` do resultado LFM2.5 já medido, sem alterar identidade, métricas, runtime ou timestamp da execução;
2. executar exclusivamente `Qwen/Qwen3-Reranker-0.6B` sobre os 50 candidates canônicos das 150 consultas LFM;
3. gerar score dedicado e pipeline canônico schema 1.0, substituindo o pipeline legado somente após sucesso integral.

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

## Proibições

- não editar `.py`, testes, schemas, YAML, JSON ou instruções manualmente;
- não repetir o smoke ou benchmark de embedding LFM;
- não executar BitNet, outros embeddings, outros rerankers ou API Voyage;
- não baixar pesos, tokenizers, configs ou runtimes;
- não alterar CUDA, driver, Python, PyTorch, Transformers ou pacotes globais;
- não sobrescrever `results/reranker/scores/qwen_local.json`;
- não tocar em arquivos não rastreados preexistentes;
- não usar force-push;
- não fazer merge.

## Retomada

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
test -f benchmark/embedding-v3/holo_benchmark/artifact_portability.py
test -f benchmark/embedding-v3/holo_benchmark/lfm_artifact_finalize.py
test -f benchmark/embedding-v3/holo_benchmark/lfm_qwen_benchmark.py
```

Preserve sem adicionar ao Git, mover, apagar ou modificar:

- `rerank/`
- `run_bitnet_benchmark.py`
- `run_light_phase.py`
- `runtimes/`

Registre o status antes e depois.

## Artefatos existentes e hashes de controle

```bash
LFM_RESULT='benchmark/embedding-v3/results/gate3/lfm_25_embedding_350m_q4_k_m_official.json'
LFM_CANDIDATE='benchmark/embedding-v3/results/reranker/candidates/lfm_25_embedding_350m_q4_k_m_official.json'
LFM_PIPELINE='benchmark/embedding-v3/results/reranker/pipelines/qwen_local/lfm_25_embedding_350m_q4_k_m_official.json'
LFM_SCORE='benchmark/embedding-v3/results/reranker/scores/qwen_local/lfm_25_embedding_350m_q4_k_m_official.json'
GLOBAL_QWEN_SCORE='benchmark/embedding-v3/results/reranker/scores/qwen_local.json'

for path in "$LFM_RESULT" "$LFM_CANDIDATE" "$LFM_PIPELINE" "$GLOBAL_QWEN_SCORE"; do
  test -f "$path"
done

test ! -e "$LFM_SCORE"

RESULT_SHA_BEFORE="$(sha256sum "$LFM_RESULT" | awk '{print $1}')"
CANDIDATE_SHA_BEFORE="$(sha256sum "$LFM_CANDIDATE" | awk '{print $1}')"
PIPELINE_SHA_BEFORE="$(sha256sum "$LFM_PIPELINE" | awk '{print $1}')"
GLOBAL_SCORE_SHA_BEFORE="$(sha256sum "$GLOBAL_QWEN_SCORE" | awk '{print $1}')"

export LFM_RESULT LFM_CANDIDATE LFM_PIPELINE LFM_SCORE GLOBAL_QWEN_SCORE
export RESULT_SHA_BEFORE CANDIDATE_SHA_BEFORE PIPELINE_SHA_BEFORE GLOBAL_SCORE_SHA_BEFORE
```

O candidate deve registrar exatamente:

- `variant = lfm_25_embedding_350m_q4_k_m_official`;
- `ranking_sha256 = 3a80b1969d82383386199bcd0877140786b9865f3d74f2f444e192a171630db3`;
- 150 consultas;
- 50 candidates únicos por consulta;
- GGUF SHA-256 `4d7aa9dc6406a10fc3dec2c11f8f06781af063bf49211b8e4132e9b876d3f32a`.

## Modelo Qwen fixo e offline

Use somente o snapshot local exato:

```bash
export QWEN_MODEL="$HOME/.cache/huggingface/hub/models--Qwen--Qwen3-Reranker-0.6B/snapshots/e61197ed45024b0ed8a2d74b80b4d909f1255473"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1

test -d "$QWEN_MODEL"
test "$(basename "$QWEN_MODEL")" = 'e61197ed45024b0ed8a2d74b80b4d909f1255473'
test -f "$QWEN_MODEL/model.safetensors"
test "$(stat -c '%s' "$QWEN_MODEL/model.safetensors")" = '1191588280'
test "$(sha256sum "$QWEN_MODEL/model.safetensors" | awk '{print $1}')" = '27cd75a405b9c1b46b59abfd88aaa209e6fed2a1972cde9b70e7659537c5e65b'
```

Se qualquer arquivo estiver ausente ou divergente, pare. Não baixe nem substitua nada.

## Testes prévios

Execute e registre exit codes:

```bash
python .ai/validate_governance.py
PYTHONPATH=benchmark/embedding-v3 \
  python -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_artifact_portability.py' -v
PYTHONPATH=benchmark/embedding-v3 \
  python -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_lfm_artifact_finalize.py' -v
PYTHONPATH=benchmark/embedding-v3 \
  python -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_lfm_qwen_benchmark.py' -v
PYTHONPATH=benchmark/embedding-v3 \
  python -m unittest discover -s benchmark/embedding-v3/tests -v
python -m compileall -q benchmark/embedding-v3
git diff --check
```

Todos devem retornar código 0. Se houver falha, pare e reporte o traceback integral sanitizado. Não corrija código.

## Finalização portátil do resultado LFM

Capture uma cópia temporária antes da transformação:

```bash
cp -- "$LFM_RESULT" /tmp/lfm-result-before-finalize.json

PYTHONPATH=benchmark/embedding-v3 \
python -m holo_benchmark.lfm_artifact_finalize \
  --result "$LFM_RESULT"
```

Valide programaticamente que:

1. o JSON permanece schema 1.0, `status=COMPLETED` e `gate_result=PASS`;
2. métricas, identidade, dataset, runtime e `completed_at` são exatamente iguais ao arquivo temporário;
3. somente o bloco `hardware` pode divergir;
4. não há `/home/`, `Playstoria`, nome da worktree, username, caminho Windows absoluto ou executável absoluto;
5. URLs públicas continuam preservadas;
6. o candidate permanece byte a byte inalterado.

Use Python de leitura para comparar. Não edite o JSON.

## Execução canônica do Qwen local

Antes da execução, confirme RAM e VRAM livres. Não encerre processos não relacionados.

Execute uma única vez:

```bash
PYTHONPATH=benchmark/embedding-v3 \
python -m holo_benchmark.lfm_qwen_benchmark \
  --model-path "$QWEN_MODEL" \
  --candidate "$LFM_CANDIDATE" \
  --score-output "$LFM_SCORE" \
  --pipeline-output "$LFM_PIPELINE" \
  --batch-size 8
```

O runner deve:

- operar com `HF_HUB_OFFLINE=1` e `TRANSFORMERS_OFFLINE=1`;
- validar revisão, bytes e SHA-256 do peso;
- usar CUDA com evidência positiva de VRAM;
- pontuar exatamente 7.500 pares, 50 por consulta;
- permitir promoção de candidates das posições 21–50 para o top 20;
- gravar score dedicado sem tocar em `scores/qwen_local.json`;
- vincular score e pipeline ao `ranking_sha256` do candidate;
- persistir identidade do modelo sem caminho absoluto;
- substituir o pipeline legado somente após pontuação e avaliação completas.

## Validação obrigatória do score

Valide:

1. `schema_version = "1.0"`;
2. `reranker_id = "qwen_local"`;
3. modelo `Qwen/Qwen3-Reranker-0.6B`;
4. revisão `e61197ed45024b0ed8a2d74b80b4d909f1255473`;
5. peso com 1.191.588.280 bytes e SHA-256 fixo;
6. corpus 600/150 e SHA-256 congelado;
7. candidate variant e ranking SHA-256 exatos;
8. 150 consultas na ordem congelada;
9. 50 `candidate_ids` e 50 scores finitos por consulta;
10. `runtime.device = "cuda"`;
11. `runtime.pairs = 7500`;
12. `runtime.peak_vram_bytes > 0`;
13. nenhum caminho absoluto ou identificador do host.

## Validação obrigatória do pipeline

Valide:

1. `schema_version = "1.0"`;
2. `pipeline_id = "lfm_25_embedding_350m_q4_k_m_official__qwen_local"`;
3. `embedding_variant` e identidade do GGUF corretos;
4. `candidate_ranking_sha256 = 3a80b1969d82383386199bcd0877140786b9865f3d74f2f444e192a171630db3`;
5. identidade completa do Qwen sem path absoluto;
6. `candidate_top_k = 50` e `rerank_top_k = 20`;
7. `score_artifact` aponta para o score dedicado relativo ao projeto;
8. `evaluation.base_metrics.per_query` contém 150 entradas;
9. `evaluation.reranked_metrics.per_query` contém 150 entradas;
10. ambos os `by_query_type` contêm os sete tipos reais;
11. `evaluation.per_query_effect` contém 150 entradas;
12. não há NaN ou infinito;
13. não há caminho absoluto ou identificador do host;
14. registre métricas base, reranked, rescue, damage e melhorias de rank.

O pipeline novo deve ter SHA-256 diferente do pipeline legado.

## Validações posteriores

```bash
python .ai/validate_governance.py
PYTHONPATH=benchmark/embedding-v3 \
  python -m unittest discover -s benchmark/embedding-v3/tests -v
python -m compileall -q benchmark/embedding-v3
python benchmark/embedding-v3/validate_coverage.py
git diff --check
```

Confirme ainda:

```bash
test "$(sha256sum "$LFM_CANDIDATE" | awk '{print $1}')" = "$CANDIDATE_SHA_BEFORE"
test "$(sha256sum "$GLOBAL_QWEN_SCORE" | awk '{print $1}')" = "$GLOBAL_SCORE_SHA_BEFORE"
test "$(sha256sum "$LFM_PIPELINE" | awk '{print $1}')" != "$PIPELINE_SHA_BEFORE"
```

## Commit e push

Os únicos caminhos autorizados no commit são:

- `benchmark/embedding-v3/results/gate3/lfm_25_embedding_350m_q4_k_m_official.json`;
- `benchmark/embedding-v3/results/reranker/scores/qwen_local/lfm_25_embedding_350m_q4_k_m_official.json`;
- `benchmark/embedding-v3/results/reranker/pipelines/qwen_local/lfm_25_embedding_350m_q4_k_m_official.json`.

O candidate não deve ser staged porque deve permanecer byte a byte inalterado.

```bash
git add -- "$LFM_RESULT" "$LFM_SCORE" "$LFM_PIPELINE"
git diff --cached --check
git diff --cached --name-only
```

Pare se houver outro caminho staged.

```bash
git commit -m 'Finalize LFM artifacts and rerun canonical Qwen pipeline'
git push origin exec/embed-rerank-batch2-light
```

Mantenha o PR #20 aberto e draft. Não faça merge.

## Retorno obrigatório

Retorne:

1. HEAD inicial e final completos;
2. worktree antes e depois;
3. comandos e exit codes;
4. total de testes, passes, failures e errors;
5. quantidade de strings sanitizadas do resultado;
6. confirmação de que métricas/runtime/timestamp do embedding não mudaram;
7. identidade e hash do Qwen;
8. runtime completo do reranker, incluindo pares, duração, throughput e VRAM;
9. métricas base e reranked completas;
10. rescue rate, damage rate e melhorias de rank;
11. SHA-256 do candidate antes/depois;
12. SHA-256 do pipeline legado e novo;
13. SHA-256 do score dedicado;
14. arquivos exatos commitados;
15. confirmação de ausência de downloads, Voyage, outros modelos, edição de código, alteração do score global, arquivos não rastreados no commit e merge.

Termine exatamente com:

`Versão do retorno da IA local: 2.2.3 — Finalização portátil do LFM e pipeline Qwen canônico`
