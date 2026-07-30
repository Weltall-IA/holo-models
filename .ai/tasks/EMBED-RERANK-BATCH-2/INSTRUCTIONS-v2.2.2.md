# INSTRUCTIONS v2.2.2 — execução canônica do LFM2.5

Esta versão substitui integralmente a v2.2.1.

## Correção desta versão

A v2.2.1 procurava o `llama-server` somente dentro da worktree ou no `PATH`. No host real, o build estável já validado está em:

`/home/alpha/llama.cpp/build/bin/llama-server`

Esta versão inclui o runtime instalado no diretório pessoal na resolução canônica. Não copie, mova, recompile ou duplique esse binário dentro da worktree.

## Objetivo

Executar o smoke versionado e o benchmark completo do perfil `lfm_25_embedding_350m_q4_k_m_official`, usando exclusivamente o GGUF e o llama.cpp já existentes no host.

O executante não está autorizado a programar. Qualquer defeito de código deve ser reportado ao gerente.

## Estado obrigatório

- Repositório: `Weltall-IA/holo-models`
- Worktree: `/home/alpha/Playstoria/models-embed-batch2-light`
- Branch: `exec/embed-rerank-batch2-light`
- PR: `#20`, aberto e draft
- Não fazer merge.

Leia, nesta ordem:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`;
6. este arquivo.

## Proibições

- não editar `.py`, testes, schemas, YAML ou instruções;
- não baixar, compilar, copiar, mover ou substituir pesos e runtimes;
- não criar symlink ou cópia do llama.cpp dentro de `runtimes/`;
- não executar BitNet, outros embeddings ou rerankers;
- não chamar API Voyage;
- não alterar ou excluir o pipeline Qwen do LFM;
- não alterar CUDA, driver, Python, PyTorch ou pacotes globais;
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
test -f benchmark/embedding-v3/holo_benchmark/lfm_benchmark.py
test -f benchmark/embedding-v3/holo_benchmark/lfm_smoke.py
test -f benchmark/embedding-v3/tests/test_lfm_benchmark.py
test -f benchmark/embedding-v3/tests/test_lfm_smoke.py
```

Preserve sem adicionar ao Git, mover, apagar ou modificar:

- `rerank/`
- `run_bitnet_benchmark.py`
- `run_light_phase.py`
- `runtimes/`

## Identidade fixa do GGUF

```bash
export GGUF='embed/lfm_25_embedding_350m_q4_k_m_official/LFM2.5-Embedding-350M-Q4_K_M.gguf'

test -f "$GGUF"
test "$(stat -c '%s' "$GGUF")" = '229311232'
test "$(sha256sum "$GGUF" | awk '{print $1}')" = '4d7aa9dc6406a10fc3dec2c11f8f06781af063bf49211b8e4132e9b876d3f32a'
```

Identidade esperada:

- repositório: `LiquidAI/LFM2.5-Embedding-350M-GGUF`
- revisão: `a80de9c5b941d429104f0038292a0ef5a860e486`
- licença: `Apache-2.0`
- quantização: `Q4_K_M`
- dimensão: `1024`
- pooling: `cls`
- normalização: `l2`
- prefixos: `document: ` e `query: `

Qualquer divergência é bloqueio. Não substitua o arquivo.

## Resolução corrigida do llama-server existente

Use somente um binário executável já existente. Resolva exatamente nesta ordem:

1. caminho previamente definido em `LLAMA_SERVER`;
2. runtime dentro da worktree, caso exista;
3. build estável instalado em `$HOME/llama.cpp/build/bin/llama-server`;
4. caminho explícito conhecido do host `/home/alpha/llama.cpp/build/bin/llama-server`;
5. `llama-server` ou `llama-server-cuda` no `PATH`.

