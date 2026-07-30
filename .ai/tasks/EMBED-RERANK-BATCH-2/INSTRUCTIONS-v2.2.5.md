# INSTRUCTIONS v2.2.5 — Voyage Context offline a partir de checkpoints existentes

Esta versão sucede a v2.2.4.

## Objetivo

Resolver exclusivamente o pipeline obrigatório `voyage-context-4__qwen_local` sem repetir o embedding remoto e sem chamar qualquer API Voyage.

O fluxo deve:

1. localizar um par completo de checkpoints locais já existentes de `voyage-context-4`;
2. validar os 600 vetores de documentos e 150 vetores de consultas;
3. recompor o ranking com o mesmo algoritmo float32/cosseno usado no benchmark original;
4. exigir correspondência integral com o resultado publicado de `voyage-context-4`;
5. materializar o candidate canônico top 50;
6. executar somente `Qwen/Qwen3-Reranker-0.6B` sobre os 7.500 pares;
7. gerar score e pipeline canônicos por perfil.

Se o par completo de checkpoints não existir, pare e reporte `BLOCKED`. Não chame a API, não regenere embeddings, não copie arquivos e não crie commit vazio.

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
- não executar `voyage_benchmark.py`;
- não importar ou chamar `voyageai`;
- não usar `.voyage4_token`, `VOYAGE_API_KEY` ou qualquer credencial;
- não chamar API de embedding ou reranking Voyage;
- não repetir LFM, BitNet, Nemotron ou qualquer outro embedding;
- não baixar pesos, checkpoints, tokenizers, configs ou runtimes;
- não copiar, mover, reflinkar ou criar symlink dos checkpoints;
- não alterar CUDA, driver, Python, PyTorch, Transformers ou pacotes globais;
- não sobrescrever `results/reranker/scores/qwen_local.json`;
- não tocar nos arquivos não rastreados preexistentes;
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
test -f benchmark/embedding-v3/holo_benchmark/voyage_context_candidate.py
test -f benchmark/embedding-v3/holo_benchmark/qwen_candidate_benchmark.py
test -f benchmark/embedding-v3/tests/test_voyage_context_candidate.py
```

Preserve sem adicionar ao Git, mover, apagar ou modificar:

- `rerank/`
- `run_bitnet_benchmark.py`
- `run_light_phase.py`
- `runtimes/`

Registre o status antes e depois.

## Artefatos e proteção do trabalho concluído

```bash
PROJECT='benchmark/embedding-v3'
PUBLISHED="$PROJECT/results/voyage/voyage-context-4.json"
CANDIDATE="$PROJECT/results/reranker/candidates/voyage-context-4.json"
SCORE="$PROJECT/results/reranker/scores/qwen_local/voyage-context-4.json"
PIPELINE="$PROJECT/results/reranker/pipelines/qwen_local/voyage-context-4.json"
GLOBAL_QWEN="$PROJECT/results/reranker/scores/qwen_local.json"

NVFP4_CANDIDATE="$PROJECT/results/reranker/candidates/nemotron_3_embed_1b_nvfp4.json"
NVFP4_SCORE="$PROJECT/results/reranker/scores/qwen_local/nemotron_3_embed_1b_nvfp4.json"
NVFP4_PIPELINE="$PROJECT/results/reranker/pipelines/qwen_local/nemotron_3_embed_1b_nvfp4.json"
GGUF_CANDIDATE="$PROJECT/results/reranker/candidates/nemotron_3_embed_1b_q4_k_m_gguf.json"
GGUF_SCORE="$PROJECT/results/reranker/scores/qwen_local/nemotron_3_embed_1b_q4_k_m_gguf.json"
GGUF_PIPELINE="$PROJECT/results/reranker/pipelines/qwen_local/nemotron_3_embed_1b_q4_k_m_gguf.json"

for path in \
  "$PUBLISHED" "$GLOBAL_QWEN" \
  "$NVFP4_CANDIDATE" "$NVFP4_SCORE" "$NVFP4_PIPELINE" \
  "$GGUF_CANDIDATE" "$GGUF_SCORE" "$GGUF_PIPELINE"; do
  test -f "$path"
done

test ! -e "$CANDIDATE"
test ! -e "$SCORE"
test ! -e "$PIPELINE"

