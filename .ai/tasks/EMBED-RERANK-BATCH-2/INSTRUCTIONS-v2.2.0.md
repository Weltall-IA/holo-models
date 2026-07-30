# INSTRUCTIONS v2.2.0 — reexecução canônica do LFM2.5 350M Q4_K_M

## Objetivo

Executar exclusivamente o benchmark completo do perfil `lfm_25_embedding_350m_q4_k_m_official` pelo entrypoint versionado implementado pelo gerente, usando o GGUF e o llama.cpp já existentes no host.

Esta etapa deve substituir o resultado e o candidate antigos somente por artefatos produzidos pela execução real do novo runner. O pipeline Qwen existente não deve ser alterado nesta etapa; ele será auditado separadamente contra o novo ranking.

## Repositório, branch e PR

- Repositório: `Weltall-IA/holo-models`
- Worktree: `/home/alpha/Playstoria/models-embed-batch2-light`
- Branch: `exec/embed-rerank-batch2-light`
- PR: `#20`
- Estado obrigatório: aberto e draft
- Não faça merge.

## Autoridade e escopo

Leia integralmente, nesta ordem:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`;
6. este arquivo.

A IA local está autorizada somente a:

- inspecionar o estado local;
- executar testes;
- localizar o llama-server estável já instalado;
- verificar hashes e versões;
- executar o smoke test e o benchmark LFM2.5;
- validar os artefatos gerados;
- fazer commit e push somente dos artefatos LFM legitimamente gerados.

É proibido:

- editar qualquer `.py`, teste, schema, YAML ou instrução;
- baixar outro GGUF ou runtime;
- alterar CUDA, driver, PyTorch, Python ou pacotes globais;
- executar BitNet, outros embeddings, rerankers ou API Voyage;
- alterar ou excluir o pipeline Qwen existente do LFM;
- tocar nos arquivos não rastreados preexistentes;
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
test -f benchmark/embedding-v3/holo_benchmark/lfm_benchmark.py
test -f benchmark/embedding-v3/tests/test_lfm_benchmark.py
```

Preserve integralmente, sem adicionar ao Git, mover, apagar ou modificar:

- `rerank/`
- `run_bitnet_benchmark.py`
- `run_light_phase.py`
- `runtimes/`

Registre o status antes e depois.

## Identidade fixa do modelo

GGUF obrigatório:

`embed/lfm_25_embedding_350m_q4_k_m_official/LFM2.5-Embedding-350M-Q4_K_M.gguf`

Identidade esperada:

- repositório: `LiquidAI/LFM2.5-Embedding-350M-GGUF`
- revisão: `a80de9c5b941d429104f0038292a0ef5a860e486`
- licença: `Apache-2.0`
- tamanho: `229311232` bytes
- SHA-256: `4d7aa9dc6406a10fc3dec2c11f8f06781af063bf49211b8e4132e9b876d3f32a`
- dimensão: `1024`
- pooling: `cls`
- normalização: `l2`
- prefixo de documentos: `document: `
- prefixo de consultas: `query: `

Verifique antes de iniciar o servidor:

```bash
GGUF='embed/lfm_25_embedding_350m_q4_k_m_official/LFM2.5-Embedding-350M-Q4_K_M.gguf'
test -f "$GGUF"
test "$(stat -c '%s' "$GGUF")" = '229311232'
test "$(sha256sum "$GGUF" | awk '{print $1}')" = '4d7aa9dc6406a10fc3dec2c11f8f06781af063bf49211b8e4132e9b876d3f32a'
```

Qualquer divergência é bloqueio. Não substitua o arquivo.

## Resolução do llama-server

Use somente um binário já existente. Não compile nem baixe runtime nesta etapa.

Resolva nesta ordem:

```bash
if test -x runtimes/llama.cpp/build/bin/llama-server; then
  LLAMA_SERVER="$(realpath runtimes/llama.cpp/build/bin/llama-server)"
elif command -v llama-server >/dev/null 2>&1; then
  LLAMA_SERVER="$(realpath "$(command -v llama-server)")"
elif command -v llama-server-cuda >/dev/null 2>&1; then
  LLAMA_SERVER="$(realpath "$(command -v llama-server-cuda)")"
else
  echo 'llama-server estável não encontrado' >&2
  exit 2
fi

export LLAMA_SERVER
"$LLAMA_SERVER" --version
```

A versão deve comprovar o build estável `9972` ou o commit `c92e806d1`. Caso contrário, pare e reporte a versão real; não troque de runtime silenciosamente.

Registre:

- caminho resolvido apenas no retorno local, não em JSON versionado;
- SHA-256 do binário;
- saída de `--version`;
- estado inicial de RAM e VRAM.

