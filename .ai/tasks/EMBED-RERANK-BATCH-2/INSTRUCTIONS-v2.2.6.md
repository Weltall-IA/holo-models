# INSTRUCTIONS v2.2.6 — painel Mixedbread canônico e portabilidade BitNet

## Objetivo

Continuar a fase leve de `EMBED-RERANK-BATCH-2` no branch do PR #20, sem repetir embeddings, downloads ou pipelines já concluídos.

Esta etapa possui exatamente dois objetivos:

1. sanitizar os dois resultados BitNet completos, removendo somente caminhos e identificadores locais sem alterar identidade, métricas, gate ou timestamps;
2. substituir os cinco pipelines Mixedbread incompletos e adicionar o sexto membro obrigatório, executando `mixedbread-ai/mxbai-rerank-base-v2` realmente sobre os 50 candidates de cada uma das 150 consultas.

Esta etapa **não** regenera `ALL_BENCHMARK_RESULTS.json`, **não** atualiza `README.md` e **não** conclui o lote. Depois dela ainda será necessária a segunda tentativa tecnicamente correta do painel NVIDIA Nemotron Rerank 1B v2. Somente após fechar esse painel será autorizada a consolidação canônica final.

## Repositório, branch e HEAD

- repositório: `Weltall-IA/holo-models`;
- worktree: `/home/alpha/Playstoria/models-embed-batch2-light`;
- branch: `exec/embed-rerank-batch2-light`;
- PR: `#20`, que deve permanecer draft e aberto;
- HEAD inicial completo esperado: substitua pelo SHA completo informado na mensagem de handoff;
- nenhum merge é autorizado.

## Regras obrigatórias

Leia integralmente, nesta ordem:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`;
6. esta instrução;
7. o diff completo do PR #20.

A IA local está autorizada somente a:

- inspecionar o ambiente e os artefatos;
- executar testes e os módulos versionados;
- ajustar o `--batch-size` somente na sequência `8`, `4`, `2`, `1` quando houver OOM real;
- validar os artefatos produzidos;
- commitar somente os resultados listados nesta instrução;
- fazer push no mesmo branch.

A IA local não pode editar código, testes, configuração, documentação ou instruções.

Proibições:

- não executar embeddings;
- não executar Qwen, Voyage ou outro reranker;
- não chamar qualquer API Voyage;
- não baixar modelos, pesos, checkpoints, runtimes ou pacotes;
- não alterar CUDA, driver, PyTorch, Python do sistema ou ambientes existentes;
- não copiar ou renomear candidates entre perfis;
- não sobrescrever scores de outro reranker;
- não alterar `ALL_BENCHMARK_RESULTS.json` ou `README.md`;
- não usar `reset --hard`, `clean`, `checkout --`, stash automático ou force-push;
- não incluir arquivos não rastreados preexistentes no commit;
- não fazer merge.

## 1. Atualização e inventário inicial

Execute:

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
test "$(git rev-parse HEAD)" = "<HEAD_COMPLETO_ESPERADO_DO_HANDOFF>"
test -f .ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.6.md
```

O remote deve corresponder inequivocamente a `Weltall-IA/holo-models`.

Registre antes de qualquer execução:

```bash
git status --short
ps -eo pid,cmd | grep -E 'python|llama|vllm|benchmark|rerank' | grep -v grep || true
free -h
nvidia-smi
```

Arquivos não rastreados conhecidos que devem permanecer intocados:

- `rerank/`;
- `run_bitnet_benchmark.py`;
- `run_light_phase.py`;
- `runtimes/`.

Não inclua nenhum deles no commit.

## 2. Proteção dos resultados concluídos

Antes da execução, grave em `/tmp/embed-rerank-v226-protected.sha256` os SHA-256 de:

- todos os artefatos LFM;
- candidates, scores e pipelines Qwen dos dois Nemotron;
- candidate, score e pipeline Qwen de `voyage-context-4`;
- score global `results/reranker/scores/qwen_local.json`, quando existir;
- os dois artefatos de admissão Nemotron;
- todos os pipelines e scores de rerankers diferentes de `mxbai_rerank_base_v2`.

