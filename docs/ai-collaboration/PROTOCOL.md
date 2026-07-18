# Protocolo de colaboração por IA

## Princípios

- O GitHub é a fonte de verdade para conteúdo versionado.
- Toda edição ocorre em feature branch; a branch principal é `master`.
- O SHA recebido e o SHA executado devem ser rastreáveis.
- Resultados devem corresponder a execuções reais.
- Alterações preexistentes devem ser preservadas.
- Force push, merge automático e publicação automática são proibidos.
- Segredos, tokens e credenciais não entram em commits, logs publicados ou relatórios.
- Pesos de modelos, caches e artefatos volumosos não são versionados.
- O comportamento é definido pelo papel e pelo modo, não pela ferramenta.

## Resolução do modo

1. `mode` de `.ai/tasks/<task-id>/STATUS.yml`, quando existir;
2. modo ativo em `.ai/WORKFLOW.yml`;
3. ausência de modo válido: interromper.

Valores válidos: `dual`, `remoto`, `local`.

## Preparação comum

Antes de editar ou executar:

1. ler `AGENTS.md`, workflow, papéis, protocolo e política local;
2. ler `REQUEST.md` e `STATUS.yml`;
3. confirmar repositório, tarefa, modo, turno, branch, base e `expected_head`;
4. ler regras de armazenamento e os arquivos diretamente envolvidos;
5. confirmar que a branch não é `master`;
6. inspecionar alterações preexistentes;
7. sincronizar referências sem `pull`, stash ou reset destrutivo automático;
8. executar somente o trabalho compatível com o turno.

## Modo dual — autor remoto

1. criar ou selecionar feature branch baseada no HEAD confirmado de `master`;
2. definir objetivo, escopo, critérios, arquivos e validações;
3. alterar os arquivos do projeto;
4. revisar o diff;
5. publicar commits na feature branch;
6. registrar `expected_head`;
7. entregar o turno com:

```yaml
status: pronto-para-execucao-local
turn: executor-local
```

## Modo dual — executor local

1. sincronizar a mesma feature branch;
2. confirmar working tree e SHA;
3. interromper em caso de divergência;
4. executar somente as validações e mutações de runtime autorizadas;
5. coletar executável, argumentos, diretório, ambiente não secreto, stdout, stderr, código e duração;
6. não modificar conteúdo versionado fora dos caminhos explicitamente autorizados;
7. registrar `EXECUTION.md` e atualizar `STATUS.yml`;
8. publicar apenas arquivos permitidos;
9. devolver:

```yaml
status: pronto-para-revisao-remota
turn: autor-remoto
last_actor: executor-local
```

## Modo remoto

O autor remoto planeja, implementa e revisa em feature branch. Validações não executadas são declaradas. Pull request é aberto sem merge automático.

## Modo local

O executor local assume o ciclo completo em feature branch, mas continua proibido de fazer merge, publicar modelos ou remover dados sem autorização humana.

## Arquivos de comunicação

Por padrão, o executor local pode modificar:

- `.ai/tasks/<task-id>/EXECUTION.md`;
- `.ai/tasks/<task-id>/STATUS.yml`;
- arquivos adicionais explicitamente listados em `REQUEST.md`.

## Divergências

- SHA divergente: bloquear e registrar esperado/atual.
- Branch incorreta: não editar até preservar o estado.
- Alterações preexistentes: não usar `reset --hard`, stash automático ou sobrescrita.
- Segredo detectado: interromper publicação e não reproduzir o valor.
- OOM ou falha CUDA: registrar; não alterar driver ou sistema sem nova autorização.
- Download, custo ou licença divergente: interromper antes de baixar.
- Turno incorreto: devolver ao responsável.
