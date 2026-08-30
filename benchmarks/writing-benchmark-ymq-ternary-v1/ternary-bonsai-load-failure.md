# Ternary Bonsai: falha de carregamento

Data: 30 de agosto de 2026

Arquivo testado: `Ternary-Bonsai-27B-Abliterated-LowDeg-Q2_0.gguf`

- Tamanho: 7.165.121.600 bytes
- SHA-256: `527f276ddf047b3494de964985b5529b9fc3ecf739ea64d8fab3a6ef8403e81d`
- Backend inicial: geo-llama `llama-server` CUDA
- Teste inicial: boot com contexto 8192, `-np 1`, `-ngl 99`, Flash Attention ON

## Erro

```text
tensor 'output_norm.weight' has offset 337715200, expected 357580800
failed to read tensor data
llama_model_loader: failed to load model
llama_model_load_from_file_impl: failed to load model
```

O erro não indica corrupção do arquivo. Este Bonsai usa o formato `Q2_0` group-128 do fork PrismML, que não é compatível com o loader do llama.cpp principal usado pelo geo-llama.

## Solução confirmada

O arquivo carregou e gerou texto com o build local do Prism (`b9599-9ca265a57`) usando as bibliotecas CUDA 12 do LM Studio:

```fish
set -lx LD_LIBRARY_PATH \
	/home/alpha/.lmstudio/extensions/backends/vendor/linux-llama-cuda12-vendor-v1 \
	/home/alpha/Playstoria/models/engines/prism-llama/llama-prism-b9599-9ca265a

engines/prism-llama/llama-prism-b9599-9ca265a/llama-cli \
	-m text/Ternary-Bonsai-27B-Abliterated-LowDeg/Ternary-Bonsai-27B-Abliterated-LowDeg-Q2_0.gguf \
	-c 2048 -ngl 99 -fa on -n 96 \
	--temp 0.7 --seed 3407 \
	-p 'Responda em portugues brasileiro. Explique em duas frases por que a chuva molha o chao.' \
	--no-display-prompt
```

Resultado do smoke test: carregamento concluído, inferência CUDA ativa e geração observada em aproximadamente 35,6 tok/s. O `llama-cli` entrou no modo interativo após a resposta; isso não invalida o carregamento nem a geração.

O runtime correto para este arquivo é o fork PrismML. Não substituir o GGUF nem tentar carregá-lo no geo-llama/mainline. A documentação do formato confirma que `*-Q2_0.gguf` group-128 requer o fork Prism, enquanto `*-Q2_0_g64.gguf` é o formato destinado ao llama.cpp principal.