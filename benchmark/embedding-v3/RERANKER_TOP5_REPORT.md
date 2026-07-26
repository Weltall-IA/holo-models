# RERANKER_TOP5 — Relatório de Sessão

## Resumo

Sessão de reranking aplicada às 5 melhores famílias de embeddings selecionadas por MRR@10
após colapso por família (mantido modelo nativo de cada família). Candidatos top 50 reutilizados.
Embeddings não recalculados.

Nesta atualização o reranker **`voyage_rerank_2_5`** (Voyage Batch API) foi incorporado ao
ranking unificado:

- **4 pipelines novos executados via Voyage Batch API** na franquia gratuita (sem método de
  pagamento, sem cobrança observada): `pplx_embed_v1_4b_q8_0`, `nomic_embed_text_v2_moe_q4`,
  `bge_m3_dense`, `snowflake_arctic_embed_l_v2_q4`.
- O resultado `embeddinggemma_768_float32__voyage_rerank_2_5` **já existente foi reutilizado
  sem nova chamada à API**.
- Frozen corpus SHA-256: `8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b`.
- Total agora: **30 pipelines** (5 embeddings × 6 rerankers / sessão).

## Famílias colapsadas

| Família | Modelos | Seleção final |
|---------|---------|---------------|
| gemma | embeddinggemma (native), embeddinggemma_gguf (GGUF) | embeddinggemma (native) |
| perplexity | pplx_embed_v1_06b_native, pplx_embed_v1_4b_q8_0 | pplx_embed_v1_4b_q8_0 (4B) |
| voyage | voyage4_nano (API) | Excluída como família de embedding (dependência de API) |
| nomic | nomic_embed_text_v2_moe_q4 | nomic_embed_text_v2_moe_q4 |
| bge | bge_m3_dense | bge_m3_dense |
| snowflake | snowflake_arctic_embed_l_v2_q4 | snowflake_arctic_embed_l_v2_q4 |

> O reranker `voyage_rerank_2_5` é um reranker de API, não uma família de embedding. Ele foi
> adicionado como sexta coluna de reranker, não como sexta família de embedding.

## Embeddings selecionados

| # | Modelo | Família | MRR@10 (raw) | HR@10 | nDCG@10 |
|---|--------|---------|-------------|-------|---------|
| 1 | embeddinggemma | gemma | 0.7562 | 0.8600 | 0.7739 |
| 2 | pplx_embed_v1_4b_q8_0 | perplexity | 0.7562 | 0.8600 | 0.7778 |
| 3 | nomic_embed_text_v2_moe_q4 | nomic | 0.7420 | 0.8333 | 0.7562 |
| 4 | bge_m3_dense | bge | 0.7182 | 0.8800 | 0.7490 |
| 5 | snowflake_arctic_embed_l_v2_q4 | snowflake | 0.7113 | 0.8600 | 0.7394 |

## Rerankers

| Reranker | Tipo | Modelo | Backend |
|----------|------|--------|---------|
| qwen_local | CrossEncoder | qwen3_reranker_06 (Qwen3-Reranker-0.6B) | local |
| kalm_reranker_v1_small | EncoderDecoder | KaLM-Reranker-V1-Small | local |
| kalm_reranker_v1_nano | EncoderDecoder | KaLM-Reranker-V1-Nano | local |
| jina_reranker_v3_noncommercial | CausalLM+Projector | jina-reranker-v3 | local |
| querit_reranker_4b | CausalLM+Head | Querit-4B | local |
| voyage_rerank_2_5 | API (Batch) | rerank-2.5 | Voyage Batch API (franquia gratuita) |

## Destaques (best-of)

Estes quatro pontos são intentionalmente distintos e não devem ser confundidos:

- **Melhor Voyage desta sessão** (dos 4 novos pipelines Batch):
  `nomic_embed_text_v2_moe_q4__voyage_rerank_2_5`, **MRR@10 = 0.8209**.
- **Melhor pipeline da matriz Top-5** (todas as combinações locais + voyage das 5 famílias):
  `nomic_embed_text_v2_moe_q4__qwen_local`, **MRR@10 = 0.8229**.