Use uma lista ordenada e caminhos relativos ao repositório. No final, compare novamente. Nenhum desses arquivos pode mudar.

Também registre separadamente os SHA-256 iniciais dos dois resultados BitNet. Eles mudarão apenas por sanitização portátil:

- `benchmark/embedding-v3/results/gate3/bitnet_06b_current.json`;
- `benchmark/embedding-v3/results/gate3/bitnet_270m_current.json`.

Antes de sanitizá-los, extraia para `/tmp/bitnet-v226-semantic-before.json`:

- `schema_version`;
- `id`;
- `gate`;
- `status`;
- `gate_result`;
- `model`;
- `dataset`;
- `metrics`;
- `completed_at`.

A comparação semântica após a sanitização deve ser exata.

## 3. Python do benchmark

Resolva o mesmo interpretador que aprovou a suíte v2.2.5. Não crie ambiente novo e não instale dependências.

Exemplo de resolução, sem alterar o ambiente:

```bash
PYTHON=""
for candidate in \
  benchmarks/holo-embedding-benchmark-v3/.venv/bin/python \
  /home/alpha/Playstoria/models/benchmarks/holo-embedding-benchmark-v3/.venv/bin/python \
  .venv/bin/python \
  python3; do
  if [ -x "$candidate" ] || command -v "$candidate" >/dev/null 2>&1; then
    PYTHON="$candidate"
    break
  fi
done

test -n "$PYTHON"
"$PYTHON" --version
```

Registre versões realmente usadas:

```bash
"$PYTHON" - <<'PY'
import importlib.metadata
import torch
print("torch", torch.__version__)
print("torch_cuda", torch.version.cuda)
print("cuda_available", torch.cuda.is_available())
print("sentence-transformers", importlib.metadata.version("sentence-transformers"))
print("transformers", importlib.metadata.version("transformers"))
PY
```

`torch.cuda.is_available()` deve ser verdadeiro. Não aceite fallback para CPU.

## 4. Validações anteriores à execução

Execute:

```bash
"$PYTHON" .ai/validate_governance.py
"$PYTHON" -m unittest \
  benchmark.embedding-v3.tests.test_mxbai_panel_benchmark \
  benchmark.embedding-v3.tests.test_bitnet_artifact_finalize -v
"$PYTHON" -m unittest discover -s benchmark/embedding-v3/tests -v
"$PYTHON" -m compileall -q benchmark/embedding-v3

git diff --check
```

Todos devem retornar código 0. Registre o total exato da suíte integral.

Se algum teste falhar, pare e reporte. Não edite código.

## 5. Validação do modelo Mixedbread existente

Modelo autorizado:

- ID: `mxbai_rerank_base_v2`;
- repositório: `mixedbread-ai/mxbai-rerank-base-v2`;
- revisão imutável: `2cae013cb0d1dc0d16409ebd405e35875576d78e`;
- peso: `model.safetensors`;
- SHA-256 esperado: `c01649fe56b3fe32e52da43c69e084dff7c2252cf231a38c56d5a291a674338f`;
- licença: Apache-2.0;
- backend: `sentence-transformers.CrossEncoder`;
- execução: CUDA obrigatória.

O caminho esperado é:

`rerank/mxbai_rerank_base_v2`

Ele é trabalho local preexistente e deve continuar não rastreado. Não mova, copie, renomeie ou versione o diretório.

Valide somente leitura:

```bash
MXBAI_MODEL="rerank/mxbai_rerank_base_v2"
test -d "$MXBAI_MODEL"
test -f "$MXBAI_MODEL/model.safetensors"
test -f "$MXBAI_MODEL/config.json"
test -f "$MXBAI_MODEL/tokenizer.json"

test "$(sha256sum "$MXBAI_MODEL/model.safetensors" | awk '{print $1}')" = \
  "c01649fe56b3fe32e52da43c69e084dff7c2252cf231a38c56d5a291a674338f"
```

Registre bytes do peso e bytes totais do diretório. Nenhum download é permitido.

## 6. Candidates do painel fixo

Os seis perfis obrigatórios são, nesta ordem:

1. `nemotron_3_embed_1b_nvfp4`;
2. `nomic_embed_text_v2_moe_q4`;
3. `qwen3_embedding_4b_q8_0`;
4. `embeddinggemma`;
5. `colibri_ptbr`;
6. `granite_embedding_311m_r2`.

Candidates autorizados:

```text
benchmark/embedding-v3/results/reranker/candidates/nemotron_3_embed_1b_nvfp4.json
benchmark/embedding-v3/results/reranker/candidates/nomic_embed_text_v2_moe_q4.json
benchmark/embedding-v3/results/reranker/candidates/qwen3_embedding_4b_q8_0.json
benchmark/embedding-v3/results/reranker/candidates/embeddinggemma.json
benchmark/embedding-v3/results/reranker/candidates/colibri_ptbr.json
benchmark/embedding-v3/results/reranker/candidates/granite_embedding_311m_r2.json
```

O runner aceita o candidate schema 1.0 do Nemotron e os cinco formatos legados somente depois de validar:

- exatamente 150 consultas do corpus congelado;
- exatamente 50 IDs únicos por consulta;
- todos os IDs existentes no corpus;
- ordem completa das consultas;
- perfil correto;
- hash normalizado do ranking;
- identidade do embedding recuperada do consolidado canônico atual.

Não altere os candidates nesta etapa.

## 7. Sanitização portátil dos resultados BitNet

Execute uma vez para cada perfil:

```bash
"$PYTHON" -m holo_benchmark.bitnet_artifact_finalize \
  --profile-id bitnet_06b_current \
  --result benchmark/embedding-v3/results/gate3/bitnet_06b_current.json

"$PYTHON" -m holo_benchmark.bitnet_artifact_finalize \
  --profile-id bitnet_270m_current \
  --result benchmark/embedding-v3/results/gate3/bitnet_270m_current.json
```

O módulo deve retornar `PASS`. Depois:

- nenhum caminho absoluto ou nome local pode permanecer;
- o JSON semântico protegido deve ser idêntico ao arquivo anterior;
- os resultados continuam `COMPLETED` e gate `FAIL`;
- não gere candidates ou rerankers BitNet;
- não altere os tempos ou métricas.

Se a comparação semântica divergir, pare sem commit e reporte.

## 8. Execução Mixedbread

Configure modo offline:

```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
unset VOYAGE_API_KEY
unset VOYAGE_API_KEY_PATH
```

Crie somente os diretórios de resultados versionados:

```bash
mkdir -p benchmark/embedding-v3/results/reranker/scores/mxbai_rerank_base_v2
mkdir -p benchmark/embedding-v3/results/reranker/pipelines/mxbai_rerank_base_v2
```

Execute um perfil por vez, liberando memória entre eles. Comece com batch 8. Reduza apenas após OOM real para 4, depois 2, depois 1. Não mude instrução, candidates, top-k, precisão, backend ou dispositivo.

Para cada perfil `PROFILE` e candidate `CANDIDATE`, execute:

```bash
"$PYTHON" -m holo_benchmark.mxbai_panel_benchmark \
  --profile-id "$PROFILE" \
  --model-path "$MXBAI_MODEL" \
  --candidate "$CANDIDATE" \
  --canonical benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json \
  --score-output "benchmark/embedding-v3/results/reranker/scores/mxbai_rerank_base_v2/${PROFILE}.json" \
  --pipeline-output "benchmark/embedding-v3/results/reranker/pipelines/mxbai_rerank_base_v2/${PROFILE}.json" \
  --batch-size 8
```

Depois de cada perfil:

- confirme saída `PASS`;
- confirme 7.500 pares;
- confirme CUDA e pico de VRAM positivo;
- confirme 150 consultas, 50 scores por consulta e scores finitos;
- confirme candidate ranking SHA-256;
- confirme `base_metrics`, `reranked_metrics`, `effect` e 150 `per_query_effect`;
- confirme sete tipos de consulta;
- confirme ausência de caminhos absolutos;
- encerre processos e registre RAM/VRAM antes de seguir.

Se um perfil falhar por OOM, tente a sequência de batch autorizada. Se falhar por identidade do peso, candidate, score inválido ou erro de modelo depois das duas formas de carregamento já implementadas, pare e reporte o erro exato. Não preserve JSON parcial e não pule para o perfil seguinte.

