# INSTRUCTIONS v2.2.8 — completar snapshot Mixedbread e retomar protocolo nativo

## Estado e objetivo

O retorno v2.2.7 terminou corretamente como `BLOCKED` antes de executar qualquer benchmark porque o diretório local `rerank/mxbai_rerank_base_v2` não contém o snapshot completo exigido pelo protocolo oficial.

O bloqueio não reprova nem abandona o modelo. Esta instrução autoriza uma única correção de dependência:

1. baixar exclusivamente os oito arquivos críticos não-peso da revisão imutável `3ea9d4dffa7d12a4f366be8e275c349de9fc9865`;
2. comprovar que os nove arquivos críticos e seus metadados pertencem à mesma revisão;
3. preservar byte a byte `model.safetensors` e todos os resultados aceitos;
4. executar o smoke oficial e, somente após PASS, substituir os 12 artefatos Mixedbread inválidos de `1cda1db32ae20be61112b2cc527135b0109317ca`;
5. validar e commitar somente esses 12 artefatos.

Esta etapa não executa embeddings, Qwen, Voyage ou NVIDIA Nemotron. Não regenera `ALL_BENCHMARK_RESULTS.json`, não atualiza `README.md` e não conclui o lote.

## Repositório, branch e PR

- repositório: `Weltall-IA/holo-models`;
- worktree: `/home/alpha/Playstoria/models-embed-batch2-light`;
- branch: `exec/embed-rerank-batch2-light`;
- PR: `#20`, que deve permanecer aberto e draft;
- HEAD inicial: deve coincidir exatamente com o SHA completo informado no handoff;
- nenhum merge é autorizado.

## Leitura obrigatória

Leia integralmente, nesta ordem:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`;
6. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.7.md`;
7. esta instrução;
8. diff completo do PR #20.

Esta v2.2.8 substitui somente a proibição de download da v2.2.7. Todas as demais proteções, comandos de teste, protocolo nativo, perfis, outputs, validações e formato de retorno da v2.2.7 permanecem vigentes.

A IA local pode somente:

- inspecionar o ambiente;
- baixar os oito arquivos explicitamente autorizados nesta instrução, da revisão fixada e do repositório fixado;
- executar testes e módulos já versionados;
- substituir os 12 resultados Mixedbread autorizados;
- validar, commitar e fazer push no mesmo branch.

A IA local não pode editar código, testes, configuração, documentação ou instruções.

## Proibições

- não baixar `model.safetensors` novamente;
- não baixar qualquer arquivo fora da lista exata desta instrução;
- não usar outra revisão, branch ou repositório do modelo;
- não instalar ou atualizar `huggingface_hub`, CLI, Python, PyTorch, CUDA, driver ou qualquer pacote;
- não executar ou repetir embeddings;
- não executar Qwen, Voyage, NVIDIA Nemotron ou outro reranker;
- não chamar APIs Voyage ou qualquer API paga;
- não incluir `rerank/` ou seus metadados no commit;
- não alterar os dois BitNet sanitizados;
- não alterar candidates;
- não alterar `ALL_BENCHMARK_RESULTS.json` ou `README.md`;
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
test -f .ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.8.md
```

Confirme que o remote corresponde inequivocamente a `Weltall-IA/holo-models` e que o HEAD coincide com o handoff. Em divergência, pare.

Preserve sem inclusão no commit:

- `rerank/`;
- `run_bitnet_benchmark.py`;
- `run_light_phase.py`;
- `runtimes/`.

## 2. Ambiente e proteção dos artefatos

Use o mesmo interpretador já aprovado:

```bash
PYTHON=/home/alpha/Playstoria/models/benchmarks/holo-embedding-benchmark-v3/.venv/bin/python
test -x "$PYTHON"
export PYTHONPATH="$PWD/benchmark/embedding-v3${PYTHONPATH:+:$PYTHONPATH}"
"$PYTHON" --version
```

Antes de qualquer download:

1. aplique integralmente a proteção de artefatos da seção 2 da v2.2.7;
2. registre separadamente os SHA-256 antigos dos 12 outputs Mixedbread que serão substituídos;
3. registre `git status --short`;
4. registre espaço livre, RAM e VRAM;
5. confirme que nenhum processo de benchmark ou servidor está ativo.

## 3. Proteção do peso e inventário local

```bash
MODEL_DIR=rerank/mxbai_rerank_base_v2
REVISION=3ea9d4dffa7d12a4f366be8e275c349de9fc9865
WEIGHT="$MODEL_DIR/model.safetensors"

