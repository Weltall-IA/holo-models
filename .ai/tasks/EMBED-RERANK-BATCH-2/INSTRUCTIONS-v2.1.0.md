# INSTRUCTIONS v2.1.0 — fase leve de embeddings e rerankers

## Objetivo

Executar somente a fase leve da rodada `EMBED-RERANK-BATCH-2`, preservando os resultados canônicos existentes, usando pesos identificados e produzindo evidências completas.

O contrato técnico obrigatório permanece:

`benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`

Estas instruções definem a ordem operacional, os limites da execução e o formato obrigatório do retorno.

## Repositório e branch de origem

- Repositório: `Weltall-IA/holo-models`
- Caminho principal esperado: `/home/alpha/Playstoria/models`
- Branch do contrato: `agent/prepare-next-embedding-rerank-batch-v2`
- Branch de execução a criar: `exec/embed-rerank-batch2-light`

## 1. Atualização obrigatória e worktree limpa

Não executar no diretório principal que contém stash ou arquivos não rastreados.

Execute:

```bash
set -euo pipefail

cd /home/alpha/Playstoria/models

git remote get-url origin
git fetch origin --prune

git show-ref --verify \
  refs/remotes/origin/agent/prepare-next-embedding-rerank-batch-v2

if [ ! -d ../models-embed-batch2-light/.git ] && \
   [ ! -f ../models-embed-batch2-light/.git ]; then
  git worktree add \
    -b exec/embed-rerank-batch2-light \
    ../models-embed-batch2-light \
    origin/agent/prepare-next-embedding-rerank-batch-v2
fi

cd ../models-embed-batch2-light

git pull --ff-only origin agent/prepare-next-embedding-rerank-batch-v2

CONTRACT_HEAD="$(git rev-parse origin/agent/prepare-next-embedding-rerank-batch-v2)"
LOCAL_HEAD="$(git rev-parse HEAD)"

test "$LOCAL_HEAD" = "$CONTRACT_HEAD"
test -z "$(git status --porcelain)"

git branch --show-current
git rev-parse HEAD
```

O remote deve corresponder a `Weltall-IA/holo-models`. Pare em caso de divergência.

## 2. Leitura obrigatória

Leia integralmente, nesta ordem:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/README.md`;
6. `benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`;
7. este arquivo.

As regras versionadas têm precedência sobre suposições locais.

## 3. Dry-run corrigido

Antes de baixar ou executar modelos, valide o estado canônico.

```bash
python - <<'PY'
import json
from pathlib import Path

path = Path("benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json")
assert path.is_file(), path

data = json.loads(path.read_text(encoding="utf-8"))

assert data["schema_version"] == "2.0.0"
assert data["validation"]["status"] == "PASS"
assert data["validation"]["raw_profile_count"] == 36
assert data["canonical_scope"]["raw_embedding_profiles"] == 36
assert data["canonical_scope"]["published_reranked_pipeline_artifacts"] == 89

expected_sources = {
    "gate2": 11,
    "gate3": 16,
    "voyage_raw": 2,
    "nemotron_admission": 2,
    "historical_raw_none": 5,
}
assert data["validation"]["raw_profile_source_counts"] == expected_sources

assert data["canonical_scope"]["corpus_documents"] == 600
assert data["canonical_scope"]["corpus_queries"] == 150
assert data["canonical_scope"]["corpus_sha256"] == (
    "8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b"
)

print("PASS: 36 raw profiles, 89 pipelines, corpus canônico íntegro.")
PY
```

Interpretação obrigatória:

- os 27 arquivos Gate 2 + Gate 3 não representam todo o inventário;
- os dois Nemotron admission, dois Voyage raw e cinco históricos completam os 36 perfis;
- não criar baselines artificiais em Gate 2 ou Gate 3;
- não regenerar `ALL_BENCHMARK_RESULTS.json` antes das execuções novas;
- o consolidado existente é entrada canônica da rodada.

## 4. Política de pesos

Aplicar em todos os modelos:

1. `NVFP4` confiável para o modelo exato;
2. `Q4_K_M` ou outro Q4 confiável;
3. Q8 ou precisão nativa somente para modelos de até 1B, quando não existir NVFP4/Q4 confiável, com preflight de memória e justificativa registrada.

Modelos acima de 1B não podem ser baixados ou executados em Q8 nesta rodada.

Nunca trocar silenciosamente peso, quantização, runtime, dimensão, pooling ou prompt após falha.

## 5. Resolver revisões antes dos downloads

Use o Hugging Face Hub para resolver revisões imutáveis:

```bash
python - <<'PY'
from huggingface_hub import HfApi

repos = [
    "LiquidAI/LFM2.5-Embedding-350M-GGUF",
    "microsoft/bitnet-embedding-0.6b",
    "microsoft/bitnet-embedding-270m",
    "mixedbread-ai/mxbai-rerank-base-v2",
    "nvidia/llama-nemotron-rerank-1b-v2",
]

