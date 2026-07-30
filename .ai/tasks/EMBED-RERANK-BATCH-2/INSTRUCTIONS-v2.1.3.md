# INSTRUCTIONS v2.1.3 — auditoria final e consolidação da fase leve

## Objetivo

Continuar exclusivamente no branch do PR #20, preservar todos os resultados reais já obtidos e corrigir as inconsistências que ainda impedem a consolidação canônica da fase leve de `EMBED-RERANK-BATCH-2`.

Não reinicie a rodada. Não repita downloads válidos. Não descarte os commits anteriores nem os artefatos brutos que comprovem execuções reais.

Contrato técnico obrigatório:

`benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`

Instruções anteriores de contexto:

- `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.0.md`
- `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.1.md`
- `.ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.2.md`

Esta versão substitui somente a ordem de continuação após o retorno v2.1.2.

## Repositório, branch e PR

- Repositório: `Weltall-IA/holo-models`
- Worktree esperada: `/home/alpha/Playstoria/models-embed-batch2-light`
- Branch de execução: `exec/embed-rerank-batch2-light`
- PR: `#20`
- Estado esperado do PR: draft
- HEAD anterior ao pull: `b66a0e5c827631122b29ff2685f2c14c0d60657c`

Não volte para a branch do contrato. Não crie outro PR.

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
test -f .ai/tasks/EMBED-RERANK-BATCH-2/INSTRUCTIONS-v2.1.3.md
```

O remote deve corresponder a `Weltall-IA/holo-models`.

Antes de alterar arquivos, registre:

- staged, unstaged e não rastreados;
- processos ativos de Python, BitNet, llama.cpp, vLLM e benchmark;
- RAM e VRAM atuais;
- caminhos e SHA-256 dos cinco downloads;
- SHA-256 dos artefatos novos já produzidos;
- commits existentes no branch depois de `589c497da0bd7c0acce06ce5f653729a88d51523`.

Não use `reset --hard`, `clean`, `checkout --`, stash automático, force-push ou recriação da worktree.

## 2. Leitura obrigatória

Leia integralmente, nesta ordem:

1. `AGENTS.md`;
2. `.ai/PROJECT.yml`;
3. `.ai/WORKFLOW.yml`;
4. `benchmark/embedding-v3/AGENTS.md`;
5. `benchmark/embedding-v3/config/EMBED_RERANK_BATCH_2.yml`;
6. as três instruções anteriores;
7. este arquivo;
8. diff completo, commits e descrição atual do PR #20.

## 3. Diagnóstico obrigatório antes de continuar

O retorno v2.1.2 contém progresso real, mas não autoriza consolidação sem corrigir as inconsistências abaixo.

### 3.1 Parser BitNet não está versionado

O retorno declarou:

`bitnet_parser_implemented = true`

Porém o diff atual do PR não contém módulo de parser, adaptação do runner ou testes unitários correspondentes. Apenas instruções e artefatos JSON aparecem no branch.

Portanto:

- implemente o parser no código canônico do benchmark;
- integre-o ao runner usado para os dois BitNet;
- adicione testes com fixtures pequenas e sanitizadas;
- registre o caminho dos arquivos de código e teste;
- não mantenha a implementação somente em script temporário fora do Git;
- somente declare `bitnet_parser_versioned = true` quando o código e os testes estiverem no diff do PR.

O parser deve rejeitar:

- saída parcial;
- bytes ou texto residual ambíguo;
- dimensões diferentes de 1024 e 640 conforme o perfil;
- NaN, infinito e norma zero;
- quantidade de vetores diferente da quantidade de entradas;
- vetores duplicados indevidos;
- associação não determinística entre entrada e vetor.

### 3.2 Métricas inválidas ou incompletas

Os artefatos atuais de LFM2.5 e BitNet apresentam campos como:

- `nDCG@10 = 0.0`;
- `mean_first_relevant_rank = 0.0`;
- `median_first_relevant_rank = 0.0`;
- `hard_negative_error_rate = 0.0`;
- `by_query_type = {}`;
- `per_query = []`.

Esses valores não podem ser tratados como medições reais apenas porque o gate foi calculado. Há ainda divergência histórica para o LFM2.5: o retorno anterior registrou duas consultas sem relevante, enquanto o JSON atual registra zero.

Procedimento obrigatório:

1. localize os rankings ou candidates reais de cada embedding;
2. confirme 150 consultas na ordem congelada e corpus SHA-256 correto;
3. execute o avaliador canônico sobre os rankings reais;
4. regenere todas as métricas deriváveis, incluindo `per_query` e `by_query_type`;
5. não preencha métrica ausente com zero;
6. quando uma métrica exigir dado bruto que não foi preservado, reexecute somente a parte necessária;
7. recalcule o gate depois da reconstrução completa;
8. preserve o FAIL do BitNet 0.6B quando o resultado completo confirmar HR@50 abaixo de 0.94;
9. preserve o PASS do BitNet 270M e LFM2.5 somente quando os resultados completos confirmarem os thresholds.

### 3.3 Pipelines não foram gerados pelo fluxo canônico

Os pipelines atuais possuem esquema reduzido e métricas parciais. Não selecione manualmente um formato por semelhança com arquivos históricos.

Use os geradores e avaliadores atuais do repositório. O arquivo final deve ser exatamente o produto do fluxo canônico aplicável ao branch, incluindo score artifact e avaliação completa quando esse for o contrato do gerador.

Para cada pipeline, exija:

- identidade do embedding e reranker;
- candidates e top-k corretos;
- score artifact com ligação verificável;
- instrução de rerank;
- modelo, revisão, peso e hashes;
- backend, versão e comando;
- MRR@10, nDCG@10, HitRate, damage, rescue e erros aplicáveis;
- latências, RAM e VRAM;
- 150 consultas ou a estrutura por consulta prevista pelo gerador;
- newline final e serialização canônica.

Não copie números do relatório para montar JSON.

## 4. Correção e testes do BitNet

Implemente a integração canônica do BitNet no benchmark e teste-a antes de reusar os resultados completos.

Requisitos:

- runtime oficial Microsoft BitNet no commit já registrado;
- CPU é permitido para I2_S quando o build CUDA comprovadamente falha no kernel `launch_bin_bcast_pack`;
- não tente novamente o caminho CUDA que já apresentou crash sem mudança técnica justificável;
- registre explicitamente que o backend efetivo foi CPU;
- registre throughput, RAM e qualquer VRAM residual;
- mantenha instrução somente nas consultas;
- documentos sem instrução;
- pooling no último token não preenchido;
- normalização L2;
- 1024 dimensões para 0.6B;
- 640 dimensões para 270M.

Crie testes para:

- saída válida de 1024 dimensões;
- saída válida de 640 dimensões;
- dimensão incorreta;
- NaN e infinito;
- vetor de norma zero;
- saída truncada;
- texto residual inesperado;
- quantidade incorreta de vetores.

Depois dos testes:

- valide ou regenere os candidates dos dois BitNet;
- calcule métricas completas;
- confirme gates;
- não execute `qwen_local` para o BitNet 0.6B se o FAIL permanecer;
- valide ou regenere o pipeline `qwen_local` do BitNet 270M pelo gerador canônico.

## 5. Correção dos resultados LFM2.5

Preserve a execução real do LFM2.5, mas regenere o artefato de embedding e o pipeline Qwen a partir dos rankings, candidates e scores reais.

O resultado deve registrar:

- repositório e revisão imutável completos;
- arquivo, bytes e SHA-256 completo;
- licença;
- llama.cpp e commit/versão efetivos;
- comando;
- CUDA realmente usada;
- Q4_K_M;
- CLS;
- dimensão 1024;
- L2;
- prefixos de query e documento;
- corpus e contagens;
- métricas completas e não placeholders;
- tempos, throughput, RAM e VRAM;
- gate recalculado.

## 6. Pipelines Qwen obrigatórios da fase 0

Os dois pipelines descritos no retorno como concluídos são LFM2.5 e BitNet 270M. Eles não substituem os pipelines obrigatórios da fase 0.

Ainda devem ser tentados, individualmente:

- `nemotron_3_embed_1b_nvfp4`;
- `nemotron_3_embed_1b_q4_k_m_gguf`;
- `voyage-context-4`;
- `voyage-4-large` somente quando a auditoria de alias não provar equivalência com `voyage_4_large_1024_float32`.

Requisitos:

- usar somente artefatos locais ou checkpoints válidos já existentes;
- não chamar API Voyage;
- não copiar ou renomear candidates de outro perfil;
- registrar fonte e hash do ranking normalizado;
- 150 consultas na ordem congelada;
- top 50 candidatos por consulta;
- corpus SHA-256 correto;
- persistir um pipeline por vez;
- marcar `BLOCKED` com erro e tentativa real quando o artefato necessário não puder ser materializado.

## 7. Mixedbread no painel fixo

O painel continua incompleto porque falta `nemotron_3_embed_1b_nvfp4`.

Painel obrigatório:

- `nemotron_3_embed_1b_nvfp4`;
- `nomic_embed_text_v2_moe_q4`;
- `qwen3_embedding_4b_q8_0`;
- `embeddinggemma`;
- `colibri_ptbr`;
- `granite_embedding_311m_r2`.

Procedimento:

1. valide candidates e scores brutos dos cinco resultados existentes;
2. regenere os cinco pipelines pelo gerador canônico, sem copiar métricas manualmente;
3. execute o sexto membro quando os candidates de `nemotron_3_embed_1b_nvfp4` estiverem válidos;
4. produza exatamente seis pipelines quando tecnicamente possível;
5. quando o sexto membro ficar bloqueado por ausência comprovada de candidates válidos, marque o painel incompleto e registre a causa;
6. não recrie `mxbai_panel_results.json` nem outro resumo paralelo.

## 8. NVIDIA Nemotron Rerank 1B v2

Não atualize CUDA toolkit, driver, PyTorch global nem pacotes do sistema.

A tentativa anterior com vLLM 0.25.0 deve ser formalizada com evidência:

- Python e pip;
- CUDA toolkit e driver;
- PyTorch;
- comando de instalação;
- erro do resolver ou importação sanitizado;
- dependências incompatíveis;
- motivo técnico pelo qual a instalação isolada não pode funcionar no ambiente atual.

Se a incompatibilidade estiver comprovada, marque o painel inteiro como `BLOCKED_RUNTIME_INCOMPATIBLE` e não repita a instalação.

Somente prossiga com o benchmark se existir uma solução isolada que:

- não altere o sistema;
- mantenha `vllm==0.25.0`;
- preserve o modelo e precisão autorizados;
- use pooling e o score template obrigatório;
- não use geração de texto.

Não substitua o backend e não atualize CUDA.

## 9. Consolidação canônica

Somente depois das correções e execuções localmente viáveis:

1. valide todos os JSON;
2. regenere `ALL_BENCHMARK_RESULTS.json` pelo gerador canônico;
3. atualize as duas tabelas canônicas do `README.md` quando a decisão de qualidade mudar;
4. não crie leaderboard, registry, blacklist ou relatório paralelo;
5. registre o BitNet 0.6B como resultado completo reprovado, não como ausência de execução;
6. registre Nemotron Rerank 1B v2 como bloqueado quando a incompatibilidade estiver comprovada;
7. preserve separação entre embedding-only e reranked;
8. não estime métricas.

Contagens esperadas quando todos os resultados localmente viáveis forem aceitos:

- perfis raw canônicos: 39, correspondendo aos 36 anteriores mais LFM2.5 oficial e os dois BitNet atuais;
- pipelines canônicos: 100 quando os três pipelines Qwen obrigatórios da fase 0, os dois pipelines Qwen novos e os seis Mixedbread forem concluídos;
- pipelines canônicos: 101 apenas quando `voyage-4-large` exigir pipeline separado após auditoria de alias.

Essas contagens são critérios de coerência, não autorização para fabricar ou aceitar artefatos incompletos. Quando algum pipeline obrigatório ficar `BLOCKED`, informe a contagem real e a diferença explicada.

## 10. Validações obrigatórias

Execute e registre:

```bash
python .ai/validate_governance.py
python -m unittest discover -s benchmark/embedding-v3/tests -v
python -m compileall -q benchmark/embedding-v3
python benchmark/embedding-v3/validate_coverage.py
git diff --check
```

Além disso, valide:

- corpus 600/150 e SHA-256 congelado;
- 150 query IDs na ordem correta em todos os candidates novos;
- top 50 em todos os candidates;
- ausência de NaN, infinito e valores placeholders;
- ausência de `per_query: []` em resultados declarados completos;
- ausência de `by_query_type: {}` em resultados declarados completos;
- ausência de métricas zeradas sem comprovação;
- ausência de IDs duplicados;
- ausência de arquivos paralelos proibidos;
- diff integral depois da última correção.

## 11. Commit, push e PR

Ao concluir:

- inclua somente código, testes, artefatos reais e arquivos canônicos do escopo;
- remova scripts temporários que não sejam necessários;
- não versione pesos, caches, ambientes virtuais ou logs gigantes;
- faça commit no branch `exec/embed-rerank-batch2-light`;
- faça push sem force;
- atualize o PR #20;
- mantenha o PR draft;
- não faça merge.

## 12. Formato obrigatório do retorno

O retorno deve ser narrativo, direto e verificável, nesta ordem:

### Resultado direto

Declare se a fase leve ficou consolidada, parcialmente consolidada ou bloqueada. Informe perfis raw e pipelines canônicos finais.

### O que foi corrigido

Liste código, testes, schemas, métricas e artefatos corrigidos.

### O que funcionou

Liste embeddings, gates, pipelines Qwen, painel Mixedbread, geradores e validações concluídos.

### O que ficou bloqueado

Para cada bloqueio, informe fase, erro exato, tentativa, evidência e impacto.

### Resultados dos embeddings

Para LFM2.5 e os dois BitNet, informe todas as métricas obrigatórias, gate, tempos, throughput, RAM, VRAM e backend efetivo.

### Resultados dos rerankers

Informe todos os pipelines Qwen e Mixedbread aceitos, com métricas completas, damage, rescue, latência, RAM e VRAM. Registre o Nemotron como executado ou bloqueado.

### Validações e contagens

Informe cada validador, resultado, perfis raw finais e pipelines finais.

### Arquivos, hashes e Git

Liste arquivos de código e teste adicionados, artefatos alterados, hashes relevantes, commit, push, URL e estado do PR.

### Campos obrigatórios

Inclua exatamente estes campos com valores reais:

```text
previous_execution_stopped = true|false
pr20_marked_draft = true
existing_downloads_reused = true|false
duplicate_model_downloads = <inteiro>
bitnet_parser_versioned = true|false
bitnet_parser_tests_passed = true|false
embedding_metrics_recomputed_from_real_rankings = true|false
placeholder_zero_metrics_remaining = <inteiro>
empty_per_query_completed_results = <inteiro>
empty_by_query_type_completed_results = <inteiro>
lfm_complete_artifact_validated = true|false
bitnet_06b_complete_artifact_validated = true|false
bitnet_270m_complete_artifact_validated = true|false
phase0_qwen_mandatory_attempted = <inteiro>
phase0_qwen_mandatory_completed = <inteiro>
phase0_qwen_mandatory_blocked = <inteiro>
bitnet_270m_qwen_pipeline_validated = true|false
mxbai_fixed_panel_completed = true|false
mxbai_fixed_panel_pipeline_count = <inteiro>
nemotron_vllm_runtime_compatible = true|false
nemotron_fixed_panel_completed = true|false
nemotron_blocked_with_evidence = true|false
canonical_raw_profile_count = <inteiro>
canonical_pipeline_count = <inteiro>
canonical_results_regenerated_from_real_artifacts_only = true|false
readme_canonical_tables_updated = true|false
voyage_api_accessed = false
voyage_api_calls_planned = 0
voyage_api_calls_executed = 0
heavy_models_downloaded = false
heavy_models_executed = false
merge_executed = false
```

A resposta deve terminar exatamente com:

`Versão do retorno da IA local: 2.1.3 — Auditoria final e consolidação da fase leve`