test -d "$MODEL_DIR"
test -f "$WEIGHT"
test "$(stat -c '%s' "$WEIGHT")" = "988097536"
test "$(sha256sum "$WEIGHT" | awk '{print $1}')" = \
  "c01649fe56b3fe32e52da43c69e084dff7c2252cf231a38c56d5a291a674338f"

sha256sum "$WEIGHT" > /tmp/mxbai-v228-weight-before.sha256
find "$MODEL_DIR" -type f -printf '%P\n' | sort > /tmp/mxbai-v228-files-before.txt
```

Registre também os hashes e bytes dos oito arquivos abaixo quando já existirem. A existência prévia não os torna confiáveis sem metadata da revisão fixada.

## 4. Download estritamente limitado

Arquivos autorizados, exatamente:

```text
config.json
tokenizer.json
tokenizer_config.json
modules.json
sentence_bert_config.json
config_sentence_transformers.json
chat_template.jinja
1_LogitScore/config.json
```

O peso `model.safetensors` não aparece na lista e não pode ser transferido.

Antes do download, remova somente as variáveis de modo offline para esta operação:

```bash
unset HF_HUB_OFFLINE
unset TRANSFORMERS_OFFLINE
unset HF_DATASETS_OFFLINE
unset VOYAGE_API_KEY
unset VOYAGE_API_KEY_PATH
```

Resolva uma ferramenta já instalada, sem instalar nada:

```bash
HF_CLI=""
if command -v hf >/dev/null 2>&1; then
  HF_CLI=hf
elif command -v huggingface-cli >/dev/null 2>&1; then
  HF_CLI=huggingface-cli
fi
printf 'HF CLI: %s\n' "$HF_CLI"
```

### Caminho preferencial — CLI já instalada

Quando `HF_CLI` não estiver vazio, execute uma vez:

```bash
"$HF_CLI" download mixedbread-ai/mxbai-rerank-base-v2 \
  config.json \
  tokenizer.json \
  tokenizer_config.json \
  modules.json \
  sentence_bert_config.json \
  config_sentence_transformers.json \
  chat_template.jinja \
  1_LogitScore/config.json \
  --revision "$REVISION" \
  --local-dir "$MODEL_DIR"
```

### Fallback autorizado — biblioteca já instalada

Use este fallback somente quando nenhuma das duas CLIs existir ou quando a CLI rejeitar a sintaxe antes de iniciar transferências. Não instale pacote.

```bash
"$PYTHON" - <<'PY'
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="mixedbread-ai/mxbai-rerank-base-v2",
    revision="3ea9d4dffa7d12a4f366be8e275c349de9fc9865",
    local_dir="rerank/mxbai_rerank_base_v2",
    allow_patterns=[
        "config.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "modules.json",
        "sentence_bert_config.json",
        "config_sentence_transformers.json",
        "chat_template.jinja",
        "1_LogitScore/config.json",
    ],
)
PY
```

Regras de falha:

- em erro transitório HTTP, Xet ou conexão, repita somente uma vez a mesma operação com a mesma lista, repositório e revisão;
- é permitido definir `HF_HUB_DISABLE_XET=1` na repetição, sem instalar dependências;
- se a primeira operação criar os arquivos mas deixar algum metadata ausente, é permitido repetir somente os oito arquivos com `--force-download` quando a CLI suportar essa opção;
- nunca inclua `model.safetensors` na repetição;
- em 401/403, revisão inexistente, divergência de repositório ou arquivo ausente na revisão fixada, pare e reporte;
- não troque de revisão para contornar erro.

## 5. Validação pós-download e retorno ao modo offline

Imediatamente após o download:

```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
unset VOYAGE_API_KEY
unset VOYAGE_API_KEY_PATH

sha256sum -c /tmp/mxbai-v228-weight-before.sha256
```

A seguir, execute a validação canônica:

```bash
"$PYTHON" - <<'PY'
from pathlib import Path
from holo_benchmark.mxbai_panel_protocol import validate_complete_model

