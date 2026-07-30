# INSTRUCTIONS v1.2 — uso obrigatório de `hf_tokens` para Hugging Face

## Aplicação

Esta versão complementa e corrige `INSTRUCTIONS-v1.1.md`. Todas as regras de quantização, telemetria, benchmark raw, rerankers, consolidação e segurança da v1.1 continuam integralmente válidas.

A partir desta versão, toda operação da IA local que consulte ou baixe artefatos do Hugging Face deve obedecer também à seção `huggingface_download_policy` de:

`benchmark/embedding-v3/config/CANONICAL_BENCHMARK_CANDIDATES.json`

## Arquivo obrigatório

Usar sempre o arquivo local de segredo:

`hf_tokens`

para autenticar downloads e consultas ao Hugging Face que necessitem token.

Antes de qualquer chamada ao Hugging Face:

1. localizar o arquivo `hf_tokens` no ambiente local conforme o fluxo já adotado pelo operador;
2. confirmar somente que ele existe, é arquivo regular e está legível;
3. carregar o token a partir desse arquivo sem imprimir seu conteúdo;
4. passar o token ao cliente ou comando de download de forma que não apareça em argumentos registrados, logs, traces, histórico do shell ou artefatos versionados;
5. registrar apenas o caminho sanitizado utilizado, a existência, as permissões relevantes e o sucesso ou falha da autenticação.

## Proibições

É proibido:

- pedir ao usuário para colar o token no chat ou terminal;
- executar login interativo do Hugging Face;
- usar token escrito diretamente no comando;
- imprimir, ecoar, registrar, hashear ou incluir o conteúdo de `hf_tokens` em relatórios;
- copiar `hf_tokens` para a worktree, branch, cache versionado, artefato ou PR;
- commitar `hf_tokens` ou qualquer derivado que contenha o segredo;
- substituir silenciosamente o arquivo por `HF_TOKEN`, `HUGGING_FACE_HUB_TOKEN` ou outro segredo de ambiente sem autorização explícita do usuário;
- iniciar download autenticado se `hf_tokens` estiver ausente ou ilegível.

Se o arquivo estiver ausente ou ilegível, registrar:

`BLOCKED_HF_TOKEN_FILE_UNAVAILABLE`

com caminho esperado, tipo de falha e condição de desbloqueio, sem revelar segredo e sem remover o candidato da fila.

## Downloads quantizados

O uso de `hf_tokens` não altera a prioridade de artefatos. Antes de baixar, continuar obedecendo:

1. NVFP4;
2. Q4_K_M;
3. outro Q4 comprovado somente quando os anteriores não existirem ou forem incompatíveis.

O token serve apenas para acesso ao Hugging Face. Ele não autoriza download de FP32, FP16, BF16, Q8 proibido, revisão diferente ou artefato não resolvido previamente.

## Retorno obrigatório

Além do retorno das versões anteriores, informar:

1. se `hf_tokens` foi localizado e estava legível, sem mostrar conteúdo;
2. quais downloads ou consultas Hugging Face usaram autenticação via arquivo;
3. confirmação de que nenhum token apareceu em comandos, logs, artefatos, diff ou PR;
4. qualquer bloqueio `BLOCKED_HF_TOKEN_FILE_UNAVAILABLE`.

Frase final obrigatória:

`Downloads do Hugging Face autenticados exclusivamente pelo arquivo local hf_tokens, sem exposição ou versionamento do segredo.`