PUBLISHED_SHA_BEFORE="$(sha256sum "$PUBLISHED" | awk '{print $1}')"
GLOBAL_QWEN_SHA_BEFORE="$(sha256sum "$GLOBAL_QWEN" | awk '{print $1}')"
NVFP4_CANDIDATE_SHA_BEFORE="$(sha256sum "$NVFP4_CANDIDATE" | awk '{print $1}')"
NVFP4_SCORE_SHA_BEFORE="$(sha256sum "$NVFP4_SCORE" | awk '{print $1}')"
NVFP4_PIPELINE_SHA_BEFORE="$(sha256sum "$NVFP4_PIPELINE" | awk '{print $1}')"
GGUF_CANDIDATE_SHA_BEFORE="$(sha256sum "$GGUF_CANDIDATE" | awk '{print $1}')"
GGUF_SCORE_SHA_BEFORE="$(sha256sum "$GGUF_SCORE" | awk '{print $1}')"
GGUF_PIPELINE_SHA_BEFORE="$(sha256sum "$GGUF_PIPELINE" | awk '{print $1}')"

export PROJECT PUBLISHED CANDIDATE SCORE PIPELINE GLOBAL_QWEN
export PUBLISHED_SHA_BEFORE GLOBAL_QWEN_SHA_BEFORE
export NVFP4_CANDIDATE_SHA_BEFORE NVFP4_SCORE_SHA_BEFORE NVFP4_PIPELINE_SHA_BEFORE
export GGUF_CANDIDATE_SHA_BEFORE GGUF_SCORE_SHA_BEFORE GGUF_PIPELINE_SHA_BEFORE
```

## Testes prévios

Execute e registre exit codes:

```bash
python .ai/validate_governance.py
PYTHONPATH=benchmark/embedding-v3 \
  python -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_voyage_context_candidate.py' -v
PYTHONPATH=benchmark/embedding-v3 \
  python -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_qwen_candidate_benchmark.py' -v
PYTHONPATH=benchmark/embedding-v3 \
  python -m unittest discover -s benchmark/embedding-v3/tests -v
python -m compileall -q benchmark/embedding-v3
git diff --check
```

Resultados mínimos esperados:

- `test_voyage_context_candidate.py`: 4 testes, todos PASS;
- `test_qwen_candidate_benchmark.py`: 3 testes, todos PASS;
- suíte integral: pelo menos 194 testes, todos PASS.

Se houver falha, pare e reporte o traceback integral sanitizado. Não corrija código.

## Resolução dos checkpoints locais

Não presuma um único checkout. Aceite primeiro variáveis explícitas e depois os diretórios conhecidos.

```bash
DOCS_CP="${VOYAGE_CONTEXT_DOCUMENTS_CHECKPOINT:-}"
QUERIES_CP="${VOYAGE_CONTEXT_QUERIES_CHECKPOINT:-}"

if { test -n "$DOCS_CP" && test -z "$QUERIES_CP"; } || \
   { test -z "$DOCS_CP" && test -n "$QUERIES_CP"; }; then
  echo 'BLOCKED: somente um checkpoint explícito foi informado' >&2
  exit 2
fi

if test -n "$DOCS_CP"; then
  DOCS_CP="$(realpath "$DOCS_CP")"
  QUERIES_CP="$(realpath "$QUERIES_CP")"
else
  for base in \
    "$PWD/benchmark/embedding-v3/results/raw/voyage/voyage-context-4" \
    "/home/alpha/Playstoria/models/benchmark/embedding-v3/results/raw/voyage/voyage-context-4"; do
    if test -f "$base/documents.json" && test -f "$base/queries.json"; then
      DOCS_CP="$(realpath "$base/documents.json")"
      QUERIES_CP="$(realpath "$base/queries.json")"
      break
    fi
  done
fi

if ! test -f "$DOCS_CP" || ! test -f "$QUERIES_CP"; then
  echo 'BLOCKED: checkpoints completos de voyage-context-4 não encontrados' >&2
  printf 'caminhos verificados:\n'
  printf '%s\n' \
    "$PWD/benchmark/embedding-v3/results/raw/voyage/voyage-context-4/documents.json" \
    "$PWD/benchmark/embedding-v3/results/raw/voyage/voyage-context-4/queries.json" \
    "/home/alpha/Playstoria/models/benchmark/embedding-v3/results/raw/voyage/voyage-context-4/documents.json" \
    "/home/alpha/Playstoria/models/benchmark/embedding-v3/results/raw/voyage/voyage-context-4/queries.json"
  git status --short
  exit 2
