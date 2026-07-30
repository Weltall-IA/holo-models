# EMBED-RERANK-BATCH-2 — INSTRUCTIONS v2.2.12

## Objetivo

Corrigir a pendência que invalidou o encerramento anterior do lote:

1. reexecutar **do zero** os dois artefatos Nemotron 8B anteriormente registrados como `nemotron_8b_abiray_q4` e `nemotron_8b_aqua00_q4`;
2. provar que Abiray e Aqua00 correspondem a pesos locais distintos, com repositório, revisão imutável, arquivo, tamanho e SHA-256;
3. gerar novos resultados raw e novos candidates independentes em 4096 e 1024 dimensões;
4. executar novamente o Qwen3-Reranker-0.6B sobre esses candidates;
5. completar a comparação Voyage Rerank 2.5 para as quatro novas variantes quando a execução puder ocorrer sem cobrança;
6. preservar todos os artefatos antigos como evidência histórica, sem reutilizá-los como entrada.

Esta etapa **não** consolida `ALL_BENCHMARK_RESULTS.json` e **não** altera `README.md`. A consolidação será refeita somente após a auditoria destes novos resultados.

## Estado Git obrigatório

Repositório:

`Weltall-IA/holo-models`

Worktree:

`/home/alpha/Playstoria/models-embed-batch2-light`

Branch:

`exec/embed-rerank-batch2-light`

O HEAD deve corresponder exatamente ao SHA informado no handoff do gerente.

PR:

`#20`

O PR deve permanecer aberto, draft e sem merge.

Antes de qualquer execução:

```bash
cd /home/alpha/Playstoria/models-embed-batch2-light
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse origin/exec/embed-rerank-batch2-light
```

Pare se:

- a branch divergir;
- HEAD local e remoto divergirem;
- houver alteração rastreada não esperada;
- qualquer arquivo protegido já estiver modificado.

Preserve integralmente os não rastreados existentes:

- `rerank/`
- `run_bitnet_benchmark.py`
- `run_light_phase.py`
- `runtimes/`

Não faça stash, reset, clean, checkout destrutivo ou force-push.

## Responsabilidade da IA executora

A IA executora pode:

- inspecionar arquivos, metadados e runtimes locais;
- resolver identidades imutáveis no Hugging Face;
- baixar somente os dois GGUF Q4_K_M autorizados, quando necessário;
- executar testes;
- executar os dois benchmarks de embedding;
- executar Qwen3-Reranker-0.6B;
- executar Voyage Rerank 2.5 apenas nas condições de cobrança desta instrução;
- validar e commitar apenas os artefatos gerados.

A IA executora não pode:

- editar código, testes, configuração, instruções ou documentação;
- alterar os JSONs antigos dos dois 8B;
- reutilizar candidates, scores ou pipelines antigos;
- usar outro embedding ou outro reranker;
- atualizar o consolidado ou a README;
- mesclar o PR.

Falha de código deve ser reportada ao gerente sem correção local.

## Python e runtime

Use:

```bash
PYTHON=/home/alpha/Playstoria/models/benchmarks/holo-embedding-benchmark-v3/.venv/bin/python
```

Confirme:

```bash
"$PYTHON" --version
```

Use exclusivamente o `llama-server` estável build 9972 já instalado. Não instale ou atualize llama.cpp, CUDA, driver, Python ou PyTorch.

Use CUDA. CPU não é protocolo equivalente para esta etapa.

## Proteção dos artefatos existentes

Antes de executar, produza um manifesto SHA-256 de todos os arquivos rastreados existentes sob:

- `benchmark/embedding-v3/results/`
- `benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json`
- `benchmark/embedding-v3/README.md`

Exclua do conjunto protegido apenas os novos caminhos listados em “Outputs autorizados”. Como ainda não existem no HEAD inicial, nenhum arquivo antigo deve ser excluído na primeira captura.

Ao final, todos os arquivos protegidos antigos devem permanecer byte a byte idênticos, inclusive:

- `results/gate3/nemotron_8b_abiray_q4.json`
- `results/gate3/nemotron_8b_aqua00_q4.json`
- `results/reranker/candidates/nemotron_8b_abiray_q4.json`
- `results/reranker/candidates/nemotron_8b_aqua00_q4.json`
- `results/reranker/pipelines/qwen_local/nemotron_8b_abiray_q4.json`
- `results/reranker/pipelines/qwen_local/nemotron_8b_aqua00_q4.json`
- todos os resultados Voyage existentes;
- todos os resultados Mixedbread, NVIDIA Nemotron 1B, BitNet, LFM e demais modelos;
- `ALL_BENCHMARK_RESULTS.json`;
- `README.md`.