```bash
LLAMA_SERVER_REQUESTED="${LLAMA_SERVER:-}"

if test -n "$LLAMA_SERVER_REQUESTED" && test -x "$LLAMA_SERVER_REQUESTED"; then
  LLAMA_SERVER="$(realpath "$LLAMA_SERVER_REQUESTED")"
elif test -x runtimes/llama.cpp/build/bin/llama-server; then
  LLAMA_SERVER="$(realpath runtimes/llama.cpp/build/bin/llama-server)"
elif test -x "$HOME/llama.cpp/build/bin/llama-server"; then
  LLAMA_SERVER="$(realpath "$HOME/llama.cpp/build/bin/llama-server")"
elif test -x /home/alpha/llama.cpp/build/bin/llama-server; then
  LLAMA_SERVER="$(realpath /home/alpha/llama.cpp/build/bin/llama-server)"
elif command -v llama-server >/dev/null 2>&1; then
  LLAMA_SERVER="$(realpath "$(command -v llama-server)")"
elif command -v llama-server-cuda >/dev/null 2>&1; then
  LLAMA_SERVER="$(realpath "$(command -v llama-server-cuda)")"
else
  echo 'llama-server existente não encontrado nos caminhos autorizados' >&2
  exit 2
fi
export LLAMA_SERVER

test -x "$LLAMA_SERVER"
LLAMA_VERSION="$("$LLAMA_SERVER" --version 2>&1)"
printf '%s\n' "$LLAMA_VERSION"
printf '%s\n' "$LLAMA_VERSION" | grep -Eq '9972|c92e806d1'
LLAMA_SHA256="$(sha256sum "$LLAMA_SERVER" | awk '{print $1}')"
printf 'llama-server sha256: %s\n' "$LLAMA_SHA256"
export LLAMA_VERSION LLAMA_SHA256
```

O caminho esperado no host atual é `/home/alpha/llama.cpp/build/bin/llama-server`. A versão deve comprovar o build `9972` ou o commit `c92e806d1`.

Se o binário resolvido não for executável ou a versão divergir, pare e reporte. Não selecione outro runtime depois de uma divergência e não copie o binário para a worktree.

## Hash do pipeline Qwen a preservar

```bash
QWEN_PIPELINE='benchmark/embedding-v3/results/reranker/pipelines/qwen_local/lfm_25_embedding_350m_q4_k_m_official.json'
test -f "$QWEN_PIPELINE"
QWEN_SHA_BEFORE="$(sha256sum "$QWEN_PIPELINE" | awk '{print $1}')"
export QWEN_PIPELINE QWEN_SHA_BEFORE
```

## Testes prévios

```bash
python .ai/validate_governance.py
PYTHONPATH=benchmark/embedding-v3 \
  python -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_lfm*.py' -v
PYTHONPATH=benchmark/embedding-v3 \
  python -m unittest discover -s benchmark/embedding-v3/tests -v
python -m compileall -q benchmark/embedding-v3
git diff --check
```

Todos devem retornar código 0. Em caso de falha, pare e entregue o traceback integral sanitizado. Não edite código.

## Smoke versionado 20/10

Execute:

```bash
rm -f /tmp/lfm25-smoke.json
PYTHONPATH=benchmark/embedding-v3 \
python -m holo_benchmark.lfm_smoke \
  --gguf-path "$GGUF" \
  --llama-server "$LLAMA_SERVER" \
  --output /tmp/lfm25-smoke.json
```

O smoke deve retornar código 0 e comprovar:

- 20 documentos e 10 consultas;
- dimensão 1024;
- vetores finitos e normalizados;
- ausência de duplicação indevida;
- `peak_vram_bytes > 0`;
- pelo menos 7 de 10 verificações semânticas aprovadas;
- hashes do binário e do GGUF.

`/tmp/lfm25-smoke.json` não pode ser adicionado ao Git.

Se o smoke falhar, não execute o corpus completo.

## Benchmark completo

Confirme que não há servidor antigo do mesmo modelo ativo. Não encerre processos não relacionados.

Execute uma única vez:

```bash
PYTHONPATH=benchmark/embedding-v3 \
python -m holo_benchmark.lfm_benchmark \
  --gguf-path "$GGUF" \
  --llama-server "$LLAMA_SERVER" \
  --hardware-json benchmark/embedding-v3/system_info.json
```

