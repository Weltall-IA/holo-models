# Regras locais do benchmark de embeddings

Este arquivo especializa `AGENTS.md` da raiz para todo o conteúdo sob
`benchmark/embedding-v3/`. As proteções de `.ai/WORKFLOW.yml` continuam
integralmente aplicáveis.

## Fontes canônicas

- Métricas numéricas: `ALL_BENCHMARK_RESULTS.json` e os artefatos individuais
  em `results/`.
- Interpretação humana, confiança, modelos reutilizáveis e blacklist:
  `README.md`, na seção `Registro canônico de qualidade dos embeddings`.
- Não usar `LISTA_BLACKLIST.md` da raiz para embeddings; esse arquivo possui
  outro escopo histórico.

## Regra de arquivo único

Não criar novos leaderboards, registries, tabelas de modelos bons, blacklists,
resumos ou relatórios de decisão para embeddings. Atualize as duas tabelas
canônicas do `README.md`. Um novo arquivo desse tipo exige autorização humana
explícita e justificativa de por que o arquivo existente não pode ser usado.

## Política de quantização para 16 GB de VRAM

A seleção de pesos para qualquer embedding ou reranker local deve seguir esta
ordem obrigatória:

1. `NVFP4`, quando existir um artefato confiável, compatível com o runtime e
   identificado para o modelo exato;
2. `Q4` — preferencialmente `Q4_K_M` — quando não houver NVFP4 confiável;
3. `Q8` somente quando **todas** as condições abaixo forem satisfeitas:
   - não existir NVFP4 nem Q4 confiável para o modelo;
   - o modelo for pequeno o bastante para caber com folga na RTX 5060 Ti de
     16 GB, incluindo pesos, KV/cache, buffers e overhead do runtime;
   - o preflight registrar memória prevista e justificar por que Q8 é necessário;
   - houver aprovação explícita no contrato da rodada.

Regras adicionais:

- modelos grandes não devem ser baixados ou retestados em Q8 apenas por maior
  precisão teórica;
- nunca confundir um NVFP4 de outra escala, revisão ou família com o modelo
  pretendido; por exemplo, um NVFP4 oficial de 1B não prova a existência de um
  NVFP4 de 8B;
- na ausência de NVFP4/Q4 confiável, marcar `BLOCKED` em vez de escolher Q8
  silenciosamente;
- resultados históricos Q8 permanecem registrados, mas não obrigam futuras
  rodadas a repetir a mesma quantização;
- qualquer exceção precisa registrar modelo, tamanho, VRAM estimada, motivo,
  aprovação humana e novo `profile_id`.

## Registro de resultados

1. Registre somente métricas realmente obtidas no corpus e protocolo declarados.
2. Atualize arquivos gerados somente pela execução real do gerador correspondente.
3. Mantenha o resultado do embedding sozinho e o resultado com reranker em
   colunas distintas; nunca trate os dois como a mesma medição.
4. Registre o ID exato, revisão ou hash do peso, backend, versão do runtime,
   dimensão, pooling, normalização, prefixes, hardware e caminho do artefato.
5. Modelos sem métricas ficam como `BLOCKED` ou pendentes e não entram no ranking.
6. Alias só herda resultado quando a identidade dos pesos ou da revisão estiver
   comprovada.

## Classificação e blacklist

- `APROVADO` significa que o perfil exato pode ser reutilizado em novas
  comparações; não significa seleção automática para produção.
- A blacklist deve atingir primeiro o artefato, quantização ou configuração
  exatos. Não blacklistar toda a família por uma única execução suspeita.
- Resultado sem proveniência suficiente, duplicação de candidates, divergência
  extrema de fonte externa ou protocolo oficial não comprovado deve ser marcado
  como `BLACKLIST_PROVISÓRIA` ou `BLACKLIST_DO_ARTEFATO` até reexecução limpa.
- Promover uma família inteira à blacklist exige pelo menos duas execuções
  independentes, reproduzíveis e corretamente configuradas.
- Uma entrada só sai da blacklist após novo benchmark completo com evidências
  suficientes; não editar a decisão apenas por reputação do modelo.

## Verificação externa

Model cards oficiais, MTEB, MTEB-BR ou outra avaliação pública servem como
sanity check de ordem e expectativa. Métricas de protocolos diferentes não são
convertidas nem comparadas numericamente como equivalentes. Divergência externa
é sinal para auditoria, não autorização para substituir o resultado local.

## Atualização obrigatória

Após qualquer benchmark novo ou correção de artefato:

1. validar os artefatos e o consolidado;
2. atualizar as duas tabelas do `README.md` quando a decisão mudar;
3. revisar referências e equivalências de variantes;
4. executar as validações aplicáveis do projeto;
5. revisar o diff completo antes de commit e PR.