## Testes antes do benchmark

Execute:

```bash
cd benchmark/embedding-v3

"$PYTHON" validate_governance.py

"$PYTHON" -m unittest -v \
  tests.test_nemotron_8b_audit

"$PYTHON" -m unittest discover -s tests -p 'test_*.py'
```

Critérios:

- testes dedicados: `6/6`;
- suíte integral: pelo menos `235` testes;
- zero falhas e zero erros.

Depois:

```bash
"$PYTHON" -m compileall -q .
```

Qualquer falha de código bloqueia a execução e deve ser reportada.

## Identidade independente dos dois pesos

Os dois modelos obrigatórios são:

| ID de auditoria | Proprietário obrigatório |
|---|---|
| `nemotron_8b_abiray_q4_audit` | `Abiray/` |
| `nemotron_8b_aqua00_q4_audit` | `Aqua00/` |

Para cada proprietário:

1. identifique o repositório Nemotron-3-Embed-8B GGUF exato;
2. resolva o SHA imutável de 40 caracteres da revisão;
3. identifique exatamente um arquivo `Q4_K_M.gguf`;
4. registre tamanho em bytes;
5. registre SHA-256 local;
6. registre a fonte usada para provar repositório, revisão e arquivo.

Não use `main` como revisão na execução.

### Abiray já conhecido historicamente

O artefato Abiray planejado anteriormente era:

- arquivo: `Nemotron-3-Embed-8B-Q4_K_M.gguf`;
- bytes: `5116768352`;
- SHA-256: `524689a7d434da58483a9ffe24b01bb23cbb48ec1a17a8ade5d86db10e16069c`.

Se o snapshot imutável recuperado para Abiray não corresponder a esses bytes e hash:

- não substitua silenciosamente;
- registre a revisão nova e a divergência;
- use o artefato novo somente se foi baixado diretamente do repositório Abiray na revisão imutável informada;
- destaque a mudança no retorno.

### Downloads autorizados

Prefira um snapshot local existente somente quando metadados verificáveis provarem repositório, revisão imutável e arquivo.

Se essa prova não existir, está autorizado baixar novamente **somente**:

- um GGUF `Q4_K_M` do repositório Abiray resolvido;
- um GGUF `Q4_K_M` do repositório Aqua00 resolvido;
- os pequenos metadados necessários para provar identidade.

Use diretórios separados e não rastreados sob:

`runtimes/nemotron-8b-audit/`

Não baixe outras quantizações, shards ou modelos.

Antes do download, confirme espaço suficiente para os dois pesos e uma margem mínima de 10 GiB. Se não houver espaço, reporte `BLOCKED_DISK_SPACE` sem apagar nada.

Após o download, compute novamente bytes e SHA-256. O valor passado ao runner deve ser o valor já verificado externamente no preflight; o runner recalculará e exigirá igualdade.

### Distinção obrigatória

Os dois pesos devem ter:

- repositórios distintos;
- revisões registradas;
- arquivos registrados;
- SHA-256 distintos.

Se os SHA-256 forem iguais:

- não execute benchmarks duplicados;
- reporte `BLOCKED_IDENTICAL_WEIGHTS_PROVEN`;
- inclua toda a prova;
- não trate isso como dois modelos distintos;
- não altere os artefatos antigos.

## Protocolo de embedding obrigatório

Runner versionado:

```bash
"$PYTHON" -m holo_benchmark.nemotron_8b_audit
```

Protocolo fixo:

- corpus: 600 documentos e 150 consultas;
- corpus SHA-256: `8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b`;
- backend: llama.cpp estável build 9972;
- device: CUDA;
- quantização: Q4_K_M;
- pooling: `mean`;
- normalização do servidor: `2`;
- documentos: prefixo `passage: `;
- consultas: prefixo `query: `;
- dimensão nativa exigida: pelo menos 4096;
- variantes publicadas por peso: 4096 e 1024;
- normalização L2 após truncamento;
- batch de embedding: 8;
- candidate top-k: 50;
- `-ngl 99`;
- contexto: 4096;
- server batch/ubatch: 512/512.

Execute Abiray e Aqua00 em processos separados. Não reutilize embeddings, caches de vetores ou candidates entre os dois pesos.

Modelo de comando:

```bash
"$PYTHON" -m holo_benchmark.nemotron_8b_audit embed \
  --model-id nemotron_8b_abiray_q4_audit \
  --repo '<REPOSITORIO_ABIRAY_EXATO>' \
  --revision '<SHA_IMUTAVEL_ABIRAY>' \
  --model-file '<CAMINHO_GGUF_ABIRAY>' \
  --expected-bytes '<BYTES_ABIRAY>' \
  --expected-sha256 '<SHA256_ABIRAY>'
```

