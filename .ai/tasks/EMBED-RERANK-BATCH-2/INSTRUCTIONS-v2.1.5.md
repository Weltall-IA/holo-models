# INSTRUCTIONS v2.1.5 — conclusão efetiva após execução parcial da v2.1.4

## Objetivo

Continuar exclusivamente no PR #20 e concluir os itens da v2.1.4 que não foram executados, corrigindo também as inconsistências objetivamente encontradas no commit `8dc9d2adb2f7fe5a57cfe2ed721c269c2964e3da`.

Não reinicie a rodada. Preserve benchmarks e scores reais. Não repita downloads válidos. Não execute modelos pesados. Não chame API Voyage. Não altere CUDA, driver, PyTorch global, Python do sistema ou pacotes globais.

Contrato técnico obrigatório:

`benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`

A v2.1.4 permanece como contexto obrigatório. Esta versão substitui somente a ordem de continuação depois da auditoria do retorno v2.1.4.

## Repositório, branch e PR

- Repositório: `Weltall-IA/holo-models`
- Worktree esperada: `/home/alpha/Playstoria/models-embed-batch2-light`
- Branch: `exec/embed-rerank-batch2-light`
- PR: `#20`
- Estado obrigatório: aberto e draft
- HEAD auditado: `8dc9d2adb2f7fe5a57cfe2ed721c269c2964e3da`

Não crie outro PR. Não faça merge.

## 1. Retomada segura

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
test -f .ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.5.md
```

O remote deve corresponder a `Weltall-IA/holo-models`.

Antes de alterar arquivos, registre staged, unstaged, não rastreados, processos ativos, RAM, VRAM, downloads, hashes dos pesos, hashes dos binários e hashes dos artefatos existentes.

Não use `reset --hard`, `clean`, `checkout --`, stash automático, force-push ou recriação da worktree.

## 2. Leitura obrigatória

Leia integralmente, nesta ordem:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`;
6. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.0.md`;
7. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.1.md`;
8. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.2.md`;
9. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.3.md`;
10. `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.4.md`;
11. este arquivo;
12. diff, commits e descrição atual do PR #20.

## 3. Estado auditado do retorno v2.1.4

O commit `8dc9d2adb2f7fe5a57cfe2ed721c269c2964e3da` contém somente alterações em:

- `benchmark/embedding-v3/holo_benchmark/bitnet_parser.py`;
- `benchmark/embedding-v3/holo_benchmark/bitnet_runner.py`;
- `benchmark/embedding-v3/tests/test_bitnet_parser.py`.

Portanto, o retorno não concluiu a v2.1.4. Nenhum artefato de embedding, candidate, score artifact, pipeline, consolidado, README ou evidência Nemotron foi alterado nesse commit.

Não declare como criado ou corrigido no commit um arquivo que já existia e permaneceu inalterado.

### 3.1 Inconsistências do parser atual

O parser melhorou, mas ainda não comprova gramática estrita completa:

- tokens vazios são ignorados com `continue`; uma sequência malformada com vírgula dupla pode ser aceita quando a contagem final de números coincide com a dimensão esperada;
- a política de vetores idênticos está separada da identidade real das entradas;
- o runner sempre chama o parser com `allow_identical=False`, então entradas textualmente idênticas podem produzir falso bloqueio;
- o parser deve validar o formato real observado, sem aceitar separadores ausentes, duplicados ou estruturas ambíguas.

### 3.2 Inconsistências do runner atual

O arquivo é um helper versionado, mas ainda não é integração canônica completa:

- nenhum entrypoint real do benchmark foi alterado para usá-lo;
- nenhum artefato canônico foi produzido por ele;
- não usa `atomic_json`;
- não registra comando sanitizado, exit code, commit BitNet, RAM ou VRAM residual;
- `doc_encode_seconds` e `query_encode_seconds` recebem o mesmo tempo combinado, o que não representa medições separadas;
- `doc_indices` é usado somente como contagem e não há validação explícita de índices, sobreposição ou cobertura;
- a política de entradas idênticas não é propagada ao parser.

