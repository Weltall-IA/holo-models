# INSTRUCTIONS v2.2.10 — runtime vLLM isolado e retomada do painel NVIDIA Nemotron

## Estado e objetivo

O retorno v2.2.9 terminou corretamente como `BLOCKED_RUNTIME_NOT_FOUND` antes de iniciar o servidor, o smoke ou os seis benchmarks. Nenhum resultado foi alterado, nenhum commit foi criado e o modelo não foi reprovado.

O bloqueio prova somente que não existe runtime vLLM instalado no host. Ele não prova incompatibilidade do modelo nem encerra o painel.

Esta instrução autoriza uma única correção de dependência, totalmente isolada:

1. criar um ambiente Python 3.12 exclusivamente sob `runtimes/vllm-nemotron-0.25.1/`;
2. instalar nele exatamente `vllm==0.25.1` a partir de wheels publicados, sem build de fonte;
3. não modificar o Python, PyTorch, CUDA, driver ou ambientes globais;
4. validar CUDA e o runtime isolado;
5. retomar integralmente a v2.2.9 a partir do servidor local, smoke e seis perfis;
6. produzir e commitar somente os 12 outputs NVIDIA autorizados.

O runtime, caches e logs permanecem não rastreados sob `runtimes/` ou `/tmp` e nunca entram no commit.

Esta etapa não executa embeddings, Qwen, Voyage ou Mixedbread. Não regenera `ALL_BENCHMARK_RESULTS.json`, não altera `README.md` e não conclui o lote. A consolidação continua bloqueada até a auditoria do painel NVIDIA.

## Repositório, branch e PR

- repositório: `Weltall-IA/holo-models`;
- worktree: `/home/alpha/Playstoria/models-embed-batch2-light`;
- branch: `exec/embed-rerank-batch2-light`;
- PR: `#20`, aberto e draft;
- HEAD inicial: deve coincidir exatamente com o SHA completo informado no handoff;
- nenhum merge é autorizado.

## Autoridade e leitura obrigatória

Leia integralmente, nesta ordem:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`;
6. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.9.md`;
7. esta instrução;
8. diff completo do PR #20.

Esta v2.2.10 substitui somente estas proibições da v2.2.9:

- `não instalar ou atualizar vLLM`;
- `não criar ambiente virtual novo`.

A substituição vale exclusivamente para o ambiente isolado e a versão fixados nesta instrução. Todas as demais regras, proteções, modelos, candidates, outputs, validações e formato de retorno da v2.2.9 permanecem obrigatórios.

A IA local pode somente:

- inspecionar o ambiente;
- criar o runtime isolado autorizado;
- instalar exatamente `vllm==0.25.1` e suas dependências dentro desse runtime;
- executar testes e módulos já versionados;
- iniciar e encerrar o servidor local;
- executar smoke e seis perfis NVIDIA;
- validar, commitar exatamente os 12 resultados e fazer push no mesmo branch.

A IA local não pode editar código, testes, configuração, documentação ou instruções.

## Proibições

- não instalar pacotes no Python do benchmark, no Python do sistema, em `--user`, Conda, pipx ou outro ambiente;
- não usar `sudo`, `apt`, `dnf`, `pacman`, Docker ou alteração de sistema;
- não instalar outra versão do vLLM;
- não usar nightly, commit wheel, build de fonte, `git clone` do vLLM ou compilação CUDA;
- não atualizar pip, setuptools, wheel, Python, PyTorch, CUDA ou driver fora do novo ambiente;
- não baixar novamente `model.safetensors`;
- não baixar outro modelo ou arquivo não autorizado pela v2.2.9;
- não executar embeddings, Qwen, Voyage, Mixedbread ou outro reranker;
- não chamar APIs pagas;
- não alterar candidates ou artefatos aceitos;
- não alterar o bloqueio histórico versionado;
- não alterar `ALL_BENCHMARK_RESULTS.json` ou `README.md`;
- não incluir `runtimes/`, `rerank/`, caches, logs ou arquivos preexistentes no commit;
- não usar `reset --hard`, `clean`, `checkout --`, stash automático ou force-push;
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
test -f .ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.10.md
```

Confirme que o remote corresponde inequivocamente a `Weltall-IA/holo-models` e que o HEAD coincide com o handoff. Em divergência, pare.

Preserve sem inclusão no commit:

- `rerank/`;
- `run_bitnet_benchmark.py`;
- `run_light_phase.py`;
- `runtimes/`.

## 2. Proteção e preflight

Aplique integralmente a seção 2 da v2.2.9 e recrie a lista de SHA-256 dos 184 arquivos protegidos. Confirme que os 12 outputs NVIDIA ainda não existem.

Registre:

```bash
git status --short
free -h
df -h . runtimes /tmp
nvidia-smi
ss -ltnp | grep ':8099' || true
ps -eo pid,ppid,cmd | grep -E 'vllm|nemotron|rerank|benchmark' | grep -v grep || true
```

A porta `8099` deve estar livre. Não mate processos que não tenham sido iniciados nesta etapa.

Exija pelo menos 12 GiB livres no filesystem que contém `runtimes/`. Se não houver, reporte `BLOCKED_RUNTIME_DISK_SPACE` sem apagar dados preexistentes.

## 3. Testes e ambiente do benchmark

Use o mesmo Python aprovado, sem instalar nada nele:

```bash
BENCH_PYTHON=/home/alpha/Playstoria/models/benchmarks/holo-embedding-benchmark-v3/.venv/bin/python
test -x "$BENCH_PYTHON"
export PYTHONPATH="$PWD/benchmark/embedding-v3${PYTHONPATH:+:$PYTHONPATH}"

