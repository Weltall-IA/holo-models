# RERANKER_TOP5 — Relatório de Sessão

## Resumo

Sessão de reranking local aplicada às 5 melhores famílias de embeddings selecionadas por MRR@10
após colapso por família (mantido modelo nativo de cada família). Candidatos top 50 reutilizados.
Embeddings não recalculados. Nenhuma chamada paga a API externa.

## Famílias colapsadas

| Família | Modelos | Seleção final |
|---------|---------|---------------|
| gemma | embeddinggemma (native), embeddinggemma_gguf (GGUF) | embeddinggemma (native) |
| perplexity | pplx_embed_v1_06b_native, pplx_embed_v1_4b_q8_0 | pplx_embed_v1_4b_q8_0 (4B) |
| voyage | voyage4_nano (API) | Excluída (dependência de API) |
| nomic | nomic_embed_text_v2_moe_q4 | nomic_embed_text_v2_moe_q4 |
| bge | bge_m3_dense | bge_m3_dense |
| snowflake | snowflake_arctic_embed_l_v2_q4 | snowflake_arctic_embed_l_v2_q4 |

## Embeddings selecionados

| # | Modelo | Família | MRR@10 (raw) | HR@10 | nDCG@10 |
|---|--------|---------|-------------|-------|---------|
| 1 | embeddinggemma | gemma | 0.7562 | 0.8600 | 0.7739 |
| 2 | pplx_embed_v1_4b_q8_0 | perplexity | 0.7562 | 0.8600 | 0.7778 |
| 3 | nomic_embed_text_v2_moe_q4 | nomic | 0.7420 | 0.8333 | 0.7562 |
| 4 | bge_m3_dense | bge | 0.7182 | 0.8800 | 0.7490 |
| 5 | snowflake_arctic_embed_l_v2_q4 | snowflake | 0.7113 | 0.8600 | 0.7394 |

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
|  1 | nomic_embed_text_v2_moe_q4__qwen_local                            | 0.8229 | 0.8800 | 0.8290 | 0.7933 |
|  2 | pplx_embed_v1_4b_q8_0__qwen_local                                 | 0.8221 | 0.8800 | 0.8282 | 0.7933 |
|  3 | embeddinggemma__qwen_local                                        | 0.8197 | 0.8933 | 0.8294 | 0.7867 |
|  4 | snowflake_arctic_embed_l_v2_q4__qwen_local                        | 0.8158 | 0.8733 | 0.8220 | 0.7867 |
|  5 | pplx_embed_v1_4b_q8_0__kalm_reranker_v1_small                     | 0.8136 | 0.8800 | 0.8215 | 0.7867 |
|  6 | nomic_embed_text_v2_moe_q4__jina_reranker_v3_noncommercial        | 0.8132 | 0.8667 | 0.8183 | 0.7867 |
|  7 | embeddinggemma__kalm_reranker_v1_small                             | 0.8116 | 0.8733 | 0.8183 | 0.7867 |
|  8 | nomic_embed_text_v2_moe_q4__kalm_reranker_v1_small                | 0.8097 | 0.8800 | 0.8185 | 0.7800 |
|  9 | bge_m3_dense__qwen_local                                          | 0.8067 | 0.8733 | 0.8150 | 0.7733 |
| 10 | pplx_embed_v1_4b_q8_0__jina_reranker_v3_noncommercial             | 0.8065 | 0.8733 | 0.8145 | 0.7800 |
| 11 | snowflake_arctic_embed_l_v2_q4__kalm_reranker_v1_small             | 0.8019 | 0.8667 | 0.8094 | 0.7733 |
| 12 | bge_m3_dense__kalm_reranker_v1_small                               | 0.8009 | 0.8667 | 0.8087 | 0.7733 |
| 13 | embeddinggemma__jina_reranker_v3_noncommercial                     | 0.7919 | 0.8600 | 0.8007 | 0.7533 |
| 14 | bge_m3_dense__jina_reranker_v3_noncommercial                       | 0.7901 | 0.8600 | 0.7988 | 0.7600 |
| 15 | snowflake_arctic_embed_l_v2_q4__jina_reranker_v3_noncommercial     | 0.7886 | 0.8600 | 0.7980 | 0.7533 |
| 16 | nomic_embed_text_v2_moe_q4__kalm_reranker_v1_nano                 | 0.7596 | 0.8533 | 0.7745 | 0.7133 |
| 17 | embeddinggemma__kalm_reranker_v1_nano                              | 0.7588 | 0.8533 | 0.7738 | 0.7133 |
| 18 | pplx_embed_v1_4b_q8_0__kalm_reranker_v1_nano                      | 0.7572 | 0.8533 | 0.7725 | 0.7133 |
| 19 | snowflake_arctic_embed_l_v2_q4__kalm_reranker_v1_nano              | 0.7550 | 0.8467 | 0.7693 | 0.7133 |
| 20 | bge_m3_dense__kalm_reranker_v1_nano                                | 0.7474 | 0.8400 | 0.7618 | 0.7067 |
| 21 | snowflake_arctic_embed_l_v2_q4__querit_reranker_4b                | 0.2198 | 0.5400 | 0.2938 | 0.1200 |
| 22 | bge_m3_dense__querit_reranker_4b                                   | 0.2195 | 0.6067 | 0.3074 | 0.0933 |
| 23 | pplx_embed_v1_4b_q8_0__querit_reranker_4b                         | 0.2106 | 0.5533 | 0.2880 | 0.0800 |
| 24 | nomic_embed_text_v2_moe_q4__querit_reranker_4b                    | 0.1995 | 0.5733 | 0.2854 | 0.0733 |
| 25 | embeddinggemma__querit_reranker_4b                                 | 0.1985 | 0.6000 | 0.2888 | 0.0733 |

