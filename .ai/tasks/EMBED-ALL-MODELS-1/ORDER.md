# EMBED-ALL-MODELS-1 — BAIXAR TUDO E EXECUTAR UM ÚNICO BENCHMARK

## Objetivo único

Encontrar o melhor modelo de embedding textual no computador local.

Fluxo obrigatório:

1. verificar todos os pesos já existentes;
2. baixar todos os pesos ausentes das listas abaixo;
3. corrigir qualquer erro de download ou runtime até o modelo funcionar;
4. confirmar que todos os downloads estão completos;
5. somente então executar um único benchmark textual consolidado;
6. depois aplicar o reranker local a todos os embeddings concluídos.

Não criar nova branch, PR, issue, repositório, auditoria, integração ou deploy. Use esta branch já existente e mantenha resultados localmente. Não faça commit nem push adicionais.

## Repositório

- local: `/home/alpha/Playstoria/models`
- remoto esperado: `Weltall-IA/holo-models`
- branch existente: `ai/download-all-before-full-benchmark-v1`

Preserve sem alteração os arquivos preexistentes não relacionados, inclusive:

- `benchmark/benchmark/`
- `benchmark/embedding-v3/run_voyage.py`
- `comandos.md`
- `runtime/vane-native-ops/`

Pesos e caches continuam fora do Git.

## Regra contra exclusão

Nenhum modelo desta ordem pode receber `enabled:false`, `optional`, `disabled`, `not applicable`, `blocked` como encerramento, nem ser retirado por preferência, licença, idioma, formato ou dificuldade de runtime.

Erro significa: diagnosticar, corrigir e repetir.

Não prossiga para o benchmark antes de todos os downloads das listas textual e VL estarem presentes e verificados.

## Lista textual obrigatória a verificar ou baixar

### Já existentes, mas ainda sem benchmark textual completo confiável

1. `gte_multilingual_base`
2. `KaLM-Embedding-Gemma3-12B-2511-i1-Q4_K_M`
3. `KaLM-Embedding-Gemma3-12B-2511-Q4_K_M`
4. `LFM2.5-Embedding-350M-Q4_K_M`
5. `Nemotron-3-Embed-8B-Abiray-Q4_K_M`
6. `Nemotron-3-Embed-8B-Aqua00-Q4_K_M`
7. `nomic-embed-text-v2-moe-Q4_K_M`
8. `snowflake-arctic-embed-l-v2.0-Q4_K_M`
9. `embeddinggemma/` — checkpoint Transformers nativo
10. `microsoft/bitnet-embedding-270m`
11. `microsoft/bitnet-embedding-0.6b`

Os dois Nemotron 8B desta tarefa são exclusivamente os dois Q4_K_M já baixados, Abiray e Aqua00. Não baixar Nemotron 8B BF16 ou FP16. Não baixar Nemotron 1B BF16.

### Adições obrigatórias

12. `ibm-granite/granite-embedding-311m-multilingual-r2`
13. `ibm-granite/granite-embedding-97m-multilingual-r2`
14. `jinaai/jina-embeddings-v5-text-small`
15. `ai-sage/Giga-Embeddings-instruct`

Registrar a licença, mas não excluir por licença. O Jina é somente para avaliação porque a licença é `CC-BY-NC-4.0`; ainda assim deve ser baixado e benchmarkado. Granite e Giga permanecem na comparação.

Não adicionar Qwen3-Embedding-4B, novos Nemotron BF16/FP16 ou qualquer modelo textual não listado nesta ordem.

## Baselines textuais já benchmarkados que também entram na nova rodada única

Reexecutar no mesmo ciclo, sem aproveitar o resultado antigo como substituto:

- `colibri_ptbr`
- `multilingual_e5_large_instruct`
- `qwen3_embedding_06`
- `bge_m3_dense`
- `voyage4_nano`
- `qwen3_embedding_8b_gguf`
- `embeddinggemma_gguf`
- `qwen3_embedding_06_gguf`
- `nemotron_3_embed_1b_nvfp4`
- `nemotron_3_embed_1b_q4_k_m_gguf`

`gte_multilingual_base` já está na lista obrigatória e deve ser reexecutado após correção do runtime.

Os resultados congelados de `voyage-4-large` e `voyage-context-4` podem aparecer somente como referência histórica separada. Não chamar API paga nesta tarefa.

## Lista VL — baixar agora, benchmark depois

Verificar e baixar, sem executar benchmark nesta fase:

1. `llama-nemotron-embed-vl-1b-v2-FP8`
2. exatamente as cinco variações `Qwen3-VL-Embedding-*` já solicitadas ou inventariadas localmente

Resolva os cinco nomes e repositórios exatos a partir do inventário e metadados existentes. Não invente uma sexta variação e não adicione outro VL.

