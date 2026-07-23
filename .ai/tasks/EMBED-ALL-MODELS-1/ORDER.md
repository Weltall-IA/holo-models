# EMBED-ALL-MODELS-1 — DOWNLOAD COMPLETO ANTES DO BENCHMARK

## Objetivo

Corrigir a execução anterior: nenhum modelo pode ser excluído por `enabled:false`, `required:false`, `optional`, alias, preferência operacional, incompatibilidade do runtime atual ou decisão interna de prioridade.

A sequência obrigatória é:

1. inventariar todos os perfis;
2. baixar e verificar todos os pesos ausentes;
3. preparar um runtime compatível para cada formato;
4. confirmar o gate de completude;
5. somente então executar um benchmark unificado no corpus congelado;
6. não publicar vencedor enquanto existir perfil sem resultado real.

## Regra absoluta

É PROIBIDO iniciar o benchmark enquanto qualquer item da fila de download não estiver presente e verificado.

Se qualquer download falhar, pare antes do benchmark e retorne o erro exato. Não execute subconjunto. Não transforme falha em `optional`, `disabled`, `not applicable`, `alias` ou `coverage_complete`.

Modelos já presentes não devem ser baixados novamente. Apenas verifique caminho, revisão, tamanho e SHA-256.

## Repositório e preservação

- Repositório: `Weltall-IA/holo-models`
- Checkout local esperado: `/home/alpha/Playstoria/models`
- Branch: `ai/download-all-before-full-benchmark-v1`
- Preserve integralmente qualquer arquivo não versionado ou trabalho fora do escopo, inclusive:
  - `benchmark/benchmark/`
  - `benchmark/embedding-v3/run_voyage.py`
  - `comandos.md`
  - `runtime/vane-native-ops/`
- Não use stash automático, reset destrutivo, force-push ou remoção de pesos existentes.
- Pesos e caches permanecem fora do Git.

## Fila obrigatória atualmente sem benchmark completo

### Nemotron

1. `nvidia/Nemotron-3-Embed-8B-BF16`
   - situação: ausente do benchmark e do manifesto anterior;
   - baixar o checkpoint oficial completo;
   - backend preferencial: vLLM ou Transformers/Sentence Transformers isolado, conforme suporte real.

2. `Abiray/Nemotron-3-Embed-8B-GGUF`
   - arquivo Q4_K_M local já identificado;
   - situação: somente inspeção estrutural e cinco startups; NÃO houve benchmark de retrieval no corpus completo;
   - executar como perfil independente.

3. `Aqua00/Nemotron-3-Embed-8B-GGUF`
   - arquivo Q4_K_M local já identificado;
   - situação: somente inspeção estrutural e cinco startups; NÃO houve benchmark de retrieval no corpus completo;
   - executar como perfil independente, mesmo que os payloads de tensor coincidam com o Abiray.

4. `nvidia/Nemotron-3-Embed-1B-BF16`
   - situação: ausente do benchmark;
   - baixar e executar como perfil separado do NVFP4 e do GGUF.

### Qwen

5. `Qwen/Qwen3-Embedding-4B`
   - situação: foi marcado `enabled:false` e omitido;
   - baixar checkpoint nativo completo e executar.

6. `Qwen/Qwen3-Embedding-4B-GGUF`
   - arquivo primário: `Qwen3-Embedding-4B-Q8_0.gguf`;
   - situação: perfil não criado anteriormente;
   - baixar e executar via llama.cpp;
   - não substituir silenciosamente por outra quantização.

### BitNet

7. `microsoft/bitnet-embedding-270m`
   - arquivo: `bitnet-embeddings-270m-bf16-i2_s.gguf`;
   - situação: peso já resolvido/baixado, mas benchmark não concluído por incompatibilidade do llama.cpp 9972;
   - preparar runtime isolado compatível; não alterar nem substituir o llama.cpp estável existente.

8. `microsoft/bitnet-embedding-0.6b`
   - arquivo: `bitnet-embeddings-0.6b-bf16-i2_s.gguf`;
   - situação: peso já resolvido/baixado, mas benchmark não concluído por incompatibilidade do llama.cpp 9972;
   - preparar runtime isolado compatível; não alterar nem substituir o llama.cpp estável existente.

### EmbeddingGemma

9. `google/embeddinggemma-300m`
   - situação: checkpoint nativo foi excluído por acesso gated; somente o GGUF foi benchmarkado;
   - tentar download autenticado do checkpoint nativo;
   - se o acesso não estiver concedido, parar antes do benchmark e retornar esse único bloqueio, sem executar subconjunto.

## Não adicionar modelo inexistente

Até a data desta ordem, a coleção oficial NVIDIA contém `Nemotron-3-Embed-1B-NVFP4`, `Nemotron-3-Embed-1B-BF16` e `Nemotron-3-Embed-8B-BF16`. Não inventar um perfil oficial `Nemotron-3-Embed-8B-NVFP4` sem repositório e pesos reais.

## Fase 1 — Manifesto único de download

Crie um manifesto versionável que liste TODOS os perfis existentes e ausentes, sem campos que permitam exclusão silenciosa.

Arquivo sugerido:

`benchmark/embedding-v3/config/all_models_benchmark_manifest.json`

Para cada perfil registre:

- `id`;
- `repo`;
- `revision` fixada;
- `format`;
- `weight_file` ou lista de arquivos;
- `expected_size_bytes`;
- `local_path`;
- `sha256` real;
- `download_state`: somente `PRESENT_VERIFIED`, `DOWNLOADED_VERIFIED` ou `DOWNLOAD_FAILED`;
- `benchmark_state`: inicialmente `PENDING`;
- `runtime` planejado;
- dimensão nativa e dimensão comparável;
- licença.

Não use `enabled`, `required`, `optional`, `selected`, `priority` ou campos equivalentes para retirar modelo da execução.

Inclua no manifesto todos os modelos já benchmarkados anteriormente, além dos nove perfis acima. O benchmark final será uma única matriz completa.

## Fase 2 — Download antes de qualquer inferência

1. Verifique espaço livre e tamanho total antes de baixar.
2. Baixe sequencialmente para evitar pressão desnecessária de RAM/disco.
3. Use revisão fixada e download retomável.
4. Valide tamanho e SHA-256 após cada download.
5. Não execute embedding, smoke test ou benchmark nesta fase.
6. Não apague versões ou pesos existentes.
7. Não marque download como concluído sem arquivo real e hash.

Ao final, gere:

`benchmark/embedding-v3/results/all_models_download_gate.json`

O campo `download_gate_passed` só pode ser `true` quando TODOS os perfis estiverem `PRESENT_VERIFIED` ou `DOWNLOADED_VERIFIED`.

Se for `false`, encerre a execução e retorne a lista exata de falhas. NÃO INICIE BENCHMARK.

## Fase 3 — Preparação dos runtimes

Somente após `download_gate_passed=true`:

- mantenha o llama.cpp estável 9972 intacto;
- crie runtime/build isolado para BitNet, se necessário;
- use ambiente isolado para Nemotron BF16/NVFP4;
- não reutilize vetores falsos;
- valide apenas carregamento mínimo e encerramento limpo de cada runtime;
- uma falha de runtime bloqueia o benchmark completo; não prossiga com subconjunto.

Gere:

`benchmark/embedding-v3/results/all_models_runtime_gate.json`

O benchmark só pode começar com `runtime_gate_passed=true` para todos.

## Fase 4 — Benchmark unificado, uma única vez

Depois dos dois gates aprovados, execute todos os perfis no mesmo corpus congelado:

- 600 documentos;
- 150 consultas;
- SHA-256 `8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b`;
- prefixos oficiais por modelo;
- normalização recomendada e registrada;
- mesmo protocolo de métricas;
- execução isolada por perfil;
- nenhum resultado reaproveitado como sucesso sem reexecução neste ciclo, exceto baselines remotos Voyage congelados que não exijam nova cobrança.

Métricas mínimas:

- HitRate/Recall @1, @3, @5, @10, @20 e @50;
- MRR@10;
- nDCG@10;
- mean/median first relevant rank;
- hard-negative error rate;
- load/startup;
- documentos/s e consultas/s;
- RAM e VRAM de pico;
- tempo total;
- revisão, arquivo, hash, backend, dtype, dimensão, pooling e normalização.

Para modelos com dimensão Matryoshka:

- registre a dimensão nativa;
- execute também a dimensão comparável de 1024 quando oficialmente suportada;
- reporte os dois perfis separadamente; não esconda um deles.

Os dois GGUF Nemotron 8B devem ser executados separadamente no corpus completo, apesar da equivalência estrutural observada.

## Fase 5 — Reranking local completo

Após todos os embeddings concluírem:

- aplique o Qwen3-Reranker-0.6B local a TODOS os perfis de embedding;
- preserve top 50 e reranqueie top 20 com os mesmos textos e instrução;
- registre rescue e damage;
- não exclua Nemotron, BitNet, Qwen 4B ou qualquer outro perfil.

Não faça nova chamada paga ao Voyage nesta ordem. Reutilize apenas resultados remotos congelados já existentes como baseline. Uma nova rodada paga exige autorização de custo separada.

## Critério de conclusão

A tarefa só pode ser declarada concluída quando:

- todos os nove perfis anteriormente ausentes tiverem download e hash verificados;
- todos os modelos do manifesto tiverem runtime funcional;
- todos tiverem resultado completo no corpus, sem `PENDING`, `BLOCKED`, `OPTIONAL`, `DISABLED` ou `NOT_APPLICABLE`;
- todos os embeddings concluídos tiverem pipeline com o reranker local;
- o ranking final incluir cada perfil explicitamente;
- testes, parse de JSON/YAML, `compileall`, `validate_coverage.py`, scan de segredos e `git diff --check` passarem;
- nenhum modelo seja escondido por alias sem resultado próprio, exceto duplicata byte a byte quando o usuário autorizar explicitamente — não há essa autorização nesta ordem.

## Publicação

- Commit e push somente na feature branch.
- Abra PR draft enquanto downloads, runtime ou benchmark estiverem incompletos.
- Não faça merge enquanto existir qualquer perfil faltante ou falha.
- Não crie outro repositório, integração de aplicação ou deploy.

## Retorno curto obrigatório

Retorne somente:

1. total de perfis no manifesto;
2. downloads: verificados / falhos;
3. lista de qualquer download falho;
4. runtime gate: PASS/FAIL e falhas;
5. benchmark iniciado: SIM/NÃO;
6. se iniciado, resultados concluídos / total;
7. PR/commit atual;
8. próximo bloqueio real, se houver.
