# nvidia-omni-embed-nemotron-3b — reserva de áudio (não usar para texto/imagem puros)

## Por que este modelo está aqui

É o **ÚNICO modelo da stack com encoder de áudio** (base Qwen2.5-Omni).
Foi mantido como **reserva estratégica** para o caso de o Playstoria precisar
de busca por áudio (falas em vídeos, trilhas sonoras, dublagem, áudio→áudio).

**NÃO usar para texto puro nem imagem pura** — o benchmark mostrou que perde
feio para os especialistas:

| Domínio | Especialista | omni-nemotron-3B |
|---|---|---|
| Texto | lightonai-mDenseOn: 0.8256 | 0.4163 (15º de 16) |
| Visão | qwen3-vl-2b-vdr: 0.9634 | 0.9402 (3º de 4) |

Custo: 8.8 GB disco, ~9.8-12.4 GB VRAM, ~4-5.5 GB RAM — caro demais para
qualidade inferior aos especialistas nos domínios cobertos.

## O que ele faz (capacidades)

- **Texto + imagem + áudio** no mesmo espaço de embedding (2048 dims)
- Bi-encoder multimodal: `encode_query` / `encode_document`
- Entrada com chat template: `{"role": "user", "content": [{"type": "text",
  "text": "passage: "}, {"type": "image", "image": <PIL>}]}`
- Embedding = média do last_hidden_state + L2 normalize (método usado no
  benchmark; o model card sugere o mesmo com `output_hidden_states=True`)

## Como usar quando o domínio de áudio surgir

1. Carregar via transformers (trust_remote_code) — funciona no venv:
```python
from transformers import AutoModel, AutoProcessor
import torch
p = AutoProcessor.from_pretrained("embed/omni/nvidia-omni-embed-nemotron-3b", trust_remote_code=True)
m = AutoModel.from_pretrained("embed/omni/nvidia-omni-embed-nemotron-3b",
                              trust_remote_code=True, dtype=torch.bfloat16).to("cuda")
```
2. Para áudio: incluir `{"type": "audio", "audio": <caminho/array>}` no content
   (ver model card do HF para o formato exato de áudio).
3. Benchmarkar no corpus de áudio com o mesmo protocolo (MRR@10, queries
   divergentes) ANTES de decidir produção.

## Resultados do benchmark (referência)

- Texto (240 queries): MRR 0.4163 — 15º/16
- Visão (300 queries): MRR 0.9402, VRAM 9.82 GB, RAM 3.90 GB, 75s
- Imagem+texto funciona, mas o qwen3-vl-2b-vdr (4.27 GB) faz melhor e mais barato.

## Decisão

Manter no disco enquanto não existir demanda de áudio. Se o áudio nunca
entrar no produto, este modelo pode ser removido (8.8 GB) — os especialistas
cobrem tudo.
