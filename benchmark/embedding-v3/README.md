# Benchmark de embeddings e reranking v3

Implementação versionada dos Gates 0, 1, 2 e 3 do benchmark do Projeto Holo.

## Segurança

- pesos e caches permanecem fora do Git;
- nenhuma API paga é chamada nos Gates 2 ou 3;
- o corpus congelado não pode ser regenerado;
- cada modelo é executado em processo isolado;
- falha CUDA, OOM, erro de modelo ou falha do `llama-server` não interrompe os modelos seguintes;
- Gates 4 a 6 permanecem bloqueados até autorização explícita.

## Estado das tarefas

- Gates 0 e 1: `.ai/tasks/EMBED-BENCH-V3-1.1/STATUS.yml`;
- Gate 2: `.ai/tasks/EMBED-BENCH-V3-1.2/STATUS.yml`;
- Gate 3: `.ai/tasks/EMBED-BENCH-V3-1.3/STATUS.yml`.

## Gate 2 — modelos locais compactos

Obrigatórios para aprovação:

1. `tardellirs/colibri-embed-ptbr`;
2. `intfloat/multilingual-e5-large-instruct`;
3. `Qwen/Qwen3-Embedding-0.6B`;
4. `BAAI/bge-m3` em modo denso.

O Voyage Nano foi executado como opcional e reproduzido com `transformers==4.57.6`. Os BitNet 270M e 0.6B foram tentados, mas os GGUF legados são incompatíveis com o llama.cpp 9972 por usarem o tipo removido `TYPE_IQ4_NL_4_4`.

O Gate 2 canônico permanece `PASS`.

## Gate 3 — embeddings GGUF no llama.cpp

O Gate 3 histórico mediu:

1. `Qwen/Qwen3-Embedding-8B-GGUF` em `Q8_0`;
2. `ggml-org/embeddinggemma-300M-GGUF` em `Q8_0`;
3. `Qwen/Qwen3-Embedding-0.6B-GGUF` em `Q8_0`.

A execução completa exige:

- Gates 0, 1 e 2 em `PASS`;
- corpus completo de 600 documentos e 150 consultas;
- dispositivo CUDA;
- revisão imutável, licença, arquivo GGUF, tamanho e SHA-256 registrados;
- modelo executado em processo e servidor isolados;
- versão do `llama-server`, pooling, quantização, dimensão, throughput e pico de VRAM registrados.

Qwen3 usa pooling no último token não preenchido, instrução apenas na consulta e normalização L2. O modelo 8B retorna até 4096 dimensões e suporta Matryoshka. Qualquer redução dimensional deve usar o prefixo do vetor e nova normalização L2.

O resultado atual de `qwen3_embedding_8b_gguf` está em `AUDIT_REQUIRED`: apesar de registrar peso Q8_0, hash, pooling `last`, dimensão 1024 e normalização L2, ficou abaixo do Qwen3 4B, contrariando a tendência oficial da família. A execução não preserva no artefato final a instrução exata aplicada às consultas nem um controle em 4096 dimensões. Até a auditoria, esse resultado e seu pipeline Qwen não participam de seleção operacional.

Uma seleção parcial com `--models`, execução em CPU ou recorte do corpus nunca conclui o Gate 3 como `PASS`. Diagnósticos parciais são gravados em `results/gate3/diagnostics/` sem substituir os artefatos canônicos.

## Política de quantização no host de 16 GB

Toda nova seleção de peso local segue esta ordem:

1. **NVFP4**, quando existir para o modelo exato, tiver proveniência confiável e runtime compatível;
2. **Q4**, preferencialmente `Q4_K_M`, quando não houver NVFP4 confiável;
3. **Q8** somente quando não houver NVFP4 nem Q4, o modelo for pequeno o bastante para caber com folga em 16 GB incluindo overhead do runtime, e a exceção estiver aprovada no contrato da rodada.

Modelos grandes não devem ser baixados ou retestados em Q8 apenas por maior precisão teórica. Na ausência de NVFP4/Q4 confiável, o perfil fica `BLOCKED`. Um NVFP4 de outra escala não pode ser reaproveitado por nome: o NVFP4 oficial do Nemotron 1B, por exemplo, não comprova um NVFP4 de 8B.

