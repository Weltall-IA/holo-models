# Embedding v3 — Holo text retrieval

Este é um estágio separado do benchmark de rerankers. Todos os seis modelos foram medidos novamente no mesmo corpus congelado, sem reutilizar rankings ou scores históricos.

## Protocolo

| Campo | Valor |
|---|---|
| Corpus | `holo_fake_scenes_v3` |
| Documentos | 600 |
| Queries | 150 |
| Idioma disponível | PT-BR |
| Inglês | N/A — não existe no corpus congelado |
| Ranking | corpus inteiro, 600 documentos |
| Similaridade | cosseno após normalização L2 |
| Labels | `query_type`; não há code/docs/tools/agent |
| Visual | não executado; benchmark versionado é texto-only |
| SHA-256 corpus | `8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b` |

As implementações de retrieval assimétrico usam `encode_query`/`encode_document` quando fornecidas pelo modelo. O Qwen3 usa o `prompt_name="query"` oficial; o Gemma usa o backend llama.cpp existente com pooling mean e os templates versionados.

## Resultados medidos

| Modelo | Dim | NDCG@10 | MRR@10 | MAP | Hit@1 | R@10 | R@20 | R@50 | VRAM MiB | RAM MiB | p50 batch s | p95 batch s | q/s | total s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| lightonai-mDenseOn | 768 | 0.7422 | 0.7249 | 0.7246 | 0.6667 | 0.8167 | 0.9267 | 0.9533 | 1402.1 | 2388.6 | 0.180 | 0.191 | 7.171 | 20.918 |
| embeddinggemma-300m | 768 | 0.7395 | 0.7123 | 0.7118 | 0.6267 | 0.8433 | 0.9600 | 1.0000 | 524.0 | 1310.4 | 0.149 | 0.401 | 13.317 | 11.264 |
| WeMM-Embedding-2B | 2048 | 0.7261 | 0.6976 | 0.6980 | 0.6267 | 0.8367 | 0.9600 | 1.0000 | 5498.9 | 6445.1 | 0.241 | 0.257 | 2.415 | 62.121 |
| jina-v5-omni-small | 1024 | 0.7059 | 0.6752 | 0.6782 | 0.5867 | 0.8167 | 0.9833 | 1.0000 | 3862.3 | 4777.5 | 0.178 | 0.186 | 2.915 | 51.452 |
| Qwen3-Embedding-4B | 2560 | 0.7025 | 0.6656 | 0.6688 | 0.5600 | 0.8300 | 1.0000 | 1.0000 | 7904.3 | 5808.2 | 0.194 | 0.208 | 1.590 | 94.358 |
| Nemotron-Embedding | 2048 | 0.4294 | 0.3511 | 0.3650 | 0.2400 | 0.6900 | 0.8400 | 0.8933 | 9464.0 | 5867.4 | 0.166 | 0.177 | 1.726 | 86.920 |

## WeMM contra comparadores

| Comparador | Delta WeMM NDCG@10 | Delta WeMM MRR@10 | Resultado textual |
|---|---:|---:|---|
| lightonai-mDenseOn | -0.0161 | -0.0274 | WeMM abaixo no NDCG@10 |
| jina-v5-omni-small | +0.0201 | +0.0224 | WeMM acima no NDCG@10 |
| Qwen3-Embedding-4B | +0.0235 | +0.0320 | WeMM acima no NDCG@10 |
| Nemotron-Embedding | +0.2966 | +0.3465 | WeMM acima no NDCG@10 |

## Por query type

