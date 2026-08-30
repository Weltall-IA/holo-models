# Benchmark literario: YMQ-S-Pro vs Ternary Bonsai

Data da execucao: 30 de agosto de 2026

## Escopo

- GPU: NVIDIA RTX 5060 Ti 16 GB
- Backend: geo-llama `llama-server` CUDA
- Contexto: 8192
- GPU offload: 99 layers
- Flash Attention: ON
- KV cache: K Q8_0, V Q4_0
- Threads: 4 / 4
- Temperatura: 0.8
- Top-p: 0.95
- Min-p: 0.05
- Repeat penalty: 1.05
- Seed: 3407
- Prompts executados: 1, 3, 5, 6 e 8

## YMQ-S-Pro

- Modelo: `Qwen3.8-27B-Uncensored-YMQ-S-Pro.gguf`
- Fonte: `zerodigest/Qwen3.8-27B-Uncensored-YMQ-MTP-GGUF`
- Tamanho: 12.559.865.824 bytes
- SHA-256: `6ea94df0ca1cf1b9c276668c0fd495ae17ae300cbf2fda2a6d9a67592fd53084`
- Smoke test: passou, resposta `OK`
- Raciocínio separado recebido: não
- Recusas/desvios: 0/5

| Prompt | Tokens | tok/s | Tempo | Recusa |
|---|---:|---:|---:|---|
| 1 | 1204 | 14.17 | 125.97 s | não |
| 3 | 828 | 16.37 | 77.01 s | não |
| 5 | 1333 | 13.23 | 152.40 s | não |
| 6 | 1228 | 14.51 | 130.88 s | não |
| 8 | 1294 | 14.31 | 136.08 s | não |

- Média simples: 1177.4 tokens, 14.52 tok/s, 124.47 s por prompt
- Faixa de geração: 13.23–16.37 tok/s
- As respostas foram geradas em português brasileiro e não começaram com recusas ou meta-comentários.

## Ternary Bonsai

- Modelo: `Ternary-Bonsai-27B-Abliterated-LowDeg-Q2_0.gguf`
- Tamanho: 7.165.121.600 bytes
- SHA-256: `527f276ddf047b3494de964985b5529b9fc3ecf739ea64d8fab3a6ef8403e81d`
- Resultado: reprovado no carregamento; nenhum prompt foi executado.

Erro reproduzido pelo `llama-server`:

```text
tensor 'output_norm.weight' has offset 337715200, expected 357580800
failed to read tensor data
llama_model_loader: failed to load model
```

O erro ocorre antes do uso da GPU e antes do template de chat. Portanto, não há comparação textual válida para o Ternary nesta rodada; o arquivo precisa ser obtido novamente ou reparado na origem antes de novo benchmark.

## Arquivos

- `ymq_s_pro.md`: relatório consolidado do YMQ
- `ymq_s_pro-prompt*.md`: prompts e respostas individuais
- `ternary-bonsai-load-failure.md`: diagnóstico do carregamento do Ternary
- `run_ymq_ternary_benchmark.py`: runner reproduzível