Resultados Q8 históricos continuam preservados como evidência. Eles não definem a quantização das próximas rodadas. O Qwen3 Embedding 8B será auditado em `Q4_K_M`; o Q8_0 antigo será apenas o controle histórico suspeito.

## Perfis Nemotron 1B admitidos

Os perfis `nvidia/Nemotron-3-Embed-1B-NVFP4` em vLLM e `zenmagnets/Nemotron-3-Embed-1B-Q4_K_M-GGUF` em llama.cpp permanecem separados no benchmark completo. A configuração canônica está em `config/nemotron_1b_profiles.json`; ambos usam o corpus congelado completo, prefixos `query: ` e `passage: `, pooling mean e normalização L2.

O NVFP4 deve ser executado somente com vLLM em ambiente isolado. O GGUF é o perfil de menor consumo e cold start; o NVFP4 é o perfil de maior throughput em lote no host medido. Resultados, limites e evidências da admissão estão em `NEMOTRON_AUDIT_1_0_5_REPORT.md`.

## Execução

```text
python benchmark.py --gate 2 --dry-run --device cuda --skip-api
python benchmark.py --gate 2 --device cuda --skip-api

python benchmark.py --gate 3 --dry-run --device cuda --skip-api
python benchmark.py --gate 3 --device cuda --batch-size 16 --skip-api
```

Opções relevantes:

```text
--models
--device
--batch-size
--model-timeout
--max-documents
--max-queries
```

## Resultados

Gate 2:

- manifesto resolvido: `download_manifest.resolved.json`;
- relatório: `GATE_2_REPORT.md`;
- resumo: `results/gate2/summary.json`;
- resultados por modelo: `results/gate2/<model-id>.json`;
- diagnósticos: `results/gate2/diagnostics/`.

Gate 3:

- manifesto resolvido: `download_manifest_gate3.resolved.json`;
- relatório: `GATE_3_REPORT.md`;
- resumo: `results/gate3/summary.json`;
- resultados por modelo: `results/gate3/<model-id>.json`;
- diagnósticos: `results/gate3/diagnostics/`.

Evidências temporárias de workers permanecem em `results/raw/` e são ignoradas pelo Git.

## Fonte canônica consolidada

Para inventário, ranking e comparação de embeddings e rerankers, consulte somente:

`ALL_BENCHMARK_RESULTS.json`

Os artefatos individuais em `results/reranker/pipelines/` continuam sendo a fonte autoritativa das métricas. Registros e relatórios anteriores foram movidos para `archive/superseded/`; os caminhos antigos contêm apenas avisos de compatibilidade e não devem ser usados como leaderboard.

## Registro canônico de qualidade dos embeddings

Esta seção é o registro humano canônico para decisões de reutilização dos embeddings medidos. Os números continuam vindo de `ALL_BENCHMARK_RESULTS.json` e dos artefatos individuais; esta seção registra interpretação, confiança e decisão operacional sem criar outro leaderboard ou registry paralelo.

Revisão desta classificação: **2026-07-29**.

As colunas não misturam protocolos:

- **MRR@10 sozinho** mede somente o embedding;
- **Melhor MRR@10 com reranker** mostra o melhor pipeline publicado para aquele perfil;
- `—` significa que a combinação não foi executada ou não possui resultado publicado;
- **Faixa A** identifica candidatos fortes; **B**, candidatos úteis; **C**, perfis de nicho ou dependentes de reranker;
- a faixa é específica do corpus Holo e não representa uma nota universal do modelo.