- **Melhor pipeline absoluto histórico** (inclui sessões anteriores):
  `embeddinggemma_768_float32__voyage_rerank_2_5`, **MRR@10 = 0.826444**.
- **Melhor pipeline totalmente local histórico** (reranker local, sem API):
  `qwen3_embedding_4b_q8_0__qwen_local`, **MRR@10 = 0.8243**.

> Observação: os pipelines `qwen_local` usam como modelo subjacente `qwen3_reranker_06`; o
> rótulo `qwen_local` identifica o reranker local na matriz Top-5.

## Ranking unificado por MRR@10 (matriz 5 famílias × 6 rerankers)

| Embedding | voyage_rerank_2_5 | qwen_local | kalm_reranker_v1_small | jina_reranker_v3_noncommercial | kalm_reranker_v1_nano | querit_reranker_4b |
|-----------|-------------------|------------|------------------------|-------------------------------|----------------------|---------------------|
| embeddinggemma | 0.8264 | 0.8197 | 0.8116 | 0.7919 | 0.7588 | 0.1985 |
| pplx_embed_v1_4b_q8_0 | 0.8206 | 0.8221 | 0.8136 | 0.8065 | 0.7572 | 0.2106 |
| nomic_embed_text_v2_moe_q4 | 0.8209 | 0.8229 | 0.8097 | 0.8132 | 0.7596 | 0.1995 |
| bge_m3_dense | 0.8040 | 0.8067 | 0.8009 | 0.7901 | 0.7474 | 0.2195 |
| snowflake_arctic_embed_l_v2_q4 | 0.8040 | 0.8158 | 0.8019 | 0.7886 | 0.7550 | 0.2198 |

## Ranking completo por MRR@10 (30 pipelines)

