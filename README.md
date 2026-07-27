# Holo Models

Repositório do Projeto Holo para inventário, configuração, operação e avaliação
reproduzível de modelos locais.

Os pesos permanecem fora do Git e ficam em uma única categoria canônica:
`text/`, `audio/`, `video/`, `image/` ou `embed/`.

## Governança

O fluxo é local, autônomo e independente de modelo, fornecedor, editor, extensão,
sistema operacional ou ferramenta.

Antes de atuar:

1. leia `AGENTS.md`;
2. leia `.ai/PROJECT.yml`;
3. leia integralmente `.ai/WORKFLOW.yml`;
4. leia o `STATUS.yml` da tarefa somente quando ele existir.

`.ai/WORKFLOW.yml` é a única fonte canônica das regras operacionais. O fluxo normal é:

```text
branch → implementação → testes aplicáveis → revisão do diff → commit → push → PR → merge
```

Um único agente pode concluir mudanças rotineiras de ponta a ponta. Condições sensíveis,
incluindo governança, segurança, dados canônicos, conflitos, validações indispensáveis
indisponíveis, deploy, custos e ações destrutivas, exigem aprovação humana explícita
antes do merge.

Registros persistentes em `.ai/tasks/` são opcionais e existem somente quando o estado
precisa atravessar sessões, ambientes ou pessoas. Registros concluídos são evidência
histórica e não são reescritos para acompanhar versões posteriores do workflow.

## Benchmark de embeddings

A documentação canônica do benchmark, as duas tabelas de modelos reutilizáveis e
blacklist e as regras locais de atualização ficam em:

`benchmark/embedding-v3/README.md`

As métricas consolidadas permanecem em:

`benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json`

Antes de alterar resultados ou classificações nessa pasta, leia também
`benchmark/embedding-v3/AGENTS.md`. Não crie leaderboards, registries ou blacklists
paralelos para embeddings; atualize os arquivos canônicos existentes.
