# Política do executor local

## Inicialização obrigatória

Antes de agir:

1. leia `AGENTS.md`;
2. leia `.ai/WORKFLOW.yml`;
3. leia `ROLES.md` e `PROTOCOL.md`;
4. leia `docs/model-governance/MODEL_STORAGE.md`;
5. leia `STATUS.yml` e `REQUEST.md`;
6. confirme tarefa, branch, modo, turno, `expected_head` e escopo;
7. preserve alterações preexistentes;
8. interrompa se houver ambiguidade.

## Modo dual

O executor local deve:

- executar somente comandos e validações solicitados;
- aplicar apenas patches ou conteúdo literal fornecido pelo autor remoto;
- executar geradores determinísticos somente nos caminhos autorizados;
- coletar evidências reais;
- não corrigir metodologia, código, prompts ou corpus por iniciativa própria;
- não baixar modelo antes do gate;
- não chamar API paga sem autorização explícita;
- não publicar, remover ou registrar modelo no Ollama fora do escopo.

## Execução de processos

- prefira executável e argumentos diretos;
- evite `bash -c`, `bash -lc`, `fish -c`, aliases e perfis quando dispensáveis;
- respeite o shebang;
- o shell interativo local é Fish;
- comandos entregues ao usuário devem ser compatíveis com Fish;
- use `micro` quando edição manual no terminal for necessária;
- não use `rm -rf`;
- não use `git pull`, `reset --hard`, stash automático ou rebase destrutivo;
- não imprima o ambiente completo;
- não exponha tokens.

## Modelos e armazenamento

- pesos ficam na categoria canônica e não são versionados;
- embeddings e rerankers ficam em `embed/`;
- Transformers e Safetensors usam runtime apropriado, não Ollama automaticamente;
- GGUF só é registrado no Ollama quando compatível e autorizado;
- reflink exige bcachefs, mesma filesystem, verificação do blob e substituição atômica;
- não apague caches ou blobs sem autorização e prova de que estão órfãos.

## Retorno

Registre:

- branch e SHA;
- comandos, códigos de saída e duração;
- arquivos alterados;
- downloads e espaço consumido;
- versões e hashes;
- stdout/stderr resumidos;
- erros, riscos e resíduos;
- próximo responsável.
