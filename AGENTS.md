# AGENTS.md — Regras permanentes para agentes

Estas regras valem para qualquer IA, automação ou operador que trabalhe no repositório `Weltall-IA/holo-models`.

## Finalidade do repositório

Este repositório governa modelos locais do Projeto Holo:

- inventário e documentação;
- configurações e `Modelfile`;
- scripts operacionais;
- benchmarks reproduzíveis;
- regras de armazenamento, runtimes e reflink;
- evidências sanitizadas;
- tarefas versionadas para colaboração entre agentes.

Pesos, caches, bancos, tokens e artefatos volumosos não são publicados no GitHub.

## Inicialização obrigatória

Antes de planejar, editar arquivos ou executar comandos:

1. leia `.ai/WORKFLOW.yml`;
2. leia `docs/ai-collaboration/ROLES.md`;
3. leia `docs/ai-collaboration/PROTOCOL.md`;
4. quando ocupar o papel de executor local, leia `docs/ai-collaboration/LOCAL_EXECUTOR.md`;
5. leia `.ai/tasks/<task-id>/STATUS.yml` e `REQUEST.md`, quando existirem;
6. leia `docs/model-governance/MODEL_STORAGE.md`;
7. leia instruções específicas do diretório, scripts e arquivos diretamente envolvidos.

Não presuma que uma referência textual significa que o conteúdo já foi carregado.

## Modo operacional

A precedência é:

1. modo da tarefa;
2. modo global;
3. ausência de modo válido: interromper.

Os modos válidos são `dual`, `remoto` e `local`.

Confirme repositório, branch, HEAD, tarefa, modo, turno, escopo, runtime e restrições antes de editar ou executar.

## Fonte de verdade

O GitHub é a fonte de verdade para:

- regras;
- código e scripts;
- branches, commits e pull requests;
- tarefas e decisões;
- metadados, hashes e revisões;
- evidências sanitizadas.

O armazenamento local é a fonte física dos pesos, mas cada modelo deve ser identificável por repositório, revisão, arquivo, quantização e hash.

## Regras Git

- Não trabalhar diretamente em `master` ou branch protegida.
- Criar ou selecionar feature branch antes de editar.
- Preservar alterações preexistentes.
- Sincronizar referências e confirmar o HEAD.
- Não usar force push.
- Não fazer merge, release, publicação, deploy ou remoção sem autorização humana.
- Não usar `git pull`, stash automático, `reset --hard` ou rebase destrutivo automaticamente.
- Revisar o diff completo antes de commit e push.
- Não incluir arquivos fora do escopo.

Em checkout local, execute o equivalente a:

```text
git status --short
git branch --show-current
git fetch origin
git rev-parse HEAD
git rev-parse origin/master
```

## Papéis no modo dual

O `AUTOR_REMOTO` cria e altera conteúdo versionado. O `EXECUTOR_LOCAL` executa comandos, valida o ambiente, baixa modelos quando autorizado e coleta evidências.

O executor local não modifica conteúdo de projeto por padrão. A exceção exige em `STATUS.yml` ou `REQUEST.md`:

```yaml
allow_local_project_edits: true
```

A autorização deve listar caminhos e comportamento permitidos. Uma falha não autoriza correção automática.

## Autoria de alterações

- O ChatGPT é o responsável padrão por definir e redigir alterações em arquivos do projeto.
- A IA local não cria, completa, redesenha, corrige ou adapta conteúdo versionado por iniciativa própria.
- A IA local aplica conteúdo integral, patch literal ou executa geradores determinísticos fornecidos pelo autor remoto.
- Antes de aplicar patch manual, deve exibir o diff completo.
- Se houver alteração adicional, remoção, reordenação, reformatação ou adaptação não autorizada, deve parar.
- Quando o conteúdo não puder ser aplicado literalmente, deve retornar o bloqueio.
- A IA local pode instalar dependências autorizadas, rodar comandos, testes e benchmarks e coletar evidências.
- Exceções exigem autorização humana explícita.

## Categorias de modelos

Cada modelo baixado deve ficar na categoria principal:

- `text/` — LLMs, chat, restauração de pontuação e texto;
- `audio/` — ASR, Whisper, TTS, voz e áudio;
- `video/` — upscaling, RIFE, CUDA e vídeo;
- `image/` — diffusion, super-resolution e faces;
- `embed/` — embeddings e rerankers.

Não duplique pesos entre categorias. Registre usos adicionais em metadados.

## Nomenclatura e inventário

