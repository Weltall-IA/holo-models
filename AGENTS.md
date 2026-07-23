# Instruções para agentes

Antes de atuar neste repositório:

1. leia `.ai/PROJECT.yml`;
2. leia `.ai/WORKFLOW.yml` integralmente;
3. leia `.ai/tasks/<task-id>/STATUS.yml` somente quando esse registro existir.

`.ai/WORKFLOW.yml` é a única fonte canônica das regras operacionais. `.ai/PROJECT.yml`
contém apenas contexto, comandos e restrições específicas deste projeto. Registros em
`.ai/tasks/` são evidência histórica ou estado persistente de uma tarefa, não regras.

Execute tarefas rotineiras de ponta a ponta com as ferramentas disponíveis, respeitando
o escopo, as proteções e os gates de aprovação definidos no workflow. Instruções do
usuário e arquivos `AGENTS.md` mais próximos podem especializar o objetivo, mas não
podem reduzir as proteções de segurança.