### 3.3 Testes declarados e testes realmente necessários

A suíte adicionada testa helpers, mas o teste chamado de integração do candidate apenas monta um dicionário em memória. Ele não chama `load_candidate_payloads` e não valida os arquivos finais do branch.

Também continuam ausentes, no mínimo:

- timeout do subprocesso;
- vírgula dupla ou token vazio;
- vírgula final;
- separador estrutural inválido;
- índices fora do intervalo, duplicados ou sobrepostos;
- entradas textualmente idênticas com associação determinística;
- chamada real do loader canônico contra payload persistido;
- entrypoint canônico produzindo artefato aceito pelo loader e avaliador.

Executar somente `test_bitnet_parser.py` não autoriza `local_test_suite_passed = true`. Esse campo exige a suíte integral definida no projeto.

### 3.4 Campos incorretos no retorno

Não repita estas declarações enquanto o estado não mudar:

- `bitnet_runner_canonical_integration = true`: falso enquanto nenhum entrypoint e nenhum artefato canônico usarem o runner;
- `bitnet_06b_complete_artifact_validated = true`: falso enquanto o artefato mantiver métricas incompletas;
- `bitnet_270m_complete_artifact_validated = true`: falso enquanto o artefato mantiver métricas incompletas;
- `empty_per_query_completed_results = 0`: incompatível com artefatos `COMPLETED` que ainda possuem `per_query: []`;
- `empty_by_query_type_completed_results = 0`: incompatível com artefatos `COMPLETED` que ainda possuem `by_query_type: {}`;
- `nemotron_blocked_with_complete_evidence = true`: falso enquanto o arquivo de evidência insuficiente da auditoria anterior permanecer inalterado;
- `local_test_suite_passed = true`: falso quando somente 25 testes de um arquivo foram reportados.

## 4. Finalizar parser e runner BitNet

### 4.1 Parser

Implemente gramática de consumo integral para o formato real preservado no smoke test.

O parser deve:

1. rejeitar tokens vazios, vírgula dupla e vírgula final;
2. rejeitar separadores ou brackets extras;
3. rejeitar texto residual, truncamento, NaN, infinito, norma zero, dimensão e contagem incorretas;
4. validar normalização sem normalizar silenciosamente;
5. associar vetores às entradas de forma determinística;
6. rejeitar vetores idênticos somente quando as entradas correspondentes forem distintas;
7. aceitar vetores idênticos para entradas textualmente idênticas quando essa condição for explicitamente comprovada pelo chamador;
8. manter dimensões configuradas por perfil;
9. produzir erros objetivos.

Não use busca permissiva que ignore partes da saída.

### 4.2 Runner

O runner deve:

- validar existência e tipo de binário e GGUF antes do subprocesso;
- validar índices, faixa, duplicação, sobreposição e cobertura;
- propagar ao parser quais entradas são textualmente idênticas;
- aplicar instrução somente às queries;
- registrar comando sanitizado, exit code, duração, throughput, pico de RAM, VRAM residual, caminho e SHA-256 do binário, commit BitNet, caminho, bytes e SHA-256 do GGUF;
- não registrar tempos separados quando a execução foi combinada; use um campo combinado ou meça separadamente de verdade;
- tratar `TimeoutExpired` com erro sanitizado e teste correspondente;
- integrar-se a um entrypoint versionado que produza candidate e resultado no esquema canônico;
- gravar JSON somente com o serializador atômico do projeto.

### 4.3 Testes

Adicione testes objetivos para todos os itens acima. O teste de loader deve chamar `load_candidate_payloads` de verdade, usando arquivo temporário ou o artefato final, com dataset congelado controlado ou mocks mínimos apenas onde necessário.

Não considere uma inspeção manual de chaves como teste do loader.

## 5. Concluir candidates e métricas dos embeddings

Depois da integração:

### 5.1 Candidates

Para LFM2.5 e BitNet 270M:

- preserve rankings reais quando origem e ordem forem comprovadas;
- valide 150 queries na ordem congelada;
- valide top 50 e IDs únicos por query;
- registre `variant`, `dataset.corpus_sha256`, `candidate_top_k`, `queries` e `candidates` no esquema vigente;
- registre fonte e hash normalizado do ranking;
- inclua os perfis no fluxo canônico sem quebrar variantes existentes;
- grave por `atomic_json`;
- execute `load_candidate_payloads` contra os arquivos finais.

BitNet 0.6B não recebe pipeline Qwen se o gate completo continuar FAIL.

### 5.2 Métricas

Recalcule, pelo avaliador canônico e a partir dos rankings reais, LFM2.5, BitNet 0.6B e BitNet 270M.

Exija:

- HitRate@1, @3, @5, @10, @20 e @50;
- Recall quando previsto;
- MRR@10;
- nDCG@10;
- mean e median first relevant rank;
- queries_without_relevant;
- hard-negative error rate;
- `by_query_type` completo;
- `per_query` com 150 entradas;
- identidade e proveniência completas;
- comando, backend, versão, commit e dispositivo;
- tempos, throughput, RAM e VRAM;
- corpus, contagens e SHA-256;
- gate recalculado.

Não mantenha zero placeholder. Não marque artefato completo apenas pelo HR@50.

## 6. Concluir pipelines Qwen

Para LFM2.5 e BitNet 270M aprovado:

1. produza score artifact separado pelo fluxo canônico;
2. gere pipeline pelo avaliador vigente;
3. valide MRR@10, nDCG@10, HitRate, damage, rescue, erros, latência, RAM e VRAM;
4. remova formatos reduzidos somente depois de preservar e reutilizar scores reais com vínculo comprovado;
5. confirme caminhos existentes para todo `score_artifact` referenciado.

Tente individualmente os pipelines obrigatórios da fase 0:

- `nemotron_3_embed_1b_nvfp4`;
- `nemotron_3_embed_1b_q4_k_m_gguf`;
- `voyage-context-4`;
- `voyage-4-large` somente quando a auditoria de alias exigir execução separada.

Não use API Voyage. Quando bloqueado, registre tentativa, caminhos, comando, erro e dependência ausente.

## 7. Concluir painel Mixedbread

- valide scores reais preservados;
- gere score artifact canônico;
- regenere os cinco pipelines existentes pelo gerador vigente;
- execute o sexto membro quando houver candidate válido;
- compute evaluation, damage e rescue pelo avaliador;
- registre modelo, revisão, pesos, hashes, tokenizer, truncamento, backend, comando, latência, RAM e VRAM;
- mantenha o painel incompleto se o sexto candidate estiver comprovadamente bloqueado;
- não crie resumo paralelo.

Os cinco JSON reduzidos atuais não contam como pipelines canônicos.

## 8. Corrigir a evidência do NVIDIA Nemotron

O arquivo anterior não foi alterado no commit auditado. Complete a evidência exigida pela v2.1.4:

- caminho e versão do Python;
- versão do pip;
- caminho do ambiente isolado;
- driver NVIDIA;
- CUDA toolkit;
- PyTorch;
- comando exato;
- índice de pacotes;
- saída sanitizada do resolver ou importação;
- constraints e dependências incompatíveis;
- caminho do log local;
- revisão, arquivo, bytes e SHA-256 do peso.

Confirme a causa raiz real. Não assuma que a mensagem resumida anterior comprova sozinha incompatibilidade do toolkit. Verifique também compatibilidade do Python e disponibilidade de wheels.

Não altere o sistema e não repita tentativa já conclusiva sem uma hipótese técnica nova e isolada.

## 9. Consolidação canônica

Somente quando os artefatos individuais localmente viáveis estiverem válidos:

1. execute o gerador canônico de `ALL_BENCHMARK_RESULTS.json`;
2. confirme `source_commit`, `generated_at`, contagens e validação;
3. atualize somente as duas tabelas canônicas do README quando a decisão mudar;
4. preserve embedding-only separado de reranked;
5. não inclua bloqueados ou incompletos no ranking aceito;
6. não use contagem manual;
7. não copie métricas manualmente;
8. não crie leaderboard, registry, blacklist ou relatório paralelo.

