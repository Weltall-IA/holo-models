# BGE-VL-large — MRR@10 0.9522

**Embedding de visão (fallback de produção).**
Benchmark visão v2: 300 queries divergentes (Flickr30k), 150 imagens, 768 dims.
VRAM: 2.35 GB | RAM: 0.81 GB | Disco: 822 MB | Tamanho: 300M (CLIP-L/14)

## Top 6 — ranking de visão (300 queries)

| # | Modelo | Dim | MRR@10 |
|---|---|---|---|
| 1 | qwen3-vl-2b-vdr | 1024 | 0.9634 |
| **2** | **BGE-VL-large** | 768 | **0.9522** |
| 3 | omni-nemotron-3B | 2048 | 0.9402 |
| 4 | BGE-VL-base | 512 | 0.9303 |
| 5 | llama-nemotron-VL-FP8 | 2048 | 0.5815 |
| 6 | Qwen3-VL-8B-i1 (GGUF IQ1) | 4096 | 0.0081 |

## Quem ganhou de quem

- **Venceu: omni-nemotron-3B (0.9402), BGE-VL-base (0.9303), llama-nemotron-VL (0.5815), Qwen3-VL-8B-i1 (0.0081)**.
- **Perdeu apenas para: qwen3-vl-2b-vdr** (0.9634) — por +0.0112 do vdr.

## Notas

- **SOTA de CLIP-based no MMEB** (benchmark acadêmico) — o nosso ranking local reproduz isso.
- Mantido como **fallback** por ser 5× menor que o vdr (822 MB vs 4 GB) e quase igual em qualidade (0.9522 vs 0.9634).
- Se o vdr falhar em algum caso de uso, este é o plano B barato.
- Fine-tune oficial BGE-VL-v1.5-mmeb (7B) testado: **não cabe na RTX 5060 Ti** (14.08 GiB de pesos) — por isso o fallback é este large.
