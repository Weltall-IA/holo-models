# INSTRUCTIONS v1.0 — embeddings modernos omitidos + todos os rerankers

## Objetivo

Executar os candidatos modernos preservados na fila canônica, primeiro em benchmark raw e depois contra todos os rerankers locais ou gratuitos elegíveis. Nenhum candidato pode desaparecer sem resultado incorporado ou bloqueio técnico reproduzível.

## Repositório e branch

- Repositório: `Weltall-IA/holo-models`
- Branch de execução: `bench/modern-embeddings-all-rerankers`
- PR final: draft contra `bench/complete-embedding-reranker-matrix`
- Não fazer merge.

Antes de atuar, confirmar remote, branch, HEAD, working tree, worktrees, stashes, arquivos não rastreados e processos de GPU. Não usar `reset --hard`, `clean`, stash automático ou force-push.

## Leitura obrigatória

Leia integralmente, nesta ordem:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json`;
6. `benchmark/embedding-v3/config/CANONICAL_BENCHMARK_CANDIDATES.json`;
7. artefatos e runners existentes sob `benchmark/embedding-v3/`;
8. esta instrução.

## Fonte canônica de pendências

Use exatamente:

`benchmark/embedding-v3/config/CANONICAL_BENCHMARK_CANDIDATES.json`

Esse arquivo é uma fila, não um leaderboard. Uma entrada só pode ser removida depois que:

- o raw e os pipelines reranqueados forem incorporados ao `ALL_BENCHMARK_RESULTS.json`; ou
- um bloqueio reproduzível, com comando, erro, versões, tentativas e condição de desbloqueio, for incorporado ao arquivo canônico.

## Embeddings obrigatórios

Executar raw, na ordem:

1. `gemini_embedding_2_768_float32`;
2. `gemini_embedding_2_1536_float32`;
3. `gemini_embedding_001_768_float32`;
4. `qwen3_embedding_0_6b_1024`;
5. `jina_embeddings_v5_text_small_1024`;
6. `jina_embeddings_v5_text_nano_768`;
7. `jina_embeddings_v4_q4`, somente após preflight de memória e licença;
8. `cohere_embed_v4_0`, somente com franquia gratuita comprovada ou autorização explícita de custo.

Não substituir silenciosamente modelo, revisão, dimensão, dtype, task type, quantização ou backend.

## Protocolo raw

Usar o corpus congelado vigente:

- 600 documentos;
- 150 consultas;
- mesmo `corpus_sha256` do consolidado;
- mesmas métricas e preparação de textos;
- normalização oficial de cada modelo;
- candidates top 50 persistidos por perfil;
- identidade, revisão, dimensão, dtype, runtime e parâmetros completos.

Para Gemini:

- usar os IDs exatos `gemini-embedding-2` e `gemini-embedding-001`;
- usar Gemini Developer API, não Vertex AI;
- executar apenas dentro da cota gratuita;
- não ativar billing;
- registrar SDK, endpoint, task type, dimensão, tokens e requisições;
- sem cota gratuita, registrar `BLOCKED_FREE_TIER_UNAVAILABLE` e manter a pendência.

Para Qwen3 0.6B:

- usar runner ou endpoint de embedding;
- é proibido chamar endpoint de chat.

Para Jina:

- registrar licença e revisão;
- modelos não comerciais ficam `BENCHMARK_ONLY_NONCOMMERCIAL` e não podem ser promovidos automaticamente para produção.

## Rerankers obrigatórios

Para cada embedding com raw e candidates válidos, executar todos os rerankers locais ou gratuitos elegíveis:

1. `qwen_local`;
2. `llama_nemotron_rerank_1b_v2`;
3. `mxbai_rerank_base_v2`;
4. `jina_reranker_v3_noncommercial`;
5. `kalm_reranker_v1_small`;
6. `kalm_reranker_v1_nano`;
7. `querit_reranker_4b`;
8. `voyage_rerank_2_5`, somente com franquia gratuita comprovada e sem cobrança;
9. `lamar_600m` / `nlpai-lab/LAMAR-600m`;
10. `ettin_reranker_150m_v1`;
11. `ettin_reranker_68m_v1`.

Não executar `google_vertex_ranking_api` sem autorização explícita de custo e billing. Não usar Gemini gerativo como reranker no ranking de cross-encoders.

## Medição obrigatória de recursos e desempenho

A medição não é opcional nem limitada aos rerankers novos. Deve ser registrada para cada benchmark raw local e cada pipeline de reranking local.

Antes de cada execução local:

- encerrar processos antigos do modelo ou reranker;
- registrar RAM e VRAM de baseline;
- registrar GPU, driver, CUDA, runtime, versão do runner e comando exato;
- executar o modelo isoladamente sempre que a arquitetura permitir.

Para cada embedding raw local, registrar obrigatoriamente:

- tamanho do peso em bytes e MiB;
- SHA-256 e quantização/dtype;
- tempo de carregamento;
- RAM baseline, pico e delta;
- VRAM baseline, pico e delta;
- duração total da indexação de 600 documentos;
- throughput em documentos por segundo;
- duração total das 150 consultas;
- latência por consulta p50, p95, p99 e máxima;
- throughput em consultas por segundo;
- quantidade de erros, retries e timeouts;
- duração total do benchmark.

Para cada reranker local isolado, registrar obrigatoriamente:

- tamanho do peso, SHA-256, dtype/quantização e revisão;
- tempo de carregamento;
- RAM baseline, pico e delta;
- VRAM baseline, pico e delta;
- duração do smoke test;
- throughput de pares por segundo.

Para cada pipeline embedding + reranker local, registrar obrigatoriamente:

- RAM e VRAM com os componentes efetivamente residentes;
- pico combinado de RAM e VRAM;
- tempo de reranking das 150 consultas;
- latência p50, p95, p99 e máxima por consulta;
- throughput de consultas e pares por segundo;
- número total de pares avaliados;
- erros, retries, OOMs e timeouts;
- duração total do pipeline.

Para APIs externas, RAM e VRAM local devem ser `NOT_APPLICABLE_REMOTE_API`, nunca zero inventado. Registrar obrigatoriamente:

- duração total;
- latência p50, p95, p99 e máxima;
- requisições, tokens e retries;
- throughput;
- cota usada e confirmação de ausência de cobrança.

Se uma métrica não puder ser coletada, registrar `MEASUREMENT_BLOCKED` com ferramenta, comando, erro e tentativa. Não usar `null` sem justificativa.

## Estados finais permitidos

Cada célula deve terminar em:

- `VALID`;
- `BLOCKED_LICENSE`;
- `BLOCKED_FREE_TIER_UNAVAILABLE`;
- `BLOCKED_RUNTIME_REPRODUCIBLE`;
- `NOT_ELIGIBLE`, somente com justificativa técnica real.

`MISSING`, `NO_RUNNER` e `NO_CANDIDATES` não são estados finais aceitáveis.

Quando o runner não estiver evidente:

1. localizar o caminho usado pelos artefatos históricos;
2. reutilizar ou adaptar o runner;
3. implementar adaptador mínimo;
4. executar smoke test;
5. bloquear somente após erro reproduzível.

Falha de uma célula não interrompe as demais.

## Preflight dos rerankers novos

Antes da matriz completa:

- verificar model card, licença, revisão e hashes;
- medir carregamento, RAM e VRAM isolados;
- testar três pares positivos e três negativos do corpus;
- confirmar saída determinística e ordenação correta;
- para Ettin, registrar que o treinamento é majoritariamente em inglês e medir no corpus PT-BR sem pressupor qualidade;
- para LAMAR, preservar a configuração multilíngue oficial.

## Artefatos e consolidação

Criar artefato individual autoritativo para cada raw e cada pipeline reranqueado.

Atualizar obrigatoriamente:

`benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json`

O consolidado deve receber:

- novos perfis raw;
- candidates e proveniência;
- todas as células de reranking;
- métricas completas de qualidade;
- todas as medições obrigatórias de RAM, VRAM, carga, duração, latência e throughput;
- bloqueios e motivos;
- rankings raw e reranqueado regenerados;
- reconciliação da fila de candidatos.

Atualizar somente o relatório humano canônico existente. Não criar leaderboard, registry, lista, matriz ou resumo paralelo.

O arquivo removido `benchmark/embedding-v3/results/load-memory/top15_matrix.json` não pode ser recriado. A matriz deve existir apenas dentro de `ALL_BENCHMARK_RESULTS.json` e no relatório humano canônico.

Depois dos novos raws:

1. recalcular o ranking raw completo;
2. recalcular o top 15 com as exclusões vigentes;
3. incluir na matriz top 15 qualquer novo perfil classificado;
4. preservar todos os resultados históricos válidos;
5. não declarar vencedor com cobertura assimétrica.

## Validações mínimas

Execute:

```bash
python -m unittest discover -s benchmark/embedding-v3/tests -v
python .ai/validate_governance.py
python -m compileall -q benchmark/embedding-v3
python benchmark/embedding-v3/validate_coverage.py
git diff --check
```

Adicionar testes para:

- candidato pendente não desaparece sem resultado ou bloqueio canônico;
- IDs e dimensões Gemini corretos;
- Qwen3 0.6B usa caminho de embedding;
- matriz retangular dos embeddings bem-sucedidos × 11 rerankers;
- nenhuma célula final `MISSING`, `NO_RUNNER` ou `NO_CANDIDATES`;
- coerência entre artefatos individuais e consolidado;
- presença das métricas obrigatórias de recursos em toda execução local válida;
- APIs remotas usam `NOT_APPLICABLE_REMOTE_API` para RAM/VRAM;
- modelos não comerciais não promovidos para produção;
- ausência de arquivos paralelos de ranking, matriz ou fila.

## Git e retorno

- commitar somente arquivos do escopo;
- fazer push da branch;
- abrir PR draft contra `bench/complete-embedding-reranker-matrix`;
- não fazer merge.

Retornar:

1. HEAD inicial e final;
2. preflight das cotas gratuitas;
3. raws executados e métricas;
4. bloqueios e evidências;
5. lista final de rerankers;
6. matriz completa;
7. pipelines executados;
8. tabela completa de peso, carga, RAM, VRAM, duração, latência e throughput por raw, reranker e pipeline;
9. rankings atualizados;
10. alterações no top 15;
11. arquivos alterados;
12. testes e validadores;
13. commit, push e PR;
14. confirmação de que nenhum candidato desapareceu;
15. confirmação de que nenhum arquivo paralelo foi criado.

Frase final obrigatória:

`Candidatos modernos preservados na fila canônica e benchmarkados em raw e contra todos os rerankers locais ou gratuitos elegíveis, com recursos e desempenho medidos, sem apagar pendências e sem criar resultados paralelos.`