Enquanto o consolidado continuar em 36 perfis raw e 89 pipelines, reporte exatamente 36 e 89.

## 10. Validações obrigatórias

Execute e registre o comando e exit code:

```bash
python .ai/validate_governance.py
python -m unittest discover -s benchmark/embedding-v3/tests -v
python -m compileall -q benchmark/embedding-v3
python benchmark/embedding-v3/validate_coverage.py
python benchmark/embedding-v3/reranker_benchmark.py --phase preflight
git diff --check
```

Valide também programaticamente:

- todos os JSON e YAML;
- corpus 600/150 e SHA-256 congelado;
- candidates com 150 queries, ordem e top 50;
- loader canônico executado contra candidates finais;
- score artifacts existentes;
- pipelines no schema vigente;
- `per_query` com 150 entradas em resultados completos;
- `by_query_type` não vazio em resultados completos;
- ausência de NaN, infinito e placeholders;
- IDs únicos;
- contagens coerentes;
- ausência de arquivos paralelos;
- ausência de Voyage;
- ausência de download e execução pesada;
- diff integral depois da última correção.

Não declare CI aprovado: não existe workflow run associado ao HEAD auditado.

## 11. Git e PR

Depois da validação:

- revise o diff completo;
- inclua somente código, testes, instruções e artefatos reais do escopo;
- faça commit no mesmo branch;
- faça push sem force;
- atualize a descrição do PR #20;
- mantenha aberto e draft;
- não faça merge;
- não abra outro PR.

## 12. Formato do retorno

Apresente:

1. resultado direto e contagens do consolidado;
2. código e testes realmente concluídos;
3. métricas completas dos três embeddings;
4. candidates aceitos pelo loader;
5. score artifacts e pipelines Qwen;
6. tentativas da fase 0;
7. painel Mixedbread;
8. evidência Nemotron;
9. consolidado, README e validadores;
10. Git e PR.

Inclua estes campos com valores reais:

```text
previous_execution_stopped = true|false
pr20_marked_draft = true
existing_downloads_reused = true|false
duplicate_model_downloads = <inteiro>
bitnet_parser_strict_full_output = true|false
bitnet_runner_canonical_integration = true|false
bitnet_runner_tests_passed = true|false
canonical_candidate_loader_tests_passed = true|false
embedding_metrics_recomputed_from_real_rankings = true|false
placeholder_zero_metrics_remaining = <inteiro>
empty_per_query_completed_results = <inteiro>
empty_by_query_type_completed_results = <inteiro>
lfm_complete_artifact_validated = true|false
bitnet_06b_complete_artifact_validated = true|false
bitnet_270m_complete_artifact_validated = true|false
lfm_candidate_validated_by_canonical_loader = true|false
bitnet_270m_candidate_validated_by_canonical_loader = true|false
qwen_score_artifacts_created = <inteiro>
phase0_qwen_mandatory_attempted = <inteiro>
phase0_qwen_mandatory_completed = <inteiro>
phase0_qwen_mandatory_blocked = <inteiro>
new_small_qwen_pipelines_canonical = <inteiro>
mxbai_fixed_panel_completed = true|false
mxbai_fixed_panel_canonical_pipeline_count = <inteiro>
nemotron_vllm_runtime_compatible = true|false
nemotron_fixed_panel_completed = true|false
nemotron_blocked_with_complete_evidence = true|false
canonical_raw_profile_count = <inteiro>
canonical_pipeline_count = <inteiro>
canonical_results_regenerated_from_real_artifacts_only = true|false
readme_canonical_tables_updated = true|false
full_local_test_suite_passed = true|false
full_local_test_count = <inteiro>
ci_run_present_for_head = false
voyage_api_accessed = false
voyage_api_calls_planned = 0
voyage_api_calls_executed = 0
heavy_models_downloaded = false
heavy_models_executed = false
merge_executed = false
```

A resposta deve terminar exatamente com:

`Versão do retorno da IA local: 2.1.5 — Conclusão efetiva após execução parcial da v2.1.4`