api = HfApi()
for repo in repos:
    info = api.model_info(repo)
    print(f"{repo}\t{info.sha}")
PY
```

Registre para cada download:

- repositório;
- revisão imutável;
- arquivo exato;
- tamanho em bytes;
- SHA-256 completo;
- licença;
- caminho local.

Pare se o arquivo esperado não existir ou se a identidade não puder ser resolvida.

## 6. Fase 0 — pipelines Qwen locais ausentes

Sem baixar ou recalcular embeddings válidos, materialize candidates top 50 a partir dos artefatos canônicos existentes e execute `qwen_local` para:

- `nemotron_3_embed_1b_nvfp4`;
- `nemotron_3_embed_1b_q4_k_m_gguf`;
- `voyage-context-4`;
- `voyage-4-large` somente se a auditoria provar que ele não é equivalente a `voyage_4_large_1024_float32`.

Regras:

- não chamar a API de embedding Voyage;
- não copiar ou renomear candidate JSON para simular execução;
- cada arquivo deve conter 150 consultas ordenadas e pelo menos 50 candidatos por consulta;
- registrar o hash normalizado do ranking;
- preservar o corpus congelado;
- registrar hash e runtime do Qwen reranker.

## 7. Fase 1 — LFM2.5 Embedding 350M Q4_K_M

Fonte:

- repositório: `https://huggingface.co/LiquidAI/LFM2.5-Embedding-350M-GGUF`
- arquivo: `LFM2.5-Embedding-350M-Q4_K_M.gguf`
- arquivo web: `https://huggingface.co/LiquidAI/LFM2.5-Embedding-350M-GGUF/blob/main/LFM2.5-Embedding-350M-Q4_K_M.gguf`

Download, substituindo `<REV>` pela revisão resolvida:

```bash
mkdir -p embed/lfm_25_embedding_350m_q4_k_m_official

hf download LiquidAI/LFM2.5-Embedding-350M-GGUF \
  LFM2.5-Embedding-350M-Q4_K_M.gguf \
  --revision <REV> \
  --local-dir embed/lfm_25_embedding_350m_q4_k_m_official

sha256sum \
  embed/lfm_25_embedding_350m_q4_k_m_official/LFM2.5-Embedding-350M-Q4_K_M.gguf
```

Configuração obrigatória:

- backend llama.cpp com CUDA;
- pooling `CLS` explícito;
- dimensão 1024;
- normalização L2;
- consultas com prefixo `query: `;
- documentos com prefixo `document: `;
- similaridade cosseno;
- não usar mean pooling;
- não usar last-token pooling;
- não usar modelo gerador;
- não usar a variante ColBERT;
- não reutilizar cache ou candidates do LFM antigo.

Faça smoke test com 20 documentos e 10 consultas antes do corpus completo.

## 8. Fase 2 — BitNet Embedding 0.6B

Fonte:

- repositório: `https://huggingface.co/microsoft/bitnet-embedding-0.6b`
- arquivo: `bitnet-embeddings-0.6b-bf16-i2_s.gguf`
- revisão esperada como controle: `459a4718ed183ebbf5d7c89e4908f66322790e9b`

Use a revisão atual resolvida somente após compará-la com a revisão esperada e documentar eventual diferença.

```bash
mkdir -p embed/bitnet_06b_current

hf download microsoft/bitnet-embedding-0.6b \
  bitnet-embeddings-0.6b-bf16-i2_s.gguf \
  --revision <REV> \
  --local-dir embed/bitnet_06b_current

sha256sum embed/bitnet_06b_current/bitnet-embeddings-0.6b-bf16-i2_s.gguf
```

Configuração:

- formato oficial I2_S;
- dimensão 1024;
- pooling no último token não preenchido;
- normalização L2;
- instrução apenas na consulta;
- documentos sem instrução;
- não usar os GGUF legados incompatíveis com llama.cpp 9972.

## 9. Fase 3 — BitNet Embedding 270M

Fonte:

- repositório: `https://huggingface.co/microsoft/bitnet-embedding-270m`
- arquivo: `bitnet-embeddings-270m-bf16-i2_s.gguf`
- revisão esperada como controle: `b01800d7eba04db105a8ef88a8be61dbac047b0b`

```bash
mkdir -p embed/bitnet_270m_current

hf download microsoft/bitnet-embedding-270m \
  bitnet-embeddings-270m-bf16-i2_s.gguf \
  --revision <REV> \
  --local-dir embed/bitnet_270m_current

sha256sum embed/bitnet_270m_current/bitnet-embeddings-270m-bf16-i2_s.gguf
```

Configuração:

- formato oficial I2_S;
- dimensão 640;
- pooling no último token não preenchido;
- normalização L2;
- instrução apenas na consulta;
- documentos sem instrução;
- executar depois do 0.6B.

## 10. Runtime BitNet

Clone e compile uma única vez:

```bash
mkdir -p runtimes

if [ ! -d runtimes/BitNet/.git ]; then
  git clone --recursive https://github.com/microsoft/BitNet.git runtimes/BitNet
else
  git -C runtimes/BitNet pull --ff-only
  git -C runtimes/BitNet submodule update --init --recursive
fi

BITNET_COMMIT="$(git -C runtimes/BitNet rev-parse HEAD)"
echo "$BITNET_COMMIT"

cmake -S runtimes/BitNet -B runtimes/BitNet/build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DGGML_NATIVE=ON \
  -DGGML_OPENMP=OFF \
  -DLLAMA_BUILD_COMMON=ON \
  -DLLAMA_BUILD_TOOLS=ON \
  -DLLAMA_BUILD_EXAMPLES=ON

cmake --build runtimes/BitNet/build \
  --target llama-embedding llama-bench \
  -j"$(nproc)"
```

Use `llama-embedding`. Não usar `llama-cli`, servidor gerador ou o llama.cpp estável antigo para esses pesos.

Registre commit, compilador, flags e saída do build.

## 11. Gate dos embeddings pequenos

Gate normal:

- HR@50 >= `0.9666666667`;
- no máximo cinco consultas sem relevante;
- proveniência completa;
- candidate artifact exclusivo e válido.

Exceção BitNet:

- HR@50 >= `0.94`, devido ao valor operacional ultraleve.

Em caso de falha:

- preservar o baseline real;
- registrar o motivo;
- não executar reranker para o perfil;
- não inventar, estimar ou substituir métricas.

Execute `qwen_local` somente nos novos embeddings que passarem.

## 12. Fase 4 — Mixedbread Base v2

Fonte:

- `https://huggingface.co/mixedbread-ai/mxbai-rerank-base-v2`

Download:

```bash
mkdir -p rerank/mxbai_rerank_base_v2

hf download mixedbread-ai/mxbai-rerank-base-v2 \
  --revision <REV> \
  --local-dir rerank/mxbai_rerank_base_v2

find rerank/mxbai_rerank_base_v2 -type f -print0 \
  | sort -z \
  | xargs -0 sha256sum
```

Configuração:

- `sentence-transformers.CrossEncoder`;
- pontuar pares consulta-documento;
- exatamente um score finito por par;
- ordem decrescente de relevância;
- não usar geração de texto;
- registrar comprimento máximo e truncamento do tokenizer;
- precisão nativa permitida como exceção de modelo pequeno somente porque não há NVFP4/Q4 confiável selecionado.

## 13. Fase 5 — NVIDIA Llama Nemotron Rerank 1B v2

Fonte:

- `https://huggingface.co/nvidia/llama-nemotron-rerank-1b-v2`

Download:

```bash
mkdir -p rerank/llama_nemotron_rerank_1b_v2

hf download nvidia/llama-nemotron-rerank-1b-v2 \
  --revision <REV> \
  --local-dir rerank/llama_nemotron_rerank_1b_v2

find rerank/llama_nemotron_rerank_1b_v2 -type f -print0 \
  | sort -z \
  | xargs -0 sha256sum
```

Configuração:

- vLLM 0.25 em ambiente isolado;
- runner de pooling;
- `trust_remote_code=true` quando exigido pelo model card;
- usar `LLM.score` ou endpoint oficial de reranking;
- não usar geração de texto;
- não inverter `relevance_score`;
- preservar os índices de documentos.

Template obrigatório:

```text
question:{{ (messages | selectattr("role", "eq", "query") | first).content }}

passage:{{ (messages | selectattr("role", "eq", "document") | first).content }}
```

Ausência desse template invalida o teste.

## 14. Painel fixo dos dois rerankers

Execute Mixedbread e NVIDIA 1B nos mesmos candidates dos seis embeddings:

- `nemotron_3_embed_1b_nvfp4`;
- `nomic_embed_text_v2_moe_q4`;
- `qwen3_embedding_4b_q8_0`;
- `embeddinggemma`;
- `colibri_ptbr`;
- `granite_embedding_311m_r2`.

Compare contra `qwen_local` usando:

- MRR@10;
- nDCG@10;
- HR@1;
- HR@10;
- rescue rate;
- damage rate;
- erros de execução;
- latência p50 e p95;
- throughput;
- pico de RAM e VRAM.

## 15. Limite obrigatório da rodada

PARE ao concluir a fase leve.

Não executar:

- Qwen3 Reranker 4B;
- BOOM 4B;
- Qwen3 Embedding 8B;
- Nemotron Embed 8B;
- KaLM 12B;
- ICT/Querit Embedding v1;
- qualquer API Voyage.