fi

export DOCS_CP QUERIES_CP
printf 'documents checkpoint: %s\n' "$DOCS_CP"
printf 'queries checkpoint: %s\n' "$QUERIES_CP"
sha256sum "$DOCS_CP" "$QUERIES_CP"
```

Não copie os checkpoints para a worktree. O gerador deve lê-los no local encontrado e persistir somente referências portáteis e hashes.

## Modelo Qwen fixo e offline

```bash
export QWEN_MODEL="$HOME/.cache/huggingface/hub/models--Qwen--Qwen3-Reranker-0.6B/snapshots/e61197ed45024b0ed8a2d74b80b4d909f1255473"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
unset VOYAGE_API_KEY || true
unset VOYAGE_API_KEY_PATH || true

test -d "$QWEN_MODEL"
test "$(basename "$QWEN_MODEL")" = 'e61197ed45024b0ed8a2d74b80b4d909f1255473'
test -f "$QWEN_MODEL/model.safetensors"
test "$(stat -c '%s' "$QWEN_MODEL/model.safetensors")" = '1191588280'
test "$(sha256sum "$QWEN_MODEL/model.safetensors" | awk '{print $1}')" = '27cd75a405b9c1b46b59abfd88aaa209e6fed2a1972cde9b70e7659537c5e65b'
```

Se o snapshot divergir, pare. Não baixe nem substitua nada.

## Materialização offline do candidate

Execute uma única vez:

```bash
PYTHONPATH=benchmark/embedding-v3 \
python -m holo_benchmark.voyage_context_candidate \
  --documents-checkpoint "$DOCS_CP" \
  --queries-checkpoint "$QUERIES_CP" \
  --published-result "$PUBLISHED" \
  --output "$CANDIDATE"
```

O materializador deve falhar antes de gravar o candidate se qualquer uma destas condições divergir:

- schemas, modelo, input types ou dimensão 1024 dos checkpoints;
- conjunto e ordem dos 600 chunk IDs e 150 query IDs;
- vetor não finito ou de norma zero;
- identidade publicada `voyage-context-4`;
- corpus congelado 600/150 e SHA-256;
- qualquer summary, métrica por tipo ou métrica por consulta do resultado publicado.

Valide o candidate:

1. `schema_version = "1.0"`;
2. `variant = "voyage-context-4"`;
3. 150 consultas na ordem congelada;
4. 50 candidates únicos e rank-only por consulta;
5. `ranking_sha256` com 64 caracteres;
6. identidade de embedding com `sha256_scope = model_endpoint_and_effective_checkpoint_vectors`;
7. hashes distintos dos vetores efetivos de documentos e consultas;
8. hashes dos dois checkpoints e do resultado publicado registrados;
9. referências internas relativas ou externas como `<external>/<basename>`;
10. ausência de caminho absoluto, username, token ou credencial.

## Execução Qwen local

Antes da execução, registre RAM e VRAM livres. Não encerre processos não relacionados.

Execute uma única vez:

```bash
PYTHONPATH=benchmark/embedding-v3 \
python -m holo_benchmark.qwen_candidate_benchmark \
  --profile-id voyage-context-4 \
  --model-path "$QWEN_MODEL" \
  --candidate "$CANDIDATE" \
  --score-output "$SCORE" \
  --pipeline-output "$PIPELINE" \
  --batch-size 8
