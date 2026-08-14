# Qwen3-VL-Embedding-2B-vdr — MRR@10 0.9634

**Embedding de visão de produção (LÍDER).**
Benchmark visão v2: 300 queries divergentes (Flickr30k), 150 imagens, 1024 dims.
VRAM: 4.27 GB | RAM: 4.24 GB | Disco: 4.0 GB | Tamanho: 2.1B params

## Top 6 — ranking de visão (300 queries)

| # | Modelo | Dim | MRR@10 |
|---|---|---|---|
| **1** | **qwen3-vl-2b-vdr** | 1024 | **0.9634** |
| 2 | BGE-VL-large | 768 | 0.9522 |
| 3 | omni-nemotron-3B | 2048 | 0.9402 |
| 4 | BGE-VL-base | 512 | 0.9303 |
| 5 | llama-nemotron-VL-FP8 | 2048 | 0.5815 |
| 6 | Qwen3-VL-8B-i1 (GGUF IQ1) | 4096 | 0.0081 |

## Quem ganhou de quem

- **Venceu TODOS os modelos de visão testados** — incluindo o BGE-VL-large (0.9522) por +0.0112 e o omni-nemotron-3B (0.9402) por +0.0232.
- R@10 = 1.0000 (acertou todas as 300 queries no top-10).
- O mesmo Qwen3-VL-2B **sem** fine-tune VDR (GGUF antigo) tinha MRR 0.4607 em texto e imagem quebrada — o fine-tune o transformou em líder.

## Notas

- **Fine-tune VDR** (Visual Document Retrieval) por tomaarsen (autor do sentence-transformers) sobre Qwen/Qwen3-VL-Embedding-2B.
- NDCG@10 publicado pelo autor: 0.947 vs 0.888 do base — confirmado no nosso benchmark.
- Carrega via sentence-transformers (NÃO via vLLM — bug de mapeamento `embed_tokens` no vLLM 0.26).
- Requer `LD_LIBRARY_PATH` com `/opt/cuda/targets/x86_64-linux/lib` + symlink `libnvrtc-builtins.so.13.0 → 13.3`.
- Ideal para retrieval visual de documentos (filmes, séries, animes, screenshots).
