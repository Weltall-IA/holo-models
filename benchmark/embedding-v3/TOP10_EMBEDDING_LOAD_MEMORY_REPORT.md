# Top 10 Embedding Load Memory Report

| # | Embedding | Params | Quant | Size MB | Size MiB | RAM idle MiB | VRAM idle MiB | Load s | Status |
|--:|-----------|-------:|-------|--------:|---------:|-------------|--------------|-------:|--------|
| 1 | Qwen3-Embedding-4B-Q8_0 | 4B | Q8_0 | 4279.7 | 4081.4 | 877.4 | 6275.9 | 12.3 | PASS |
| 2 | nomic-embed-text-v2-moe-Q4_K_M | 137M MoE | Q4_K_M | 344.1 | 328.2 | 852.1 | 1793.9 | 11.5 | PASS |
| 3 | Nemotron-3-Embed-1B-NVFP4 | 1B | NVFP4 | 1027.8 | 980.2 | 0.0 | 0.0 | 0.0 | SMOKE_FAILED |
| 4 | Nemotron-3-Embed-8B-Q4_K_M (Abiray) | 8B | Q4_K_M | 4896.4 | 4669.6 | 956.2 | 6813.9 | 12.3 | PASS |
| 5 | Colibri-1.5B-PT-BR-Q8_0 | 1.5B | Q8_0 | 602.8 | 574.9 | 0.0 | 0.0 | 0.0 | SMOKE_FAILED |
| 6 | EmbeddingGemma-300M-Q8_0 | 300M | Q8_0 | 333.6 | 318.1 | 652.1 | 1861.9 | 11.3 | PASS |
| 7 | embeddinggemma_768_float32 | ? | ? | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | NOT_MEASURED |
| 8 | Voyage-4-Large | N/A | N/A | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | REMOTE_API_NO_LOCAL_LOAD |

### Notas

- `nemotron_8b_abiray_q4_audit_4096` excluído do escopo nesta rodada
- `voyage_4_large_1024` registrado como REMOTE_API (sem carga local)
- Nemotron 1B NVFP4 e Colibri: medição falhou (safetensors via sentence_transformers não completou)
- Nenhum reranker foi carregado
- Nenhuma API paga foi chamada
