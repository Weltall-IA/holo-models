# INTEGRAÇÃO — Stack de Embeddings do Holo (para o holo-api)

Data: 2026-08-12. Autor: benchmark Holo (validado com 240 queries texto + 300 queries visão).
Este documento define a stack de produção de embeddings/reranking para o
holo-api. Decisões baseadas em benchmark próprio (ver seção 6).

---

## 1. Modelos escolhidos

| Função | Modelo | Dim | VRAM | MRR validado |
|---|---|---|---|---|
| Embedding texto | **lightonai-mDenseOn** | **768** | 1.37 GB | 0.8256 |
| Embedding texto (fallback leve) | embeddinggemma-300m-qat-q4 | 768 | 0.06 GB | 0.7992 |
| Reranker | **llama-nemotron-rerank-1b-v2** | — | 2.30 GB | 0.8867 médio |
| Embedding visão | **qwen3-vl-2b-vdr** (tomaarsen) | 1024 | 4.27 GB | 0.9634 |
| Embedding visão (fallback) | BGE-VL-large | 768 | 2.35 GB | 0.9522 |
| Áudio (reserva) | nvidia-omni-embed-nemotron-3b | 2048 | 9.8 GB | — (não benchmarkado p/ áudio) |

**Pipeline final texto:** mDenseOn + llama-nemotron-rerank = **0.9257 MRR@10**
**Pipeline final visão:** qwen3-vl-2b-vdr = **0.9634 MRR@10**

### Decisões fixas

- **Texto: mDenseOn 768** — o melhor do benchmark, supera modelos 4B.
  A migration do pgvector precisa aceitar `vector(768)` (hoje está `vector(1024)`).
- **Reranker: llama-nemotron-rerank-1b-v2** — pipeline NATIVO transformers
  (ver seção 4.2 — CrossEncoder QUEBRA o modelo).
- **Visão: qwen3-vl-2b-vdr 1024** — fine-tune VDR, líder absoluto.
- **Áudio: omni-nemotron-3B** — já mantido na stack; único com encoder de
  áudio. Não há outro omni necessário (texto/visão usam especialistas).

---

## 2. Arquitetura de serviços

O holo-api (Laravel/PHP) NÃO executa Python/ML. Os modelos rodam em
**microserviços HTTP separados** (Python) que o holo-api consome.

```
holo-api (Laravel)
  │  HTTP
  ├──→ Serviço Embedding (texto)  — mDenseOn 768
  ├──→ Serviço Reranking          — llama-nemotron-rerank
  └──→ Serviço Embedding (visão)  — qwen3-vl-2b-vdr (quando multimodal)

PostgreSQL 18 + pgvector (knowledge_chunks)
```

### 2.1 Interface esperada dos serviços

**Embedding (texto)** — formato OpenAI-compatible:

```
POST /v1/embeddings
{ "input": "texto do chunk" }              # ou ["chunk1", "chunk2"]
→ { "data": [ { "embedding": [0.012, ...] } ], "model": "mDenseOn" }

GET /v1/models → lista modelos disponíveis
```

- Resposta: vetor L2-normalizado, **768 dims** (mDenseOn/gemma).
- Batch: aceitar lista de strings (indexação eficiente).

**Reranking:**

```
POST /v1/rerank
{ "model": "llama-nemotron-rerank-1b-v2",
  "query": "pergunta do usuário",
  "documents": ["doc1", "doc2", ...] }     # até 50
→ { "results": [ { "index": 3, "score": 0.91 }, ... ] }
```

- Retorna scores ordenados (maior = mais relevante).
- Entrada: query + lista de documentos candidatos (top-50 da busca).

**Embedding (visão):** mesma interface OpenAI-compatible, mas aceita
imagens (base64/data-URI) além de texto. 1024 dims.

---

## 3. Pipeline de ingestão (texto)

```
1. Documento chega no holo-api (rota de ingestão)
2. KnowledgeIngestService extrai seções (chunks) — já implementado
3. Para cada chunk:
   a. chamar Serviço Embedding → vetor 768
   b. salvar em knowledge_chunks.embedding (pgvector)
4. Índice HNSW mantido (vector_cosine_ops)
```

### 3.1 Troca do placeholder sintético

Hoje `KnowledgeIngestService::embeddingFor()` gera vetor DETERMINÍSTICO
(hash → 1024 dims) como placeholder. Substituir por:

```php
// chamada HTTP ao serviço de embedding (mDenseOn)
$embedding = EmbeddingClient::generate($chunkBody); // float[768]
$chunkData['embedding'] = '[' . implode(',', array_map('floatval', $embedding)) . ']';
```

### 3.2 Dimensão da migration

```sql
-- HOJE: vector(1024) — mudar para 768 (texto mDenseOn)
ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(768);
-- ou recriar a coluna (mais simples em pré-produção):
ALTER TABLE knowledge_chunks DROP COLUMN embedding;
ALTER TABLE knowledge_chunks ADD COLUMN embedding vector(768);
-- reconstruir HNSW:
CREATE INDEX idx_knowledge_chunks_embedding
  ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);
```

⚠️ `KnowledgeSearchService` valida `count($embedding) === 1024` (linha 61) —
**mudar para 768** quando o texto entrar.

---

## 4. Pipeline de busca (texto) — com reranking