```

O runner deve:

- operar offline;
- usar CUDA com evidência positiva de VRAM;
- pontuar exatamente 7.500 pares;
- reranquear os 50 candidates para top 20;
- gerar score dedicado sem tocar no score global;
- vincular score e pipeline ao `ranking_sha256` do candidate;
- manter a identidade Voyage sem alegar hash de peso remoto;
- persistir apenas caminhos portáteis.

## Validação dos artefatos gerados

Valide programaticamente:

### Score

- schema 1.0;
- `reranker_id = qwen_local`;
- identidade e revisão exatas do Qwen;
- corpus 600/150 congelado;
- candidate `voyage-context-4` e ranking SHA correspondentes;
- 150 consultas;
- 50 IDs e 50 scores finitos por consulta;
- `runtime.device = cuda`;
- `runtime.pairs = 7500`;
- pico de VRAM positivo;
- nenhum caminho absoluto ou dado de host.

### Pipeline

- schema 1.0;
- `pipeline_id = voyage-context-4__qwen_local`;
- identidade Voyage igual à do candidate;
- candidate top 50 e rerank top 20;
- score dedicado relativo ao projeto;
- base e reranked com 150 entradas `per_query`;
- sete tipos reais em ambos os `by_query_type`;
- 150 entradas `per_query_effect`;
- rescue, damage e melhorias de rank presentes;
- nenhum NaN, infinito, path absoluto ou credencial.

Registre as métricas completas base e reranked, além de rescue/damage.

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
test "$(sha256sum "$PUBLISHED" | awk '{print $1}')" = "$PUBLISHED_SHA_BEFORE"
test "$(sha256sum "$GLOBAL_QWEN" | awk '{print $1}')" = "$GLOBAL_QWEN_SHA_BEFORE"
test "$(sha256sum "$NVFP4_CANDIDATE" | awk '{print $1}')" = "$NVFP4_CANDIDATE_SHA_BEFORE"
test "$(sha256sum "$NVFP4_SCORE" | awk '{print $1}')" = "$NVFP4_SCORE_SHA_BEFORE"
test "$(sha256sum "$NVFP4_PIPELINE" | awk '{print $1}')" = "$NVFP4_PIPELINE_SHA_BEFORE"
test "$(sha256sum "$GGUF_CANDIDATE" | awk '{print $1}')" = "$GGUF_CANDIDATE_SHA_BEFORE"
test "$(sha256sum "$GGUF_SCORE" | awk '{print $1}')" = "$GGUF_SCORE_SHA_BEFORE"
test "$(sha256sum "$GGUF_PIPELINE" | awk '{print $1}')" = "$GGUF_PIPELINE_SHA_BEFORE"
```

## Commit e push

Os únicos caminhos autorizados no commit são:

- `benchmark/embedding-v3/results/reranker/candidates/voyage-context-4.json`;
- `benchmark/embedding-v3/results/reranker/scores/qwen_local/voyage-context-4.json`;
- `benchmark/embedding-v3/results/reranker/pipelines/qwen_local/voyage-context-4.json`.

Os checkpoints não são autorizados no commit.

```bash
git add -- "$CANDIDATE" "$SCORE" "$PIPELINE"
git diff --cached --check
git diff --cached --name-only
```

Pare se houver outro caminho staged.

```bash
git commit -m 'Materialize Voyage Context candidate and Qwen pipeline'
git push origin exec/embed-rerank-batch2-light
```

Mantenha o PR #20 aberto e draft. Não faça merge.

## Retorno obrigatório

Retorne:

1. HEAD inicial e final completos;
2. worktree antes e depois;
3. comandos e exit codes;
4. total de testes, passes, failures e errors;
5. caminhos resolvidos dos checkpoints, usando forma sanitizada no relato;
6. SHA-256 dos checkpoints e dos vetores efetivos;
7. ranking SHA-256 do candidate;
8. identidade SHA-256 do embedding remoto/checkpoints e seu escopo;
9. identidade Qwen completa;
10. runtime, pares, RAM e VRAM;
11. métricas completas base e reranked;
12. rescue, damage e melhorias de rank;
13. SHA-256 de candidate, score e pipeline;
14. lista exata de arquivos commitados;
15. confirmação de que não houve API, download, embedding, edição de código ou merge.

Se os checkpoints estiverem ausentes, retorne em vez disso:

- HEAD inicial e final, que devem ser iguais;
- caminhos verificados;
- confirmação de que candidate, score e pipeline não foram criados;
- confirmação de que nenhuma API, modelo ou embedding foi executado;
- nenhum commit e nenhum push.

Identifique o retorno como:

`Versão do retorno da IA local: 2.2.5 — Voyage Context offline a partir de checkpoints existentes`