| Rank | Pipeline | MRR@10 | HR@10 | nDCG@10 | Hit@1 |
|------|----------|--------|-------|---------|-------|
|  1 | embeddinggemma_768_float32__voyage_rerank_2_5 | 0.8264 | 0.8733 | 0.8346 | 0.8133 |
|  2 | nomic_embed_text_v2_moe_q4__qwen_local | 0.8229 | 0.8800 | 0.8290 | 0.7933 |
|  3 | pplx_embed_v1_4b_q8_0__qwen_local | 0.8221 | 0.8800 | 0.8282 | 0.7933 |
|  4 | nomic_embed_text_v2_moe_q4__voyage_rerank_2_5 | 0.8209 | 0.8667 | 0.8236 | 0.8067 |
|  5 | pplx_embed_v1_4b_q8_0__voyage_rerank_2_5 | 0.8206 | 0.8667 | 0.8277 | 0.8067 |
|  6 | embeddinggemma__qwen_local | 0.8197 | 0.8933 | 0.8294 | 0.7867 |
|  7 | snowflake_arctic_embed_l_v2_q4__qwen_local | 0.8158 | 0.8733 | 0.8220 | 0.7867 |
|  8 | pplx_embed_v1_4b_q8_0__kalm_reranker_v1_small | 0.8136 | 0.8800 | 0.8215 | 0.7867 |
|  9 | nomic_embed_text_v2_moe_q4__jina_reranker_v3_noncommercial | 0.8132 | 0.8667 | 0.8183 | 0.7867 |
| 10 | embeddinggemma__kalm_reranker_v1_small | 0.8116 | 0.8733 | 0.8183 | 0.7867 |
| 11 | nomic_embed_text_v2_moe_q4__kalm_reranker_v1_small | 0.8097 | 0.8800 | 0.8185 | 0.7800 |
| 12 | bge_m3_dense__qwen_local | 0.8067 | 0.8733 | 0.8150 | 0.7733 |
| 13 | pplx_embed_v1_4b_q8_0__jina_reranker_v3_noncommercial | 0.8065 | 0.8733 | 0.8145 | 0.7800 |
| 14 | bge_m3_dense__voyage_rerank_2_5 | 0.8040 | 0.8467 | 0.8116 | 0.7933 |
| 15 | snowflake_arctic_embed_l_v2_q4__voyage_rerank_2_5 | 0.8040 | 0.8467 | 0.8059 | 0.7933 |
| 16 | snowflake_arctic_embed_l_v2_q4__kalm_reranker_v1_small | 0.8019 | 0.8667 | 0.8094 | 0.7733 |
| 17 | bge_m3_dense__kalm_reranker_v1_small | 0.8009 | 0.8667 | 0.8087 | 0.7733 |
| 18 | embeddinggemma__jina_reranker_v3_noncommercial | 0.7919 | 0.8600 | 0.8007 | 0.7533 |
| 19 | bge_m3_dense__jina_reranker_v3_noncommercial | 0.7901 | 0.8600 | 0.7988 | 0.7600 |
| 20 | snowflake_arctic_embed_l_v2_q4__jina_reranker_v3_noncommercial | 0.7886 | 0.8600 | 0.7980 | 0.7533 |
| 21 | nomic_embed_text_v2_moe_q4__kalm_reranker_v1_nano | 0.7596 | 0.8533 | 0.7745 | 0.7133 |
| 22 | embeddinggemma__kalm_reranker_v1_nano | 0.7588 | 0.8533 | 0.7738 | 0.7133 |
| 23 | pplx_embed_v1_4b_q8_0__kalm_reranker_v1_nano | 0.7572 | 0.8533 | 0.7725 | 0.7133 |
| 24 | snowflake_arctic_embed_l_v2_q4__kalm_reranker_v1_nano | 0.7550 | 0.8467 | 0.7693 | 0.7133 |
| 25 | bge_m3_dense__kalm_reranker_v1_nano | 0.7474 | 0.8400 | 0.7618 | 0.7067 |
| 26 | snowflake_arctic_embed_l_v2_q4__querit_reranker_4b | 0.2198 | 0.5400 | 0.2938 | 0.1200 |
| 27 | bge_m3_dense__querit_reranker_4b | 0.2195 | 0.6067 | 0.3074 | 0.0933 |
| 28 | pplx_embed_v1_4b_q8_0__querit_reranker_4b | 0.2106 | 0.5533 | 0.2880 | 0.0800 |
| 29 | nomic_embed_text_v2_moe_q4__querit_reranker_4b | 0.1995 | 0.5733 | 0.2854 | 0.0733 |
| 30 | embeddinggemma__querit_reranker_4b | 0.1985 | 0.6000 | 0.2888 | 0.0733 |

## Análise

### Top pipelines por reranker

**voyage_rerank_2_5 (Voyage Batch API, franquia gratuita):**
Todos os 5 embeddings atingem MRR > 0.80. É o melhor reranker isolado para `embeddinggemma`
(MRR 0.8264, melhor pipeline absoluto da matriz). Melhor combinação nova:
`nomic_embed_text_v2_moe_q4__voyage_rerank_2_5` (MRR 0.8209). Executado como um único
`batch` (150 requisições, 2.380.494 tokens, 0 falhas), sem cobrança observada.

**qwen_local (qwen3_reranker_06):**
Todos os 5 embeddings atingem MRR > 0.80. Consistentemente o melhor reranker local.
Melhor combinação: `nomic_embed_text_v2_moe_q4__qwen_local` (MRR 0.8229, melhor pipeline
da matriz Top-5).

**kalm_reranker_v1_small (KaLM-Reranker-V1-Small):**
Performance sólida (MRR 0.80-0.81). Segundo melhor reranker local.
`pplx + kalm_small` supera `pplx + jina`.

**jina_reranker_v3_noncommercial:**
Performance sólida (MRR 0.79-0.81). Terceiro melhor reranker local.
Melhor com nomic (MRR 0.8132).

**kalm_reranker_v1_nano (KaLM-Reranker-V1-Nano):**
Performance moderada (MRR 0.74-0.76). Útil como alternativa leve.

**querit_reranker_4b (Querit-4B):**
Scores baixos (MRR 0.19-0.22). Inferior aos demais.

### Melhor pipeline global

**embeddinggemma_768_float32__voyage_rerank_2_5** (MRR@10 = 0.826444) — melhor pipeline
absoluto histórico, agora incluso no ranking unificado.

