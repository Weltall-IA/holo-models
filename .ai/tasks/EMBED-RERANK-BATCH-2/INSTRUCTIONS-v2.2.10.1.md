# INSTRUCTIONS v2.2.10.1 — retomar painel NVIDIA após correção de endpoint portátil

## Estado e objetivo

A v2.2.10 instalou corretamente o runtime vLLM isolado, iniciou o servidor NVIDIA Nemotron na porta `8099` e aprovou o smoke semântico. A primeira materialização foi interrompida por um defeito no código versionado: `runtime.endpoint = "/rerank"` era interpretado como caminho POSIX absoluto pelo validador genérico de portabilidade.

O defeito foi corrigido pelo gerente técnico. Rotas relativas de API agora são aceitas somente nos campos semânticos `endpoint`, `endpoint_path` e `api_endpoint`. A mesma string continua proibida em campos de filesystem, e rotas com traversal continuam bloqueadas.

Esta instrução:

1. valida a correção e toda a suíte;
2. reutiliza o servidor vLLM já ativo quando sua identidade puder ser comprovada;
3. repete o smoke semântico;
4. executa os seis perfis NVIDIA desde o início;
5. produz e valida exatamente 12 artefatos canônicos;
6. não altera nem consolida outros resultados.

Esta etapa não executa embeddings, Qwen, Voyage ou Mixedbread. Não altera `ALL_BENCHMARK_RESULTS.json` nem `README.md`. O lote permanece aberto até a auditoria NVIDIA e a consolidação final.

## Repositório e branch

- repositório: `Weltall-IA/holo-models`;
- worktree: `/home/alpha/Playstoria/models-embed-batch2-light`;
- branch: `exec/embed-rerank-batch2-light`;
- PR: `#20`, aberto e draft;
- HEAD inicial: deve coincidir exatamente com o SHA completo informado no handoff;
- nenhum merge é autorizado.

## Leitura obrigatória

Leia integralmente, nesta ordem:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`;
6. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.9.md`;
7. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.10.md`;
8. esta instrução;
9. diff completo do PR #20.

Esta instrução substitui somente o tratamento do defeito de portabilidade e a retomada do servidor. Todas as identidades, perfis, candidates, template, parâmetros vLLM, validações de modelo, outputs e proteções das v2.2.9/v2.2.10 permanecem obrigatórios.

A IA local pode apenas testar, inspecionar/reutilizar ou reiniciar o runtime isolado autorizado, executar os módulos versionados, materializar os 12 resultados, validar, commitar e fazer push. Não pode editar código, testes, configuração, documentação ou instruções.

## Proibições

- não editar ou contornar `assert_portable_payload`;
- não remover `runtime.endpoint` dos artefatos;
- não executar sem o check de portabilidade;
- não alterar o valor canônico `runtime.endpoint = "/rerank"`;
- não instalar outro runtime se `runtimes/vllm-nemotron-0.25.1/` estiver válido;
- não modificar ambientes globais, Python, PyTorch, CUDA ou driver;
- não baixar novamente o peso;
- não executar embeddings, Qwen, Voyage, Mixedbread ou outro reranker;
- não alterar candidates ou resultados protegidos;
- não alterar `ALL_BENCHMARK_RESULTS.json` ou `README.md`;
- não usar `reset --hard`, `clean`, `checkout --`, stash automático ou force-push;
- não incluir `rerank/`, `runtimes/` ou outros arquivos não rastreados no commit;
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
test -f .ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.10.1.md
```

Confirme que o remote corresponde inequivocamente a `Weltall-IA/holo-models` e que o HEAD coincide com o handoff. Em divergência, pare.

Preserve sem inclusão no commit:

- `rerank/`;
- `runtimes/`;
- `run_bitnet_benchmark.py`;
- `run_light_phase.py`.

## 2. Proteção integral

Reaplique integralmente a proteção de artefatos da seção 2 da v2.2.9. Nenhum dos 12 outputs NVIDIA deve existir como arquivo rastreado no HEAD inicial.

Registre:

```bash
git status --short
free -h
nvidia-smi
ss -ltnp | grep ':8099' || true
ps -eo pid,ppid,cmd | grep -E 'vllm|8099|llama_nemotron' | grep -v grep || true
```

Nenhum arquivo protegido pode mudar durante esta etapa.

## 3. Ambiente de benchmark e testes da correção

```bash
PYTHON=/home/alpha/Playstoria/models/benchmarks/holo-embedding-benchmark-v3/.venv/bin/python
test -x "$PYTHON"
export PYTHONPATH="$PWD/benchmark/embedding-v3${PYTHONPATH:+:$PYTHONPATH}"

"$PYTHON" .ai/validate_governance.py

"$PYTHON" -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_artifact_portability.py' -v

"$PYTHON" -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_nemotron_panel_benchmark.py' -v

"$PYTHON" -m unittest discover -s benchmark/embedding-v3/tests -v
"$PYTHON" -m compileall -q benchmark/embedding-v3
git diff --check
```

