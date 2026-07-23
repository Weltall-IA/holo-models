# Decisão de perfis operacionais de retrieval

## Referências

- Benchmark completo de embeddings e rerankers (Gates 0–5).
- Auditoria Nemotron 1.0.5 completa (correção de licença, inspeção 8B, preflight NVFP4, admissão 1B).
- Pipeline de rerankers com embeddings embeddinggemma nos rerankers qwen_local e voyage_rerank_2_5.
- `config/production_profiles.json` — definição canônica dos perfis.

## Perfis definidos

### `local_default` — padrão local

**Embedding:** `embeddinggemma_768_float32` via llama.cpp (Q8_0, 768d, float32).
**Reranker:** `qwen_local` via Transformers.
**Estado:** Habilitado.
**Custo de API:** Nenhum.
**Motivação:** Perfil autossuficiente para operação local, throughput adequado, sem dependência externa.

### `quality_external_optional` — rerank externo opcional

**Embedding:** `embeddinggemma_768_float32` via llama.cpp.
**Reranker:** `voyage_rerank_2_5` via Voyage API.
**Estado:** Desabilitado por padrão.
**Exigências:** API key configurada, autorização operacional explícita.
**Motivação:** Melhor qualidade de reranking medida, porém com custo de API e dependência externa.

### `nemotron_gguf_evaluation` — avaliação com Nemotron GGUF

**Embedding:** `nemotron_3_embed_1b_q4_k_m_gguf` via llama.cpp.
**Estado:** Desabilitado por padrão.
**Motivação:** Perfil econômico (menor cold start, RAM e VRAM). Pendente de teste de integração com a aplicação.

### `nemotron_nvfp4_evaluation` — avaliação com Nemotron NVFP4

**Embedding:** `nemotron_3_embed_1b_nvfp4` via vLLM isolado.
**Estado:** Desabilitado por padrão.
**Exigências:** Ambiente vLLM isolado.
**Motivação:** Maior throughput aquecido no host. Pendente de teste de integração com a aplicação.

## Regras

1. Nenhum perfil com `enabled: false` pode ser ativado sem autorização explícita.
2. Perfis que exigem API (`requires_api`) também exigem `requires_authorization`.
3. Cada perfil referencia exclusivamente resultados de benchmark existentes e validados.
4. Pesos, runtimes e manifests não são movidos nem alterados por esta decisão.