Não baixar pesos desses modelos nesta execução.

## 16. Resultados e documentação

Após execuções reais:

- gravar artefatos individuais nos caminhos canônicos;
- preservar baseline e reranking separadamente;
- regenerar `ALL_BENCHMARK_RESULTS.json` somente a partir de artefatos reais;
- atualizar somente as duas tabelas do README canônico quando a decisão mudar;
- não criar leaderboard, registry, blacklist ou relatório paralelo;
- remover scripts e inventários temporários do diff final.

## 17. Validações obrigatórias

Execute e registre o resultado de cada comando:

```bash
python .ai/validate_governance.py
python -m unittest discover -s benchmark/embedding-v3/tests -v
python -m compileall -q benchmark/embedding-v3
python benchmark/embedding-v3/validate_coverage.py
git diff --check
```

Também valide:

- todos os JSONs novos parseiam;
- nenhuma query está ausente;
- a ordem das 150 consultas permanece congelada;
- os hashes do corpus não mudaram;
- não há IDs duplicados;
- nenhum perfil bloqueado ou `AUDIT_REQUIRED` entrou na tabela de bons;
- nenhum modelo pesado foi executado;
- nenhuma API Voyage foi acessada.

## 18. Git, push e PR

Revise o diff completo antes do commit.

```bash
git status --short
git diff --stat
git diff --check
git diff
```

Faça commit apenas dos resultados reais, código/configuração necessários e documentação canônica.

```bash
git add <arquivos-revisados>
git commit -m "Run light embedding and reranker benchmark batch"
git push -u origin exec/embed-rerank-batch2-light
```

Abra um PR para revisão humana.

Não faça merge.

## 19. Formato obrigatório do retorno

O retorno deve ser narrativo, direto e legível. Não despejar logs completos no chat. Indicar os caminhos dos logs e artefatos detalhados.

Apresente exatamente nesta ordem:

### Resultado direto

Em poucas linhas, informe se a fase leve foi concluída, concluída parcialmente ou bloqueada. Inclua:

- quantidade de modelos executados;
- quantidade de baselines gerados;
- quantidade de pipelines gerados;
- quantidade de modelos que passaram e falharam no gate;
- principal resultado ou principal bloqueio.

### O que funcionou

Liste somente resultados efetivamente concluídos, incluindo downloads verificados, benchmarks, pipelines, rerankers e validadores aprovados.

### O que travou ou ficou bloqueado

Para cada bloqueio, informe:

- modelo e fase;
- erro objetivo;
- tentativa realizada;
- motivo de não haver fallback;
- impacto nas fases posteriores;
- ação necessária.

### Pesos, revisões e hashes

Para cada modelo baixado ou utilizado, informe:

- repositório;
- revisão imutável;
- arquivo;
- tamanho em bytes;
- quantização ou dtype;
- SHA-256 completo;
- caminho local.

### Resultados dos embeddings

Para cada baseline novo, informe:

- MRR@10;
- HR@1;
- HR@10;
- HR@20;
- HR@50;
- nDCG@10;
- hard-negative error rate;
- consultas sem relevante;
- gate PASS/FAIL;
- tempo, throughput, RAM e VRAM.

### Resultados dos rerankers

Para cada pipeline novo, informe:

- embedding;
- reranker;
- MRR@10;
- nDCG@10;
- HR@1;
- HR@10;
- rescue rate;
- damage rate;
- erros;
- latência p50 e p95;
- RAM e VRAM.

### Validações e contagens

Informe:

- corpus, documentos, consultas e SHA-256;
- contagens canônicas antes e depois;
- todos os validadores executados e seus resultados;
- confirmação de que o consolidado foi regenerado somente após resultados reais.

### Alterações realizadas

Liste arquivos criados e alterados. Confirme que não foi criado leaderboard, registry, blacklist ou relatório paralelo.

### Estado Git

Informe:

- branch;
- HEAD final;
- commit;
- push;
- URL do PR;
- estado do PR;
- confirmação de que não houve merge.

### Campos obrigatórios

Inclua exatamente estes campos, com valores reais:

```text
contract_branch_updated = true|false
canonical_input_present = true|false
canonical_raw_profiles_before = <inteiro>
canonical_reranked_pipelines_before = <inteiro>
light_models_planned = <inteiro>
light_models_executed = <inteiro>
light_phase_completed = true|false
qwen3_embedding_8b_executed = false
nemotron_embedding_8b_executed = false
heavy_models_executed = false
voyage_api_accessed = false
voyage_api_calls_planned = 0
voyage_api_calls_executed = 0
canonical_results_regenerated_from_real_artifacts_only = true|false
merge_executed = false
```

A resposta deve terminar exatamente com:

`Versão do retorno da IA local: 2.1.0 — Fase leve de embeddings e rerankers`