## Testes antes da execução

Execute exatamente:

```bash
python .ai/validate_governance.py
PYTHONPATH=benchmark/embedding-v3 \
  python -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_lfm_benchmark.py' -v
PYTHONPATH=benchmark/embedding-v3 \
  python -m unittest discover -s benchmark/embedding-v3/tests -v
python -m compileall -q benchmark/embedding-v3
git diff --check
```

Todos devem retornar código 0. Se qualquer teste falhar, preserve o traceback integral sanitizado e pare. Não edite o código.

## Smoke test determinístico 20/10

O smoke test não pode gravar artefatos dentro do repositório. Execute o código abaixo, que seleciona 20 documentos contendo os relevantes das primeiras 10 consultas, valida dimensão, finitude, normalização, ausência de vetores duplicados indevidos, uso de VRAM e uma verificação semântica mínima.

```bash
PYTHONPATH=benchmark/embedding-v3 python - <<'PY'
import json
import os
from pathlib import Path

import numpy as np

from holo_benchmark.lfm_benchmark import (
    DIMENSION,
    lfm_embed_queries_and_docs,
)
from holo_benchmark.reranker_runtime import load_frozen_dataset

project = Path('benchmark/embedding-v3').resolve()
chunks, queries = load_frozen_dataset(project)
queries = queries[:10]
chunk_by_id = {str(row['chunk_id']): row for row in chunks}

selected_ids = []
for query in queries:
    for chunk_id in list(query['relevant_chunk_ids']) + list(query['hard_negative_chunk_ids'][:1]):
        if chunk_id not in selected_ids:
            selected_ids.append(chunk_id)
for chunk in chunks:
    chunk_id = str(chunk['chunk_id'])
    if chunk_id not in selected_ids:
        selected_ids.append(chunk_id)
    if len(selected_ids) == 20:
        break

selected = [chunk_by_id[chunk_id] for chunk_id in selected_ids]
query_embeddings, document_embeddings, runtime = lfm_embed_queries_and_docs(
    [str(row['query']) for row in queries],
    [str(row['text']) for row in selected],
    gguf_path=Path(os.environ['GGUF']),
    llama_server=Path(os.environ['LLAMA_SERVER']),
    batch_size=10,
)

assert query_embeddings.shape == (10, DIMENSION)
assert document_embeddings.shape == (20, DIMENSION)
assert np.all(np.isfinite(query_embeddings))
assert np.all(np.isfinite(document_embeddings))
assert np.allclose(np.linalg.norm(query_embeddings, axis=1), 1.0, atol=1e-3)
assert np.allclose(np.linalg.norm(document_embeddings, axis=1), 1.0, atol=1e-3)
assert int(runtime['peak_vram_bytes']) > 0

scores = query_embeddings @ document_embeddings.T
positions = {chunk_id: index for index, chunk_id in enumerate(selected_ids)}
semantic_passes = 0
for query_index, query in enumerate(queries):
    relevant = max(scores[query_index, positions[chunk_id]] for chunk_id in query['relevant_chunk_ids'])
    unrelated_indices = [
        index for index, chunk_id in enumerate(selected_ids)
        if chunk_id not in query['relevant_chunk_ids']
        and chunk_id not in query['hard_negative_chunk_ids']
    ][:5]
    unrelated_mean = float(np.mean(scores[query_index, unrelated_indices]))
    semantic_passes += int(float(relevant) > unrelated_mean)
assert semantic_passes >= 7, semantic_passes

Path('/tmp/lfm25-smoke.json').write_text(
    json.dumps({
        'queries': 10,
        'documents': 20,
        'dimension': DIMENSION,
        'semantic_passes': semantic_passes,
        'peak_vram_bytes': runtime['peak_vram_bytes'],
        'backend_version': runtime['backend_version'],
        'binary_sha256': runtime['binary_sha256'],
        'gguf_sha256': runtime['gguf_sha256'],
    }, ensure_ascii=False, indent=2) + '\n',
    encoding='utf-8',
)
print(Path('/tmp/lfm25-smoke.json').read_text(encoding='utf-8'))
PY
```

Se o smoke falhar, pare. Não execute o corpus completo.

## Benchmark completo

Antes da execução, confirme que não há servidor llama.cpp antigo ativo para esse modelo. Não mate processos não relacionados.

Execute uma única vez:

```bash
PYTHONPATH=benchmark/embedding-v3 \
python -m holo_benchmark.lfm_benchmark \
  --gguf-path "$GGUF" \
  --llama-server "$LLAMA_SERVER" \
  --hardware-json benchmark/embedding-v3/system_info.json
```

O entrypoint:

- verifica tamanho e SHA-256 do GGUF;
- usa CUDA com `-ngl 99`;
- exige evidência positiva de VRAM e bloqueia fallback CPU;
- aplica `cls`, L2 e os prefixes oficiais;
- calcula métricas completas pelo avaliador canônico;
- grava o resultado Gate 3 atomicamente;
- grava candidate somente quando o gate passa;
- remove candidate antigo somente quando a nova execução termina com gate FAIL;
- valida candidate com o loader canônico.

Não execute Qwen nesta etapa.

## Validação obrigatória dos artefatos

Resultado esperado:

`benchmark/embedding-v3/results/gate3/lfm_25_embedding_350m_q4_k_m_official.json`

Candidate condicional:

`benchmark/embedding-v3/results/reranker/candidates/lfm_25_embedding_350m_q4_k_m_official.json`

Valide programaticamente:

1. JSON parseável e newline final;
2. `schema_version = "1.0"`;
3. `status = "COMPLETED"`;
4. `gate_result` é `PASS` ou `FAIL` conforme as métricas reais;
5. identidade, revisão, licença, tamanho e SHA-256 exatos;
6. corpus SHA-256 congelado, 600 documentos e 150 consultas;
7. `metrics.per_query` contém 150 entradas;
8. `metrics.by_query_type` contém os sete tipos reais;
9. métricas sem NaN ou infinito;
10. `runtime.device = "cuda"`;
11. `runtime.pooling = "cls"` e `runtime.normalization = "l2"`;
12. `runtime.peak_vram_bytes > 0`;
13. comando persistido sem caminhos absolutos ou identificadores do host;
14. se PASS, candidate com 150 consultas ordenadas e 50 IDs únicos por consulta;
15. se PASS, candidate aceito por `load_candidate_payloads`;
16. se FAIL, candidate ausente;
17. pipeline Qwen antigo permanece byte a byte inalterado.

Registre o SHA-256 do pipeline Qwen antes e depois:

`benchmark/embedding-v3/results/reranker/pipelines/qwen_local/lfm_25_embedding_350m_q4_k_m_official.json`

## Validações depois da execução

```bash
python .ai/validate_governance.py
PYTHONPATH=benchmark/embedding-v3 \
  python -m unittest discover -s benchmark/embedding-v3/tests -v
python -m compileall -q benchmark/embedding-v3
python benchmark/embedding-v3/validate_coverage.py
git diff --check
```

Registre todos os exit codes.

## Git e push

Revise o diff completo. Os únicos artefatos autorizados para commit são:

- `benchmark/embedding-v3/results/gate3/lfm_25_embedding_350m_q4_k_m_official.json`;
- `benchmark/embedding-v3/results/reranker/candidates/lfm_25_embedding_350m_q4_k_m_official.json`, somente se o gate passar;
- a remoção desse candidate, somente se a nova execução terminar com gate FAIL.

Não inclua `/tmp/lfm25-smoke.json`, logs, caches, pesos, runtimes, arquivos não rastreados ou o pipeline Qwen.

```bash
git add -- benchmark/embedding-v3/results/gate3/lfm_25_embedding_350m_q4_k_m_official.json

if test -e benchmark/embedding-v3/results/reranker/candidates/lfm_25_embedding_350m_q4_k_m_official.json; then
  git add -- benchmark/embedding-v3/results/reranker/candidates/lfm_25_embedding_350m_q4_k_m_official.json
else
  git add -u -- benchmark/embedding-v3/results/reranker/candidates/lfm_25_embedding_350m_q4_k_m_official.json
fi

git diff --cached --check
git diff --cached --name-only
```

Confirme que o staged contém somente os caminhos autorizados. Depois:

```bash
git commit -m "Regenerate canonical LFM2.5 benchmark artifacts"
git push origin exec/embed-rerank-batch2-light
```

Não use force-push. Mantenha o PR #20 draft. Não faça merge.

## Retorno obrigatório

Retorne:

1. HEAD inicial e final completos;
2. status da worktree antes e depois;
3. caminho, SHA-256 e versão do llama-server;
4. tamanho e SHA-256 do GGUF;
5. comandos e exit codes;
6. total de testes, passes, failures e errors;
7. resultado do smoke, inclusive `semantic_passes` e pico de VRAM;
8. métricas completas do benchmark;
9. gate final;
10. validação do candidate ou confirmação de ausência;
11. SHA-256 do pipeline Qwen antes e depois;
12. lista exata de arquivos commitados;
13. confirmação de ausência de downloads, Voyage, outros modelos, edição de código e merge.

Termine exatamente com:

`Versão do retorno da IA local: 2.2.0 — Reexecução canônica do LFM2.5 350M Q4_K_M`
