# INSTRUCTIONS v2.1.6 — execução do código BitNet implementado pelo gerente

## Objetivo

Executar e validar, na máquina que contém os pesos e runtimes locais, o código BitNet já implementado pelo gerente técnico no PR #20.

Esta instrução **não autoriza programação pela IA local**. Não editar arquivos Python, testes, schemas, geradores ou instruções. Quando houver defeito de código, teste falhando ou incompatibilidade do entrypoint, pare e reporte a evidência objetiva para correção pelo gerente.

Contrato técnico obrigatório:

`benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`

## Repositório, branch e PR

- Repositório: `Weltall-IA/holo-models`
- Worktree: `/home/alpha/Playstoria/models-embed-batch2-light`
- Branch: `exec/embed-rerank-batch2-light`
- PR: `#20`
- Estado obrigatório: aberto e draft

Não crie outro PR. Não faça merge.

## 1. Atualização obrigatória

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
test -f .ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.6.md
```

O remote deve corresponder a `Weltall-IA/holo-models`.

Antes da execução, registre staged, unstaged, não rastreados, processos ativos, RAM, VRAM, caminhos e SHA-256 dos dois GGUF BitNet e do binário `llama-embedding`.

Não use `reset --hard`, `clean`, `checkout --`, stash automático, force-push ou recriação da worktree.

## 2. Leitura obrigatória

Leia integralmente, nesta ordem:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`;
6. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.4.md`;
7. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.5.md`;
8. este arquivo;
9. diff e descrição atual do PR #20.

## 3. Proibição de alterações de código

Não modificar:

- `benchmark/embedding-v3/holo_benchmark/bitnet_parser.py`;
- `benchmark/embedding-v3/holo_benchmark/bitnet_runner.py`;
- `benchmark/embedding-v3/holo_benchmark/bitnet_benchmark.py`;
- `benchmark/embedding-v3/tests/test_bitnet_parser.py`;
- qualquer outro `.py`, schema, gerador ou teste.

Não criar scripts temporários para substituir o entrypoint versionado.

Se qualquer teste ou comando revelar defeito no código, preserve stdout/stderr sanitizado, informe o comando e o traceback e pare sem corrigir.

## 4. Validação do código recebido

Execute a partir da raiz da worktree:

```bash
python .ai/validate_governance.py
PYTHONPATH=benchmark/embedding-v3 python -m unittest \
  benchmark/embedding-v3/tests/test_bitnet_parser.py -v
PYTHONPATH=benchmark/embedding-v3 python -m compileall -q \
  benchmark/embedding-v3/holo_benchmark/bitnet_parser.py \
  benchmark/embedding-v3/holo_benchmark/bitnet_runner.py \
  benchmark/embedding-v3/holo_benchmark/bitnet_benchmark.py
git diff --check
```

Registre comando, exit code e quantidade real de testes.

Depois execute a suíte integral do projeto:

```bash
PYTHONPATH=benchmark/embedding-v3 python -m unittest discover \
  -s benchmark/embedding-v3/tests -v
```

Não declare suíte integral aprovada quando somente o arquivo BitNet tiver sido executado.

## 5. Resolver caminhos e identidade do runtime

```bash
BITNET_BIN="runtimes/BitNet/build/bin/llama-embedding"
BITNET_COMMIT="$(git -C runtimes/BitNet rev-parse HEAD)"
BITNET_BIN_SHA256="$(sha256sum "$BITNET_BIN" | awk '{print $1}')"

BITNET_06B_GGUF="embed/bitnet_06b_current/bitnet-embeddings-0.6b-bf16-i2_s.gguf"
BITNET_270M_GGUF="embed/bitnet_270m_current/bitnet-embeddings-270m-bf16-i2_s.gguf"

sha256sum "$BITNET_BIN" "$BITNET_06B_GGUF" "$BITNET_270M_GGUF"
stat -c '%n %s bytes' "$BITNET_BIN" "$BITNET_06B_GGUF" "$BITNET_270M_GGUF"
```

Confirme que:

- binário e pesos são arquivos regulares;
- o binário é executável;
- os hashes dos GGUF correspondem aos downloads previamente verificados;
- não houve novo download.

