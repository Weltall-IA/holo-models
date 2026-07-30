# INSTRUCTIONS v1.0 — embeddings modernos omitidos + todos os rerankers

## Objetivo

Executar corretamente os candidatos modernos que foram omitidos do benchmark, primeiro em raw e depois contra todos os rerankers elegíveis, preservando-os até que cada resultado ou bloqueio reproduzível seja incorporado ao arquivo canônico.

## Repositório e branch

- Repositório: `Weltall-IA/holo-models`
- Branch de execução: criar a partir de `bench/complete-embedding-reranker-matrix`
- Nome sugerido: `bench/modern-embeddings-all-rerankers`
- Não fazer merge.

Antes de alterar qualquer coisa, confirmar remote, branch, HEAD, working tree, worktrees, stashes, processos de GPU e arquivos não rastreados. Preservar integralmente trabalho preexistente. Não usar `reset --hard`, `clean`, force-push ou stash automático.

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

## Fonte de candidatos obrigatória

Use exatamente:

`benchmark/embedding-v3/config/CANONICAL_BENCHMARK_CANDIDATES.json`

Esse arquivo é uma fila canônica de pendências, não um leaderboard. Nenhum candidato pode ser removido porque falhou uma vez, porque faltou token, porque um endpoint estava errado ou porque um runner não foi localizado. Só remover uma entrada depois que:

- o resultado raw e os pipelines reranqueados forem incorporados ao `ALL_BENCHMARK_RESULTS.json`; ou
- existir bloqueio técnico reproduzível, com comando, erro, versões, tentativas e condição objetiva de desbloqueio, também incorporado ao arquivo canônico.

## Embeddings obrigatórios

Executar raw, na ordem:

1. `gemini_embedding_2_768_float32`;
2. `gemini_embedding_2_1536_float32`;
3. `gemini_embedding_001_768_float32`;
4. `qwen3_embedding_0_6b_1024`;
5. `jina_embeddings_v5_text_small_1024`;
6. `jina_embeddings_v5_text_nano_768`;
7. `jina_embeddings_v4_q4`, somente após preflight de memória e licença;
8. `cohere_embed_v4_0`, somente se houver franquia gratuita comprovada ou autorização explícita de custo.

Não testar modelos descontinuados do Google. Não substituir silenciosamente IDs, dimensões, dtypes ou revisões.

## Protocolo raw obrigatório

Usar exatamente o corpus congelado e o protocolo canônico vigente:

- 600 documentos;
- 150 consultas;
- mesmo `corpus_sha256` do consolidado;
- mesmas métricas raw;
- mesma preparação de query e documento definida para cada modelo;
- normalização conforme model card e contrato do benchmark;
- candidates top 50 persistidos por perfil;
- identidade completa do modelo/API, revisão quando aplicável, dimensão, dtype, task type e parâmetros.

Para Gemini:

- usar os IDs estáveis exatos `gemini-embedding-2` e `gemini-embedding-001`;
- usar a Gemini Developer API, não Vertex AI;
- fazer preflight de cota sem cobrança;
- não ativar billing nem migrar para paid tier;
- registrar endpoint, SDK/versão, task type, dimensão e quantidade de tokens/requisições;
- se a cota gratuita não estiver disponível, registrar `BLOCKED_FREE_TIER_UNAVAILABLE`, sem apagar a pendência.

Para `qwen3_embedding_0_6b_1024`, usar endpoint/runner de embedding. É proibido repetir o erro histórico de chamar endpoint de chat.

Para Jina v5/v4, registrar licença. Perfis não comerciais podem ser benchmarkados, mas devem ficar `BENCHMARK_ONLY_NONCOMMERCIAL` e não podem ser promovidos automaticamente para produção.

## Rerankers obrigatórios

Depois de gerar raw e candidates válidos, executar cada novo embedding contra todos os rerankers locais ou gratuitos elegíveis:

### Rerankers já canônicos

- `qwen_local` / Qwen3-Reranker-0.6B;
- `llama_nemotron_rerank_1b_v2`;
- `mxbai_rerank_base_v2`;
- `jina_reranker_v3_noncommercial`;
- `kalm_reranker_v1_small`;
- `kalm_reranker_v1_nano`;
- `querit_reranker_4b`;
- `voyage_rerank_2_5`, somente dentro de franquia gratuita comprovada e sem cobrança.

### Rerankers modernos novos

- `lamar_600m` / `nlpai-lab/LAMAR-600m`;
- `ettin_reranker_150m_v1`;
- `ettin_reranker_68m_v1`.

