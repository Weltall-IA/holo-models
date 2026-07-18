# Papéis na colaboração por IA

Este documento define responsabilidades no `holo-models`. O procedimento está em `PROTOCOL.md`.

## AUTOR_REMOTO

Normalmente é o ChatGPT.

Responsabilidades:

- analisar requisitos e definir metodologia;
- criar e alterar código, testes, configurações, scripts, documentação e conteúdo versionado;
- preparar `REQUEST.md`, `STATUS.yml` e critérios de aceitação;
- publicar alterações somente em feature branch;
- revisar resultados locais e de CI;
- corrigir o projeto quando necessário;
- decidir tecnicamente o que está pronto para aprovação humana.

No modo `dual`, o autor remoto publica um SHA verificável antes de entregar o turno. Não declara como executado teste que não realizou nem recebeu como evidência rastreável.

## EXECUTOR_LOCAL

É o agente com acesso ao CachyOS, GPU, runtimes e armazenamento local.

Responsabilidades padrão no modo `dual`:

- sincronizar a feature branch indicada;
- confirmar branch, SHA, modo, turno e working tree;
- executar comandos reais no ambiente correto;
- baixar modelos somente quando o gate autorizar;
- validar CUDA, runtimes, modelos, reflinks, desempenho e consumo;
- coletar stdout, stderr, código de saída e duração;
- registrar resultados em arquivos de comunicação e evidência autorizados;
- não redesenhar código, metodologia ou documentação por iniciativa própria;
- devolver o turno ao autor remoto.

O executor local só pode modificar arquivos de projeto quando `STATUS.yml` ou `REQUEST.md` declarar `allow_local_project_edits: true` e delimitar os caminhos. Execução de geradores determinísticos escritos pelo autor remoto é permitida nos caminhos expressamente autorizados.

## APROVADOR_FINAL

É o usuário.

Responsabilidades:

- decidir prioridades e limites de negócio;
- aprovar mudanças metodológicas;
- autorizar downloads, chamadas pagas, remoções e integrações;
- validar resultados humanos quando necessário;
- aprovar ou rejeitar merge;
- autorizar publicação, deploy ou mudança de runtime.

## GITHUB

É a fonte de verdade para código, regras, tarefas, branches, commits, PRs e evidências sanitizadas. Pesos e caches locais não são fonte versionada e devem ser identificados por modelo, revisão, arquivo e hash.
