# INSTRUCTIONS v1.1 — matriz top 15 raw × rerankers

## Substituição de escopo

Esta versão substitui integralmente `INSTRUCTIONS-v1.0.md`.

A tarefa NÃO cobre todos os embeddings do repositório. O universo obrigatório é exatamente o **top 15 de embeddings/perfis pelo MRR@10 raw** na fonte canônica vigente, após aplicar as exclusões explícitas do usuário.

Não repetir benchmarks raw já válidos. Não recalcular embeddings nem candidates quando artefatos compatíveis já existirem. Executar somente as combinações de reranker ausentes ou inválidas para os 15 selecionados.

## Repositório e branch

- Repositório: `Weltall-IA/holo-models`
- Branch: `bench/complete-embedding-reranker-matrix`
- Base: `agent/prepare-next-embedding-rerank-batch-v2`
- Não fazer merge.

Antes de atuar, confirmar remote, branch, HEAD, working tree, worktrees, stashes e arquivos não rastreados. Preservar integralmente todo trabalho preexistente. Não usar `reset --hard`, `clean`, stash automático ou force-push.

## Leitura obrigatória

Leia integralmente, nesta ordem:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json`;
6. artefatos individuais necessários em `benchmark/embedding-v3/results/reranker/pipelines/`;
7. esta instrução.

## Seleção exata dos embeddings

1. Ordene os perfis raw válidos por `MRR@10` decrescente usando `ALL_BENCHMARK_RESULTS.json`.
2. Exclua perfis `BLOCKED`, blacklist, `AUDIT_REQUIRED` sem artefato validado ou explicitamente excluídos pelo usuário.
3. Exclua `nemotron_8b_abiray_q4_audit_4096` e qualquer perfil operacional de 4096 dimensões do Nemotron 8B.
4. Se uma exclusão ocorrer dentro das 15 primeiras posições, promova o próximo perfil raw elegível até completar exatamente 15 linhas.
5. Preserve perfis distintos quando dimensão, dtype ou quantização forem distintos. Não deduplique apenas por família de modelo.
6. Registre a lista final com posição raw, profile_id, MRR@10 raw, dimensão, dtype/quantização e artefato-fonte.

A lista final deve conter exatamente 15 perfis, salvo bloqueio comprovado no próprio consolidado. Não adicionar candidatos por interesse operacional fora do top 15 raw.

## Rerankers

Mapeie todos os rerankers publicados e tecnicamente elegíveis presentes no consolidado, incluindo no mínimo:

- `qwen_local`;
- `llama_nemotron_rerank_1b_v2`;
- `mxbai_rerank_base_v2`;
- `jina_reranker_v3_noncommercial`;
- `kalm_reranker_v1_small`;
- `kalm_reranker_v1_nano`;
- `querit_reranker_4b`;
- `voyage_rerank_2_5`.

Para cada um dos 15 embeddings, crie uma célula para cada reranker. Nenhuma célula pode desaparecer silenciosamente.

## Reutilização antes de execução

Antes de executar qualquer benchmark:

1. construa a matriz esperada `15 × rerankers`;
2. localize artefatos existentes para cada célula;
3. valide identidade do embedding, corpus, candidates top 50, rerank top 20, instrução, dimensão, dtype, normalização e métricas;
4. classifique cada célula como:
   - `VALID_REUSABLE`;
   - `REEXECUTE_PROTOCOL_MISMATCH`;
   - `MISSING`;
   - `BLOCKED`;
   - `NOT_ELIGIBLE`;
5. reutilize toda célula `VALID_REUSABLE` sem reexecutar;
6. execute somente células locais `MISSING` ou `REEXECUTE_PROTOCOL_MISMATCH`.

Não repetir benchmark raw. Não recalcular candidates quando os candidates existentes forem compatíveis e verificáveis.

## Protocolo obrigatório

Todas as células executadas devem usar exatamente:

- corpus congelado vigente;
- candidates top 50;
- rerank top 20;
- mesma instrução;
- mesmos textos de query e documento;
- dimensão e dtype próprios do perfil raw selecionado;
- mesma normalização;
- mesmas métricas.

Uma ausência de teste nunca pode ser interpretada como derrota.

## APIs pagas

Não executar chamadas pagas sem autorização explícita específica.

Para `voyage_rerank_2_5`:

- reutilizar resultados existentes e compatíveis;
- marcar células faltantes como `BLOCKED_PAID_API_AUTH_REQUIRED`;
- manter a coluna na matriz;
- não fingir cobertura completa.

## Consolidação única

Atualizar a fonte canônica existente:

`benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json`

Adicionar ou atualizar uma seção explícita para o top 15 raw contendo:

- seleção final dos 15 perfis;
- regra de seleção e exclusões;
- lista de rerankers;
- matriz completa de células;
- status de cada célula;
- caminho do artefato;
- MRR@10, HitRate@1, HitRate@10 e nDCG@10;
- motivo de bloqueio ou inelegibilidade;
- cobertura total e local;
- ranking único apenas das células válidas.

Não criar outro JSON de leaderboard, registry ou ranking concorrente.

## Tabela humana única

Gerar ou atualizar somente:

`benchmark/embedding-v3/COMPLETE_EMBED_RERANK_MATRIX_REPORT.md`

O relatório deve conter:

1. lista do top 15 raw;
2. matriz de cobertura com 15 embeddings nas linhas e rerankers nas colunas;
3. uma tabela única de todos os pipelines válidos desses 15 embeddings, ordenada por MRR@10;
4. tabela resumida por embedding com raw, melhor reranker, melhor MRR e cobertura;
5. lista objetiva das células faltantes, bloqueadas ou inelegíveis;
6. comparação direta entre variantes do mesmo modelo quando ambas estiverem no top 15 raw;
7. nenhuma conclusão de vencedor baseada em cobertura desigual.

Formato mínimo da tabela de pipelines:

| Rank | Raw rank | Embedding | Params | Quant/dtype | Dim | Reranker | MRR@10 | HR@1 | HR@10 | nDCG@10 | Status | Artifact |

## Execução

- Executar somente células locais faltantes ou incompatíveis do top 15 raw.
- Persistir checkpoint após cada célula.
- Falha independente não interrompe as demais.
- Não trocar silenciosamente embedding, reranker, dimensão, dtype, candidates ou instrução.
- Registrar comando, versões, hashes, duração e erros sanitizados.

## Gates de conclusão

Só declarar conclusão quando:

- a seleção dos 15 perfis raw estiver provada e reproduzível;
- a matriz completa estiver enumerada;
- todas as células locais elegíveis estiverem reutilizadas, executadas ou bloqueadas com evidência;
- nenhum benchmark raw tiver sido repetido sem necessidade;
- nenhuma ausência tiver sido tratada como derrota;
- `ALL_BENCHMARK_RESULTS.json` e o relatório único tiverem sido regenerados a partir dos artefatos reais;
- não houver leaderboard paralelo;
- validações aplicáveis passarem;
- o diff completo tiver sido revisado.

## Validações

Execute, no mínimo:

```bash
python -m unittest discover -s benchmark/embedding-v3/tests -v
python .ai/validate_governance.py
python -m compileall -q benchmark/embedding-v3
python benchmark/embedding-v3/validate_coverage.py
git diff --check
```

Adicionar testes para:

- exatamente 15 perfis raw selecionados;
- seleção ordenada e reproduzível;
- promoção do próximo perfil após exclusão;
- matriz retangular completa;
- nenhuma célula sem status;
- nenhum pipeline duplicado;
- ranking derivado somente de células válidas;
- coerência entre consolidado, artefatos individuais e relatório.

## Git e PR

- Commitar somente arquivos deste escopo.
- Fazer push da branch.
- Abrir ou atualizar PR draft contra `agent/prepare-next-embedding-rerank-batch-v2`.
- Não fazer merge.

Mensagem sugerida:

`Complete reranker matrix for top 15 raw embeddings`

## Retorno obrigatório

Informar:

1. HEAD inicial e final;
2. lista exata do top 15 raw;
3. exclusões e promoções aplicadas;
4. lista de rerankers;
5. total de células esperadas;
6. células reutilizadas;
7. células executadas;
8. células bloqueadas ou inelegíveis;
9. matriz de cobertura;
10. ranking único final;
11. validações;
12. arquivos alterados;
13. commit, push e PR;
14. confirmação de que nenhum benchmark raw válido foi repetido e nenhum leaderboard paralelo foi criado.

Frase final obrigatória:

`Top 15 raw comparado na matriz canônica de rerankers, reutilizando resultados válidos e executando somente as células faltantes.`