Não executar `google_vertex_ranking_api` sem autorização explícita de custo e billing. O Google não possui reranker dedicado gratuito equivalente na Gemini Developer API. Não usar um Gemini gerativo como “reranker” e misturá-lo no ranking de cross-encoders sem uma tarefa futura específica e protocolo separado.

## Regra “todos os rerankers”

A matriz esperada é:

`embeddings raw executados com sucesso × 11 rerankers locais/gratuitos listados acima`

Cada célula deve terminar em um dos estados:

- `VALID`;
- `BLOCKED_LICENSE`;
- `BLOCKED_FREE_TIER_UNAVAILABLE`;
- `BLOCKED_RUNTIME_REPRODUCIBLE`;
- `NOT_ELIGIBLE`, somente com justificativa técnica real.

`MISSING`, `NO_RUNNER` e `NO_CANDIDATES` não são estados finais aceitáveis.

Se um runner não estiver óbvio:

1. localizar o caminho usado pelos artefatos históricos;
2. reutilizar ou adaptar esse caminho;
3. implementar adaptador mínimo dentro do escopo;
4. executar smoke test;
5. somente bloquear após erro reproduzível.

Falha em uma célula não interrompe as demais.

## Rerankers novos: preflight

Antes da matriz completa:

- verificar model card, licença, revisão e hashes;
- medir load time, RAM e VRAM isolados;
- executar smoke em três pares positivos e três negativos do corpus;
- confirmar saída determinística e ordenação correta;
- usar `sentence-transformers.CrossEncoder` ou runner equivalente versionado;
- para Ettin, registrar explicitamente que foi treinado em inglês e avaliar seu comportamento no corpus PT-BR sem pressupor qualidade;
- para LAMAR, preservar configuração multilíngue oficial.

## Artefatos

Criar artefato individual autoritativo para cada raw e para cada pipeline reranqueado. Não criar leaderboard ou registry paralelo.

Atualizar obrigatoriamente:

`benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json`

O consolidado deve receber:

- novos perfis raw;
- candidates e proveniência;
- todas as células de reranking;
- métricas completas;
- status e bloqueios;
- memória e throughput quando disponíveis;
- ranking raw regenerado;
- ranking reranqueado regenerado;
- fila de candidatos reconciliada.

Atualizar o relatório humano existente da matriz. Não criar outro relatório concorrente.

Após ingestão bem-sucedida, remover do `CANONICAL_BENCHMARK_CANDIDATES.json` apenas as entradas concluídas; manter bloqueadas e pendentes com evidência.

## Relação com top 15

Depois dos novos resultados raw:

1. regenerar o ranking raw completo;
2. recalcular o top 15 raw aplicando exclusões vigentes;
3. se qualquer novo perfil entrar no top 15, incorporá-lo à matriz top 15 × rerankers;
4. não remover resultados históricos;
5. não declarar vencedor antes de cobertura comparável.

## Validações mínimas

Executar:

```bash
python -m unittest discover -s benchmark/embedding-v3/tests -v
python .ai/validate_governance.py
python -m compileall -q benchmark/embedding-v3
python benchmark/embedding-v3/validate_coverage.py
git diff --check
```

Adicionar testes para:

- nenhum candidato pendente desaparecer sem resultado/bloqueio canônico;
- IDs exatos Gemini e dimensões corretas;
- Qwen3 0.6B usa runner de embedding;
- matriz retangular dos embeddings bem-sucedidos × 11 rerankers;
- nenhuma célula final `MISSING`, `NO_RUNNER` ou `NO_CANDIDATES`;
- coerência entre artefatos individuais e `ALL_BENCHMARK_RESULTS.json`;
- licenças não comerciais não promovidas para produção.

## Git e retorno

- commit após cada grupo seguro de resultados;
- push da branch;
- abrir PR draft contra `bench/complete-embedding-reranker-matrix`;
- não fazer merge.

Retornar:

1. HEAD inicial e final;
2. preflight de cota gratuita Gemini e Voyage;
3. perfis raw executados e métricas;
4. perfis bloqueados e evidências;
5. lista final de rerankers;
6. matriz completa;
7. pipelines executados;
8. memória, duração e erros;
9. ranking raw atualizado;
10. ranking reranqueado atualizado;
11. alterações no top 15;
12. arquivos alterados;
13. testes e validadores;
14. commit, push e PR;
15. confirmação de que nenhum candidato desapareceu.

Frase final obrigatória:

`Candidatos modernos preservados na fila canônica e benchmarkados em raw e contra todos os rerankers locais ou gratuitos elegíveis, sem apagar pendências.`