## Análise

### Top pipelines por reranker

**qwen_local (Qwen3-Reranker-0.6B):**
Todos os 5 embeddings atingem MRR > 0.80. O qwen_local é consistentemente o melhor reranker.
Melhor combinação: nomic + qwen_local (MRR 0.8229).

**kalm_reranker_v1_small (KaLM-Reranker-V1-Small):**
Performance sólida (MRR 0.80-0.81). Segundo melhor reranker.
Notavelmente, pplx + kalm_small supera pplx + jina.

**jina_reranker_v3_noncommercial:**
Performance sólida (MRR 0.79-0.81). Terceiro melhor reranker.
Melhor com nomic (MRR 0.8132).

**kalm_reranker_v1_nano (KaLM-Reranker-V1-Nano):**
Performance moderada (MRR 0.74-0.76). Útil como alternativa leve.

**querit_reranker_4b (Querit-4B):**
Scores baixos (MRR 0.19-0.22). O scoring P(no)-P(yes) com sort descendente produz ranking
razoável mas inferior aos demais. Melhor com snowflake (MRR 0.2198).

### Melhor pipeline global

**nomic_embed_text_v2_moe_q4__qwen_local**

MRR@10 = 0.8229, HR@10 = 0.8800, nDCG@10 = 0.8290, Hit@1 = 0.7933

### Melhor pipeline por família

| Família | Melhor pipeline | MRR@10 |
|---------|----------------|--------|
| gemma | embeddinggemma__qwen_local | 0.8197 |
| perplexity | pplx_embed_v1_4b_q8_0__qwen_local | 0.8221 |
| nomic | nomic_embed_text_v2_moe_q4__qwen_local | 0.8229 |
| bge | bge_m3_dense__qwen_local | 0.8067 |
| snowflake | snowflake_arctic_embed_l_v2_q4__qwen_local | 0.8158 |

### Impacto do reranking por embedding

| Embedding | Raw MRR@10 | Melhor pós-rerank | Ganho absoluto | Ganho relativo |
|-----------|-----------|-------------------|----------------|----------------|
| embeddinggemma | 0.7562 | 0.8197 (qwen) | +0.0635 | +8.4% |
| pplx_embed_v1_4b_q8_0 | 0.7562 | 0.8221 (qwen) | +0.0659 | +8.7% |
| nomic_embed_text_v2_moe_q4 | 0.7420 | 0.8229 (qwen) | +0.0809 | +10.9% |
| bge_m3_dense | 0.7182 | 0.8067 (qwen) | +0.0885 | +12.3% |
| snowflake_arctic_embed_l_v2_q4 | 0.7113 | 0.8158 (qwen) | +0.1045 | +14.7% |

### Conclusão

- 25/25 pipelines executados (5 embeddings × 5 rerankers)
- Famílias colapsadas: 5 famílias distintas representadas
- Candidatos top 50 reutilizados de sessões anteriores
- Nenhum embedding recalculado
- Nenhuma chamada API paga realizada
- Voyage rerank-2.5 existente (5 variantes) disponível para embeddings Voyage
- Ganho médio do reranking: +9.8% MRR@10 relativo sobre raw
