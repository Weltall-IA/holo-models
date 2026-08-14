# nvidia-omni-embed-nemotron-3b — MRR@10 0.9402 (visão) / 0.4163 (texto)

**Reserva estratégica — ÚNICO com encoder de ÁUDIO.**
Benchmark visão v2: 300 queries, 2048 dims.
VRAM: 9.82 GB | RAM: 3.90 GB | Disco: 8.8 GB | Tamanho: 4.7B (NV-QwenOmni)

## Top 6 — ranking de visão (300 queries)

| # | Modelo | Dim | MRR@10 |
|---|---|---|---|
| 1 | qwen3-vl-2b-vdr | 1024 | 0.9634 |
| 2 | BGE-VL-large | 768 | 0.9522 |
| **3** | **omni-nemotron-3B** | 2048 | **0.9402** |
| 4 | BGE-VL-base | 512 | 0.9303 |
| 5 | llama-nemotron-VL-FP8 | 2048 | 0.5815 |
| 6 | Qwen3-VL-8B-i1 (GGUF IQ1) | 4096 | 0.0081 |

## Quem ganhou de quem

- **Venceu: BGE-VL-base (0.9303), llama-nemotron-VL (0.5815), Qwen3-VL-8B-i1 (0.0081)**.
- **Perdeu para: qwen3-vl-2b-vdr (0.9634) e BGE-VL-large (0.9522)** — em visão.
- **Texto puro: perdeu feio** — 0.4163 (15º de 16), atrás de todos os especialistas.

## Notas

- **NÃO usar para texto puro nem imagem pura** — os especialistas ganham com fração do custo.
- **Mantido como reserva de ÁUDIO**: é o único modelo da stack com encoder de áudio (base Qwen2.5-Omni). Se o Playstoria precisar buscar por fala, trilha sonora ou dublagem, este é o único candidato.
- Custo alto: 9.8 GB VRAM, 4.7B params — justificado apenas quando o domínio de áudio existir.
- Ver `README_USO.md` nesta pasta para como carregar e usar com áudio/imagem.
- Licença: NVIDIA OneWay **não-comercial** (pesquisa apenas).