"$BENCH_PYTHON" --version
"$BENCH_PYTHON" - <<'PY'
import sys
import torch
import holo_benchmark
print("python", sys.version)
print("holo_benchmark", holo_benchmark.__file__)
print("torch", torch.__version__)
print("torch_cuda", torch.version.cuda)
print("cuda_available", torch.cuda.is_available())
assert sys.version_info[:2] == (3, 12)
assert torch.cuda.is_available()
PY

"$BENCH_PYTHON" .ai/validate_governance.py
"$BENCH_PYTHON" -m unittest discover \
  -s benchmark/embedding-v3/tests \
  -p 'test_nemotron_panel_benchmark.py' -v
"$BENCH_PYTHON" -m unittest discover -s benchmark/embedding-v3/tests -v
"$BENCH_PYTHON" -m compileall -q benchmark/embedding-v3
git diff --check
```

Resultados mínimos:

- focados NVIDIA: `7/7` PASS;
- suíte integral: pelo menos `219` testes e zero falhas/erros;
- governance, compileall e diff check: exit `0`.

Em falha, pare sem editar código.

## 4. Criação do runtime isolado

Defina exatamente:

```bash
VLLM_VERSION=0.25.1
VLLM_ENV="$PWD/runtimes/vllm-nemotron-${VLLM_VERSION}"
VLLM_PYTHON="$VLLM_ENV/bin/python"
VLLM_BIN="$VLLM_ENV/bin/vllm"
INSTALL_LOG=/tmp/vllm-v2210-install.log
```

O ambiente é descartável, não rastreado e exclusivo desta tarefa.

Se `VLLM_ENV` já existir de uma tentativa anterior incompleta desta mesma instrução, registre seu inventário e remova somente esse diretório específico:

```bash
if test -e "$VLLM_ENV"; then
  find "$VLLM_ENV" -maxdepth 3 -type f -printf '%P\n' | sort | head -200 || true
  rm -rf -- "$VLLM_ENV"
fi
```

Não remova nenhum outro caminho de `runtimes/`.

Crie o ambiente com o Python 3.12 aprovado:

```bash
"$BENCH_PYTHON" -m venv "$VLLM_ENV"
test -x "$VLLM_PYTHON"
"$VLLM_PYTHON" --version
```

Instale uma única versão, somente por wheels e sem cache persistente:

```bash
set +e
PIP_DISABLE_PIP_VERSION_CHECK=1 \
PIP_NO_INPUT=1 \
PIP_ONLY_BINARY=:all: \
"$VLLM_PYTHON" -m pip install \
  --no-cache-dir \
  "vllm==${VLLM_VERSION}" \
  >"$INSTALL_LOG" 2>&1
INSTALL_EXIT=$?
set -e
cat "$INSTALL_LOG"
```

Se `INSTALL_EXIT != 0`:

1. classifique se foi falha transitória de rede;
2. somente em falha transitória, remova exclusivamente `VLLM_ENV`, recrie-o e repita uma única vez o mesmo comando;
3. não mude versão, índice, backend, flags ou protocolo;
4. em nova falha, reporte `BLOCKED_RUNTIME_INSTALL_FAILED`, incluindo exit code e mensagem causal completa;
5. não crie commit.

Falha de resolução, ausência de wheel ou incompatibilidade de plataforma não autoriza nightly, source build nem alteração global.

## 5. Validação do runtime isolado

Após instalação:

```bash
test -x "$VLLM_BIN"
"$VLLM_BIN" --version

"$VLLM_PYTHON" - <<'PY'
import importlib.metadata
import platform
import sys
import torch
import vllm

print("python", sys.version)
print("platform", platform.platform())
print("vllm", vllm.__version__)
print("vllm_metadata", importlib.metadata.version("vllm"))
print("torch", torch.__version__)
print("torch_cuda", torch.version.cuda)
print("cuda_available", torch.cuda.is_available())
print("device_count", torch.cuda.device_count())
if torch.cuda.is_available():
    print("device_0", torch.cuda.get_device_name(0))
    print("capability_0", torch.cuda.get_device_capability(0))
assert sys.version_info[:2] == (3, 12)
assert importlib.metadata.version("vllm") == "0.25.1"
assert torch.cuda.is_available()
assert torch.cuda.device_count() >= 1
PY