Gerar uma lista final dos seis modelos VL com caminho, revisão, arquivos, tamanho e SHA-256. O benchmark VL será uma tarefa posterior.

## Fase 1 — Gate real de download

Para cada modelo textual e VL:

- localizar pesos já presentes;
- identificar repositório e revisão exatos;
- validar arquivos necessários, tamanho e SHA-256;
- baixar somente o que estiver ausente ou incompleto;
- usar download retomável;
- não apagar nem substituir pesos válidos existentes;
- não iniciar inferência ou smoke test nesta fase.

Gerar localmente:

`benchmark/embedding-v3/results/all_models_download_gate.json`

O arquivo deve listar cada modelo com apenas um destes estados:

- `PRESENT_VERIFIED`
- `DOWNLOADED_VERIFIED`
- `IN_PROGRESS`
- `ERROR_RETRYING`

Não existe estado final de desistência.

`download_gate_passed=true` somente quando todos os modelos textuais e todos os seis VL estiverem verificados.

## Política obrigatória de insistência

### Download

Em caso de erro:

1. confirmar repo, revisão e nome de arquivo;
2. retomar download parcial;
3. verificar autenticação Hugging Face quando necessária;
4. tentar `hf download`, snapshot download e mecanismo Xet compatível;
5. verificar espaço e integridade;
6. repetir até concluir ou até existir um impedimento externo que o usuário precise resolver, como aceitar licença gated.

Não continuar com subconjunto.

### Runtime

Depois de todos os downloads:

- usar runtime compatível com cada formato;
- criar ambiente ou build isolado quando necessário;
- não substituir nem quebrar o llama.cpp estável;
- para BitNet, preparar uma versão/build compatível com `TYPE_IQ4_NL_4_4`;
- para GTE, corrigir dependências/código customizado/CUDA; se CUDA continuar tecnicamente impossível, executar qualidade em CPU e registrar desempenho separadamente;
- para modelos com `trust_remote_code`, usar ambiente isolado e revisão fixada;
- para OOM, reduzir batch/contexto operacional sem truncar o texto de maneira diferente dos demais modelos e sem mudar os pesos;
- repetir carregamento e inferência até obter embeddings válidos, finitos e normalizados.

Não declarar modelo encerrado por erro de runtime.

## Fase 2 — Benchmark textual único

Começar somente após `download_gate_passed=true`.

Executar todos os modelos textuais desta ordem e todos os baselines listados em uma única rodada consolidada, usando:

- o mesmo corpus congelado de 600 documentos e 150 consultas;
- SHA-256 `8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b`;
- os prompts/prefixos oficiais de cada modelo;
- dimensão nativa;
- dimensão Matryoshka adicional somente quando oficialmente suportada, reportada como perfil separado;
- normalização recomendada;
- execução isolada e sequencial por perfil.

Os dois Nemotron 8B Q4_K_M devem ser executados e reportados separadamente, mesmo que os tensores sejam equivalentes.

Métricas mínimas por perfil:

- HitRate e Recall @1, @3, @5, @10, @20 e @50;
- MRR@10;
- nDCG@10;
- posição média e mediana do primeiro relevante;
- erro de negativo difícil;
- carga/startup;
- documentos/s e consultas/s;
- RAM e VRAM de pico;
- tempo total;
- revisão, formato, arquivo, hash, backend, dtype, dimensão, pooling, prompt e normalização.

Se um modelo falhar durante a rodada, corrija e reexecute esse modelo. Não remova o modelo e não publique ranking incompleto.

## Fase 3 — Reranker local em todos

Depois de todos os embeddings textuais concluírem:

- aplicar `Qwen3-Reranker-0.6B` local a cada perfil;
- preservar top 50 e reranquear top 20;
- usar os mesmos textos e a mesma instrução;
- registrar HitRate, MRR, nDCG, rescue e damage;
- não excluir nenhum modelo.

## Saída final

Gerar um único relatório claro com:

1. lista de downloads textuais e VL, todos verificados;
2. ranking de qualidade sem reranker;
3. ranking de qualidade com reranker local;
4. ranking de velocidade;
5. ranking de RAM/VRAM;
6. melhor qualidade absoluta;
7. melhor opção totalmente local prática;
8. melhor modelo leve;
9. limitações de licença, separadas da qualidade;
10. lista pronta dos seis VL para o benchmark posterior.

Não criar PR, não fazer merge e não iniciar integração de aplicação.

## Retorno curto no chat

Retorne somente:

- downloads textuais: `verificados/total`;
- downloads VL: `verificados/6`;
- download gate: `PASS/EM_ANDAMENTO`;
- runtime corrigido para todos: `SIM/NÃO`;
- benchmark textual iniciado: `SIM/NÃO`;
- benchmark textual concluído: `concluídos/total`;
- reranker concluído: `concluídos/total`;
- caminho do relatório final;
- único impedimento externo que ainda dependa do usuário, se existir.