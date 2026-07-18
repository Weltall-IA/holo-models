Cada modelo baixado deve ir para a subpasta de categoria correspondente:

- text/ — LLMs, chat, punctuation restoration, modelos temáticos de texto
- audio/ — ASR (Whisper), TTS, voz, processamento de áudio
- video/ — upscaling, RIFE, CUDA, vídeo
- image/ — diffusion, super-resolution, faces
- embed/ — embeddings, rerankers

### Fluxo padrão ao adicionar um novo modelo

1. Baixar o modelo pela fonte apropriada, como Hugging Face CLI, `ollama pull` ou repositório oficial.

2. Armazenar o modelo em uma única pasta canônica, dentro da subpasta correspondente à sua categoria principal.

3. Quando o modelo atender a mais de uma categoria, registrar as categorias adicionais em um arquivo de metadados dentro da pasta. Não duplicar os pesos entre categorias.

4. Criar um `Modelfile` somente quando o modelo for compatível com o Ollama. Usar as configurações recomendadas na página oficial do modelo ou no repositório do desenvolvedor.

5. Registrar modelos GGUF compatíveis no Ollama executando `ollama create <nome>:<tag> -f Modelfile` dentro da pasta do modelo, para que caminhos relativos em `FROM` sejam resolvidos corretamente.

6. O `ollama create` importa o modelo para o armazenamento de blobs do Ollama. Essa importação cria inicialmente outra cópia física dos pesos, mesmo quando a biblioteca e o diretório do Ollama estão em bcachefs.

7. Após o `ollama create` terminar e o modelo ser validado, localizar o blob final criado pelo Ollama e substituir o GGUF existente na pasta canônica por um reflink desse blob.

8. Antes de substituir o arquivo canônico, confirmar obrigatoriamente:

   * que o modelo registrado funciona no Ollama;
   * que o blob final foi identificado corretamente;
   * que a pasta canônica e `OLLAMA_MODELS` estão no mesmo sistema de arquivos bcachefs;
   * que o reflink pode ser criado com modo obrigatório, sem fallback para cópia normal;
   * que o arquivo temporário resultante possui o tamanho esperado.

9. Fazer a substituição de forma atômica: criar primeiro o reflink em um arquivo temporário dentro da pasta do modelo e somente depois substituir o arquivo canônico.

10. Depois da substituição, a pasta organizada e o armazenamento do Ollama terão inodes separados, mas compartilharão os mesmos extents físicos por CoW. O espaço adicional só será alocado se um dos arquivos for posteriormente modificado.

11. Não aplicar esse procedimento a modelos que não são armazenados pelo Ollama como um único blob GGUF identificável, como alguns modelos multimodais compostos por várias camadas.

12. Modelos Transformers, Diffusers, Whisper, ONNX, Safetensors não compatíveis e outros pipelines específicos não devem ser registrados no Ollama. Para eles, manter os pesos diretamente na pasta canônica e usar o runtime apropriado.

Exemplo mínimo de Modelfile:

FROM ./model.safetensors
PARAMETER temperature 0.7
PARAMETER num_ctx 2048

O campo FROM aceita tanto o caminho local do arquivo do modelo (`.safetensors`, `.gguf` ou diretório do modelo) quanto o nome de um modelo já registrado no Ollama. Os arquivos de blobs e manifests gerados ficam apenas em `ollama/blobs/` e `ollama/manifests/`.

Nomenclatura de pastas:

- Usar o nome do repositório no Hugging Face ou nome oficial do modelo
- Sem espaços, apenas hífens/underscores
- **Incluir a quantização no nome da pasta** (ex: `Qwen3.5-2B-PTBR-Q4_K_M`, `Qwen3.5-4B-PTBR-Q6_K`)
- A quantização fica registrada no Modelfile e no nome do modelo no Ollama

Critério de categoria quando houver duplicidade:

- Escolher a categoria mais específica
- Whisper: `audio/` (mesmo que gere texto, a finalidade é ASR)
- Modelos de TTS que também fazem chat: `audio/` (finalidade principal)

Verificação prévia:

- Antes de registrar um modelo no Ollama, verificar com `ollama list` se já existe
- Se existir, atualizar o Modelfile existente ao invés de criar duplicata

Responsabilidade:

- IA: baixar, mover para categoria, criar Modelfile, registrar via `ollama create` e criar reflink
- Usuário: validar configurações do Modelfile e sinalizar se algo falhar depois

Ao remover um modelo de qualquer subpasta, também removê-lo do Ollama para não deixar registros órfãos.

Regra anti-órfão:

- Se um modelo for removido de uma subpasta de categoria, removê-lo do Ollama (`ollama rm <modelo>`).
- Limpeza de blobs órfãos (APÓS remover): cruzar blobs em `ollama/blobs/` contra os digests em `ollama/manifests/` e apagar SÓ os não referenciados.

Fallback para modelos incompatíveis com o Ollama:

- Se `ollama create` falhar (arquitetura/GGUF não suportada pelo Ollama atual), o modelo fica restrito a `transformers`/`llama.cpp`.
- Criar `OLLAMA_INCOMPATIVEL.txt` na pasta do modelo com o motivo do erro; o Modelfile permanece para uso direto fora do Ollama.

### Regra de armazenamento

O bcachefs suporta reflink CoW. O Ollama não precisa criar o reflink durante o `ollama create`: o procedimento padrão é deixar a importação terminar normalmente e, depois, substituir a cópia canônica do GGUF por um reflink do blob final criado pelo Ollama.

Esse procedimento evita a duplicação permanente dos pesos, embora ainda exija espaço temporário suficiente para manter as duas cópias durante a importação.

A correção central é esta: **o blob do Ollama vira a fonte física dos dados, e o arquivo organizado passa a ser o reflink criado depois da importação**.

### Regra de atualização de lista

Após criar e reflinkar um modelo com sucesso, adicionar sua entrada em `LISTA_MODELOS.md` mantendo a tabela atualizada para visão geral do inventário.

### Regra de blacklist

Quando um modelo falhar no teste de restauração de pontuação da saída do Whisper, registrar em `LISTA_BLACKLIST.md` apenas após validação do usuário (via F12). Formato: `<nome-do-modelo> | motivo`.

### Regra de Modelfile para restauração de pontuação (Whisper)

Modelos usados para pontuar a saída do Whisper precisam de configuração específica no `Modelfile`, além do fluxo geral:

- `SYSTEM` com instrução de restaurar APENAS pontuação/capitalização, sem reescrever, sem raciocínio, saída direta.
- `PARAMETER temperature 0`
- `PARAMETER num_predict 1024`
- `PARAMETER stop` para os tokens de fim do modelo (`<|im_end|>`, `<|im_start|>`, `<|endoftext|>`).
- Esta versão do ollama-cuda (0.31.2) **não aceita** `PARAMETER enable_thinking` no Modelfile. Para suprimir o bloco `<think>` na inference, chamar a API com `"think": false` ou cortar `<think>…</think>` no pós-processamento do pipeline.

Template:

```
FROM ./modelo.gguf
PARAMETER temperature 0
PARAMETER num_ctx 2048
PARAMETER num_predict 1024
PARAMETER stop "<|endoftext|>"
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|im_start|>"
SYSTEM "Restaure APENAS pontuação e capitalização em texto em português. Não altere palavras, não reescreva frases, não adicione conteúdo. Não faça raciocínio, não explique, não mostre pensamento. Saída direta apenas."
```
## AUTORIA DE ALTERAÇÕES EM ARQUIVOS

- O ChatGPT é o único responsável por definir e redigir alterações em arquivos do projeto.
- A IA local não deve criar, completar, redesenhar, corrigir ou adaptar conteúdo de arquivos por iniciativa própria.
- A IA local somente pode aplicar conteúdo integral, patch ou alteração literal fornecida pelo ChatGPT.
- Antes da aplicação, a IA local deve gerar e exibir o diff completo da alteração proposta.
- O diff deve conter somente o conteúdo explicitamente aprovado pelo ChatGPT.
- Se houver qualquer alteração adicional, remoção, reordenação, reformatação ou adaptação, a execução deve parar sem aplicar o diff.
- Quando o conteúdo fornecido não puder ser aplicado literalmente, a IA local deve parar e retornar o bloqueio.
- A IA local continua responsável por executar comandos, aplicar patches literais, instalar dependências autorizadas, rodar testes e coletar evidências técnicas.
- Exceções somente são permitidas quando o usuário autorizar explicitamente a IA local a redigir ou decidir o conteúdo.

## Ambiente local e shell

- O sistema operacional do computador local é CachyOS.
- O shell interativo padrão do usuário é Fish, não Bash.
- Comandos destinados a serem copiados e executados diretamente pelo usuário devem usar sintaxe compatível com Fish.
- Não usar atribuição de variável no formato Bash `VAR=valor` em comandos para o terminal do usuário. Em Fish, usar `set VAR valor` ou informar o valor diretamente no comando.
- Quando uma operação exigir Bash, invocar explicitamente `bash -lc '...'` e não assumir que o terminal atual interpreta Bash.
- Em unidades systemd, preferir `ExecStart` com o executável e os argumentos diretamente, sem envolver Fish ou Bash desnecessariamente.
- Scripts existentes devem respeitar o shell declarado no próprio shebang.