### Melhor pipeline da matriz Top-5 (sessão atual)

**nomic_embed_text_v2_moe_q4__qwen_local** (MRR@10 = 0.8229) — melhor entre todas as
combinações das 5 famílias desta sessão.

### Melhor pipeline por família (reranker local campeão)

| Família | Melhor pipeline local | MRR@10 | Melhor voyage (ref.) |
|---------|----------------------|--------|----------------------|
| gemma | embeddinggemma__qwen_local | 0.8197 | embeddinggemma_768_float32__voyage_rerank_2_5 (0.8264) |
| perplexity | pplx_embed_v1_4b_q8_0__qwen_local | 0.8221 | pplx_embed_v1_4b_q8_0__voyage_rerank_2_5 (0.8206) |
| nomic | nomic_embed_text_v2_moe_q4__qwen_local | 0.8229 | nomic_embed_text_v2_moe_q4__voyage_rerank_2_5 (0.8209) |
| bge | bge_m3_dense__qwen_local | 0.8067 | bge_m3_dense__voyage_rerank_2_5 (0.8040) |
| snowflake | snowflake_arctic_embed_l_v2_q4__qwen_local | 0.8158 | snowflake_arctic_embed_l_v2_q4__voyage_rerank_2_5 (0.8040) |

### Impacto do reranking por embedding (melhor reranker disponível)

| Embedding | Raw MRR@10 | Melhor pós-rerank | Ganho absoluto | Ganho relativo |
|-----------|-----------|-------------------|----------------|----------------|
| embeddinggemma | 0.7562 | 0.8264 (voyage) | +0.0702 | +9.3% |
| pplx_embed_v1_4b_q8_0 | 0.7562 | 0.8229 (qwen) | +0.0667 | +8.8% |
| nomic_embed_text_v2_moe_q4 | 0.7420 | 0.8229 (qwen) | +0.0809 | +10.9% |
| bge_m3_dense | 0.7182 | 0.8067 (qwen) | +0.0885 | +12.3% |
| snowflake_arctic_embed_l_v2_q4 | 0.7113 | 0.8158 (qwen) | +0.1045 | +14.7% |

## Notas de execução — Voyage Batch API (franquia gratuita)

- Endpoint: `POST /v1/rerank` via Batch API (`/v1/batches`), `model=rerank-2.5`,
  `completion_window=12h`.
- `batch_id`: `batch-7vzuBuWXsCmo5UFkFaVvKNLAxToqnMj6pA2BC`.
- Requisições: **150/150 concluídas**, **0 falhas**.
- Tokens: **2.380.494** (`estimated_standard_price_usd` ≈ 0.1190; `charged_cost_usd = null`).
- Duração: criado 21:43:31 → concluído 21:50:17 UTC (~407 s).
- Candidatos: união top-20 das 4 variantes autorizadas por consulta (sem sub-batching, sem
  mesclar scores). `corpus_sha256` validado.
- `embeddinggemma_768_float32__voyage_rerank_2_5` foi **reutilizado** (sessão histórica), sem
  nova chamada.
- Correção de transporte: o download do output do batch retornava HTTP 307 para uma URL
  pré-assinada; `urllib` descartava o header `Authorization` no redirect e travava. Corrigido
  em `holo_benchmark/voyage_batch.py` (`_text_request`) para seguir redirects (via `requests`,
  com fallback `urllib` sem redirect handler), **sem alterar nenhum parâmetro de reranking**.
  Teste de regressão em `tests/test_voyage_batch.py`.

## Conclusão

- 30/30 pipelines executados (5 embeddings × 6 rerankers).
- 6 rerankers na matriz (5 locais + `voyage_rerank_2_5` via Batch API).
- Famílias colapsadas: 5 famílias distintas representadas.
- Candidatos top 50 reutilizados de sessões anteriores; embeddings não recalculados.
- Execução Voyage via franquia gratuita: **sem método de pagamento, sem cobrança observada**.
- `voyage_rerank_2_5` é o melhor reranker isolado para `embeddinggemma`; `qwen_local` segue
  como o melhor reranker local e o melhor da matriz Top-5.
