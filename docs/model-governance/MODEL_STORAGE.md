# Armazenamento e operação de modelos

Este documento incorpora e organiza as regras históricas do repositório.

## Categorias canônicas

Cada modelo baixado deve ficar na categoria principal:

- `text/` — LLMs, chat, restauração de pontuação e modelos temáticos;
- `audio/` — ASR, Whisper, TTS, voz e processamento de áudio;
- `video/` — upscaling, RIFE, CUDA e vídeo;
- `image/` — diffusion, super-resolution e faces;
- `embed/` — embeddings e rerankers.

Quando um modelo tiver usos adicionais, registre-os em metadados; não duplique pesos.

## Fluxo para adicionar modelo

1. confirmar tarefa, gate, licença, revisão, arquivo e tamanho;
2. conferir espaço livre e manter margem temporária adequada;
3. baixar pela fonte oficial no diretório canônico;
4. registrar revisão, hash, formato, quantização, backend e finalidade;
5. criar `Modelfile` somente quando houver compatibilidade real com Ollama;
6. validar o modelo no runtime adequado;
7. atualizar `LISTA_MODELOS.md` somente após validação;
8. não publicar pesos no GitHub.

## Nomenclatura

- use o nome oficial ou do repositório Hugging Face;
- não use espaços;
- inclua quantização no nome da pasta quando aplicável;
- mantenha um único diretório físico canônico por modelo.

## Ollama e GGUF

Antes de `ollama create`, execute `ollama list` e evite duplicatas.

O `FROM` do `Modelfile` deve apontar para arquivo ou diretório compatível. Modelos Transformers, Diffusers, Whisper, ONNX, Safetensors ou pipelines não suportados permanecem no runtime apropriado.

Se `ollama create` falhar por incompatibilidade:

- mantenha o modelo para Transformers ou `llama.cpp`, quando aplicável;
- crie `OLLAMA_INCOMPATIVEL.txt` com erro sanitizado;
- não force conversão nem altere o modelo silenciosamente.

## Reflink bcachefs

A importação do Ollama pode criar uma segunda cópia temporária. Após validação, o blob do Ollama pode se tornar a fonte física e o arquivo canônico pode ser substituído por reflink CoW.

Antes da substituição, confirme:

- modelo registrado e funcional;
- blob correto identificado;
- diretório canônico e `OLLAMA_MODELS` na mesma filesystem bcachefs;
- reflink obrigatório disponível, sem fallback para cópia normal;
- arquivo temporário com tamanho esperado.

Faça a troca atomicamente: crie o reflink temporário no diretório de destino e só depois substitua o arquivo canônico. Não aplique a modelos compostos que não correspondam a um único blob GGUF identificável.

## Remoção e anti-órfão

Remover um diretório canônico exige remover também o registro correspondente do Ollama, quando existir. Limpeza de blobs só pode ocorrer após cruzar manifests e digests e provar que o blob não é referenciado. Não apague caches ou blobs sem autorização humana.

## Restauração de pontuação do Whisper

Modelos usados para pontuação/capitalização devem:

- restaurar apenas pontuação e capitalização;
- não reescrever palavras;
- não adicionar conteúdo;
- usar temperatura zero;
- limitar saída;
- suprimir raciocínio na chamada quando o runtime suportar.

A versão documentada do Ollama não aceita `PARAMETER enable_thinking` no `Modelfile`; use `think: false` na API ou pós-processamento aprovado.

Modelo de configuração:

```text
FROM ./modelo.gguf
PARAMETER temperature 0
PARAMETER num_ctx 2048
PARAMETER num_predict 1024
PARAMETER stop "<|endoftext|>"
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|im_start|>"
SYSTEM "Restaure APENAS pontuação e capitalização em texto em português. Não altere palavras, não reescreva frases, não adicione conteúdo. Não faça raciocínio, não explique, não mostre pensamento. Saída direta apenas."
```

Modelos reprovados entram em `LISTA_BLACKLIST.md` somente após validação humana.