## 6. Executar BitNet 0.6B pelo entrypoint versionado

```bash
PYTHONPATH=benchmark/embedding-v3 python -m holo_benchmark.bitnet_benchmark \
  --profile-id bitnet_06b_current \
  --gguf-path "$BITNET_06B_GGUF" \
  --bitnet-bin "$BITNET_BIN" \
  --bitnet-commit "$BITNET_COMMIT" \
  --revision 16176d108561b62e3d6f2b558587afe1140b413f \
  --license MIT \
  --hardware-json benchmark/embedding-v3/system_info.json
```

O resultado deve ser gravado por `atomic_json` em:

`benchmark/embedding-v3/results/gate3/bitnet_06b_current.json`

Se o gate continuar FAIL, não produzir nem publicar candidate Qwen para esse perfil.

## 7. Executar BitNet 270M pelo entrypoint versionado

```bash
PYTHONPATH=benchmark/embedding-v3 python -m holo_benchmark.bitnet_benchmark \
  --profile-id bitnet_270m_current \
  --gguf-path "$BITNET_270M_GGUF" \
  --bitnet-bin "$BITNET_BIN" \
  --bitnet-commit "$BITNET_COMMIT" \
  --revision 5f1c2fd19f37ca653a3d719c8ee6cc1895f4b64f \
  --license MIT \
  --hardware-json benchmark/embedding-v3/system_info.json
```

Quando o gate for PASS, o entrypoint deve:

- gravar o resultado completo em `results/gate3/bitnet_270m_current.json`;
- gravar candidate em `results/reranker/candidates/bitnet_270m_current.json`;
- validar o candidate com `load_candidate_payloads` real;
- registrar 150 queries, top 50, IDs únicos, corpus SHA-256 e `ranking_sha256`.

## 8. Validação programática dos artefatos

Sem editar os JSON manualmente, confirme:

- `metrics.per_query` possui 150 entradas nos dois resultados;
- `metrics.by_query_type` não está vazio;
- nDCG@10, mean/median first relevant rank e hard-negative error rate foram calculados pelo avaliador;
- runtime contém comando sanitizado, exit code, duração combinada, throughput, RAM, VRAM residual, binário, commit e hashes;
- dataset contém 600 documentos, 150 queries e o SHA-256 congelado;
- o candidate 270M possui schema `1.0`, `variant`, `dataset`, top 50 e ordem congelada;
- nenhum zero foi inserido como placeholder;
- nenhum candidate foi publicado para o 0.6B reprovado.

Execute também:

```bash
PYTHONPATH=benchmark/embedding-v3 python benchmark/embedding-v3/validate_coverage.py
PYTHONPATH=benchmark/embedding-v3 python benchmark/embedding-v3/reranker_benchmark.py --phase preflight
git diff --check
git status --short
```

## 9. Limites

- Não chamar API Voyage.
- Não baixar ou executar modelos pesados.
- Não alterar CUDA, driver, PyTorch global, Python do sistema ou pacotes globais.
- Não executar Qwen ou Mixedbread nesta etapa.
- Não regenerar `ALL_BENCHMARK_RESULTS.json` nesta etapa.
- Não atualizar README nesta etapa.
- Não editar código para contornar falha.
- Não fazer merge.

## 10. Commit e retorno

Inclua somente os dois resultados BitNet e o candidate 270M realmente regenerados. Não inclua caches, pesos, ambientes ou logs extensos.

Faça commit e push no mesmo branch. Mantenha o PR draft.

No retorno, informe:

- HEAD inicial e final completos;
- comandos e exit codes;
- total da suíte BitNet e da suíte integral;
- hashes do binário e pesos;
- métricas completas dos dois BitNet;
- gates finais;
- validação do candidate 270M pelo loader real;
- arquivos alterados;
- confirmação de que nenhum código foi editado;
- confirmação de ausência de Voyage, modelos pesados e merge.

A resposta deve terminar exatamente com:

`Versão do retorno da IA local: 2.1.6 — Execução do código BitNet implementado pelo gerente`
