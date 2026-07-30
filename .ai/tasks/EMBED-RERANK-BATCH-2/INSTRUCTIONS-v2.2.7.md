# INSTRUCTIONS v2.2.7 — correção do protocolo Mixedbread

## Estado e objetivo

Esta é a instrução ativa para corrigir exclusivamente os 12 artefatos Mixedbread produzidos no commit `1cda1db32ae20be61112b2cc527135b0109317ca`.

A sanitização dos dois BitNet desse commit está aceita e deve permanecer byte a byte inalterada.

Os seis resultados Mixedbread de `1cda1db` não estão aceitos. O padrão `HitRate@1` entre `0.0067` e `0.0267`, perda de mais de metade dos relevantes no top 20 e dezenas de consultas sem relevante é uma falha de protocolo, não uma decisão de qualidade do modelo.

Causa corrigida no código versionado:

1. o runner anterior validava apenas peso, `config.json` e `tokenizer.json`, embora a integração oficial Sentence Transformers da revisão `3ea9d4dffa7d12a4f366be8e275c349de9fc9865` dependa também de `modules.json`, `1_LogitScore/config.json`, `sentence_bert_config.json`, `config_sentence_transformers.json` e `chat_template.jinja`;
2. o runner anterior acrescentava uma instrução genérica à consulta; o protocolo oficial do modelo usa o par bruto `(query, passage)`;
3. o runner anterior não comprovava que o módulo `LogitScore` foi carregado e não bloqueava um fallback genérico ou head aleatório;
4. o runner corrigido exige snapshot local coerente, `LogitScore`, logits com ativação identidade e smoke semântico oficial antes de pontuar o corpus Holo.

Esta etapa não executa embeddings, Qwen, Voyage ou NVIDIA Nemotron. Não regenera `ALL_BENCHMARK_RESULTS.json`, não atualiza `README.md` e não conclui o lote.

## Repositório e branch

- repositório: `Weltall-IA/holo-models`;
- worktree: `/home/alpha/Playstoria/models-embed-batch2-light`;
- branch: `exec/embed-rerank-batch2-light`;
- PR: `#20`, aberto e draft;
- HEAD inicial: deve corresponder exatamente ao SHA completo informado no handoff;
- nenhum merge é autorizado.

## Autoridade e leitura obrigatória

Leia integralmente, nesta ordem:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`;
6. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.6.md`;
7. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.6.1.md`;
8. esta instrução;
9. diff completo do PR #20.

A regra específica desta instrução substitui, para `mxbai_rerank_base_v2`, qualquer interpretação que aplique a instrução genérica de reranking. O formato obrigatório é o par bruto oficial de consulta e documento.

A IA local pode somente inspecionar, testar, executar o código versionado, validar, commitar os 12 resultados autorizados e fazer push no mesmo branch. Não pode editar código, testes, configuração, documentação ou instruções.

## Proibições

- não executar ou repetir embeddings;
- não executar Qwen, Voyage, NVIDIA Nemotron ou outro reranker;
- não chamar APIs;
- não baixar ou atualizar arquivos do modelo;
- não instalar ou atualizar pacotes;
- não alterar Python, PyTorch, CUDA ou driver;
- não usar `reset --hard`, `clean`, `checkout --`, stash automático ou force-push;
- não incluir arquivos não rastreados preexistentes;
- não alterar os dois BitNet sanitizados;
- não alterar `ALL_BENCHMARK_RESULTS.json` ou `README.md`;
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
test -f .ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.7.md
```

Confirme que o remote corresponde inequivocamente a `Weltall-IA/holo-models` e que o HEAD coincide com o handoff. Em divergência, pare.

Preserve sem inclusão no commit:

- `rerank/`;
- `run_bitnet_benchmark.py`;
- `run_light_phase.py`;
- `runtimes/`.

## 2. Proteção de artefatos

Antes de qualquer teste ou load do modelo, grave uma lista ordenada de SHA-256 de todos os arquivos rastreados sob:

- `benchmark/embedding-v3/results/gate3/`;
- `benchmark/embedding-v3/results/reranker/candidates/`;
- `benchmark/embedding-v3/results/reranker/scores/`;
- `benchmark/embedding-v3/results/reranker/pipelines/`;

Exclua da lista protegida somente estes 12 caminhos, que serão substituídos:

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

Registre separadamente os SHA-256 antigos desses 12 arquivos. Ao final, todos os protegidos devem permanecer idênticos e os 12 antigos devem ter sido substituídos.

## 3. Ambiente Python

Use o mesmo interpretador aprovado na v2.2.6:

```bash
PYTHON=/home/alpha/Playstoria/models/benchmarks/holo-embedding-benchmark-v3/.venv/bin/python
test -x "$PYTHON"
export PYTHONPATH="$PWD/benchmark/embedding-v3${PYTHONPATH:+:$PYTHONPATH}"

export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
unset VOYAGE_API_KEY
unset VOYAGE_API_KEY_PATH

"$PYTHON" --version
"$PYTHON" - <<'PY'
import importlib.metadata
import torch
import holo_benchmark
print("holo_benchmark", holo_benchmark.__file__)
print("torch", torch.__version__)
print("torch_cuda", torch.version.cuda)
print("cuda_available", torch.cuda.is_available())
print("sentence-transformers", importlib.metadata.version("sentence-transformers"))
PY
```

CUDA deve estar disponível. Não aceite fallback para CPU.

## 4. Testes obrigatórios anteriores

```bash
"$PYTHON" .ai/validate_governance.py

"$PYTHON" -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_mxbai_panel_protocol.py' -v

"$PYTHON" -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_mxbai_panel_execution.py' -v

"$PYTHON" -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_mxbai_panel_benchmark.py' -v

"$PYTHON" -m unittest discover -s benchmark/embedding-v3/tests -v
"$PYTHON" -m compileall -q benchmark/embedding-v3
git diff --check
```

Resultados focados esperados:

- protocolo nativo: `7/7` PASS;
- bootstrap de execução: `3/3` PASS;
- serializer/evaluator Mixedbread: `5/5` PASS.

A suíte integral deve ter pelo menos `212` testes e zero falhas. Reporte a contagem real. Em qualquer falha, pare sem editar código.

## 5. Validação integral do snapshot local

Modelo local:

`rerank/mxbai_rerank_base_v2`

Revisão imutável esperada:

`3ea9d4dffa7d12a4f366be8e275c349de9fc9865`

Peso esperado:

- arquivo: `model.safetensors`;
- bytes: `988097536`;
- SHA-256: `c01649fe56b3fe32e52da43c69e084dff7c2252cf231a38c56d5a291a674338f`.

O snapshot deve conter todos os arquivos críticos:

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

Para cada caminho acima deve existir o metadata correspondente sob:

`.cache/huggingface/download/<caminho>.metadata`

A primeira linha de todos os nove metadados deve ser exatamente a mesma revisão imutável esperada. O runner valida bytes e SHA-256 de todos os arquivos e aborta se qualquer arquivo estiver ausente ou vier de revisão divergente.

Execute somente leitura:

```bash
"$PYTHON" - <<'PY'
from pathlib import Path
from holo_benchmark.mxbai_panel_protocol import validate_complete_model

path, identity = validate_complete_model(
    Path("rerank/mxbai_rerank_base_v2"),
    "3ea9d4dffa7d12a4f366be8e275c349de9fc9865",
)
print(path)
for item in identity["critical_snapshot_files"]:
    print(item["file"], item["bytes"], item["sha256"], item["revision"])
PY
```

Se algum arquivo ou metadata estiver ausente, pare e reporte. Não baixe nada nesta etapa.

## 6. Smoke semântico oficial obrigatório

Carregue uma vez o modelo em CUDA, offline, e execute o smoke oficial antes do corpus:

```bash
"$PYTHON" - <<'PY'
from pathlib import Path
import torch
from sentence_transformers import CrossEncoder
from holo_benchmark.mxbai_panel_protocol import (
    official_semantic_smoke,
    require_logit_score_module,
)

model = CrossEncoder(
    str(Path("rerank/mxbai_rerank_base_v2").resolve()),
    device="cuda",
    trust_remote_code=True,
    local_files_only=True,
)
modules = require_logit_score_module(model)
smoke = official_semantic_smoke(model, torch.nn.Identity())
print("modules", modules)
print("smoke", smoke)
assert smoke["status"] == "PASS"
assert smoke["top_index"] == 1
PY
```

O retorno deve comprovar:

- presença de `sentence_transformers.cross_encoder.modules.logit_score.LogitScore`;
- consulta oficial sobre o planeta vermelho;
- passagem de Marte em primeiro lugar;
- margem top-1 positiva;
- scores finitos.

Sem esse PASS, não execute o painel.

## 7. Execução corrigida dos seis perfis

Perfis e candidates, nesta ordem:

```text
nemotron_3_embed_1b_nvfp4 benchmark/embedding-v3/results/reranker/candidates/nemotron_3_embed_1b_nvfp4.json
nomic_embed_text_v2_moe_q4 benchmark/embedding-v3/results/reranker/candidates/nomic_embed_text_v2_moe_q4.json
qwen3_embedding_4b_q8_0 benchmark/embedding-v3/results/reranker/candidates/qwen3_embedding_4b_q8_0.json
embeddinggemma benchmark/embedding-v3/results/reranker/candidates/embeddinggemma.json
colibri_ptbr benchmark/embedding-v3/results/reranker/candidates/colibri_ptbr.json
granite_embedding_311m_r2 benchmark/embedding-v3/results/reranker/candidates/granite_embedding_311m_r2.json
```

Execute um perfil por vez:

```bash
"$PYTHON" -m holo_benchmark.mxbai_panel_execution \
  --profile-id "$PROFILE" \
  --model-path rerank/mxbai_rerank_base_v2 \
  --model-revision 3ea9d4dffa7d12a4f366be8e275c349de9fc9865 \
  --candidate "$CANDIDATE" \
  --canonical benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json \
  --score-output "benchmark/embedding-v3/results/reranker/scores/mxbai_rerank_base_v2/${PROFILE}.json" \
  --pipeline-output "benchmark/embedding-v3/results/reranker/pipelines/mxbai_rerank_base_v2/${PROFILE}.json" \
  --batch-size 8
```

Não passe `--instruction`. O valor deve permanecer vazio.

Em OOM real, reduza somente `8 → 4 → 2 → 1`, registrando a falha. Não altere protocolo, modelo, precisão, candidatos ou dispositivo.

Depois de cada perfil, libere a memória do processo antes do próximo. Não reutilize scores da v2.2.6.

## 8. Validação dos 12 artefatos corrigidos

Cada score deve comprovar:

- schema `1.0`;
- modelo e revisão exatos;
- nove arquivos críticos com bytes, SHA-256 e revisão;
- backend `sentence-transformers.CrossEncoder`;
- versão `5.6.0` realmente usada;
- device `cuda`;
- `query_format = raw_query_document_pair`;
- `activation_fn = torch.nn.Identity`;
- `LogitScore` presente em `model_modules`;
- `official_semantic_smoke.status = PASS`;
- 150 consultas;
- 7.500 pares;
- 50 IDs e 50 scores finitos por consulta;
- ranking SHA do candidate preservado;
- RAM, VRAM e latências positivas;
- nenhum caminho absoluto ou identificador do host.

Cada pipeline deve comprovar:

- schema `1.0`;
- pipeline ID correto;
- candidate top 50 e rerank top 20;
- base e reranked com summary completo;
- sete tipos de consulta;
- 150 `per_query` em base e reranked;
- 150 `per_query_effect`;
- rescue, damage e coverage calculados;
- score artifact correspondente;
- nenhum caminho absoluto.

Os novos resultados devem divergir materialmente da assinatura inválida de `1cda1db`. Se qualquer perfil continuar com `HitRate@1 <= 0.03`, `MRR@10 <= 0.10` ou mais de 50 consultas sem relevante no top 20, não trate como resultado aceito: pare sem commit e reporte todos os dados do smoke, módulo carregado, score range e métricas. Não tente inverter scores ou alterar prompt manualmente.

## 9. Validações posteriores

```bash
"$PYTHON" .ai/validate_governance.py
"$PYTHON" -m unittest discover -s benchmark/embedding-v3/tests -v
"$PYTHON" -m compileall -q benchmark/embedding-v3
"$PYTHON" benchmark/embedding-v3/validate_coverage.py
git diff --check
```

Confirme ainda:

- todos os artefatos protegidos idênticos;
- os dois BitNet idênticos ao início da v2.2.7;
- `ALL_BENCHMARK_RESULTS.json` idêntico;
- `README.md` idêntico;
- exatamente os 12 arquivos Mixedbread alterados;
- nenhum arquivo não rastreado incluído.

## 10. Commit e push

Se todas as validações passarem:

```bash
git add \
  benchmark/embedding-v3/results/reranker/scores/mxbai_rerank_base_v2 \
  benchmark/embedding-v3/results/reranker/pipelines/mxbai_rerank_base_v2

git diff --cached --name-only
git diff --cached --check

git commit -m "Correct Mixedbread panel with native reranker protocol"
git push origin exec/embed-rerank-batch2-light
```

O commit deve conter exatamente 12 arquivos.

## Retorno obrigatório

Título:

`Retorno v2.2.7 — Mixedbread corrigido com protocolo nativo`

Inclua:

- HEAD inicial e final completos;
- worktree antes/depois;
- interpretador e versões;
- resultado dos 15 testes focados e da suíte integral;
- inventário dos nove arquivos críticos com bytes, SHA-256 e revisão;
- lista de módulos carregados;
- scores e margem do smoke oficial;
- ranking SHA dos seis candidates;
- batch efetivo por perfil;
- para cada perfil: base e reranked HR@1, HR@10, HR@20, MRR@10, nDCG@10, consultas sem relevante, rescue e damage;
- latência p50/p95, RAM e VRAM;
- SHA-256 dos 12 artefatos;
- confirmação de que os arquivos protegidos e BitNet permaneceram idênticos;
- confirmação de que consolidado e README não mudaram;
- lista exata do commit;
- confirmação de ausência de downloads, APIs, edição de código e merge.

Depois desta etapa, pare. A próxima etapa será a segunda tentativa tecnicamente correta do painel NVIDIA Nemotron Rerank 1B v2. A consolidação canônica continuará proibida até esse painel ser fechado ou bloqueado com evidência válida.
