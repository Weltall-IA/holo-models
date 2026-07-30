# INSTRUCTIONS v2.1.2 — correção e conclusão da fase leve

## Objetivo

Continuar a execução no próprio branch do PR #20, preservar os resultados reais já obtidos, corrigir os artefatos que não seguem o esquema canônico e concluir somente a fase leve de `EMBED-RERANK-BATCH-2`.

Não reinicie a rodada. Não repita downloads válidos. Não descarte o commit `589c497da0bd7c0acce06ce5f653729a88d51523` nem os artefatos brutos que comprovem execuções reais.

Contrato técnico obrigatório:

`benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`

Instruções anteriores de contexto:

- `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.0.md`
- `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.1.md`

Esta versão substitui a ordem de continuação após a abertura do PR #20.

## Repositório, branch e PR

- Repositório: `Weltall-IA/holo-models`
- Worktree esperada: `/home/alpha/Playstoria/models-embed-batch2-light`
- Branch de execução: `exec/embed-rerank-batch2-light`
- PR de execução: `#20`
- Base empilhada: `agent/prepare-next-embedding-rerank-batch-v2`
- Commit de resultado anterior a preservar: `589c497da0bd7c0acce06ce5f653729a88d51523`

Não volte para a branch do contrato para executar esta continuação. O `pull` deve ser feito no branch do PR #20.

