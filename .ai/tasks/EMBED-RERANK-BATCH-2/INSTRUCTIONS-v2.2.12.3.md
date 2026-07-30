# EMBED-RERANK-BATCH-2 — INSTRUCTIONS v2.2.12.3

## Objetivo

Fechar a única lacuna restante da auditoria de identidade entre os dois GGUF Nemotron 8B.

O artefato `benchmark/embedding-v3/results/reranker/nemotron_8b_abiray_aqua00_identity_audit.json` concluiu `IDENTICAL_TENSORS_METADATA_ONLY_DIFFERENCE`, mas verificou conteúdo de apenas 10 dos 308 tensores. Manifestos, metadados, shapes, tipos, tamanhos, candidates e métricas são idênticos; porém identidade integral do conteúdo tensorial ainda exige hash de todos os bytes de todos os tensores.

Esta etapa não executa embeddings, rerankers ou APIs. Não inicia servidores. Não baixa modelos. Não altera consolidado ou README.

## Estado obrigatório

- repositório: `Weltall-IA/holo-models`
- worktree: `/home/alpha/Playstoria/models-embed-batch2-light`
- branch: `exec/embed-rerank-batch2-light`
- PR: `#20`, aberto e draft
- HEAD inicial: deve coincidir exatamente com o SHA completo informado no handoff
- nenhum merge autorizado

Leia integralmente, nesta ordem:

1. `AGENTS.md`
2. `.ai/PROJECT.yml`
3. `.ai/WORKFLOW.yml`
4. `benchmark/embedding-v3/AGENTS.md`
5. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.12.md`
6. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.12.1.md`
7. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.2.12.2.md`
8. esta instrução
9. descrição e diff atuais do PR #20

Preserve os não rastreados existentes:

- `rerank/`
- `run_bitnet_benchmark.py`
- `run_light_phase.py`
- `runtimes/`

Não use stash, reset, clean, checkout destrutivo ou force-push.

## Pesos obrigatórios

Use exatamente os mesmos arquivos locais já auditados:

### Abiray

- repositório: `Abiray/Nemotron-3-Embed-8B-GGUF`
- revisão: `1ffb81e403311c4dc6879b9c3cbb6ebfa18b86df`
- arquivo: `Nemotron-3-Embed-8B-Q4_K_M.gguf`
- bytes: `4896390039`
- SHA-256: `a2aa29c618da6eed10d9474e72e33188c61e5fd700aed2fe9a1d98abdc90c6fc`

### Aqua00

- repositório: `Aqua00/Nemotron-3-Embed-8B-GGUF`
- revisão: `fa8f1317579eee6ecfa0a5623f4df0c0d19f5a87`
- arquivo: `Nemotron-3-Embed-8B-Q4_K_M.gguf`
- bytes: `4896389984`
- SHA-256: `1352d929879c61fccf76ff855c6250c7fdc924479932918febcc6fe384cb70a7`

Antes da comparação, recalcule bytes e SHA-256 dos dois arquivos e exija correspondência exata. Em divergência, pare.

## Comparação integral obrigatória

Use `gguf.GGUFReader` ou ferramenta equivalente somente leitura.

Para cada um dos 308 tensores, em ordem canônica por nome:

1. valide nome, shape, tipo GGUF e quantidade de bytes;
2. leia integralmente os bytes do tensor, não apenas uma amostra;
3. calcule SHA-256 do conteúdo tensorial;
4. registre o digest em um manifesto local temporário;
5. compare Abiray e Aqua00 tensor por tensor.

Calcule também:

- SHA-256 canônico do conjunto completo, alimentado por nome, shape, tipo, tamanho e SHA-256 de cada tensor;
- quantidade total de bytes tensoriais lidos;
- quantidade de tensores com digest divergente;
- lista de divergências, caso exista.

Não inclua caminhos absolutos no artefato.

## Classificação permitida

Use exatamente uma das seguintes classificações:

### `IDENTICAL_ALL_TENSOR_CONTENT_METADATA_ONLY_CONTAINER_DIFFERENCE`

Somente quando:

- 308/308 tensores possuem SHA-256 de conteúdo idêntico;
- metadados permanecem 54/54 idênticos;
- shapes, tipos e tamanhos permanecem idênticos;
- hash canônico completo é idêntico;
- a única diferença observável continua fora do conteúdo tensorial, no container/padding/trailing.

### `DIFFERENT_TENSOR_CONTENT_FUNCTIONALLY_EQUIVALENT_ON_BENCHMARK`

Quando pelo menos um tensor possuir conteúdo diferente, ainda que candidates e métricas sejam idênticos.

Nesse caso, registre todos os nomes divergentes e não alegue identidade tensorial.

## Artefato autorizado

Atualize exclusivamente:

`benchmark/embedding-v3/results/reranker/nemotron_8b_abiray_aqua00_identity_audit.json`

O artefato deve incluir:

- nova classificação factual;
- `tensor_count`;
- `tensor_content_hashes_compared: 308`;
- `tensor_content_diff_count`;
- hash canônico completo de cada peso;
- total de bytes tensoriais processados por peso;
- lista de tensores divergentes, vazia quando idênticos;
- preservação das provas anteriores de metadata, candidates e pipelines;
- ferramentas e versões usadas;
- portabilidade aprovada.

Não versionar o manifesto temporário com 308 hashes individuais, a menos que seja pequeno e necessário para auditoria. Preferencialmente registre apenas os hashes canônicos completos e as divergências.

## Validações

Execute:

```bash
PYTHON=/home/alpha/Playstoria/models/benchmarks/holo-embedding-benchmark-v3/.venv/bin/python

"$PYTHON" .ai/validate_governance.py
"$PYTHON" -m unittest discover -s benchmark/embedding-v3/tests -v
"$PYTHON" -m compileall -q benchmark/embedding-v3
"$PYTHON" benchmark/embedding-v3/validate_coverage.py
git diff --check
```

Exija:

- pelo menos 235 testes;
- zero failures e zero errors;
- todos os comandos com exit code 0;
- somente o artefato autorizado alterado;
- todos os 13 artefatos v2.2.12.1 preservados byte a byte;
- `ALL_BENCHMARK_RESULTS.json` e `README.md` preservados;
- nenhum processo de modelo ou API iniciado.

## Commit e retorno

Commit somente o artefato atualizado e faça push sem force.

O retorno deve informar:

1. HEAD inicial e commit final completo;
2. bytes e SHA-256 dos dois GGUF reconfirmados;
3. número de tensores comparados integralmente;
4. total de bytes tensoriais lidos por arquivo;
5. hash canônico completo de cada conjunto tensorial;
6. quantidade e nomes de tensores divergentes;
7. classificação final exata;
8. testes e exit codes;
9. arquivos alterados;
10. confirmação de ausência de embeddings, rerankers, APIs, downloads e merge.

O lote continua aberto. Voyage permanece pendente e não é autorizado nesta etapa.