Depois:

```bash
"$PYTHON" -m holo_benchmark.nemotron_8b_audit embed \
  --model-id nemotron_8b_aqua00_q4_audit \
  --repo '<REPOSITORIO_AQUA00_EXATO>' \
  --revision '<SHA_IMUTAVEL_AQUA00>' \
  --model-file '<CAMINHO_GGUF_AQUA00>' \
  --expected-bytes '<BYTES_AQUA00>' \
  --expected-sha256 '<SHA256_AQUA00>'
```

Cada comando deve produzir exatamente:

- dois resultados raw;
- dois candidates.

Os quatro IDs novos devem ser:

- `nemotron_8b_abiray_q4_audit_4096`
- `nemotron_8b_abiray_q4_audit_1024`
- `nemotron_8b_aqua00_q4_audit_4096`
- `nemotron_8b_aqua00_q4_audit_1024`

Confirme que:

- cada candidate contém 150 consultas;
- cada consulta contém 50 candidates;
- os candidates Abiray e Aqua00 não são copiados;
- os payloads preservam pesos e revisões corretos;
- todos passam `assert_portable_payload`.

Resultados numericamente iguais são permitidos somente se foram realmente gerados por execuções independentes e os candidates completos confirmarem isso. Não force divergência artificial.

## Qwen3-Reranker-0.6B obrigatório

Use exclusivamente o artefato local Qwen3-Reranker-0.6B já usado nos benchmarks canônicos.

Não use Qwen 4B, 8B ou seleção automática de outro tamanho.

Localize o caminho exato sob `rerank/` e execute:

```bash
"$PYTHON" -m holo_benchmark.nemotron_8b_audit qwen \
  --qwen-model-path '<CAMINHO_QWEN3_RERANKER_0.6B>' \
  --device cuda \
  --reranker-batch-size 8 \
  --rerank-top-k 20
```

O runner deve:

- carregar os quatro candidates novos;
- validar que os dois pesos são distintos;
- construir uma união estável dos top-20;
- escrever score separado, sem sobrescrever `scores/qwen_local.json`;
- produzir quatro pipelines Qwen novos;
- registrar base metrics, reranked metrics e efeito;
- passar portabilidade.

Não reutilize os dois pipelines Qwen antigos.

## Voyage Rerank 2.5

A comparação Voyage é obrigatória para as quatro novas variantes, mas nenhuma cobrança pode ser realizada implicitamente.

### Condição para execução

Antes de qualquer chamada:

- confirme que a chave é a mesma chave de franquia gratuita usada anteriormente;
- confirme que não há método de pagamento habilitado para cobrança automática;
- confirme que a execução continuará sem cobrança;
- registre essa confirmação no retorno.

Somente após essa confirmação:

```bash
export VOYAGE_NO_CHARGE_CONFIRMED=1

"$PYTHON" -m holo_benchmark.nemotron_8b_audit voyage \
  --api-key-path /home/alpha/Playstoria/models/.voyage4_token \
  --rerank-top-k 20 \
  --request-interval-seconds 1 \
  --confirm-no-charge
```

Se ocorrer interrupção recuperável, repita com `--resume`.

O runner deve:

- usar `rerank-2.5`;
- usar somente os quatro candidates novos;
- escrever checkpoint e score separados;
- não sobrescrever os nove pipelines Voyage existentes;
- produzir quatro pipelines Voyage novos;
- registrar requests, tokens, duração e `charged_cost_usd: null`.

### Bloqueio de cobrança

Se a ausência de cobrança não puder ser provada antes da chamada:

- não configure `VOYAGE_NO_CHARGE_CONFIRMED`;
- não chame a API;
- reporte `BLOCKED_VOYAGE_NO_CHARGE_PROOF`;
- conclua e versione os resultados locais de embedding + Qwen;
- não declare a auditoria completa.

Erros 401, 402, quota/billing ou qualquer indicação de cobrança devem interromper a etapa Voyage.

## Validação final

Se Voyage foi executado:

```bash
"$PYTHON" -m holo_benchmark.nemotron_8b_audit validate \
  --require-voyage
```

Se Voyage foi bloqueado antes da chamada:

```bash
"$PYTHON" -m holo_benchmark.nemotron_8b_audit validate
```

Depois execute novamente:

```bash
"$PYTHON" validate_governance.py
"$PYTHON" -m unittest -v tests.test_nemotron_8b_audit
"$PYTHON" -m unittest discover -s tests -p 'test_*.py'
"$PYTHON" -m compileall -q .
"$PYTHON" validate_coverage.py
git diff --check
```