Resultados mínimos esperados:

- portabilidade: `7/7` PASS;
- painel NVIDIA: `7/7` PASS;
- suíte integral: pelo menos `222` testes, zero failures e zero errors;
- governance, compileall e diff check: exit code `0`.

Confirme explicitamente pelo teste que:

- `{ "runtime": { "endpoint": "/rerank" } }` é portátil;
- `{ "path": "/rerank" }` continua não portátil;
- `/v1/../rerank` continua não portátil.

Em qualquer falha, pare sem editar código.

## 4. Modelo, peso, template e runtime isolado

Use as identidades e validações integrais das seções 4 e 5 da v2.2.9.

```bash
MODEL_DIR=rerank/llama_nemotron_rerank_1b_v2
MODEL_REVISION=d896ceda696c5c6fe0abf65f63a77c691bbf4548
MODEL_WEIGHT="$MODEL_DIR/model.safetensors"
TEMPLATE=benchmark/embedding-v3/templates/nemotron-rerank.jinja
VLLM_ENV=runtimes/vllm-nemotron-0.25.1
VLLM_BIN="$VLLM_ENV/bin/vllm"

 test -x "$VLLM_BIN"
 test "$($VLLM_BIN --version | tail -n1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | tail -n1)" = "0.25.1"
 sha256sum "$MODEL_WEIGHT"
```

Valide novamente o snapshot, o peso e o template pelos módulos versionados. O peso deve permanecer com `2471649792` bytes e SHA-256 `7d60ff24db62fe6a639c4c6f4aeac3a3b32ed20939ab72a0be4b019c2219e5e0`.

Não reinstale o vLLM quando o ambiente isolado acima passar nas validações.

## 5. Reutilização segura ou reinício do servidor

Defina:

```bash
PORT=8099
BASE_URL="http://127.0.0.1:${PORT}"
LOG=/tmp/nemotron-v2210-vllm.log
```

### 5.1 Reutilização

Quando a porta já estiver ocupada, identifique o PID e a linha de comando. Reutilize somente se for comprovadamente o servidor iniciado pela v2.2.10 e a linha de comando contiver todos os itens:

- executável sob `runtimes/vllm-nemotron-0.25.1/`;
- `serve rerank/llama_nemotron_rerank_1b_v2` ou o caminho absoluto equivalente;
- `--runner pooling`;
- `--chat-template benchmark/embedding-v3/templates/nemotron-rerank.jinja` ou equivalente;
- `--served-model-name llama_nemotron_rerank_1b_v2`;
- `--dtype bfloat16`;
- porta `8099`.

Registre o PID como `SERVER_PID`. Não mate nem reutilize processo de identidade ambígua.

### 5.2 Reinício controlado

Se o servidor anterior não estiver ativo, estiver encerrado ou não puder ser comprovado, inicie novamente usando exatamente o comando da seção 7 da v2.2.9, substituindo `VLLM_BIN` pelo ambiente isolado fixado acima.

Somente processos comprovadamente iniciados nas v2.2.10/v2.2.10.1 podem ser encerrados. Instale trap de cleanup para servidor iniciado nesta retomada.

Aguarde `SERVER_READY` com `wait_for_server`. Registre versão vLLM, PID, comando, CUDA e VRAM positiva.

## 6. Smoke semântico obrigatório

Repita integralmente o smoke da seção 8 da v2.2.9, mesmo que ele já tenha passado antes do pull.

Exigências:

- endpoint local `/rerank`;
- template oficial `question:… passage:…`;
- passagem relevante em top-1;
- margem positiva;
- scores finitos;
- servidor ainda ativo;
- VRAM positiva.

Sem novo PASS, não execute o painel.

## 7. Execução dos seis perfis

Execute novamente os seis perfis desde o primeiro, na ordem e com os comandos exatos da seção 9 da v2.2.9.

Perfis:

1. `nemotron_3_embed_1b_nvfp4`;
2. `nomic_embed_text_v2_moe_q4`;
3. `qwen3_embedding_4b_q8_0`;
4. `embeddinggemma`;
5. `colibri_ptbr`;
6. `granite_embedding_311m_r2`.

Cada execução deve:

- usar o candidate canônico 150×50;
- pontuar exatamente `7.500` pares;
- registrar CUDA e VRAM positiva;
- manter `runtime.endpoint` exatamente `/rerank`;
- passar `assert_portable_payload` sem sanitização manual;
- produzir score e pipeline schema 1.0 completos;
- continuar mesmo quando métricas válidas forem baixas.

Outputs autorizados, exatamente:

```text
benchmark/embedding-v3/results/reranker/scores/llama_nemotron_rerank_1b_v2/nemotron_3_embed_1b_nvfp4.json
benchmark/embedding-v3/results/reranker/scores/llama_nemotron_rerank_1b_v2/nomic_embed_text_v2_moe_q4.json
benchmark/embedding-v3/results/reranker/scores/llama_nemotron_rerank_1b_v2/qwen3_embedding_4b_q8_0.json
benchmark/embedding-v3/results/reranker/scores/llama_nemotron_rerank_1b_v2/embeddinggemma.json
benchmark/embedding-v3/results/reranker/scores/llama_nemotron_rerank_1b_v2/colibri_ptbr.json
benchmark/embedding-v3/results/reranker/scores/llama_nemotron_rerank_1b_v2/granite_embedding_311m_r2.json
benchmark/embedding-v3/results/reranker/pipelines/llama_nemotron_rerank_1b_v2/nemotron_3_embed_1b_nvfp4.json
benchmark/embedding-v3/results/reranker/pipelines/llama_nemotron_rerank_1b_v2/nomic_embed_text_v2_moe_q4.json
benchmark/embedding-v3/results/reranker/pipelines/llama_nemotron_rerank_1b_v2/qwen3_embedding_4b_q8_0.json
benchmark/embedding-v3/results/reranker/pipelines/llama_nemotron_rerank_1b_v2/embeddinggemma.json
benchmark/embedding-v3/results/reranker/pipelines/llama_nemotron_rerank_1b_v2/colibri_ptbr.json
benchmark/embedding-v3/results/reranker/pipelines/llama_nemotron_rerank_1b_v2/granite_embedding_311m_r2.json
```

Não remova nem altere o artefato histórico de bloqueio.

## 8. Validação posterior

Execute integralmente as validações posteriores da seção 10 da v2.2.9 e, adicionalmente:

```bash
"$PYTHON" - <<'PY'
import json
from pathlib import Path
from holo_benchmark.artifact_portability import assert_portable_payload

roots = [
    Path("benchmark/embedding-v3/results/reranker/scores/llama_nemotron_rerank_1b_v2"),
    Path("benchmark/embedding-v3/results/reranker/pipelines/llama_nemotron_rerank_1b_v2"),
]
files = sorted(path for root in roots for path in root.glob("*.json"))
assert len(files) == 12, len(files)
for path in files:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert_portable_payload(payload)
    runtime = payload.get("runtime") or payload.get("reranker_runtime")
    if isinstance(runtime, dict) and "endpoint" in runtime:
        assert runtime["endpoint"] == "/rerank", (path, runtime["endpoint"])
    print(path)
PY
```

Confirme:

- `219+` testes anteriores mais os três novos testes, total mínimo `222`;
- 12 artefatos portáteis;
- 45.000 pares totais;
- seis summaries base e reranked;
- seis blocos por sete query types;
- 150 per-query e 150 effects por pipeline;
- valores finitos;
- nenhum caminho do host;
- endpoint `/rerank` preservado;
- todos os artefatos protegidos byte a byte idênticos;
- peso e runtime isolado preservados;
- servidor encerrado ao final, quando iniciado ou herdado das etapas NVIDIA.

## 9. Commit e push

O diff rastreado deve conter exatamente os 12 outputs autorizados. A IA local não pode incluir os três arquivos de código/teste/instrução já recebidos pelo pull, pois eles já fazem parte do HEAD inicial.

```bash
git status --short
git diff --check
git diff --name-only
```

Commit:

```bash
git add \
  benchmark/embedding-v3/results/reranker/scores/llama_nemotron_rerank_1b_v2 \
  benchmark/embedding-v3/results/reranker/pipelines/llama_nemotron_rerank_1b_v2

git commit -m "Complete NVIDIA Nemotron reranker panel"
git push origin exec/embed-rerank-batch2-light
```

Não faça merge.

## 10. Retorno obrigatório

Reporte:

1. HEAD inicial completo e commit final completo;
2. worktree antes/depois;
3. servidor reutilizado ou reiniciado, PID e forma de encerramento;
4. Python do benchmark e runtime vLLM isolado;
5. versões vLLM, Python, PyTorch e CUDA do runtime;
6. identidade e hashes dos cinco arquivos críticos do modelo;
7. smoke completo;
8. todos os comandos e exit codes;
9. testes focados e suíte total;
10. para cada perfil: pares, tempo, VRAM, base/reranked HR@1, MRR@10, nDCG@10, hard-negative error, rescue e damage;
11. confirmação de `runtime.endpoint = "/rerank"` nos artefatos;
12. SHA-256 dos 12 outputs;
13. lista exata dos 12 arquivos commitados;
14. prova de que todos os protegidos permaneceram idênticos;
15. confirmação de nenhum embedding/API/outro modelo/merge;
16. confirmação de que `ALL_BENCHMARK_RESULTS.json` e README não foram alterados.

Linha final exata:

`Versão do retorno da IA local: 2.2.10.1 — correção de portabilidade e retomada NVIDIA Nemotron`