| Query type | Modelo | NDCG@10 | MRR@10 | MAP | R@10 |
|---|---|---:|---:|---:|---:|
| character_name | lightonai-mDenseOn | 0.1726 | 0.1239 | 0.1667 | 0.3333 |
| character_name | embeddinggemma-300m | 0.1602 | 0.0867 | 0.1249 | 0.4000 |
| character_name | WeMM-Embedding-2B | 0.1325 | 0.0889 | 0.1406 | 0.2667 |
| character_name | jina-v5-omni-small | 0.1202 | 0.0750 | 0.1178 | 0.2667 |
| character_name | Qwen3-Embedding-4B | 0.1535 | 0.0972 | 0.1374 | 0.3333 |
| character_name | Nemotron-Embedding | 0.1246 | 0.0630 | 0.1120 | 0.3333 |
| context_dependency | lightonai-mDenseOn | 0.5490 | 0.5833 | 0.5531 | 0.5500 |
| context_dependency | embeddinggemma-300m | 0.4888 | 0.5028 | 0.4799 | 0.5500 |
| context_dependency | WeMM-Embedding-2B | 0.5590 | 0.5870 | 0.5610 | 0.5833 |
| context_dependency | jina-v5-omni-small | 0.5156 | 0.5333 | 0.5221 | 0.5500 |
| context_dependency | Qwen3-Embedding-4B | 0.5511 | 0.5778 | 0.5691 | 0.5500 |
| context_dependency | Nemotron-Embedding | 0.3585 | 0.2844 | 0.2942 | 0.6167 |
| emotion_intention | lightonai-mDenseOn | 0.9262 | 0.9000 | 0.9000 | 1.0000 |
| emotion_intention | embeddinggemma-300m | 0.9409 | 0.9200 | 0.9200 | 1.0000 |
| emotion_intention | WeMM-Embedding-2B | 0.9209 | 0.8933 | 0.8933 | 1.0000 |
| emotion_intention | jina-v5-omni-small | 0.8434 | 0.7900 | 0.7900 | 1.0000 |
| emotion_intention | Qwen3-Embedding-4B | 0.7988 | 0.7300 | 0.7300 | 1.0000 |
| emotion_intention | Nemotron-Embedding | 0.4881 | 0.3838 | 0.3911 | 0.8400 |
| exact_phrase | lightonai-mDenseOn | 0.8431 | 0.8250 | 0.8317 | 0.9000 |
| exact_phrase | embeddinggemma-300m | 0.7339 | 0.6458 | 0.6458 | 1.0000 |
| exact_phrase | WeMM-Embedding-2B | 0.9000 | 0.8667 | 0.8667 | 1.0000 |
| exact_phrase | jina-v5-omni-small | 0.7095 | 0.6158 | 0.6158 | 1.0000 |
| exact_phrase | Qwen3-Embedding-4B | 0.7464 | 0.6643 | 0.6643 | 1.0000 |
| exact_phrase | Nemotron-Embedding | 0.2746 | 0.2042 | 0.2365 | 0.5000 |
| indirect_dialogue | lightonai-mDenseOn | 0.9645 | 0.9550 | 0.9550 | 1.0000 |
| indirect_dialogue | embeddinggemma-300m | 0.9815 | 0.9750 | 0.9750 | 1.0000 |
| indirect_dialogue | WeMM-Embedding-2B | 0.8046 | 0.7433 | 0.7433 | 1.0000 |
| indirect_dialogue | jina-v5-omni-small | 0.8627 | 0.8167 | 0.8167 | 1.0000 |
| indirect_dialogue | Qwen3-Embedding-4B | 0.8455 | 0.7933 | 0.7933 | 1.0000 |
| indirect_dialogue | Nemotron-Embedding | 0.4200 | 0.3515 | 0.3644 | 0.6500 |
| semantic_event | lightonai-mDenseOn | 0.9085 | 0.8779 | 0.8779 | 1.0000 |
| semantic_event | embeddinggemma-300m | 0.9034 | 0.8717 | 0.8717 | 1.0000 |
| semantic_event | WeMM-Embedding-2B | 0.9024 | 0.8704 | 0.8704 | 1.0000 |
| semantic_event | jina-v5-omni-small | 0.9106 | 0.8896 | 0.8914 | 0.9750 |
| semantic_event | Qwen3-Embedding-4B | 0.9017 | 0.8698 | 0.8698 | 1.0000 |
| semantic_event | Nemotron-Embedding | 0.6299 | 0.5528 | 0.5595 | 0.8750 |
| similar_scene | lightonai-mDenseOn | 0.5049 | 0.4417 | 0.4562 | 0.7000 |
| similar_scene | embeddinggemma-300m | 0.7226 | 0.6643 | 0.6672 | 0.9000 |
| similar_scene | WeMM-Embedding-2B | 0.5938 | 0.5010 | 0.5076 | 0.9000 |
| similar_scene | jina-v5-omni-small | 0.6762 | 0.6333 | 0.6408 | 0.8000 |
| similar_scene | Qwen3-Embedding-4B | 0.6131 | 0.5500 | 0.5634 | 0.8000 |
| similar_scene | Nemotron-Embedding | 0.3244 | 0.2411 | 0.2429 | 0.6000 |

## PT-BR e EN

- PT-BR: medido no corpus completo de 150 queries.
- EN: `N/A / não disponível` neste benchmark versionado.
- Code/docs/tools/agent: `N/A / não disponível` como labels; o corpus fornece apenas `query_type`.

## Eficiência

| Modelo | NDCG@10/GiB VRAM | NDCG@10/p50 batch s |
|---|---:|---:|
| lightonai-mDenseOn | 0.5420 | 4.1232 |
| embeddinggemma-300m | 1.4451 | 4.9617 |
| WeMM-Embedding-2B | 0.1352 | 3.0150 |
| jina-v5-omni-small | 0.1872 | 3.9711 |
| Qwen3-Embedding-4B | 0.0910 | 3.6265 |
| Nemotron-Embedding | 0.0465 | 2.5887 |

- Melhor qualidade/VRAM: **embeddinggemma-300m**.
- Melhor qualidade/latência: **embeddinggemma-300m**.
- Esses índices são informativos de custo; não alteram o ranking de qualidade.

## Respostas

1. WeMM supera o mDenseOn no Holo? **Não**: NDCG@10 0.7261 vs 0.7422; MRR@10 0.6976 vs 0.7249.
2. Supera Jina v5 e Qwen3-Embedding-4B? **Sim nos pontos medidos**: supera Jina em NDCG +0.0201 e Qwen3 em +0.0235.
3. Como fica em PT-BR? **MRR@10 0.6976, NDCG@10 0.7261** no corpus PT-BR.
4. Custo? **5498.9 MiB VRAM, 6445.1 MiB RAM, p50 de batch 0.241s**.
5. Substitui o embedding atual? **Não para texto neste corpus**. O resultado textual não justifica substituir mDenseOn; a modalidade multimodal permanece uma opção a validar separadamente com corpus visual versionado.

## Proveniência

- Resultados brutos por modelo: diretórios `*/result.json`, `*/rankings.json` e `*/embeddings.npz` ao lado deste relatório.
- Manifesto da execução: `RUN_MANIFEST.json`.
- Nenhum score histórico ou projetado foi usado como medição.
