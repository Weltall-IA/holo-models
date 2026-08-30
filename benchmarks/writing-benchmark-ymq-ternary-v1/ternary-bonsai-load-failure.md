# Ternary Bonsai: falha de carregamento

Data: 30 de agosto de 2026

Arquivo testado: `Ternary-Bonsai-27B-Abliterated-LowDeg-Q2_0.gguf`

- Tamanho: 7.165.121.600 bytes
- SHA-256: `527f276ddf047b3494de964985b5529b9fc3ecf739ea64d8fab3a6ef8403e81d`
- Backend: geo-llama `llama-server` CUDA
- Teste: boot com contexto 8192, `-np 1`, `-ngl 99`, Flash Attention ON

## Erro

```text
tensor 'output_norm.weight' has offset 337715200, expected 357580800
failed to read tensor data
llama_model_loader: failed to load model
llama_model_load_from_file_impl: failed to load model
```

O servidor encerrou durante a leitura do GGUF. Smoke test e geração literária não foram possíveis. O arquivo deve ser considerado inválido para este backend até existir uma cópia íntegra ou uma correção confirmada na origem.