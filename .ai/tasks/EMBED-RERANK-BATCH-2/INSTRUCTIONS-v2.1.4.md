# INSTRUCTIONS v2.1.4 — correção canônica após auditoria do retorno v2.1.3

## Objetivo

Continuar exclusivamente no branch do PR #20 e corrigir as inconsistências objetivamente confirmadas após o retorno v2.1.3.

Esta versão não autoriza reiniciar a rodada, repetir benchmarks válidos sem necessidade, repetir downloads verificados, executar modelos pesados, chamar API Voyage, alterar o sistema ou consolidar artefatos incompletos.

Contrato técnico obrigatório:

`benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`

Instruções anteriores são contexto histórico. Esta versão substitui somente a ordem de continuação após a auditoria do HEAD `757686a12372ce0040fedd9012eb80f64f000ea1`.

## Repositório, branch e PR

- Repositório: `Weltall-IA/holo-models`
- Worktree esperada: `/home/alpha/Playstoria/models-embed-batch2-light`
- Branch: `exec/embed-rerank-batch2-light`
- PR: `#20`
- Estado obrigatório: aberto e draft
- HEAD auditado antes desta instrução: `757686a12372ce0040fedd9012eb80f64f000ea1`

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
test -f .ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.4.md
```

O remote deve corresponder a `Weltall-IA/holo-models`.

Antes de alterar arquivos, registre staged, unstaged, não rastreados, processos ativos, RAM, VRAM, downloads existentes, hashes dos pesos, hashes dos binários e hashes dos artefatos já produzidos.

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
10. este arquivo;
11. diff completo, commits e descrição atual do PR #20.

## 3. Estado auditado e não aceito como concluído

A auditoria do HEAD `757686a12372ce0040fedd9012eb80f64f000ea1` confirmou progresso real, mas também confirmou que a fase leve continua não consolidada.

### 3.1 Parser e runner BitNet

Os arquivos abaixo estão versionados:

- `benchmark/embedding-v3/holo_benchmark/bitnet_parser.py`;
- `benchmark/embedding-v3/holo_benchmark/bitnet_runner.py`;
- `benchmark/embedding-v3/tests/test_bitnet_parser.py`.

Isso não comprova integração canônica completa porque:

- o parser coleta arrays por regex em qualquer parte do texto e não prova consumo integral da saída;
- texto residual ambíguo pode ser ignorado;
- a suíte aceita dois vetores idênticos como caso válido, embora a v2.1.3 exija rejeição de duplicação indevida entre entradas distintas;
- não há teste de saída truncada parcialmente reconhecível;
- não há teste de texto residual antes ou depois dos vetores;
- não há teste do runner com subprocesso simulado;
- não há teste de aplicação de instrução somente às consultas;
- o runner usa `texts.index(t)` e não deve depender de busca pelo valor do texto;
- o runtime e o commit estão hardcoded no retorno de metadados;
- nenhum entrypoint canônico existente foi alterado para consumir o runner ou produzir os artefatos finais.

Portanto, não declare a integração BitNet concluída apenas porque 13 testes isolados passam.

### 3.2 Métricas dos embeddings

Os três artefatos continuam incompletos:

- `lfm_25_embedding_350m_q4_k_m_official.json`;
- `bitnet_06b_current.json`;
- `bitnet_270m_current.json`.

Eles ainda contêm `nDCG@10 = 0.0`, estruturas `by_query_type` vazias e `per_query` vazio. O LFM2.5 também mantém a divergência de consultas sem relevante e não contém toda a identidade, telemetria, comando, hardware e protocolo exigidos.

Esses arquivos não podem ser aceitos como resultados completos nem usados para regenerar o consolidado.

### 3.3 Candidates incompatíveis com o loader canônico

O loader vigente em `reranker_execution.py` exige, entre outros campos:

- `variant` igual ao perfil;
- `dataset.corpus_sha256`;
- `candidate_top_k`;
- `queries` como lista ordenada de 150 registros;
- `candidates` dentro de cada registro de consulta.

O candidate do BitNet 270M usa um mapa `candidates` por query e não usa o esquema esperado. O candidate do LFM2.5 não registra `variant` nem `dataset` no formato exigido.

Além disso, `CANDIDATE_VARIANTS` ainda não inclui os novos perfis. Logo, os candidates atuais não passaram pelo fluxo canônico vigente.

### 3.4 Pipelines e score artifacts

O gerador canônico produz score artifact separado e pipelines com:

- `schema_version`;
- `pipeline_id`;
- `embedding_variant`;
- `reranker_id`;
- `candidate_top_k`;
- `rerank_top_k`;
- `score_artifact`;
- `evaluation`;
- `completed_at`.

Os cinco pipelines Mixedbread e o pipeline Qwen do BitNet 270M continuam em formato reduzido. O pipeline Qwen do LFM2.5 armazena scores diretamente no próprio arquivo e também não corresponde ao produto do gerador atual.

Nenhum score artifact novo foi versionado no PR. Portanto, não declare esses sete pipelines como canônicos ou validados.

### 3.5 Fases ainda não executadas ou consolidadas

- pipelines Qwen obrigatórios da fase 0: zero tentados;
- painel Mixedbread: sexto membro ausente;
- painel NVIDIA Nemotron: não executado;
- `ALL_BENCHMARK_RESULTS.json`: ainda registra 36 perfis raw e 89 pipelines;
- tabelas canônicas do README: não atualizadas;
- PR: descrição ainda representa o estado anterior;
- GitHub Actions: nenhum workflow run associado ao HEAD auditado.

A contagem manual de arquivos no branch não pode ser declarada como contagem canônica enquanto o consolidado permanecer em 36/89.

## 4. Corrigir parser e runner BitNet

Corrija o código antes de aceitar ou regenerar artefatos BitNet.

### 4.1 Parser estrito

O parser deve:

1. consumir integralmente a saída válida depois de remover somente whitespace permitido;
2. rejeitar qualquer texto ou bytes residuais ambíguos;
3. rejeitar saída truncada mesmo quando parte de um vetor puder ser extraída;
4. rejeitar NaN, infinito, norma zero, dimensão incorreta e contagem incorreta;
5. validar 1024 dimensões para `bitnet_06b_current` e 640 para `bitnet_270m_current` por configuração explícita do perfil, não apenas pelo nome do arquivo;
6. manter associação determinística entre cada entrada e seu vetor;
7. rejeitar vetores idênticos para entradas distintas quando isso indicar duplicação indevida;
8. aceitar entradas textualmente idênticas somente quando o chamador registrar essa condição e a associação continuar determinística;
9. não normalizar silenciosamente um vetor que deveria chegar normalizado pelo runtime; apenas validar dentro da tolerância autorizada;
10. produzir erros objetivos e testáveis.

Não use regex para procurar vetores ignorando o restante da saída. Parseie o formato real observado no smoke test de forma completa e estrita.

### 4.2 Runner e integração

O runner deve:

- receber binário, modelo, perfil, dimensão e metadados resolvidos explicitamente;
- não hardcode commit, caminho da worktree ou versão do runtime;
- não usar `texts.index(t)`;
- aplicar instrução somente às consultas por fluxo separado e determinístico;
- preservar documentos sem instrução;
- registrar comando sanitizado, exit code, duração, throughput, RAM, VRAM residual, SHA-256 do binário, commit BitNet e SHA-256 do GGUF;
- integrar-se ao entrypoint real do benchmark ou a um entrypoint versionado e testado que produza exatamente os artefatos canônicos aceitos pelos geradores existentes;
- usar o serializador atômico do projeto.

### 4.3 Testes obrigatórios

Adicione ou corrija testes para:

- vetor válido de 1024;
- vetor válido de 640;
- múltiplos vetores distintos;
- dimensão incorreta;
- contagem incorreta;
- NaN;
- infinito;
- norma zero;
- saída vazia;
- saída truncada parcialmente reconhecível;
- texto residual antes dos vetores;
- texto residual depois dos vetores;
- duplicação indevida para entradas distintas;
- aplicação da instrução somente às consultas;
- subprocesso com exit code diferente de zero;
- timeout;
- serialização do candidate canônico;
- aceitação dos novos candidates por `load_candidate_payloads`.

Não declare testes do runner aprovados quando somente o parser foi testado.

## 5. Regenerar candidates pelo esquema canônico

Preserve os rankings reais existentes quando sua origem, ordem e hash puderem ser comprovados. Caso contrário, reexecute somente a geração de rankings necessária.

Para LFM2.5 e BitNet 270M:

1. valide 150 queries na ordem congelada;
2. valide top 50 por query;
3. valide ausência de IDs duplicados dentro de cada ranking;
4. valide o corpus SHA-256 congelado;
5. registre perfil, peso, runtime e fonte do ranking;
6. compute e registre hash normalizado do ranking;
7. gere o payload no esquema aceito por `load_candidate_payloads`;
8. inclua os novos perfis no fluxo canônico sem quebrar as variantes existentes;
9. execute programaticamente o loader canônico contra os arquivos finais;
10. grave com `atomic_json` e newline final.

Não converta manualmente o JSON apenas para satisfazer o schema quando não houver vínculo comprovado com os rankings reais.

O BitNet 0.6B reprovado não deve receber pipeline Qwen. Seu resultado completo pode existir sem candidate publicado para reranking, desde que a política canônica aplicável seja respeitada e o gate permaneça FAIL após recálculo.

## 6. Recalcular métricas completas dos embeddings

Use o avaliador canônico sobre os rankings reais de LFM2.5, BitNet 0.6B e BitNet 270M.

Os artefatos finais devem conter:

- HitRate@1, @3, @5, @10, @20 e @50;
- Recall quando previsto pelo schema canônico;
- MRR@10;
- nDCG@10;
- mean e median first relevant rank;
- queries_without_relevant;
- hard-negative error rate;
- `by_query_type` completo;
- `per_query` com 150 entradas;
- identidade completa do peso e revisão;
- arquivo, bytes, SHA-256 e licença;
- backend, versão, commit, comando e dispositivo efetivo;
- dimensão, pooling, normalização e prompts;
- tempos, throughput, RAM e VRAM;
- corpus, contagens e SHA-256;
- gate recalculado.

Não use zero como placeholder. Um zero só pode permanecer quando o avaliador canônico o produzir a partir dos rankings reais e a evidência por consulta comprovar o valor.

Resolva objetivamente a divergência do LFM2.5 sobre consultas sem relevante. Não preserve PASS ou FAIL por conveniência; aplique novamente os thresholds depois da reconstrução completa.

## 7. Regenerar pipelines Qwen pelo fluxo canônico

Depois de candidates válidos:

1. execute o fluxo canônico Qwen para LFM2.5;
2. execute o fluxo canônico Qwen para BitNet 270M somente se o gate completo continuar PASS;
3. produza score artifact separado com identidade do reranker, pesos, hashes, runtime, comando, instrução, queries, candidates e scores;
4. gere os pipelines apenas pelo avaliador canônico;
5. valide MRR@10, nDCG@10, HitRate, damage, rescue, erros, latência, RAM e VRAM;
6. não mantenha `reranked_pipelines` ou scores embutidos em formato paralelo quando o gerador vigente usa score artifact separado;
7. remova ou substitua somente os artefatos reduzidos comprovadamente inválidos, preservando os scores brutos reutilizáveis fora do diff quando necessário.

### 7.1 Pipelines obrigatórios da fase 0

Tente individualmente:

- `nemotron_3_embed_1b_nvfp4`;
- `nemotron_3_embed_1b_q4_k_m_gguf`;
- `voyage-context-4`;
- `voyage-4-large` somente se a auditoria de alias não provar equivalência com `voyage_4_large_1024_float32`.

Use somente candidates ou checkpoints locais válidos. Não chame API Voyage. Não copie candidates entre perfis.

Quando um perfil não puder ser materializado, registre tentativa, caminho procurado, comando, erro e dependência ausente. Não crie pipeline vazio e não conte bloqueio como pipeline canônico.

## 8. Regenerar o painel Mixedbread

Os cinco arquivos atuais não são aceitos como pipelines canônicos.

Proceda assim:

1. valide a ligação dos scores brutos preservados aos pares e candidates corretos;
2. produza score artifact canônico do Mixedbread;
3. regenere os cinco pipelines existentes pelo gerador vigente;
4. execute o sexto membro `nemotron_3_embed_1b_nvfp4` quando houver candidate válido;
5. produza exatamente seis pipelines somente quando todos forem tecnicamente concluídos;
6. registre tokenizer, truncamento, comprimento máximo, revisão, pesos, hashes, backend, versão, comando, latência, RAM e VRAM;
7. compute evaluation, damage e rescue pelo avaliador canônico;
8. mantenha o painel incompleto quando o sexto candidate estiver bloqueado;
9. não recrie `mxbai_panel_results.json` nem outro resumo paralelo.

Não conte os cinco arquivos reduzidos atuais como pipelines canônicos antes da regeneração.

## 9. Formalizar corretamente o bloqueio do NVIDIA Nemotron

O arquivo atual é insuficiente como evidência final porque não registra integralmente ambiente, comando, caminho do ambiente isolado, pip, driver, resolver completo sanitizado e dependências resolvidas.

Primeiro audite a tentativa já realizada e determine se a causa real foi:

- incompatibilidade do Python usado;
- ausência de wheel compatível;
- conflito de dependências CUDA;
- incompatibilidade do PyTorch;
- outra dependência objetiva.

Registre:

- caminho e versão do Python;
- versão do pip;
- ambiente virtual usado;
- driver NVIDIA;
- CUDA toolkit;
- PyTorch;
- comando exato de instalação;
- índice de pacotes usado;
- saída sanitizada do resolver ou importação;
- dependências incompatíveis e constraints relevantes;
- caminho do log preservado localmente;
- revisão, arquivo, bytes e SHA-256 do peso.

Não altere CUDA, driver, PyTorch global, Python do sistema ou pacotes globais.

Não repita a instalação quando a incompatibilidade estiver comprovada pelas evidências existentes. Uma nova tentativa isolada só é permitida se existir no host um interpretador compatível já instalado, sem alteração do sistema, e se a tentativa responder objetivamente a uma lacuna da evidência anterior.

Se continuar incompatível, mantenha `BLOCKED_RUNTIME_INCOMPATIBLE`. Não substitua backend, versão, precisão ou modelo.

## 10. Consolidação canônica

Somente depois de validar os artefatos individuais:

1. execute todos os validadores;
2. regenere `ALL_BENCHMARK_RESULTS.json` exclusivamente pelo gerador canônico;
3. confirme que o `source_commit` e `generated_at` correspondem à nova execução;
4. confirme contagens reais de perfis raw e pipelines;
5. não use contagem manual de arquivos como contagem canônica;
6. atualize somente as duas tabelas canônicas do README quando a decisão de qualidade mudar;
7. preserve separação entre embedding-only e reranked;
8. não inclua bloqueados ou incompletos no ranking de resultados aceitos;
9. não crie leaderboard, registry, blacklist ou relatório paralelo;
10. não copie métricas manualmente para o consolidado.

Enquanto `ALL_BENCHMARK_RESULTS.json` continuar em 36 perfis raw e 89 pipelines, os campos `canonical_raw_profile_count` e `canonical_pipeline_count` devem refletir 36 e 89, não 39 e 97.

## 11. Validações obrigatórias

Execute e registre o exit code de cada comando:

```bash
python .ai/validate_governance.py
python -m unittest discover -s benchmark/embedding-v3/tests -v
python -m compileall -q benchmark/embedding-v3
python benchmark/embedding-v3/validate_coverage.py
python benchmark/embedding-v3/reranker_benchmark.py --phase preflight
git diff --check
```

Adicione validação programática para:

- JSON e YAML parseáveis;
- corpus 600/150 e SHA-256 congelado;
- candidates com 150 queries ordenadas e top 50;
- candidates aceitos por `load_candidate_payloads`;
- score artifacts referenciados por caminhos existentes;
- pipelines produzidos no schema do gerador vigente;
- `per_query` com 150 entradas em resultados completos;
- `by_query_type` não vazio em resultados completos;
- ausência de NaN e infinito;
- ausência de placeholders;
- zeros justificados por evidência por consulta;
- IDs únicos;
- contagens do consolidado coerentes com os artefatos aceitos;
- ausência de arquivos paralelos proibidos;
- ausência de chamadas Voyage;
- ausência de download ou execução pesada;
- diff integral depois da última correção.

Se não houver CI configurado, não declare CI aprovado. Informe apenas os testes locais realmente executados.

## 12. Git e PR

Depois da última validação:

- revise o diff completo;
- inclua somente código, testes, instruções, artefatos reais e arquivos canônicos do escopo;
- não versione pesos, caches, ambientes virtuais ou logs extensos;
- faça commit no branch `exec/embed-rerank-batch2-light`;
- faça push sem force;
- atualize a descrição do PR #20 com estado, resultados, bloqueios e validações reais;
- mantenha o PR aberto e draft;
- não faça merge;
- não abra outro PR.

## 13. Formato obrigatório do retorno

O retorno deve ser direto e verificável, nesta ordem:

### Resultado direto

Declare se a fase leve ficou consolidada, parcialmente consolidada ou bloqueada. Informe somente as contagens presentes no consolidado canônico final.

### Correções de código e testes

Liste parser, runner, integração canônica e testes realmente alterados. Informe o comando e o total real de testes executados.

### Artefatos de embedding

Para cada um dos três embeddings, informe métricas completas, gate, backend, tempos, throughput, RAM, VRAM e se o artefato passou pela validação canônica.

### Candidates e pipelines Qwen

Informe candidates validados pelo loader, score artifacts, pipelines gerados e tentativas da fase 0. Diferencie concluído de bloqueado.

### Painel Mixedbread

Informe quantos dos seis pipelines foram gerados canonicamente, quais scores foram reutilizados e qual membro continua bloqueado.

### NVIDIA Nemotron

Informe ambiente, tentativa, causa raiz comprovada, evidência e estado final.

### Consolidação e documentação

Informe `source_commit`, `generated_at`, perfis raw, pipelines, validadores e atualização das tabelas do README.

### Git e PR

Informe HEAD inicial, commits novos, HEAD final completo, push, URL, draft/open, mergeabilidade e ausência de merge.

### Campos obrigatórios

Inclua exatamente estes campos com valores reais:

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
local_test_suite_passed = true|false
ci_run_present_for_head = true|false
voyage_api_accessed = false
voyage_api_calls_planned = 0
voyage_api_calls_executed = 0
heavy_models_downloaded = false
heavy_models_executed = false
merge_executed = false
```

A resposta deve terminar exatamente com:

`Versão do retorno da IA local: 2.1.4 — Correção canônica após auditoria do retorno v2.1.3`