O runner deve:

- usar CUDA e `-ngl 99`;
- bloquear quando não houver evidência positiva de VRAM;
- usar pooling CLS, L2 e prefixes assimétricos;
- calcular métricas completas pelo avaliador canônico;
- gravar resultado Gate 3 atomicamente;
- gerar candidate somente em gate PASS;
- remover candidate antigo somente em gate FAIL;
- validar candidate pelo loader canônico.

Não execute Qwen nesta etapa.

## Artefatos e validação

Resultado:

`benchmark/embedding-v3/results/gate3/lfm_25_embedding_350m_q4_k_m_official.json`

Candidate condicional:

`benchmark/embedding-v3/results/reranker/candidates/lfm_25_embedding_350m_q4_k_m_official.json`

Valide programaticamente:

1. JSON parseável e newline final;
2. `schema_version = "1.0"`;
3. `status = "COMPLETED"`;
4. `gate_result` coerente com as métricas;
5. identidade, revisão, licença, bytes e SHA-256 exatos;
6. corpus congelado, 600 documentos e 150 consultas;
7. `metrics.per_query` com 150 entradas;
8. `metrics.by_query_type` com sete tipos;
9. nenhuma ocorrência de NaN ou infinito;
10. `runtime.device = "cuda"`;
11. pooling `cls` e normalização `l2`;
12. `peak_vram_bytes > 0`;
13. comando persistido sem caminhos absolutos ou identificadores do host;
14. em PASS: candidate com 150 consultas e 50 IDs únicos por consulta;
15. em PASS: candidate aceito por `load_candidate_payloads`;
16. em FAIL: candidate ausente;
17. pipeline Qwen byte a byte inalterado.

Depois:

```bash
QWEN_SHA_AFTER="$(sha256sum "$QWEN_PIPELINE" | awk '{print $1}')"
test "$QWEN_SHA_AFTER" = "$QWEN_SHA_BEFORE"
```

## Validações posteriores

```bash
python .ai/validate_governance.py
PYTHONPATH=benchmark/embedding-v3 \
  python -m unittest discover -s benchmark/embedding-v3/tests -v
python -m compileall -q benchmark/embedding-v3
python benchmark/embedding-v3/validate_coverage.py
git diff --check
```

Registre todos os exit codes.

## Commit e push

Os únicos caminhos autorizados no commit são:

- `benchmark/embedding-v3/results/gate3/lfm_25_embedding_350m_q4_k_m_official.json`;
- `benchmark/embedding-v3/results/reranker/candidates/lfm_25_embedding_350m_q4_k_m_official.json`, criado/atualizado em PASS ou removido em FAIL.

```bash
git add -- benchmark/embedding-v3/results/gate3/lfm_25_embedding_350m_q4_k_m_official.json
git add -A -- benchmark/embedding-v3/results/reranker/candidates/lfm_25_embedding_350m_q4_k_m_official.json

git diff --cached --check
git diff --cached --name-only
```

Pare se o staged contiver qualquer outro caminho.

```bash
git commit -m 'Regenerate canonical LFM2.5 benchmark artifacts'
git push origin exec/embed-rerank-batch2-light
```

Mantenha o PR #20 aberto e draft. Não faça merge.

## Retorno obrigatório

Retorne:

1. HEAD inicial e final completos;
2. worktree antes e depois;
3. caminho resolvido, versão e SHA-256 do llama-server;
4. bytes e SHA-256 do GGUF;
5. comandos e exit codes;
6. total de testes, passes, failures e errors;
7. resultado completo do smoke;
8. métricas completas do benchmark;
9. gate final;
10. validação do candidate ou confirmação de ausência;
11. SHA-256 do pipeline Qwen antes e depois;
12. arquivos exatos commitados;
13. confirmação de ausência de downloads, cópia de runtime, Voyage, outros modelos, edição de código e merge.

Termine exatamente com:

`Versão do retorno da IA local: 2.2.2 — Execução canônica do LFM2.5 350M Q4_K_M`