## 9. Validação estrutural do painel

Depois das seis execuções, valide programaticamente:

- exatamente seis scores em `scores/mxbai_rerank_base_v2/`;
- exatamente seis pipelines em `pipelines/mxbai_rerank_base_v2/`;
- nenhum outro perfil no diretório;
- todos com schema 1.0;
- mesmo repositório, revisão, peso e hash Mixedbread;
- cada score com 7.500 pares e 150 consultas;
- cada pipeline com top 50, rerank top 20 e 150 efeitos;
- métricas completas e finitas;
- runtime CUDA e VRAM positiva;
- score artifact relativo correto;
- ranking SHA do pipeline igual ao score;
- nenhum caminho absoluto ou identificador do host.

Os cinco pipelines incompletos existentes devem ser substituídos pelos resultados reais. O sexto, `nemotron_3_embed_1b_nvfp4`, deve ser novo.

`benchmark/embedding-v3/results/mxbai_panel_results.json` deve continuar ausente. Não crie resumo paralelo.

## 10. Proteções posteriores

Compare `/tmp/embed-rerank-v226-protected.sha256` com os hashes posteriores. Todos os artefatos protegidos devem permanecer byte a byte iguais.

Compare os campos semânticos BitNet extraídos antes e depois. Devem ser idênticos.

Confirme que:

- candidates não mudaram;
- Qwen, LFM, Nemotron e Voyage não mudaram;
- nenhum arquivo de modelo ou runtime foi rastreado;
- `ALL_BENCHMARK_RESULTS.json` e `README.md` não mudaram;
- arquivos não rastreados preexistentes continuam presentes e fora do índice.

## 11. Validações finais

Execute novamente:

```bash
"$PYTHON" .ai/validate_governance.py
"$PYTHON" -m unittest discover -s benchmark/embedding-v3/tests -v
"$PYTHON" -m compileall -q benchmark/embedding-v3
"$PYTHON" benchmark/embedding-v3/validate_coverage.py
git diff --check
```

Todos devem retornar código 0.

Revise o diff completo. Não prossiga se houver arquivo fora do escopo.

## 12. Escopo exato do commit de execução

O commit local deve conter exatamente 14 arquivos de resultados:

- dois resultados BitNet sanitizados;
- seis scores Mixedbread;
- seis pipelines Mixedbread.

Arquivos BitNet:

```text
benchmark/embedding-v3/results/gate3/bitnet_06b_current.json
benchmark/embedding-v3/results/gate3/bitnet_270m_current.json
```

Scores:

```text
benchmark/embedding-v3/results/reranker/scores/mxbai_rerank_base_v2/<perfil>.json
```

Pipelines:

```text
benchmark/embedding-v3/results/reranker/pipelines/mxbai_rerank_base_v2/<perfil>.json
```

Use uma mensagem objetiva, por exemplo:

```text
Complete canonical Mixedbread panel and sanitize BitNet results
```

Depois:

```bash
git status --short
git diff --cached --name-only
git commit -m "Complete canonical Mixedbread panel and sanitize BitNet results"
git push origin exec/embed-rerank-batch2-light
```

Não faça merge.

## 13. Retorno obrigatório

Reporte:

1. HEAD inicial completo e HEAD final completo;
2. worktree antes e depois;
3. interpretador e versões efetivas;
4. identidade, bytes e SHA-256 do Mixedbread;
5. todos os comandos e exit codes;
6. total exato da suíte antes e depois;
7. strings sanitizadas por BitNet e prova de invariância semântica;
8. ranking SHA de cada um dos seis candidates;
9. runtime por perfil: batch, tempo, pares, RAM e VRAM;
10. métricas base e reranked completas por perfil;
11. rescue, damage e erros por perfil;
12. SHA-256 dos seis scores e seis pipelines;
13. hashes dos artefatos protegidos antes/depois;
14. lista exata dos 14 arquivos commitados;
15. confirmação de ausência de downloads, embeddings, APIs, edição de código e merge.

Título do retorno:

`Retorno v2.2.6 — Painel Mixedbread canônico e portabilidade BitNet`