## 1. Retomada segura e atualização

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
test -f .ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.2.md
```

O remote deve corresponder a `Weltall-IA/holo-models`.

Antes de alterar qualquer arquivo, registre:

- alterações staged e unstaged;
- arquivos não rastreados;
- processos de benchmark, BitNet, Python, llama.cpp e vLLM;
- uso atual de RAM e VRAM;
- caminhos dos cinco downloads existentes;
- SHA-256 dos artefatos existentes do PR #20.

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
8. este arquivo;
9. diff completo e descrição atual do PR #20.

## 3. Diagnóstico obrigatório do PR #20

Considere os resultados anteriores como evidência real reutilizável, mas não considere os novos JSON prontos para consolidação antes das correções abaixo.

### 3.1 Lacunas de execução

Ainda faltam:

- pipelines `qwen_local` obrigatórios para:
  - `nemotron_3_embed_1b_nvfp4`;
  - `nemotron_3_embed_1b_q4_k_m_gguf`;
  - `voyage-context-4`;
  - `voyage-4-large` somente quando a auditoria de alias não comprovar equivalência com `voyage_4_large_1024_float32`;
- BitNet 0.6B com candidates, métricas e gate;
- BitNet 270M com candidates, métricas e gate;
- `qwen_local` para cada BitNet que passar no gate;
- painel Mixedbread com o sexto membro `nemotron_3_embed_1b_nvfp4`;
- painel NVIDIA Nemotron Rerank 1B v2 nos seis embeddings fixos.

Nenhuma API Voyage pode ser chamada para preencher essas lacunas.

### 3.2 Artefatos que precisam ser corrigidos

Os arquivos individuais novos devem usar os esquemas e geradores canônicos já adotados pelo benchmark.

Corrija, sem inventar métricas:

- `benchmark/embedding-v3/results/gate3/lfm_25_embedding_350m_q4_k_m_official.json`:
  - não pode conter apenas `profile_id`, HR@50, consultas sem relevante e gate;
  - deve registrar identidade completa do peso, revisão imutável, arquivo, bytes, SHA-256, licença, backend, versão, quantização, dimensões, pooling, normalização, prompts, comando, hardware, métricas completas, tempos, throughput, RAM, VRAM e corpus;
  - só mantenha `PASS` quando todas as evidências obrigatórias forem reconstruídas a partir dos logs, caches e execução real já realizada;
  - quando alguma métrica não tiver sido medida e não puder ser derivada legitimamente dos rankings reais, reexecute apenas a medição necessária.

- pipelines `mxbai_rerank_base_v2` e `qwen_local`:
  - use o esquema canônico existente do benchmark;
  - preserve separação entre score artifact e pipeline evaluation;
  - registre `schema_version`, `pipeline_id`, `embedding_variant`, `reranker_id`, `candidate_top_k`, `rerank_top_k`, `score_artifact`, `evaluation` e `completed_at`;
  - `evaluation` deve conter as métricas realmente calculadas pelo código canônico, incluindo MRR@10, nDCG@10, hits, damage, rescue e erros aplicáveis;
  - o score artifact deve registrar modelo, revisão/pesos, hashes, runtime, versão, comando, instrução, latências, RAM e VRAM;
  - não copie manualmente os números do relatório para montar JSON.

- `benchmark/embedding-v3/results/mxbai_panel_results.json`:
  - remova este arquivo do branch;
  - ele é um resumo paralelo não previsto em `outputs` e proibido pela regra de arquivo único;
  - os resultados devem permanecer nos pipelines individuais e no consolidado canônico.

Todos os JSON devem terminar com newline e passar pelo serializador atômico/canônico do projeto.

## 4. Correção estrutural antes de novos benchmarks

Antes de executar BitNet ou Nemotron:

1. identifique os geradores e esquemas canônicos usados por `reranker_execution.py`, `reranker_report.py`, `reranker_metrics.py` e pelo consolidado;
2. adapte a execução de Mixedbread ao fluxo canônico, em vez de manter scripts temporários ou formatos próprios;
3. implemente testes para o backend e para a serialização dos pipelines;
4. regenere os cinco pipelines Mixedbread já executados usando os scores reais preservados, quando esses scores tiverem identidade e ordem comprovadas;
5. se os scores brutos não tiverem sido preservados ou não puderem ser ligados inequivocamente aos pares e candidates corretos, reexecute somente o Mixedbread necessário;
6. remova scripts temporários, caches e relatórios que não devam ser versionados.

Não aceite um artefato apenas porque o número final coincide com o relatório anterior.

## 5. Pipelines Qwen locais ausentes

Materialize os candidates a partir dos artefatos válidos existentes e execute os pipelines obrigatórios da fase 0.

Requisitos:

- 150 consultas na ordem congelada;
- top 50 por consulta;
- corpus SHA-256 correto;
- fonte e hash do ranking normalizado registrados;
- sem chamada à API Voyage;
- sem copiar ou renomear candidates de outro perfil;
- alias `voyage-4-large` somente com prova de identidade ou execução condicional conforme o contrato.

Execute e persista um pipeline por vez.

## 6. Parser BitNet dedicado

O bloqueio atual não encerra os BitNet. Implemente suporte no código canônico do benchmark para o formato real produzido pelo binário construído nesta rodada.

Procedimento obrigatório:

1. preserve uma amostra pequena e sanitizada de `stdout` e `stderr` do smoke test;
2. determine se `--embd-output-format array` produz texto, JSON, array delimitado ou bytes mistos na versão/commit efetivamente compilados;
3. não presuma o formato a partir de versões antigas;
4. implemente parser dedicado e estrito no módulo apropriado do benchmark;
5. rejeite saída parcial, dimensões incorretas, NaN, infinito, vetor de norma zero, quantidade inesperada de vetores e texto residual ambíguo;
6. valide 1024 dimensões para `bitnet_06b_current` e 640 para `bitnet_270m_current`;
7. aplique pooling no último token não preenchido, instrução somente nas consultas e normalização L2;
8. crie testes unitários com fixtures pequenas e sanitizadas, sem versionar pesos, embeddings completos ou logs gigantes;
9. faça smoke test determinístico antes do corpus completo;
10. execute cada BitNet no corpus 600/150, gere candidates, métricas completas e gate;
11. execute `qwen_local` apenas para os BitNet que passarem.

Se o formato não puder ser interpretado com segurança depois da inspeção real e de uma tentativa de implementação, marque cada perfil como `BLOCKED` com comando, commit do BitNet, hashes dos binários, amostra sanitizada e erro exato. Não fabrique candidates.

## 7. Mixedbread no painel fixo completo

O painel obrigatório possui seis embeddings:

- `nemotron_3_embed_1b_nvfp4`;
- `nomic_embed_text_v2_moe_q4`;
- `qwen3_embedding_4b_q8_0`;
- `embeddinggemma`;
- `colibri_ptbr`;
- `granite_embedding_311m_r2`.

Depois de corrigir o backend e os esquemas:

- preserve/reutilize os cinco resultados somente quando os scores brutos e a correspondência com os candidates forem comprovados;
- execute o membro ausente `nemotron_3_embed_1b_nvfp4`;
- produza exatamente seis pipelines canônicos;
- registre tokenizer, comprimento máximo, truncamento, backend, versão, peso, revisão, hashes, latência, RAM e VRAM;
- compute damage e rescue pelo avaliador canônico.

## 8. NVIDIA Nemotron Rerank 1B v2

A ausência do runtime local é uma dependência a resolver, não autorização para trocar de backend.

É autorizado:

- criar ou reutilizar um ambiente virtual isolado específico do benchmark;
- instalar `vllm==0.25.0` nesse ambiente, conforme a referência do contrato;
- instalar apenas dependências necessárias e registrar versões resolvidas.

É proibido:

- alterar ou remover pacotes do Python do sistema;
- atualizar globalmente CUDA, driver ou PyTorch;
- usar geração de texto;
- substituir vLLM por backend não aprovado;
- alterar a precisão ou o modelo sob o mesmo ID.

Antes da instalação, registre Python, pip, CUDA, driver, PyTorch e espaço em disco. Depois, registre o freeze relevante e o caminho do ambiente.

Se `vllm==0.25.0` não puder ser instalado ou importado por incompatibilidade real, preserve o log sanitizado e marque o painel `BLOCKED`. Não instale outra versão silenciosamente.

Se o runtime ficar disponível:

- use pooling;
- use o score template obrigatório `rerank/nemotron-rerank.jinja`;
- use `LLM.score` ou endpoint oficial de reranking;
- preserve índices e `relevance_score` sem inversão;
- faça smoke test determinístico;
- confirme pelo menos 3 GiB livres de VRAM após o load;
- execute os seis pipelines do painel;
- registre score artifact e pipelines no esquema canônico.

## 9. Consolidação canônica

Somente depois das correções e execuções reais:

1. valide todos os artefatos individuais;
2. regenere `ALL_BENCHMARK_RESULTS.json` exclusivamente pelo gerador canônico;
3. atualize as duas tabelas canônicas do `README.md` somente quando a decisão mudar;
4. não crie outro leaderboard, resumo, registry ou blacklist;
5. confirme as contagens antes e depois;
6. confirme que nenhum perfil bloqueado entra na tabela de bons;
7. confirme que embedding-only e reranked continuam separados.

Não edite manualmente métricas no consolidado.

## 10. Validações obrigatórias

Execute, no mínimo:

```bash
python .ai/validate_governance.py
python -m unittest discover -s benchmark/embedding-v3/tests -v
python -m compileall -q benchmark/embedding-v3
python benchmark/embedding-v3/validate_coverage.py
git diff --check
```

Além disso, valide programaticamente:

- todos os JSON e YAML parseiam;
- corpus permanece 600/150 com SHA-256 congelado;
- candidates têm 150 consultas ordenadas e top 50;
- todos os IDs são únicos;
- todos os novos perfis possuem identidade e protocolo completos;
- score artifacts e pipelines referenciam caminhos existentes;
- os seis membros de cada painel estão presentes quando o painel for declarado completo;
- nenhuma API Voyage foi chamada;
- nenhum modelo pesado foi baixado ou executado;
- o diff completo contém apenas arquivos do escopo.

## 11. Git e PR

O PR #20 deve permanecer draft enquanto houver qualquer item pendente, artefato fora do esquema ou validação indisponível.

Ao concluir ou atingir bloqueio final comprovado:

- revise o diff completo;
- inclua somente código, testes, instruções e artefatos reais necessários;
- faça commit adicional no branch `exec/embed-rerank-batch2-light`;
- faça push sem force;
- atualize a descrição do PR #20 com resultados e bloqueios reais;
- mantenha o PR sem merge;
- não abra outro PR para a mesma continuação.

## 12. Limites

Não baixar nem executar:

- Qwen3 Embedding 8B;
- Nemotron Embed 8B;
- KaLM 12B;
- BOOM 4B;
- ICT-TIME-and-Querit embedding v1;
- Qwen3 Reranker 4B;
- qualquer API Voyage;
- qualquer outro modelo da fase pesada.

## 13. Formato obrigatório do retorno

O retorno deve ser narrativo e apresentado exatamente nesta ordem.

### Resultado direto

Declare se a fase leve foi concluída, parcialmente concluída ou bloqueada. Informe quantidades finais de embeddings, pipelines Qwen, pipelines Mixedbread e pipelines Nemotron.

### O que foi corrigido no PR #20

Informe remoção do resumo paralelo, correção dos esquemas, código e testes adicionados e quais resultados anteriores foram reutilizados ou reexecutados.

### O que funcionou

Liste pipelines Qwen, BitNet, gates, painéis, consolidado e validadores concluídos.

### O que travou ou ficou bloqueado

Para cada bloqueio, informe fase, comando, erro sanitizado, tentativas, impacto e ação futura.

### Downloads, pesos e runtimes

Apresente revisão efetiva, caminho, tamanho e SHA-256 completo dos cinco modelos. Inclua commit e SHA-256 dos binários BitNet e ambiente/versão do vLLM.

### Resultados dos embeddings

Para LFM2.5 e cada BitNet realmente concluído, informe MRR@10, nDCG@10, HR@1, HR@3, HR@5, HR@10, HR@20, HR@50, consultas sem relevante, hard-negative error rate, gate, tempos, throughput, RAM e VRAM.

### Resultados dos rerankers

Apresente os painéis completos ou bloqueados com MRR@10, nDCG@10, HR@1, HR@10, HR@20, damage, rescue, p50, p95, RAM, VRAM e erros.

### Validações e contagens

Informe resultado individual de cada validador, contagens canônicas antes/depois, corpus e SHA-256.

### Alterações realizadas

Liste arquivos criados, modificados e removidos. Confirme que `mxbai_panel_results.json` foi removido e que nenhum relatório paralelo foi criado.

### Estado Git e PR

Informe HEAD inicial, commits novos, HEAD final, push, URL, estado draft/open, mergeabilidade e ausência de merge.

### Campos obrigatórios

Inclua exatamente estes campos com valores reais:

```text
previous_execution_stopped = true|false
pr20_marked_draft = true|false
existing_downloads_reused = true|false
duplicate_model_downloads = <inteiro>
valid_previous_scores_reused = true|false
duplicate_report_removed = true|false
lfm_artifact_schema_corrected = true|false
mxbai_pipeline_schema_corrected = true|false
missing_qwen_local_pipelines_attempted = <inteiro>
missing_qwen_local_pipelines_completed = <inteiro>
bitnet_parser_implemented = true|false
bitnet_06b_completed = true|false
bitnet_270m_completed = true|false
mxbai_fixed_panel_completed = true|false
nemotron_vllm_isolated_env_used = true|false
nemotron_fixed_panel_completed = true|false
light_embedding_benchmarks_completed = true|false
light_reranker_panel_completed = true|false
light_phase_completed = true|false
voyage_api_accessed = false
voyage_api_calls_planned = 0
voyage_api_calls_executed = 0
heavy_models_downloaded = false
heavy_models_executed = false
canonical_results_regenerated_from_real_artifacts_only = true|false
merge_executed = false
```

A resposta deve terminar exatamente com:

`Versão do retorno da IA local: 2.1.2 — Correção e conclusão da fase leve de embeddings e rerankers`