path, identity = validate_complete_model(
    Path("rerank/mxbai_rerank_base_v2"),
    "3ea9d4dffa7d12a4f366be8e275c349de9fc9865",
)
print("model_dir", path)
for item in identity["critical_snapshot_files"]:
    print(item["file"], item["bytes"], item["sha256"], item["revision"])
PY
```

A validação deve comprovar os nove arquivos críticos:

```text
model.safetensors
config.json
tokenizer.json
tokenizer_config.json
modules.json
sentence_bert_config.json
config_sentence_transformers.json
chat_template.jinja
1_LogitScore/config.json
```

Para cada arquivo deve existir `.cache/huggingface/download/<caminho>.metadata`, cuja primeira linha seja exatamente `3ea9d4dffa7d12a4f366be8e275c349de9fc9865`.

Também valide explicitamente:

```bash
"$PYTHON" - <<'PY'
import json
from pathlib import Path

root = Path("rerank/mxbai_rerank_base_v2")
modules = json.loads((root / "modules.json").read_text(encoding="utf-8"))
assert any(
    item.get("path") == "1_LogitScore"
    and str(item.get("type", "")).endswith(".LogitScore")
    for item in modules
)
assert (root / "1_LogitScore/config.json").is_file()
print("modules.json e LogitScore: PASS")
PY
```

Se qualquer validação falhar, pare sem executar o painel e reporte os arquivos/metadados divergentes. Não edite arquivos manualmente.

O diretório `rerank/` continua não rastreado e não entra no commit.

## 6. Testes e smoke

Depois que o snapshot passar integralmente, execute todos os testes obrigatórios da seção 4 da v2.2.7.

Resultados focados mínimos esperados:

- `test_mxbai_panel_protocol.py`: `7/7` PASS;
- `test_mxbai_panel_execution.py`: `3/3` PASS;
- `test_mxbai_panel_benchmark.py`: `5/5` PASS.

A suíte integral deve ter pelo menos `212` testes e zero falhas ou erros. Execute também `compileall` e `git diff --check`.

Depois execute integralmente o smoke da seção 6 da v2.2.7. Ele deve comprovar:

- módulo `LogitScore` carregado;
- ativação identidade;
- pares brutos oficiais;
- passagem de Marte em top-1;
- margem positiva;
- scores finitos;
- CUDA com VRAM positiva.

Sem smoke PASS, pare sem substituir resultados.

## 7. Reexecução dos seis perfis

Após o smoke, execute integralmente a seção 7 da v2.2.7, na mesma ordem e com os mesmos candidates:

1. `nemotron_3_embed_1b_nvfp4`;
2. `nomic_embed_text_v2_moe_q4`;
3. `qwen3_embedding_4b_q8_0`;
4. `embeddinggemma`;
5. `colibri_ptbr`;
6. `granite_embedding_311m_r2`.

Regras:

- use `mxbai_panel_execution` com `--model-revision "$REVISION"`;
- use pares brutos `(query, document)`;
- não passe instrução genérica;
- comece com batch 8 e reduza somente após OOM real: 4, 2, 1;
- não pule perfil após erro corrigível;
- execute um perfil por vez;
- libere memória entre perfis;
- substitua exatamente os seis scores e seis pipelines Mixedbread;
- não altere candidates nem outros resultados.

Métrica baixa, se produzida após snapshot completo, smoke oficial PASS e protocolo correto, é resultado real e deve ser preservada. Não interrompa nem descarte um perfil somente porque sua métrica foi inferior à base.

## 8. Validações finais

Execute integralmente as validações pós-execução da v2.2.7 e confirme:

- seis scores schema 1.0;
- seis pipelines schema 1.0;
- 7.500 pares por perfil;
- 150 consultas por perfil;
- 50 IDs e 50 scores finitos por consulta;
- candidate ranking SHA-256 correto;
- revisão `3ea9d4dffa7d12a4f366be8e275c349de9fc9865`;
- peso com bytes e SHA-256 fixados;
- `input_format = raw_query_document_pair`;
- `LogitScore` registrado;
- base, reranked e per-query-effect completos;
- sete tipos de consulta;
- CUDA e VRAM positiva;
- nenhuma string absoluta do host nos artefatos;
- todos os artefatos protegidos inalterados;
- os 12 outputs antigos substituídos;
- `model.safetensors` inalterado;
- `rerank/` ainda não rastreado;
- `ALL_BENCHMARK_RESULTS.json` e `README.md` inalterados.

Execute novamente:

```bash
"$PYTHON" .ai/validate_governance.py
"$PYTHON" -m unittest discover -s benchmark/embedding-v3/tests -v
"$PYTHON" -m compileall -q benchmark/embedding-v3
"$PYTHON" benchmark/embedding-v3/validate_coverage.py
git diff --check
```

Todos os comandos devem retornar código 0.

## 9. Commit e push

O commit pode conter exatamente estes 12 caminhos:

```text
benchmark/embedding-v3/results/reranker/scores/mxbai_rerank_base_v2/nemotron_3_embed_1b_nvfp4.json
benchmark/embedding-v3/results/reranker/scores/mxbai_rerank_base_v2/nomic_embed_text_v2_moe_q4.json
benchmark/embedding-v3/results/reranker/scores/mxbai_rerank_base_v2/qwen3_embedding_4b_q8_0.json
benchmark/embedding-v3/results/reranker/scores/mxbai_rerank_base_v2/embeddinggemma.json
benchmark/embedding-v3/results/reranker/scores/mxbai_rerank_base_v2/colibri_ptbr.json
benchmark/embedding-v3/results/reranker/scores/mxbai_rerank_base_v2/granite_embedding_311m_r2.json
benchmark/embedding-v3/results/reranker/pipelines/mxbai_rerank_base_v2/nemotron_3_embed_1b_nvfp4.json
benchmark/embedding-v3/results/reranker/pipelines/mxbai_rerank_base_v2/nomic_embed_text_v2_moe_q4.json
benchmark/embedding-v3/results/reranker/pipelines/mxbai_rerank_base_v2/qwen3_embedding_4b_q8_0.json
benchmark/embedding-v3/results/reranker/pipelines/mxbai_rerank_base_v2/embeddinggemma.json
benchmark/embedding-v3/results/reranker/pipelines/mxbai_rerank_base_v2/colibri_ptbr.json
benchmark/embedding-v3/results/reranker/pipelines/mxbai_rerank_base_v2/granite_embedding_311m_r2.json
```

Antes do commit, use `git diff --name-only` e rejeite qualquer caminho adicional.

Mensagem sugerida:

`Rerun Mixedbread panel with complete native snapshot`

Faça push para `exec/embed-rerank-batch2-light`. Não faça merge.

## 10. Retorno obrigatório

Título:

`Retorno v2.2.8 — Snapshot Mixedbread completo e painel nativo reexecutado`

Inclua:

1. HEAD inicial e final completos;
2. status antes/depois e arquivos não rastreados preservados;
3. ferramenta de download usada e exit code;
4. confirmação de que somente os oito arquivos não-peso foram solicitados;
5. bytes e SHA-256 do peso antes/depois;
6. para cada um dos nove arquivos críticos: caminho, bytes, SHA-256 e revisão do metadata;
7. smoke completo, scores, top index, margem, módulos carregados, device e VRAM;
8. comandos e exit codes;
9. total de testes antes/depois;
10. para cada perfil: ranking SHA, batch, tempo, pares, RAM, VRAM, métricas base e reranked, rescue e damage;
11. SHA-256 antes/depois dos 12 outputs;
12. lista exata dos arquivos commitados;
13. confirmação de que nenhum arquivo de `rerank/` entrou no commit;
14. confirmação de que candidates, BitNet, LFM, Nemotron Qwen, Voyage, consolidado e README permaneceram inalterados;
15. confirmação de ausência de APIs, embeddings, outros modelos e merge.

Se o snapshot continuar bloqueado, não faça commit. Retorne o comando tentado, exit code, erro sanitizado, arquivos presentes, metadados presentes e confirmação de que o peso permaneceu inalterado.

`Versão do retorno da IA local: 2.2.8 — Snapshot Mixedbread completo e painel nativo reexecutado`