A verificação externa serve apenas como teste de coerência, porque MRR@10 do corpus Holo, médias MTEB e nDCG de outros benchmarks não são numericamente intercambiáveis. Foram consultados o [MTEB-BR](https://mteb-br.org/) e model cards oficiais no Hugging Face. Artificial Analysis não foi usado como critério decisório nesta revisão, porque a comparação precisa cobrir o mesmo modelo, quantização, dimensão, pooling e protocolo do artefato local.

### Tabela 1 — embeddings bons ou reutilizáveis

Entrar nesta tabela significa que o perfil pode continuar sendo considerado em novas comparações. Não significa que ele seja o perfil de produção atual.

| Perfil | MRR@10 sozinho | Melhor MRR@10 com reranker | Faixa | Confiança | Decisão |
|---|---:|---:|---|---|---|
| `nemotron_3_embed_1b_nvfp4` | 0.7753 | 0.8318 | A | alta | Melhor baseline local; vLLM/NVFP4; melhor pipeline atual usa NVIDIA Nemotron Rerank. |
| `voyage-4-large` | 0.7728 | — | A | média | API; resultado completo, sem pipeline sob o mesmo ID. |
| `voyage_4_large_1024_float32` | 0.7728 | 0.8261 | A | média | Variante histórica 1024/F32; melhor reranker Voyage 2.5. |
| `nemotron_3_embed_1b_q4_k_m_gguf` | 0.7695 | 0.7890 | A | alta | GGUF reproduzível; menor consumo e cold start; pipeline Qwen publicado. |
| `voyage4_nano_2048_int8` | 0.7681 | 0.8200 | A | média | Variante histórica INT8; desempenho forte. |
| `embeddinggemma` | 0.7562 | 0.8299 | A | alta | Resultado coerente com a família; melhor pipeline usa NVIDIA Nemotron Rerank. |
| `pplx_embed_v1_4b_q8_0` | 0.7562 | 0.8221 | A | média-alta | Resultado histórico válido; novas variantes seguem NVFP4/Q4 antes de Q8. |
| `voyage4_nano_2048_float32` | 0.7561 | 0.8195 | A | média | Variante histórica 2048/F32. |
| `voyage4_nano` | 0.7528 | 0.8223 | A | alta | Bom equilíbrio entre qualidade e custo. |
| `voyage4_nano_1024_float32` | 0.7528 | 0.8210 | A | média | Variante histórica 1024/F32. |
| `voyage-context-4` | 0.7433 | 0.7887 | A | média | API; baseline completo e pipeline Qwen recomposto offline. |
| `nomic_embed_text_v2_moe_q4` | 0.7420 | 0.8320 | A | alta | Escolha operacional validada; melhor pipeline usa NVIDIA Nemotron Rerank. |
| `embeddinggemma_768_float32` | 0.7389 | 0.8264 | A | média | Variante histórica; melhor pipeline histórico usa Voyage 2.5. |
| `embeddinggemma_gguf` | 0.7389 | 0.8198 | A | alta | Baixo consumo e resultado coerente. |
| `bge_m3_dense` | 0.7182 | 0.8067 | A | alta | Boa cobertura; modelo oficial recomenda híbrido com reranking. |
| `snowflake_arctic_embed_l_v2_q4` | 0.7113 | 0.8158 | A | média-alta | Resultado compatível com modelo multilíngue forte. |
| `qwen3_embedding_4b_q8_0` | 0.7010 | 0.8326 | A | alta | Melhor MRR@10 reranqueado publicado; novas seleções devem preferir NVFP4/Q4. |
| `colibri_ptbr` | 0.6966 | 0.8305 | B | alta | Especializado em PT-BR; forte com NVIDIA Nemotron Rerank. |
| `jina_embeddings_v5_text_small` | 0.6742 | 0.8216 | B | média-alta | Resultado compatível com MMTEB declarado pelo modelo. |
| `octen_embedding_8b_q8_0` | 0.6739 | 0.8154 | B | média | Resultado histórico; Q8 não deve ser repetido se houver Q4/NVFP4. |
| `granite_embedding_311m_r2` | 0.6709 | 0.8185 | B | média-alta | Opção compacta; ganho grande com NVIDIA Nemotron Rerank. |
| `pplx_embed_v1_06b_native` | 0.6633 | 0.8190 | B | média-alta | Compacto e forte com reranker. |
| `giga_embeddings_instruct` | 0.6467 | 0.8184 | B | média | Útil com instrução; suporte oficial é sobretudo russo/inglês. |
| `bidirlm_17b_embedding` | 0.6423 | 0.8190 | B | média-alta | Ordem relativa coerente com MTEB-BR. |
| `multilingual_e5_large_instruct` | 0.6329 | 0.8111 | B | alta | Requer instrução de consulta; forte com reranker. |
| `qwen3_embedding_06` | 0.6163 | 0.8066 | C | alta | Baseline modesto; útil com reranker. |
| `qwen3_embedding_06_gguf` | 0.6153 | 0.7477 | C | alta | Q8 histórico aceitável pelo tamanho pequeno; controle GGUF coerente. |
| `lfm_25_embedding_350m_q4_k_m_official` | 0.6085 | 0.7768 | C | alta | Reexecução oficial com CLS e prefixos corretos; reutilizável com Qwen. |
| `gte_multilingual_base` | 0.5676 | 0.8109 | C | alta | Baseline fraco no corpus, mas pipeline útil e fonte oficial forte. |
| `granite_embedding_97m_r2` | 0.5631 | 0.7890 | C | média-alta | Muito rápido; manter apenas para perfil leve/reranqueado. |

### Tabela 2 — blacklist de artefatos e configurações

A blacklist é aplicada ao **ID, peso, quantização e configuração testados**. Ela só deve ser promovida para toda a família do modelo após execuções independentes e reproduzíveis confirmarem o problema. Resultados suspeitos não devem participar de ranking, seleção de produção ou comparação histórica como se fossem válidos.

| Perfil local | MRR@10 | Estado | Motivo | Condição para reabilitação |
|---|---:|---|---|---|
| `qwen3_embedding_8b_gguf` | 0.6920 | `AUDIT_REQUIRED` | O Q8_0 8B ficou abaixo do 4B; faltam controle dimensional e instrução exata no artefato. | Reexecutar em Q4_K_M, com instrução oficial registrada, 4096 e 1024 dimensões e cache novo. Não repetir Q8_0. |
| `nemotron_8b_abiray_q4` | 0.6919 | `BLACKLIST_PROVISÓRIA` | Candidates e métricas idênticos ao Aqua00; sem hash, runtime, pooling, dimensão ou comando. | Reexecutar do zero em NVFP4 comprovadamente 8B; na ausência, Q4_K_M. Q8 é proibido. |
| `nemotron_8b_aqua00_q4` | 0.6919 | `BLACKLIST_PROVISÓRIA` | Candidates e métricas idênticos ao Abiray; proveniência insuficiente. | Reexecutar do zero em NVFP4 comprovadamente 8B; na ausência, Q4_K_M. Q8 é proibido. |
| `lfm_25_embedding_350m_q4` | 0.4947 | `BLACKLIST_DO_ARTEFATO` | Artefato antigo não prova prefixos nem pooling CLS; a execução oficial corrigida usa outro ID e permanece na Tabela 1. | Não reabilitar este artefato. Reutilizar somente lfm_25_embedding_350m_q4_k_m_official ou uma nova execução equivalente. |
| `kalm_embedding_gemma3_12b_q4` | 0.1969 | `BLACKLIST_DO_ARTEFATO` | Resultado incompatível com o topo do MTEB-BR; metadados de execução ausentes. | Reexecução reproduzível em NVFP4 confiável ou Q4 com instruções e pooling oficiais. |
| `kalm_embedding_gemma3_12b_i1_q4` | 0.1766 | `BLACKLIST_DO_ARTEFATO` | Execução local catastrófica e sem proveniência suficiente. | Reexecução reproduzível; não herdar o resultado do outro Q4. |
| `boom_4b_v1_q8_0` | 0.1616 | `BLACKLIST_DO_ARTEFATO` | Q8 local indica configuração ou artefato inválido para uma família externamente forte. | Reexecutar em NVFP4 ou Q4, com last-token pooling, instrução e hash do peso. Não repetir Q8. |
| `bitnet_270m_current` | 0.3015 | `GATE_FAIL` | Execução completa e reproduzível, mas qualidade insuficiente: HR@50 0,8467 e alta taxa de erro em hard negatives. | Novo peso, runtime ou protocolo precisa superar o gate completo; não promover este artefato. |
| `bitnet_06b_current` | 0.2089 | `GATE_FAIL` | Execução completa e reproduzível, mas qualidade insuficiente: HR@50 0,7667. | Novo peso, runtime ou protocolo precisa superar o gate completo; não promover este artefato. |

### Leitura das inconsistências externas

A Qwen publica o 8B acima do 4B em MTEB multilíngue, inglês e chinês. O resultado local inverteu essa ordem e, portanto, passou a exigir auditoria. O Q8_0 atual fica preservado somente como evidência histórica; a auditoria usará o Q4_K_M oficial e comparará 4096 contra 1024 dimensões com a instrução exata registrada.

O MTEB-BR coloca KaLM 12B, Octen 8B, Qwen3 4B, BidirLM, BOOM 4B e EmbeddingGemma entre modelos competitivos em português. A ordem relativa de Qwen3 4B, Octen, BidirLM, Voyage e EmbeddingGemma é compatível o bastante com o benchmark Holo. KaLM e BOOM, porém, apresentaram resultados locais catastroficamente inferiores à avaliação externa; os artefatos locais foram bloqueados em vez de a família inteira ser declarada ruim.

O model card oficial do LFM2.5 exige embedding CLS, similaridade cosseno e prefixos assimétricos `query: ` e `document: `. Como o artefato local não registra que esse protocolo foi seguido e ficou muito abaixo da expectativa oficial, ele permanece bloqueado até reexecução.

Os dois Nemotron 8B ficam bloqueados por proveniência: candidates, métricas sem reranker e métricas com Qwen são idênticos, enquanto os artefatos não registram hashes dos pesos, runtime, pooling, dimensão, normalização ou comando. A auditoria deve preferir NVFP4 somente se o arquivo for comprovadamente um modelo 8B; na ausência, deve usar `Q4_K_M`. O NVFP4 oficial publicado pela NVIDIA é de 1B e não pode ser confundido com um artefato 8B.

### Fontes externas de coerência

- [MTEB-BR — benchmark nativo de português brasileiro](https://mteb-br.org/)
- [Qwen3 Embedding 8B](https://huggingface.co/Qwen/Qwen3-Embedding-8B)
- [Qwen3 Embedding 8B GGUF](https://huggingface.co/Qwen/Qwen3-Embedding-8B-GGUF)
- [EmbeddingGemma](https://huggingface.co/google/embeddinggemma-300m)
- [Nemotron 3 Embed — coleção oficial](https://huggingface.co/collections/nvidia/nemotron-3-embed)
- [Nemotron 3 Embed 1B](https://huggingface.co/nvidia/Nemotron-3-Embed-1B-BF16)
- [Nemotron 3 Embed 8B BF16](https://huggingface.co/nvidia/Nemotron-3-Embed-8B-BF16)
- [Nomic Embed Text v2 MoE](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe)
- [BGE-M3](https://huggingface.co/BAAI/bge-m3)
- [Snowflake Arctic Embed L v2](https://huggingface.co/Snowflake/snowflake-arctic-embed-l-v2.0)
- [Jina Embeddings v5 Small](https://huggingface.co/jinaai/jina-embeddings-v5-text-small)
- [PPLX Embed v1](https://huggingface.co/perplexity-ai/pplx-embed-v1-4b)
- [Octen Embedding 8B](https://huggingface.co/Octen/Octen-Embedding-8B)
- [LFM2.5 Embedding 350M](https://huggingface.co/LiquidAI/LFM2.5-Embedding-350M)
- [KaLM Embedding Gemma3 12B](https://huggingface.co/tencent/KaLM-Embedding-Gemma3-12B-2511)
- [BOOM 4B v1](https://huggingface.co/ICT-TIME-and-Querit/BOOM_4B_v1)

### Regra de manutenção

Não criar novos arquivos de leaderboard, tabela de bons, blacklist, registry ou resumo para embeddings. Atualizações futuras devem:

1. gravar métricas reais nos artefatos existentes e no consolidado canônico;
2. atualizar somente as duas tabelas desta seção;
3. preservar baseline e reranking em colunas distintas;
4. registrar o ID exato do perfil e a confiança da evidência;
5. bloquear o artefato, não a família, quando a execução for suspeita;
6. não ranquear modelos bloqueados ou sem métricas;
7. consultar `AGENTS.md` nesta pasta antes de alterar qualquer resultado ou tabela.
