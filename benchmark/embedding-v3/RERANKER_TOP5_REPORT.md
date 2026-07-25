# RERANKER_TOP5 — Relatório de Sessão

## Resumo

Sessão de reranking local aplicada aos 5 melhores embeddings brutos selecionados por MRR@10.
Candidatos top 50 reutilizados. Embeddings não recalculados. Nenhuma chamada paga a API externa.

## Embeddings selecionados

| # | Modelo | MRR@10 (raw) | HR@10 | nDCG@10 |
|---|--------|-------------|-------|---------|
| 1 | embeddinggemma | 0.7562 | 0.8600 | 0.7739 |
| 2 | pplx_embed_v1_4b_q8_0 | 0.7562 | 0.8600 | 0.7778 |
| 3 | voyage4_nano | 0.7528 | 0.8533 | 0.7719 |
| 4 | nomic_embed_text_v2_moe_q4 | 0.7420 | 0.8333 | 0.7562 |
| 5 | embeddinggemma_gguf | 0.7389 | 0.8600 | 0.7609 |

## Rerankers locais

| Reranker | Tipo | Modelo |
|----------|------|--------|
| qwen_local | CrossEncoder | Qwen3-Reranker-0.6B |
| kalm_reranker_v1_nano | EncoderDecoder | KaLM-Reranker-V1-Nano |
| kalm_reranker_v1_small | EncoderDecoder | KaLM-Reranker-V1-Small |
| jina_reranker_v3_noncommercial | CausalLM+Projector | jina-reranker-v3 |
| querit_reranker_4b | CausalLM+Head | Querit-4B |

## Ranking completo por MRR@10

| Rank | Pipeline | MRR@10 | HR@10 | nDCG@10 | Hit@1 |
|------|----------|--------|-------|---------|-------|
|  1 | nomic_embed_text_v2_moe_q4__qwen_local                       | 0.8229 | 0.8800 | 0.8290 | 0.7933 |
|  2 | voyage4_nano__qwen_local                                     | 0.8223 | 0.8867 | 0.8303 | 0.7867 |
|  3 | pplx_embed_v1_4b_q8_0__qwen_local                            | 0.8221 | 0.8800 | 0.8282 | 0.7933 |
|  4 | embeddinggemma_gguf__qwen_local                              | 0.8198 | 0.8933 | 0.8295 | 0.7867 |
|  5 | embeddinggemma__qwen_local                                   | 0.8197 | 0.8933 | 0.8294 | 0.7867 |
|  6 | pplx_embed_v1_4b_q8_0__kalm_reranker_v1_small                | 0.8136 | 0.8800 | 0.8215 | 0.7867 |
|  7 | nomic_embed_text_v2_moe_q4__jina_reranker_v3_noncommercial   | 0.8132 | 0.8667 | 0.8183 | 0.7867 |
|  8 | embeddinggemma__kalm_reranker_v1_small                       | 0.8116 | 0.8733 | 0.8183 | 0.7867 |
|  9 | embeddinggemma_gguf__kalm_reranker_v1_small                  | 0.8116 | 0.8733 | 0.8183 | 0.7867 |
| 10 | nomic_embed_text_v2_moe_q4__kalm_reranker_v1_small           | 0.8097 | 0.8800 | 0.8185 | 0.7800 |
| 11 | pplx_embed_v1_4b_q8_0__jina_reranker_v3_noncommercial        | 0.8065 | 0.8733 | 0.8145 | 0.7800 |
| 12 | voyage4_nano__jina_reranker_v3_noncommercial                 | 0.7964 | 0.8667 | 0.8059 | 0.7533 |
| 13 | embeddinggemma_gguf__jina_reranker_v3_noncommercial          | 0.7952 | 0.8667 | 0.8044 | 0.7600 |
| 14 | embeddinggemma__jina_reranker_v3_noncommercial               | 0.7919 | 0.8600 | 0.8007 | 0.7533 |
| 15 | nomic_embed_text_v2_moe_q4__kalm_reranker_v1_nano            | 0.7596 | 0.8533 | 0.7745 | 0.7133 |
| 16 | embeddinggemma__kalm_reranker_v1_nano                        | 0.7588 | 0.8533 | 0.7738 | 0.7133 |
| 17 | embeddinggemma_gguf__kalm_reranker_v1_nano                   | 0.7582 | 0.8533 | 0.7733 | 0.7133 |
| 18 | pplx_embed_v1_4b_q8_0__kalm_reranker_v1_nano                 | 0.7572 | 0.8533 | 0.7725 | 0.7133 |
| 19 | nomic_embed_text_v2_moe_q4__querit_reranker_4b               | 0.0053 | 0.0333 | 0.0115 | 0.0000 |
| 20 | voyage4_nano__querit_reranker_4b                             | 0.0049 | 0.0267 | 0.0098 | 0.0000 |
| 21 | pplx_embed_v1_4b_q8_0__querit_reranker_4b                    | 0.0034 | 0.0200 | 0.0072 | 0.0000 |
| 22 | embeddinggemma__querit_reranker_4b                           | 0.0030 | 0.0133 | 0.0053 | 0.0000 |
| 23 | embeddinggemma_gguf__querit_reranker_4b                      | 0.0030 | 0.0133 | 0.0053 | 0.0000 |
| 24 | voyage4_nano__kalm_reranker_v1_nano                          | 0.0014 | 0.0133 | 0.0032 | 0.0000 |
| 25 | voyage4_nano__kalm_reranker_v1_small                         | 0.0007 | 0.0067 | 0.0012 | 0.0000 |

## Análise

### Top pipelines por reranker

**qwen_local (Qwen3-Reranker-0.6B):**
Todos os 5 embeddings atingem MRR > 0.81. O qwen_local é consistentemente o melhor reranker.

**kalm_reranker_v1_nano e v1_small:**
Scores muito baixos (MRR < 0.01). O scoring P(no)-P(yes) com ascending sort produz ranking invertido.
Estes modelos requerem investigação adicional sobre o protocolo de scoring.

**jina_reranker_v3_noncommercial:**
Performance sólida (MRR > 0.79). Segundo melhor reranker local.

**querit_reranker_4b:**
Scores baixos (MRR < 0.03). Mesmo problema de scoring invertido dos KaLM.

### Melhor pipeline global

**nomic_embed_text_v2_moe_q4__qwen_local**

MRR@10 = 0.8229, HR@10 = 0.8800, nDCG@10 = 0.8290, Hit@1 = 0.7933

### Conclusão

- 25/25 pipelines executados (5 embeddings × 5 rerankers)
- Candidatos top 50 reutilizados de sessões anteriores
- Nenhum embedding recalculado
- Nenhuma chamada API paga realizada
- Voyage rerank-2.5 existente (5 variantes) reutilizado sem novas chamadas

