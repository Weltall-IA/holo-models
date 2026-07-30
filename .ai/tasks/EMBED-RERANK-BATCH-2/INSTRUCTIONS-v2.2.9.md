# INSTRUCTIONS v2.2.9 — segunda tentativa canônica do painel NVIDIA Nemotron

## Estado e objetivo

O retorno v2.2.8 está aceito. Os seis pipelines `mxbai_rerank_base_v2` foram reexecutados com snapshot completo, módulo `LogitScore`, pares brutos e smoke semântico aprovado. Eles devem permanecer byte a byte inalterados.

Esta etapa executa exclusivamente a segunda tentativa tecnicamente correta de `nvidia/llama-nemotron-rerank-1b-v2` sobre os mesmos seis candidates do painel fixo.

O bloqueio histórico em `benchmark/embedding-v3/results/reranker/llama_nemotron_rerank_1b_v2_blocked.json` foi produzido em Python 3.14, CUDA 12.8 e PyTorch cu128 durante uma tentativa de instalação. Ele não é uma reprovação do modelo e deve permanecer preservado como evidência histórica. Nesta etapa:

1. reutilize o peso local já verificado;
2. complete somente arquivos não-peso da mesma revisão quando necessário;
3. use um runtime vLLM já instalado e compatível, sem modificar ambientes;
4. aplique obrigatoriamente o template oficial `question:… passage:…`;
5. execute um smoke semântico antes do corpus;
6. produza seis scores e seis pipelines canônicos;
7. continue os seis perfis mesmo quando as métricas válidas forem baixas.

Esta etapa não executa embeddings, Qwen, Voyage ou Mixedbread. Não regenera `ALL_BENCHMARK_RESULTS.json`, não altera `README.md` e não conclui o lote. A consolidação permanece bloqueada até a auditoria deste painel.

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
6. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.8.md`;
7. esta instrução;
8. diff completo do PR #20.

A IA local pode somente inspecionar, baixar os arquivos não-peso explicitamente autorizados, executar testes e módulos versionados, iniciar e encerrar o servidor local vLLM, validar, commitar os 12 resultados autorizados e fazer push no mesmo branch.

A IA local não pode editar código, testes, configuração, documentação ou instruções.

## Proibições

- não baixar novamente `model.safetensors`;
- não baixar `pytorch_model.bin`, `trainer_state.json`, checkpoints ou outro modelo;
- não instalar ou atualizar vLLM, Python, PyTorch, CUDA, driver ou pacotes;
- não criar ambiente virtual novo;
- não executar ou repetir embeddings;
- não executar Qwen, Voyage, Mixedbread ou outro reranker;
- não chamar APIs pagas;
- não alterar candidates;
- não alterar o artefato histórico `llama_nemotron_rerank_1b_v2_blocked.json`;
- não alterar BitNet, LFM, Mixedbread, Nemotron Qwen ou Voyage Context;
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
test -f .ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.9.md
```

Confirme que o remote corresponde inequivocamente a `Weltall-IA/holo-models` e que o HEAD coincide com o handoff. Em divergência, pare.

Preserve sem inclusão no commit:

- `rerank/`;
- `run_bitnet_benchmark.py`;
- `run_light_phase.py`;
- `runtimes/`.

## 2. Proteção integral dos artefatos existentes

Antes de downloads, testes de modelo ou servidor, grave em `/tmp/embed-rerank-v229-protected.sha256` uma lista ordenada dos SHA-256 de todos os arquivos rastreados sob:

- `benchmark/embedding-v3/results/gate2/`;
- `benchmark/embedding-v3/results/gate3/`;
- `benchmark/embedding-v3/results/reranker/candidates/`;
- `benchmark/embedding-v3/results/reranker/scores/`;
- `benchmark/embedding-v3/results/reranker/pipelines/`;
- `benchmark/embedding-v3/results/reranker/llama_nemotron_rerank_1b_v2_blocked.json`;
- `benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json`;
- `benchmark/embedding-v3/README.md`.

Os 12 outputs NVIDIA ainda não existem e não entram na lista protegida. Ao final, todos os arquivos protegidos devem permanecer idênticos.

Registre também:

```bash
git status --short
ps -eo pid,ppid,cmd | grep -E 'vllm|python|llama|rerank|benchmark' | grep -v grep || true
free -h
nvidia-smi
ss -ltnp | grep ':8099' || true
```

A porta `8099` deve estar livre. Não mate processos que não tenham sido iniciados nesta etapa.

## 3. Python do benchmark e testes

Use o mesmo interpretador aprovado na v2.2.8:

```bash
PYTHON=/home/alpha/Playstoria/models/benchmarks/holo-embedding-benchmark-v3/.venv/bin/python
test -x "$PYTHON"
export PYTHONPATH="$PWD/benchmark/embedding-v3${PYTHONPATH:+:$PYTHONPATH}"

"$PYTHON" --version
"$PYTHON" - <<'PY'
import torch
import holo_benchmark
print("holo_benchmark", holo_benchmark.__file__)
print("torch", torch.__version__)
print("torch_cuda", torch.version.cuda)
print("cuda_available", torch.cuda.is_available())
assert torch.cuda.is_available()
PY
```

Execute antes do modelo:

```bash
"$PYTHON" .ai/validate_governance.py

"$PYTHON" -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_nemotron_panel_benchmark.py' -v

"$PYTHON" -m unittest discover -s benchmark/embedding-v3/tests -v
"$PYTHON" -m compileall -q benchmark/embedding-v3
git diff --check
```

Resultados esperados:

- teste focado NVIDIA: `7/7` PASS;
- suíte integral: pelo menos `219` testes, zero failures e zero errors;
- governance, compileall e diff check: exit code `0`.

Em falha, pare e reporte. Não edite código.

## 4. Modelo NVIDIA local

Use exatamente:

```bash
MODEL_DIR=rerank/llama_nemotron_rerank_1b_v2
MODEL_REVISION=d896ceda696c5c6fe0abf65f63a77c691bbf4548
MODEL_WEIGHT="$MODEL_DIR/model.safetensors"
TEMPLATE=benchmark/embedding-v3/templates/nemotron-rerank.jinja
```

Identidade fixada:

- repositório: `nvidia/llama-nemotron-rerank-1b-v2`;
- revisão: `d896ceda696c5c6fe0abf65f63a77c691bbf4548`;
- peso: `model.safetensors`;
- bytes: `2471649792`;
- SHA-256: `7d60ff24db62fe6a639c4c6f4aeac3a3b32ed20939ab72a0be4b019c2219e5e0`;
- precisão: BF16;
- licença: NVIDIA Open Model License;
- backend: vLLM pooling;
- template oficial obrigatório: `question:… passage:…`.

Proteja o peso:

```bash
test -d "$MODEL_DIR"
test -f "$MODEL_WEIGHT"
test "$(stat -c '%s' "$MODEL_WEIGHT")" = "2471649792"
test "$(sha256sum "$MODEL_WEIGHT" | awk '{print $1}')" = \
  "7d60ff24db62fe6a639c4c6f4aeac3a3b32ed20939ab72a0be4b019c2219e5e0"
sha256sum "$MODEL_WEIGHT" > /tmp/nemotron-v229-weight-before.sha256
```

Arquivos críticos necessários:

```text
model.safetensors
config.json
tokenizer.json
tokenizer_config.json
llama_bidirectional_model.py
```

Cada um deve possuir metadata em `.cache/huggingface/download/<arquivo>.metadata`, cuja primeira linha seja a revisão fixada.

## 5. Download limitado de arquivos não-peso

Primeiro verifique os quatro arquivos não-peso e seus metadados. Se qualquer um estiver ausente ou não tiver metadata da revisão fixada, é autorizado executar uma única vez:

```bash
hf download nvidia/llama-nemotron-rerank-1b-v2 \
  config.json \
  tokenizer.json \
  tokenizer_config.json \
  llama_bidirectional_model.py \
  special_tokens_map.json \
  --revision "$MODEL_REVISION" \
  --local-dir "$MODEL_DIR"
```

Regras:

- o comando não pode incluir `model.safetensors`;
- não use `snapshot_download` sem lista explícita;
- não use outra revisão;
- não baixe `pytorch_model.bin`;
- se houver falha transitória de rede, repita no máximo duas vezes o mesmo comando;
- depois do download, o peso deve continuar byte a byte idêntico ao hash protegido.

Valide o snapshot com o código versionado:

```bash
"$PYTHON" - <<'PY'
from pathlib import Path
from holo_benchmark.nemotron_panel_benchmark import validate_complete_model
path, identity = validate_complete_model(
    Path("rerank/llama_nemotron_rerank_1b_v2"),
    "d896ceda696c5c6fe0abf65f63a77c691bbf4548",
)
print(path)
for item in identity["critical_snapshot_files"]:
    print(item["file"], item["bytes"], item["sha256"], item["revision"])
PY

sha256sum -c /tmp/nemotron-v229-weight-before.sha256
```

Em divergência de revisão, tamanho ou hash, pare e reporte.

## 6. Descoberta do runtime vLLM existente

Não instale nada. Localize executáveis existentes:

```bash
{
  command -v vllm 2>/dev/null || true
  find /home/alpha/Playstoria /home/alpha/.local \
    -type f -path '*/bin/vllm' -perm -u+x 2>/dev/null || true
} | awk 'NF && !seen[$0]++' > /tmp/vllm-v229-candidates.txt

cat /tmp/vllm-v229-candidates.txt
```

Teste cada candidato somente com `--version` e selecione:

1. preferencialmente `vllm 0.25.0`;
2. na ausência dele, um vLLM existente `>=0.14.0`;
3. nunca instale, atualize ou crie ambiente.

Registre caminho completo, versão, shebang quando houver e ambiente Python associado. Defina:

```bash
VLLM_BIN=/caminho/comprovado/para/vllm
VLLM_VERSION="$($VLLM_BIN --version | tail -n1)"
printf 'VLLM_BIN=%s\nVLLM_VERSION=%s\n' "$VLLM_BIN" "$VLLM_VERSION"
```

Se nenhum runtime existente `>=0.14.0` for encontrado, termine `BLOCKED_RUNTIME_NOT_FOUND`. Isso não reprova nem abandona o modelo e não autoriza instalação local.

## 7. Servidor local com template oficial

Confirme o template versionado:

```bash
test -f "$TEMPLATE"
"$PYTHON" - <<'PY'
from pathlib import Path
from holo_benchmark.nemotron_panel_benchmark import validate_score_template
print(validate_score_template(Path("benchmark/embedding-v3/templates/nemotron-rerank.jinja")))
PY
```

Inicie um único servidor para os seis perfis:

```bash
PORT=8099
BASE_URL="http://127.0.0.1:${PORT}"
LOG=/tmp/nemotron-v229-vllm.log

"$VLLM_BIN" serve "$MODEL_DIR" \
  --trust-remote-code \
  --runner pooling \
  --chat-template "$TEMPLATE" \
  --served-model-name llama_nemotron_rerank_1b_v2 \
  --dtype bfloat16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.60 \
  --host 127.0.0.1 \
  --port "$PORT" \
  >"$LOG" 2>&1 &
SERVER_PID=$!

cleanup() {
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT
```

Aguarde usando o módulo versionado:

```bash
"$PYTHON" - <<'PY'
from holo_benchmark.nemotron_panel_benchmark import wait_for_server
wait_for_server("http://127.0.0.1:8099", 300)
print("SERVER_READY")
PY
```

Se o servidor encerrar, registre o log completo e pare. Não altere precisão, template, revisão, modelo ou protocolo.

Somente em OOM real de inicialização, encerre o processo e repita a mesma linha reduzindo `--gpu-memory-utilization` para `0.50` e depois `0.40`. Não altere `--max-model-len`, `--dtype`, template ou runner.

## 8. Smoke semântico obrigatório

Antes dos 45.000 pares:

```bash
"$PYTHON" - <<'PY'
from holo_benchmark.nemotron_panel_benchmark import official_semantic_smoke
smoke = official_semantic_smoke("http://127.0.0.1:8099", 120)
print(smoke)
assert smoke["status"] == "PASS"
assert smoke["top_index"] == 1
assert smoke["margin"] > 0
PY

nvidia-smi
```

O documento sobre machine learning deve superar o documento sobre bananas. Sem PASS e VRAM positiva, não execute o painel.

## 9. Execução dos seis perfis

Crie somente os diretórios versionados de saída:

```bash
mkdir -p benchmark/embedding-v3/results/reranker/scores/llama_nemotron_rerank_1b_v2
mkdir -p benchmark/embedding-v3/results/reranker/pipelines/llama_nemotron_rerank_1b_v2
```

Perfis e candidates, nesta ordem:

```text
nemotron_3_embed_1b_nvfp4 benchmark/embedding-v3/results/reranker/candidates/nemotron_3_embed_1b_nvfp4.json
nomic_embed_text_v2_moe_q4 benchmark/embedding-v3/results/reranker/candidates/nomic_embed_text_v2_moe_q4.json
qwen3_embedding_4b_q8_0 benchmark/embedding-v3/results/reranker/candidates/qwen3_embedding_4b_q8_0.json
embeddinggemma benchmark/embedding-v3/results/reranker/candidates/embeddinggemma.json
colibri_ptbr benchmark/embedding-v3/results/reranker/candidates/colibri_ptbr.json
granite_embedding_311m_r2 benchmark/embedding-v3/results/reranker/candidates/granite_embedding_311m_r2.json
```

Para cada par `PROFILE CANDIDATE`, execute:

```bash
"$PYTHON" -m holo_benchmark.nemotron_panel_benchmark \
  --profile-id "$PROFILE" \
  --model-path "$MODEL_DIR" \
  --model-revision "$MODEL_REVISION" \
  --candidate "$CANDIDATE" \
  --canonical benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json \
  --score-template "$TEMPLATE" \
  --base-url "$BASE_URL" \
  --server-pid "$SERVER_PID" \
  --vllm-version "$VLLM_VERSION" \
  --startup-timeout 300 \
  --request-timeout 300 \
  --score-output "benchmark/embedding-v3/results/reranker/scores/llama_nemotron_rerank_1b_v2/${PROFILE}.json" \
  --pipeline-output "benchmark/embedding-v3/results/reranker/pipelines/llama_nemotron_rerank_1b_v2/${PROFILE}.json"
```

Regras de continuidade:

- cada perfil deve produzir exatamente 7.500 scores finitos;
- uma métrica baixa, dano alto ou ausência de melhora não é falha operacional;
- após artefato válido, continue para o perfil seguinte;
- não pule um perfil por qualidade;
- pare somente por erro de protocolo, snapshot, runtime, servidor, resposta incompleta, score não finito, falta de CUDA ou ausência de VRAM positiva;
- não altere o template ou o sinal do score;
- `relevance_score` maior deve permanecer melhor.

## 10. Validação dos 12 artefatos

Valide programaticamente:

- seis scores e seis pipelines existem;
- schema `1.0`;
- IDs e caminhos correspondem ao perfil;
- modelo, revisão, peso, hash e licença exatos;
- backend vLLM e versão real;
- runner `pooling`, endpoint `/rerank` e template oficial;
- smoke `PASS` registrado;
- corpus congelado 600/150 e hash correto;
- ranking SHA igual ao candidate de cada perfil;
- 150 consultas em ordem;
- 50 IDs únicos e 50 scores finitos por consulta;
- `pairs = 7500`;
- device CUDA e `peak_vram_bytes > 0`;
- base e reranked com summary completo, sete tipos e 150 `per_query`;
- 150 `per_query_effect`;
- nenhum caminho absoluto, usuário local ou PID persistido;
- scores e pipelines diferentes entre os perfis quando os candidates diferirem.

Execute novamente:

```bash
"$PYTHON" .ai/validate_governance.py
"$PYTHON" -m unittest discover -s benchmark/embedding-v3/tests -v
"$PYTHON" -m compileall -q benchmark/embedding-v3
"$PYTHON" benchmark/embedding-v3/validate_coverage.py
git diff --check
```

Todos devem retornar código `0`.

Encerre o servidor com a função `cleanup`, confirme que a porta `8099` foi liberada e registre RAM/VRAM finais.

## 11. Proteções finais e commit

- compare `/tmp/embed-rerank-v229-protected.sha256` com os hashes atuais;
- confirme o peso com `/tmp/nemotron-v229-weight-before.sha256`;
- confirme que `rerank/`, `run_bitnet_benchmark.py`, `run_light_phase.py` e `runtimes/` continuam não rastreados e fora do commit;
- confirme que `ALL_BENCHMARK_RESULTS.json` e `README.md` não mudaram;
- confirme que o artefato bloqueado histórico não mudou.

O commit deve conter exatamente estes 12 arquivos:

- seis JSONs em `results/reranker/scores/llama_nemotron_rerank_1b_v2/`;
- seis JSONs em `results/reranker/pipelines/llama_nemotron_rerank_1b_v2/`.

Não inclua modelo, template, código, testes ou instruções no commit local; esses arquivos já vieram pelo pull.

Mensagem obrigatória:

```text
Run canonical NVIDIA Nemotron reranker panel
```

Faça push no mesmo branch. Não faça merge.

## 12. Retorno obrigatório

Título:

```text
Retorno v2.2.9 — Painel NVIDIA Nemotron canônico
```

Inclua:

1. HEAD inicial e final completos;
2. status antes/depois;
3. arquivos não-peso baixados ou confirmação de que não foram necessários;
4. hash do peso antes/depois;
5. arquivos críticos, bytes, hashes e revisão;
6. runtime vLLM: caminho, versão, Python associado, CUDA e comando do servidor sanitizado;
7. smoke: scores, top index, margem e VRAM;
8. comandos e exit codes;
9. total de testes;
10. para cada perfil: 7.500 pares, latências, VRAM, métricas base e reranked, rescue e damage;
11. hashes dos 12 artefatos;
12. confirmação dos arquivos protegidos;
13. lista exata do commit;
14. confirmação de servidor encerrado, sem merge e PR draft.

Última linha:

```text
Versão do retorno da IA local: 2.2.9 — Painel NVIDIA Nemotron canônico
```