"$VLLM_PYTHON" -m pip freeze | sort > /tmp/vllm-v2210-freeze.txt
sha256sum "$VLLM_BIN" > /tmp/vllm-v2210-bin.sha256
cat /tmp/vllm-v2210-bin.sha256
```

Registre versão do vLLM, versão do PyTorch isolado, variante CUDA, nome da GPU, compute capability, caminho do binário, SHA-256 do launcher e hash SHA-256 de `/tmp/vllm-v2210-freeze.txt`.

Se o import ou CUDA falhar, reporte `BLOCKED_RUNTIME_CUDA_INCOMPATIBLE`, preserve os logs e não tente alterar o sistema.

## 6. Revalidação do modelo e template

Execute integralmente as seções 4 e 5 da v2.2.9:

- identidade e hash do peso;
- cinco arquivos críticos e metadados da revisão fixada;
- download limitado somente se algum arquivo não-peso permitido estiver ausente;
- validação pelo runner versionado;
- template `benchmark/embedding-v3/templates/nemotron-rerank.jinja`.

O peso deve permanecer byte a byte idêntico.

## 7. Servidor, smoke e painel

Defina explicitamente:

```bash
VLLM_BIN="$PWD/runtimes/vllm-nemotron-0.25.1/bin/vllm"
```

Depois execute integralmente as seções 7 em diante da v2.2.9, sem alterar:

- revisão do modelo;
- peso;
- BF16;
- `runner pooling`;
- template oficial;
- `max-model-len 8192`;
- porta `8099`;
- candidates;
- top 50 para top 20;
- mapeamento dos índices e `relevance_score`;
- ordem dos seis perfis;
- outputs.

Antes do corpus, o servidor deve ficar READY e o smoke semântico deve passar. Sem smoke PASS, não execute nenhum dos 45.000 pares.

Somente o retry já autorizado na v2.2.9 para falha específica de CUDA graph pode usar `--enforce-eager`. Não altere dtype, template, modelo, revisão ou precisão.

## 8. Outputs e commit

Em sucesso, devem existir exatamente os 12 outputs NVIDIA previstos pela v2.2.9:

- seis scores sob `results/reranker/scores/llama_nemotron_rerank_1b_v2/`;
- seis pipelines sob `results/reranker/pipelines/llama_nemotron_rerank_1b_v2/`.

Valide integralmente conforme a v2.2.9:

- schema 1.0;
- modelo, revisão, peso e licença exatos;
- backend vLLM e runtime `0.25.1`;
- device CUDA e VRAM positiva;
- 7.500 pares por perfil;
- 150 queries, 50 IDs e scores finitos por query;
- ranking SHA do candidate correspondente;
- base, reranked, sete tipos, 150 per-query e 150 efeitos;
- top 50 para top 20;
- caminhos portáteis;
- todos os arquivos protegidos idênticos.

Execute novamente governance, teste focado, suíte integral, coverage, compileall e `git diff --check` conforme a v2.2.9.

O commit deve conter exatamente os 12 outputs e usar:

`Materialize NVIDIA Nemotron reranker panel`

Não inclua `runtimes/`, `rerank/`, logs, caches ou qualquer outro arquivo.

Faça push somente da branch existente. Não faça merge.

## 9. Falhas e não abandono

- instalação ausente ou incompatível é bloqueio de runtime, não reprovação do modelo;
- falha de servidor deve preservar log completo e causa raiz;
- falha de smoke deve preservar scores e resposta, sem executar o painel;
- erro transitório pode repetir uma vez a operação idêntica;
- OOM durante o painel deve seguir a redução de lote já autorizada na v2.2.9, sem mudar protocolo;
- métrica baixa após execução válida deve ser preservada, não descartada;
- continue os perfis seguintes quando a falha for isolada a um perfil e o servidor permanecer íntegro;
- não crie blacklist por uma falha isolada.

## 10. Retorno obrigatório

Comece exatamente com:

`Versão do retorno da IA local: 2.2.10 — runtime vLLM isolado e painel NVIDIA Nemotron`

Inclua:

1. HEAD inicial e final completos;
2. status antes/depois;
3. espaço livre antes/depois;
4. comando de instalação e exit code;
5. versão Python, vLLM, PyTorch isolado e CUDA;
6. GPU, compute capability, launcher e hashes do runtime;
7. snapshot, revisão, bytes e SHA-256 do modelo;
8. template e smoke;
9. servidor, flags, porta e retry, se houve;
10. comandos e exit codes;
11. total de testes;
12. 7.500 pares por perfil e 45.000 no total;
13. métricas completas base e reranked por perfil;
14. rescue, damage, latência, RAM e VRAM;
15. SHA-256 dos 12 outputs;
16. arquivos commitados;
17. confirmação de proteção, ausência de embeddings/APIs/outros modelos e ausência de merge.

Em bloqueio, informe o código exato, causa, logs relevantes, o último passo concluído, ausência de outputs e ausência de commit.