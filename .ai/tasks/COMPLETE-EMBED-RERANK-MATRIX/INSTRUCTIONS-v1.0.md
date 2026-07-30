# INSTRUCTIONS v1.0 — matriz completa embedding × reranker

## Objetivo

Concluir corretamente o benchmark Holo de embeddings e rerankers em uma única matriz canônica comparável.

Não criar novos leaderboards paralelos, painéis parciais, shortlists alternativas ou relatórios concorrentes. O resultado final deve existir em uma única fonte canônica consolidada e uma única tabela humana.

## Repositório e branch

- Repositório: `Weltall-IA/holo-models`
- Branch: `bench/complete-embedding-reranker-matrix`
- Base: `agent/prepare-next-embedding-rerank-batch-v2`
- Não fazer merge.

Antes de atuar, confirmar remote, branch, HEAD, working tree, worktrees, stashes e arquivos não rastreados. Preservar todo trabalho preexistente. Não usar `reset --hard`, `clean`, stash automático ou force-push.

## Leitura obrigatória

Leia integralmente, nesta ordem:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json`;
6. todos os artefatos individuais em `benchmark/embedding-v3/results/reranker/pipelines/`;
7. esta instrução.

## Regra principal

Para cada embedding selecionado, executar todos os rerankers elegíveis com exatamente os mesmos:

- corpus congelado;
- candidates top 50;
- rerank top 20;
- instrução;
- query/document text;
- normalização;
- dimensão e dtype específicos do perfil;
- métricas;
- hardware e runtime registrados.

Uma combinação ausente não pode ser interpretada como resultado inferior. Deve aparecer como `MISSING`, `BLOCKED` ou `NOT_ELIGIBLE`, sempre com motivo verificável.

## Embeddings obrigatórios

A matriz deve incluir, no mínimo, todos os embeddings locais ou remotos que atendam a qualquer condição abaixo:

1. top 10 embeddings únicos por MRR@10 raw no consolidado atual;
2. embeddings presentes no top 10 de pipelines reranqueados atual;
3. variantes de quantização do mesmo candidato operacional que precisam de comparação justa;
4. candidatos explicitamente discutidos para produção.

A lista mínima obrigatória inclui:

- `qwen3_embedding_4b_q8_0`;
- `nomic_embed_text_v2_moe_q4`;
- `nemotron_3_embed_1b_nvfp4`;
- `nemotron_3_embed_1b_q4_k_m_gguf`;
- `nemotron_8b_abiray_q4_audit_1024` ou seu substituto corrigido e auditado, sem perfil 4096;
- `colibri_ptbr`;
- `embeddinggemma` / `embeddinggemma_768_float32`, preservando distinção de perfil mas deduplicando peso quando apropriado;
- `voyage_4_large_1024_float32`;
- variantes Voyage Nano que apareçam entre os melhores resultados publicados;
- qualquer outro embedding que o cálculo automático identifique nas condições 1–4.

`nemotron_8b_abiray_q4_audit_4096` está excluído por decisão do usuário e não deve ser promovido à matriz operacional.

## Rerankers obrigatórios

Mapeie todos os rerankers presentes no consolidado e nos artefatos publicados. A matriz deve conter colunas explícitas para, no mínimo:

- `qwen_local` / Qwen3-Reranker-0.6B;
- `llama_nemotron_rerank_1b_v2`;
- `mxbai_rerank_base_v2`;
- `jina_reranker_v3_noncommercial`;
- `kalm_reranker_v1_small`;
- `kalm_reranker_v1_nano`;
- `querit_reranker_4b`;
- `voyage_rerank_2_5`.

Se algum reranker não for tecnicamente elegível para determinado embedding, registrar `NOT_ELIGIBLE` com justificativa técnica. Não omitir a célula.

## APIs pagas

Não executar nova chamada paga sem autorização explícita específica de custo.

Para Voyage:

- reutilizar resultados existentes e verificáveis;
- marcar células faltantes como `BLOCKED_PAID_API_AUTH_REQUIRED`;
- não fingir cobertura completa;
- não excluir a coluna da matriz.

## Auditoria inicial obrigatória

Antes de executar qualquer modelo:

1. gerar inventário de todos os embeddings selecionados;
2. gerar inventário de todos os rerankers;
3. construir matriz completa esperada embedding × reranker;
4. apontar para cada célula o artefato existente, se houver;
5. validar identidade do embedding, candidates, corpus e protocolo;
6. classificar cada célula como:
   - `VALID_REUSABLE`;
   - `REEXECUTE_PROTOCOL_MISMATCH`;
   - `MISSING`;
   - `BLOCKED`;
   - `NOT_ELIGIBLE`;
7. só então executar as células locais faltantes ou inválidas.

Resultados com proveniência divergente, candidates diferentes, corpus diferente, protocolo diferente ou identidade de peso não provada não podem preencher a matriz canônica sem reexecução.

## Execução

- Executar todas as células locais `MISSING` e `REEXECUTE_PROTOCOL_MISMATCH`.
- Persistir checkpoint após cada célula.
- Falha em uma célula não interrompe as demais.
- Nunca trocar embedding, reranker, dimensão, dtype, candidates ou instrução silenciosamente.
- Não recalcular embeddings quando candidates válidos e compatíveis puderem ser reutilizados.
- Não reutilizar candidates incompatíveis.
- Registrar comandos, versões, hashes, duração, RAM/VRAM e erros sanitizados quando disponíveis.

## Fonte canônica única

Atualizar somente a fonte canônica:

`benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json`

Ela deve passar a conter uma seção explícita de matriz completa, com:

- lista canônica de embeddings selecionados;
- lista canônica de rerankers;
- todas as células esperadas;
- status de cada célula;
- caminho do artefato individual;
- MRR@10, HitRate@1, HitRate@10, nDCG@10;
- corpus, candidates e protocolo;
- motivo de bloqueio/inelegibilidade;
- cobertura total e cobertura local;
- ranking final somente sobre células válidas.

Os artefatos individuais continuam autoritativos para cada execução; o consolidado é o índice único de comparação.

## Relatório humano único

Gerar ou atualizar apenas:

`benchmark/embedding-v3/COMPLETE_EMBED_RERANK_MATRIX_REPORT.md`

O relatório deve conter:

1. uma tabela de cobertura com embeddings nas linhas e rerankers nas colunas;
2. uma tabela única de todos os pipelines válidos, ordenada por MRR@10;
3. uma tabela por embedding com raw, melhor reranker, melhor resultado e cobertura;
4. comparação direta entre `nemotron_3_embed_1b_nvfp4` e `nemotron_3_embed_1b_q4_k_m_gguf` usando os mesmos rerankers;
5. lista objetiva de células ainda bloqueadas;
6. nenhuma conclusão de vencedor quando a comparação simétrica estiver incompleta.

Formato mínimo da tabela final:

| Rank | Embedding | Params | Quant/dtype | Dim | Reranker | MRR@10 | HR@1 | HR@10 | nDCG@10 | Status | Artifact |

## Gates de conclusão

A tarefa só pode ser declarada concluída quando:

- a matriz esperada estiver enumerada integralmente;
- todas as células locais elegíveis estiverem executadas ou bloqueadas com evidência;
- nenhuma ausência for tratada como derrota;
- NVFP4 e Q4_K_M do Nemotron 1B tiverem comparação simétrica nos rerankers locais elegíveis;
- o consolidado e o relatório forem regenerados a partir dos artefatos reais;
- não existir leaderboard paralelo novo;
- validações passarem;
- diff completo for revisado.

## Validações

Execute, no mínimo:

```bash
python -m unittest discover -s benchmark/embedding-v3/tests -v
python .ai/validate_governance.py
python -m compileall -q benchmark/embedding-v3
python benchmark/embedding-v3/validate_coverage.py
git diff --check
```

Adicionar testes específicos para:

- matriz retangular completa;
- nenhuma célula ausente sem status;
- nenhum pipeline duplicado;
- ranking derivado apenas de células válidas;
- cobertura simétrica Nemotron 1B NVFP4 vs Q4_K_M;
- coerência entre consolidado, artefatos individuais e relatório.

## Git e PR

- Commitar somente arquivos deste escopo.
- Fazer push da branch.
- Abrir PR draft contra `agent/prepare-next-embedding-rerank-batch-v2`.
- Não fazer merge.

Mensagem sugerida:

`Complete canonical embedding reranker benchmark matrix`

## Retorno obrigatório

Informar:

1. HEAD inicial e final;
2. lista final de embeddings;
3. lista final de rerankers;
4. quantidade total de células esperadas;
5. células reutilizadas;
6. células reexecutadas;
7. células bloqueadas e motivos;
8. matriz de cobertura completa;
9. ranking único final;
10. comparação simétrica NVFP4 vs Q4_K_M;
11. validações;
12. arquivos alterados;
13. commit, push e PR;
14. confirmação de que não foi criado leaderboard paralelo.

Frase final obrigatória:

`Matriz canônica embedding × reranker consolidada em uma única fonte, sem tratar ausência de teste como derrota.`