Critérios locais mínimos:

- 4 resultados raw novos;
- 4 candidates novos;
- 1 score Qwen novo;
- 4 pipelines Qwen novos;
- 150 consultas por artefato;
- 50 candidates por consulta;
- SHA-256 Abiray e Aqua00 distintos;
- 6/6 testes dedicados;
- suíte integral com pelo menos 235 testes;
- portabilidade PASS;
- nenhum arquivo antigo alterado.

Com Voyage, também:

- 1 checkpoint Voyage novo;
- 1 score Voyage novo;
- 4 pipelines Voyage novos;
- 150 requisições concluídas;
- zero falhas;
- `charged_cost_usd: null`.

## Outputs autorizados

### Sempre autorizados

- `benchmark/embedding-v3/results/gate3/nemotron_8b_abiray_q4_audit_4096.json`
- `benchmark/embedding-v3/results/gate3/nemotron_8b_abiray_q4_audit_1024.json`
- `benchmark/embedding-v3/results/gate3/nemotron_8b_aqua00_q4_audit_4096.json`
- `benchmark/embedding-v3/results/gate3/nemotron_8b_aqua00_q4_audit_1024.json`
- quatro arquivos correspondentes em `benchmark/embedding-v3/results/reranker/candidates/`
- `benchmark/embedding-v3/results/reranker/scores/qwen_local_nemotron_8b_audit.json`
- quatro arquivos correspondentes em `benchmark/embedding-v3/results/reranker/pipelines/qwen_local/`

Total local: **13 arquivos**.

### Autorizados somente se Voyage executar sem cobrança

- `benchmark/embedding-v3/results/raw/reranker/voyage_rerank_2_5_nemotron_8b_audit.json`
- `benchmark/embedding-v3/results/reranker/scores/voyage_rerank_2_5_nemotron_8b_audit.json`
- quatro arquivos correspondentes em `benchmark/embedding-v3/results/reranker/pipelines/voyage_rerank_2_5/`

Total adicional Voyage: **6 arquivos**.

Total com Voyage: **19 arquivos**.

Nenhum outro arquivo pode entrar no commit.

## Commit e push

Se Voyage foi concluído sem cobrança:

```bash
git add <os 19 outputs autorizados>
git commit -m "Rerun independent Nemotron 8B audits with Qwen and Voyage"
git push origin exec/embed-rerank-batch2-light
```

Se Voyage foi bloqueado antes da chamada:

```bash
git add <os 13 outputs locais autorizados>
git commit -m "Rerun independent Nemotron 8B audits with Qwen"
git push origin exec/embed-rerank-batch2-light
```

Não adicione:

- código;
- testes;
- instruções;
- `runtimes/`;
- `rerank/`;
- logs;
- caches;
- pesos;
- `ALL_BENCHMARK_RESULTS.json`;
- `README.md`.

## Retorno obrigatório

O retorno deve informar:

1. HEAD inicial completo;
2. commit final completo;
3. branch e PR;
4. status antes/depois;
5. Python e llama.cpp utilizados;
6. identidade Abiray:
   - repositório;
   - revisão;
   - arquivo;
   - bytes;
   - SHA-256;
   - origem da prova;
7. identidade Aqua00 com os mesmos campos;
8. comprovação de que os hashes são distintos;
9. comandos e exit codes;
10. testes antes/depois;
11. métricas raw completas das quatro variantes;
12. comparação 4096 × 1024 por peso;
13. prova de independência dos candidates:
   - hashes dos quatro candidate JSONs;
   - quantidade de consultas e candidates;
   - comparação entre payloads Abiray e Aqua00;
14. métricas Qwen completas dos quatro pipelines;
15. rescue/damage de cada pipeline Qwen;
16. status Voyage;
17. se Voyage executou:
   - métricas completas dos quatro pipelines;
   - rescue/damage;
   - requests;
   - tokens;
   - duração;
   - confirmação de cobrança nula;
18. se Voyage não executou:
   - bloqueio exato e prova de que nenhuma chamada ocorreu;
19. lista exata dos arquivos do commit;
20. confirmação de que todos os artefatos antigos, consolidado e README permaneceram idênticos;
21. confirmação de que `rerank/`, `runtimes/` e demais não rastreados foram preservados;
22. confirmação de nenhum merge.

Não declare o lote concluído. O gerente ainda deve auditar estes resultados e regenerar o consolidado canônico.

`Versão do retorno da IA local: 2.2.12 — reexecução independente dos dois Nemotron 8B e cobertura Qwen/Voyage`