- Use o nome oficial ou do repositório Hugging Face.
- Não use espaços.
- Inclua a quantização no nome da pasta quando aplicável.
- Mantenha um único diretório físico canônico.
- Antes de registrar no Ollama, verifique `ollama list`.
- Após validação, atualize `LISTA_MODELOS.md`.
- Modelos reprovados em pontuação do Whisper entram em `LISTA_BLACKLIST.md` somente após validação humana.

## Ollama, formatos e runtimes

- Crie `Modelfile` somente para modelo realmente compatível.
- Execute `ollama create` dentro da pasta do modelo quando caminhos relativos forem usados.
- Transformers, Diffusers, Whisper, ONNX, Safetensors e pipelines não compatíveis permanecem no runtime apropriado.
- Se Ollama falhar por incompatibilidade, registre `OLLAMA_INCOMPATIVEL.txt` com erro sanitizado.
- Não force conversão, registro ou alteração de arquitetura silenciosamente.
- O campo `FROM` pode apontar para arquivo, diretório compatível ou modelo registrado, conforme suporte real do runtime.

## Reflink bcachefs

O Ollama pode criar uma segunda cópia temporária dos pesos. Após validação, o blob do Ollama pode se tornar a fonte física e o arquivo canônico pode ser substituído por reflink CoW.

Antes da troca, confirme:

- modelo funcional;
- blob correto;
- mesma filesystem bcachefs;
- reflink obrigatório sem fallback para cópia normal;
- arquivo temporário com tamanho esperado.

Faça substituição atômica. Não aplique a modelos compostos sem um único blob GGUF identificável.

## Remoção e anti-órfão

Ao remover um modelo canônico, remova o registro correspondente do Ollama quando existir. Limpeza de blobs exige cruzar manifests e digests e provar que não há referência. Não apague caches, pesos ou blobs sem autorização.

## Benchmarks

- Metodologia, corpus, prompts e métricas devem ser versionados.
- Resultados devem indicar modelo, revisão, backend, dimensão, dtype, normalização e hardware.
- Não altere corpus congelado para favorecer um modelo.
- Não escolha vencedor silenciosamente.
- Não execute gate posterior sem autorização.
- Não chame API paga sem autorização explícita.
- Não registre segredo em cache, log ou relatório.
- Pesos baixados para benchmark ficam em `embed/` ou runtime autorizado e continuam ignorados pelo Git.
- Resultados brutos volumosos podem ficar em caminho ignorado; sumários e evidências sanitizadas devem ser versionados quando a tarefa exigir.

## Segurança e licenças

- Não registrar tokens, chaves, cookies, credenciais, `.env`, certificados, dumps ou dados pessoais.
- Não expor segredo em stdout ou relatório.
- Não contornar licença, autenticação, quota, paywall, CAPTCHA ou termos.
- Não remover DRM, marca-d'água ou atribuição.
- Confirme licença e aceite antes de baixar modelo restrito.
- O repositório é público; qualquer conteúdo versionado deve ser seguro para publicação pública.

## Execução de processos

- Prefira executável, argumentos, diretório, ambiente não secreto e timeout explícitos.
- Evite `bash -c`, `bash -lc`, `fish -c`, aliases, funções e perfis quando dispensáveis.
- Respeite o shebang.
- O computador local usa CachyOS e Fish.
- Comandos interativos entregues ao usuário devem ser compatíveis com Fish.
- Quando Bash for indispensável, invoque-o explicitamente.
- Use `micro` quando edição manual no terminal for necessária.
- Não use `rm -rf`.
- Identifique o runtime e ambiente virtual realmente usados.
- Não imponha editor, shell, modelo ou ferramenta além do necessário para a tarefa.

## Testes e evidências

- Não invente comandos, resultados, versões, hashes, desempenho ou validações.
- Declare explicitamente tudo que não foi executado.
- Não desative teste para obter sucesso.
- Não considere tarefa concluída apenas porque um comando retornou zero.
- Registre stdout, stderr, código de saída e duração quando aplicável.
- Associe resultados ao SHA executado.
- Revise `git diff --check`, `git diff --stat` e o diff dos arquivos alterados.
- Confirme que nenhum segredo ou peso foi incluído.

## Interrupções obrigatórias

Interrompa diante de:

- branch, SHA, modo ou turno divergente;
- alteração preexistente que possa ser sobrescrita;
- risco de perda de dados;
- segredo ou licença não resolvida;
- download sem espaço suficiente;
- modelo, arquivo ou revisão diferente do autorizado;
- ação destrutiva;
- custo não autorizado;
- OOM ou falha CUDA que exigiria alterar o sistema;
- conflito entre runtime e documentação;
- tentativa de editar fora do escopo.

O formato de retorno e os responsáveis por cada turno estão em `docs/ai-collaboration/PROTOCOL.md`.