```
1. Query do usuário
2. Serviço Embedding → vetor 768
3. pgvector: busca por cosseno → top-50 candidatos
   SELECT *, embedding <=> CAST(? AS vector) AS distance
   ORDER BY embedding <=> CAST(? AS vector) LIMIT 50
4. Serviço Reranking: llama-nemotron reordena os 50 → top-20
5. Resposta final (top-20 reordenados)
```

O reranking adiciona +0.10 MRR (0.8256 → 0.9257). Sem reranker, a busca
pura já entrega 0.8256 — aceitável para resposta rápida; reranker quando a
qualidade importar.

---

## 5. Reindexação (necessária ao ativar o modelo real)

O código documenta: "A troca pelo modelo real é etapa própria e exige
reindexação."

### 5.1 O que é

Os chunks já ingeridos com vetor SINTÉTICO (hash) não têm significado
semântico — a busca real não funciona até serem re-embeddados com mDenseOn.

### 5.2 Procedimento (script/job uma vez)

```
1. SELECT id, body FROM knowledge_chunks WHERE embedding IS NOT NULL
   (em lotes de 100-500)
2. Para cada lote: POST /v1/embeddings → vetores reais (768)
3. UPDATE knowledge_chunks SET embedding = ? WHERE id = ?
4. REINDEX INDEX idx_knowledge_chunks_embedding
```

- NÃO re-ingere documentos — só re-gera vetores dos chunks existentes.
- Custo estimado: ~10-50 ms/chunk (mDenseOn em GPU) — 10k chunks ≈ 5 min.
- Deve rodar com o serviço de embedding ativo.

---

## 6. Justificativa das escolhas (resumo do benchmark)

Benchmark próprio, corpus PT-BR (code, movies_series, anime, video):

- **Texto (240 queries):** mDenseOn 0.8256 líder; embeddinggemma 0.7992
  (2º, 23× mais leve); pplx-4B/qwen3-4B/nemotron-8B (4B+) ficaram ABAIXO
  dos 768-dim — params não compensam treinamento para retrieval.
- **Rerankers (6 testados):** llama-nemotron 0.8867 médio (vence todos os 8
  embeddings); qwen3-reranker 0.8563; os outros 4 DEGRADAM (piores que
  embedding puro — não usar: mxbai, lamar, ettin×2).
- **Visão (300 queries):** qwen3-vl-2b-vdr 0.9634 (fine-tune VDR do
  Qwen3-VL-2B, autor tomaarsen); BGE-VL-large 0.9522; omni-nemotron 0.9402
  (paga 9.8 GB VRAM e perde).
- **int8 vs fp32:** diferença ≤0.004 nos top-5 — int8 seguro para storage
  (1.0 KB/vec vs 4.1 KB/vec em 1024 fp32).
- **Omni:** especialistas vencem nos domínios; omni só necessário para
  áudio (omni-nemotron-3B é a reserva).

### Avisos críticos

1. **llama-nemotron-rerank DEVE rodar com pipeline nativo transformers**
   (`AutoModelForSequenceClassification` + template
   `question:{q} \n \n passage:{p}` como UMA sequência). CrossEncoder
   (sentence-transformers) tokeniza como 2 sequências e QUEBRA o modelo
   (média 0.7252 vs 0.9353 correta).
2. **mDenseOn é sentence-transformers** — carrega via `SentenceTransformer`.
   Não roda no Ollama (arquitetura BiEncoder não suportada por safetensors
   experimental — só Llama/Mistral/Gemma/Phi3).
3. **qwen3-vl-2b-vdr é sentence-transformers** — carrega direto; requer
   `LD_LIBRARY_PATH` com `/opt/cuda` + symlink `libnvrtc-builtins.so.13.0→13.3`
   (JIT do FlashAttention vision).
4. **embeddinggemma-300m é GGUF puro** (roda via llama.cpp) — pode ser
   importado no Ollama com reflink (feito: modelo `embeddinggemma-300m-qat`).

---

## 7. Referências

- Resultados completos: `embed/RESULTADOS_EMBEDDING.md` (histórico do benchmark)
- Protocolo detalhado: `holo-bench/RESULTADOS_BENCHMARK.md`
- Guia vLLM (NVFP4/FP8, anti-OOM): `models/vllm/COMO_USAR.md`
- Notas por modelo: arquivos `MRR X.XXXX.md` na pasta de cada modelo
- Código-fonte de referência (servidor OpenAI-compatível):
  `models/vllm/serve_embedding.py` (embeddinggemma via llama.cpp)
- Benchmark de LLMs (não relacionado): `benchmarks/local-chat-v1/`

## 8. Pendências conhecidas

| Item | Status |
|---|---|
| Migration `vector(1024)` → `vector(768)` | **A FIXAR no holo-api** |
| `searchSemantic()` valida 1024 | **A FIXAR** (linha 61) |
| `embeddingFor()` sintético → serviço real | **A FIXAR** |
| Serviço de reranking (llama-nemotron) | **A CRIAR** (interface na seção 2.1) |
| Reindexação dos chunks existentes | Após fixar embedding (seção 5) |
| Embedding de visão no Knowledge | Quando multimodal entrar |
| gemini-001 (API) | Descartado — cota pequena |
