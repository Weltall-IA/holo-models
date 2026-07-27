# INSTRUCTIONS v2.1.1 — continuação da fase leve de embeddings e rerankers

## Objetivo

Retomar a execução já iniciada da rodada `EMBED-RERANK-BATCH-2` a partir do ponto em que os downloads e o dry-run foram concluídos.

Não repetir downloads já verificados. Não reiniciar a tarefa do zero. Preservar a worktree existente, os artefatos baixados, hashes já confirmados e qualquer evidência produzida pela execução anterior.

O contrato técnico obrigatório permanece:

`benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`

A instrução anterior permanece como referência de contexto:

`.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.0.md`

Esta versão substitui apenas a ordem de retomada e o formato final do retorno.

## Estado inicial informado

Considere como esperado, mas valide antes de confiar:

- worktree: `../models-embed-batch2-light`;
- branch de execução: `exec/embed-rerank-batch2-light`;
- governança e contrato já lidos;
- dry-run aprovado com 36 perfis raw e 89 pipelines;
- corpus de 600 documentos e 150 consultas validado;
- cinco modelos já baixados e verificados por SHA-256;
- revisões efetivas dos BitNet divergentes das hints antigas do contrato, com divergência já documentada;
- build do BitNet ainda não iniciado;
- benchmarks e rerankers ainda não iniciados.

Não trate esta lista como substituta das evidências locais. Confirme caminhos, hashes, processos e estado Git.

## 1. Retomada segura

Entre na worktree existente:

```bash
set -euo pipefail
cd /home/alpha/Playstoria/models-embed-batch2-light
```

Confirme o repositório:

```bash
git remote get-url origin
git branch --show-current
git status --short
git rev-parse HEAD
```

O remote deve corresponder a `Weltall-IA/holo-models` e a branch deve ser `exec/embed-rerank-batch2-light`.

Antes de atualizar, registre separadamente:

- alterações rastreadas;
- arquivos não rastreados;
- processos ativos de benchmark, vLLM, llama-server, Python ou BitNet;
- uso atual de VRAM;
- caminhos dos cinco downloads concluídos.

Se houver alterações rastreadas não explicadas pela execução, pare e reporte. Não use `reset --hard`, `clean`, `checkout --`, remoção de worktree ou stash automático.

Atualize as refs e incorpore somente fast-forward da branch do contrato:

```bash
git fetch origin --prune
git pull --ff-only origin agent/prepare-next-embedding-rerank-batch-v2
```

Confirme que esta instrução existe após o pull:

```bash
test -f .ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.1.md
```

## 2. Confirmação da execução anterior

Antes de compilar ou executar modelos:

1. confirme que a execução anterior foi encerrada ou já estava parada;
2. finalize apenas processos comprovadamente pertencentes à rodada anterior;
3. não mate serviços não relacionados;
4. confirme que não há servidor antigo ocupando VRAM ou porta;
5. registre `nvidia-smi` e processos relevantes.

## 3. Revalidação dos downloads existentes

Não faça novos downloads automaticamente.

Para cada um dos cinco modelos já baixados:

- registre repositório;
- revisão efetiva;
- arquivo ou conjunto de arquivos;
- tamanho total;
- SHA-256 completo;
- caminho local;
- correspondência com o artefato esperado;
- divergência entre revisão efetiva e hint antiga, quando houver.

Se o arquivo existir e o SHA-256 corresponder, reutilize-o.

Somente baixe novamente quando:

- o arquivo estiver ausente;
- o hash estiver incorreto;
- o download estiver incompleto;
- a revisão efetiva não corresponder ao artefato validado.

Qualquer novo download deve ser registrado. Não substituir silenciosamente um arquivo sob o mesmo `profile_id`.

## 4. Ordem obrigatória da continuação

Execute um modelo por vez. Entre modelos:

- encerre servidores específicos da rodada;
- libere RAM e VRAM;
- confirme ausência de processo antigo na GPU;
- grave checkpoint e artefatos completos;
- continue para modelos independentes quando uma falha isolada não impedir os demais.

### Fase A — build do BitNet

Construa o runtime atual conforme o contrato YAML.

Requisitos:

- usar repositório oficial `microsoft/BitNet`;
- registrar commit exato;
- registrar submódulos;
- registrar compilador e versões;
- registrar flags CMake;
- produzir `llama-embedding` e `llama-bench`;
- executar smoke test do binário;
- não usar o llama.cpp estável antigo para os GGUF I2_S.

Caso o build falhe, preserve logs e continue com fases que não dependam do BitNet.

### Fase B — pipelines Qwen locais ausentes

Materialize candidates e execute `qwen_local` somente para os perfis autorizados no contrato:

- `nemotron_3_embed_1b_nvfp4`;
- `nemotron_3_embed_1b_q4_k_m_gguf`;
- `voyage-context-4`;
- `voyage-4-large` somente se a auditoria de alias não provar equivalência com `voyage_4_large_1024_float32`.

Não chamar a API de embeddings Voyage. Não chamar reranker Voyage.

### Fase C — embeddings leves

Execute na ordem:

1. `lfm_25_embedding_350m_q4_k_m_official`;
2. `bitnet_06b_current`;
3. `bitnet_270m_current`.

Antes do corpus completo, faça smoke test curto de cada runtime/modelo.

O LFM2.5 deve usar:

- Q4_K_M oficial;
- pooling CLS;
- dimensão 1024;
- normalização L2;
- prefixo `query: ` nas consultas;
- prefixo `document: ` nos documentos;
- candidates e cache novos.

Os BitNet devem usar:

- formato oficial I2_S;
- runtime BitNet construído nesta rodada;
- `llama-embedding`;
- pooling no último token não preenchido;
- normalização L2;
- instrução apenas nas consultas;
- documentos sem instrução;
- dimensões 1024 para 0.6B e 640 para 270M.

### Fase D — gate

Aplique os gates definidos no YAML.

- gate normal: HR@50 mínimo `0.9666666667` e no máximo cinco consultas sem relevante;
- exceção BitNet: HR@50 mínimo `0.94`;
- proveniência e candidates válidos são obrigatórios.

Execute `qwen_local` somente para embeddings que passarem.

### Fase E — rerankers leves

Execute no painel fixo de seis embeddings:

- `mixedbread-ai/mxbai-rerank-base-v2`;
- `nvidia/llama-nemotron-rerank-1b-v2`.

Painel:

- `nemotron_3_embed_1b_nvfp4`;
- `nomic_embed_text_v2_moe_q4`;
- `qwen3_embedding_4b_q8_0`;
- `embeddinggemma`;
- `colibri_ptbr`;
- `granite_embedding_311m_r2`.

Mixedbread:

- usar `sentence-transformers.CrossEncoder`;
- pontuar pares consulta-documento;
- produzir um score finito por par;
- registrar truncamento e comprimento máximo;
- não usar geração de texto.

NVIDIA Nemotron Rerank 1B v2:

- usar vLLM em pooling;
- usar o score template obrigatório definido no YAML;
- usar `LLM.score` ou endpoint oficial de reranking;
- não usar geração de texto;
- preservar índices e sentido do score.

## 5. Checkpoints e retomada

Depois de cada modelo ou pipeline concluído:

- grave o resultado individual;
- grave candidates quando aplicável;
- valide o JSON imediatamente;
- registre status concluído, falhou ou bloqueado;
- registre tempo, RAM e VRAM;
- não espere o fim da rodada para persistir evidências.

Se a execução for interrompida por tempo, erro externo ou reinício:

- preserve tudo que já foi validado;
- não regenere resultados concluídos;
- informe exatamente o último checkpoint concluído;
- não declare a fase leve concluída.

## 6. Limites obrigatórios

Não executar nem baixar nesta continuação:

- Qwen3 Embedding 8B;
- Nemotron Embed 8B;
- KaLM 12B;
- BOOM 4B;
- ICT-TIME-and-Querit embedding v1;
- Qwen3 Reranker 4B;
- qualquer modelo pesado descrito na fase posterior;
- qualquer API Voyage.

Não fazer merge.

## 7. Resultados canônicos e validação

`ALL_BENCHMARK_RESULTS.json` deve permanecer como entrada até existirem resultados novos reais.

Após as execuções reais:

- regenere o consolidado somente pelo gerador canônico;
- atualize apenas as duas tabelas canônicas do README quando a decisão mudar;
- não crie leaderboard, registry, blacklist ou relatório paralelo;
- não copie métricas manualmente;
- não estime valores ausentes.

Execute todos os validadores exigidos pelo YAML, incluindo:

- parse de todos os JSON;
- corpus e SHA-256;
- ordem das 150 consultas;
- cobertura;
- testes unitários;
- compileall;
- governança;
- `git diff --check`;
- revisão integral do diff.

## 8. Commit, push e PR

Ao concluir ou atingir um bloqueio final documentado:

- inclua somente código/configuração necessária e artefatos reais permitidos;
- remova scripts temporários que não devam permanecer;
- faça commit na branch de execução;
- faça push da branch de execução;
- abra ou atualize um PR próprio da execução conforme o workflow;
- não faça merge.

## 9. Formato obrigatório do retorno

O retorno deve ser narrativo, direto e verificável. Não despeje logs extensos no chat.

Apresente exatamente nesta ordem:

### Resultado direto

Em poucas linhas, declare se a fase leve foi concluída, parcialmente concluída ou bloqueada. Informe quantos embeddings, pipelines Qwen e pipelines de reranker foram concluídos.

### O que funcionou

Liste builds, modelos, benchmarks, gates, pipelines e validações concluídos.

### O que travou ou ficou bloqueado

Para cada falha ou bloqueio, informe modelo, fase, erro, tentativa realizada, impacto e ação futura.

### Downloads e pesos reutilizados

Apresente os cinco modelos com revisão efetiva, caminho, tamanho e SHA-256 completo. Informe qualquer download repetido e o motivo.

### Resultados dos embeddings

Para cada embedding executado, informe pelo menos:

- MRR@10;
- nDCG@10;
- HR@1;
- HR@10;
- HR@20;
- HR@50;
- consultas sem relevante;
- hard-negative error rate;
- resultado do gate;
- tempo, throughput, RAM e VRAM.

### Resultados dos rerankers

Apresente o ranking do painel com MRR@10, nDCG@10, HR@1, HR@10, damage, rescue, p95, RAM, VRAM e erros.

### Validações e contagens

Informe contagens canônicas antes e depois, corpus, SHA-256 e resultado de cada validador.

### Alterações realizadas

Liste arquivos criados, atualizados e preservados. Confirme que não foi criado nenhum registro canônico paralelo.

### Estado Git e PR

Informe branch, HEAD inicial, commit final, push, URL do PR, estado do PR e confirmação de ausência de merge.

### Campos obrigatórios

Inclua exatamente estes campos com valores reais:

```text
previous_execution_stopped = true|false
existing_downloads_reused = true|false
duplicate_model_downloads = <inteiro>
bitnet_build_completed = true|false
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

`Versão do retorno da IA local: 2.1.1 — Continuação da fase leve de embeddings e rerankers`
