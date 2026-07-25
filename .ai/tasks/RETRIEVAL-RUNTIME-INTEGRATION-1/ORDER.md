# Ordem — Integração de runtime dos perfis de retrieval

## Identificação

- Repositório: `Weltall-IA/holo-models`
- Checkout local esperado: `/home/alpha/Playstoria/models`
- Branch de trabalho já criada: `ai/retrieval-runtime-integration-v1`
- Base da branch: `master` no commit `1814a37fa8bb6814cc16335fb3337813c95d754d`
- Configuração canônica: `benchmark/embedding-v3/config/production_profiles.json`

## Objetivo verificável

Criar e validar uma camada de execução uniforme para os perfis de retrieval já aprovados, de modo que uma aplicação consiga selecionar um perfil por ID, enviar textos e receber embeddings por um contrato estável, sem conhecer detalhes de llama.cpp, vLLM ou APIs externas.

A tarefa deve comprovar no host local a integração de:

1. `local_default`;
2. `nemotron_gguf_evaluation`;
3. `nemotron_nvfp4_evaluation`.

O perfil `quality_external_optional` deve ter somente o bloqueio de autorização validado. Nenhuma API paga deve ser chamada nesta tarefa.

Esta tarefa não escolhe um novo perfil padrão, não habilita perfis atualmente desabilitados e não faz deploy.

## Inicialização obrigatória

Antes de alterar qualquer arquivo:

1. confirme que `pwd`, `git rev-parse --show-toplevel` e `git remote get-url origin` correspondem ao checkout e ao remote acima;
2. leia integralmente:
   - `AGENTS.md`;
   - `.ai/PROJECT.yml`;
   - `.ai/WORKFLOW.yml`;
   - este `ORDER.md`;
   - `benchmark/embedding-v3/config/production_profiles.json`;
   - `benchmark/embedding-v3/PRODUCTION_PROFILE_DECISION.md`;
3. execute `git fetch --prune origin`;
4. mude para `ai/retrieval-runtime-integration-v1` e confirme que ela contém este arquivo;
5. inspecione branch, upstream, staged, unstaged, não versionados, worktrees e stashes;
6. preserve integralmente qualquer trabalho preexistente fora do escopo, incluindo, quando presentes:
   - `benchmark/embedding-v3/run_voyage.py`;
   - `comandos.md`;
   - `runtime/vane-native-ops/`.

Não use stash automático, `reset --hard`, force-push ou remoção de arquivos não versionados.

## Escopo incluído

### 1. Carregador e contrato de perfis

Implemente um módulo reutilizável, preferencialmente:

`benchmark/embedding-v3/holo_benchmark/production_profile_runtime.py`

O módulo deve:

- carregar `config/production_profiles.json`;
- selecionar perfil por `id`;
- validar o perfil antes de executá-lo;
- rejeitar IDs desconhecidos;
- rejeitar perfil desabilitado salvo quando a chamada declarar explicitamente modo de avaliação;
- rejeitar qualquer perfil com `requires_api: true` sem autorização explícita;
- nunca ler, imprimir ou persistir tokens;
- expor uma interface uniforme para embeddings, independentemente do backend;
- permitir injeção de backend falso nos testes unitários;
- sanitizar mensagens de erro antes de gravá-las em evidências.

Defina um contrato simples e estável:

### Entrada lógica

```json
{
  "schema_version": "1.0",
  "profile_id": "local_default",
  "evaluation_mode": false,
  "input_type": "document",
  "texts": ["texto 1", "texto 2"]
}
```

Regras:

- `input_type`: somente `document` ou `query`;
- `texts`: lista não vazia de strings não vazias;
- limite defensivo configurável para quantidade e tamanho total dos textos;
- nenhum caminho de arquivo, shell ou argumento de runtime fornecido pelo usuário deve ser executado diretamente.

### Saída lógica

A interface Python deve retornar:

```json
{
  "schema_version": "1.0",
  "profile_id": "local_default",
  "backend": "llama.cpp",
  "dimension": 768,
  "normalized": true,
  "embeddings": [[0.0]],
  "runtime_metadata": {}
}
```

O runner de integração não deve versionar vetores completos. Evidências persistidas devem conter somente métricas, hashes determinísticos das representações serializadas, dimensões, normas, tempos e estado sanitizado.

### 2. Backends locais

Reutilize a infraestrutura existente do benchmark sempre que possível. Não crie uma segunda implementação completa de carregamento se o código existente puder ser extraído ou encapsulado com alteração pequena.

#### `local_default`

- embedding `embeddinggemma_768_float32`;
- backend llama.cpp;
- localizar o peso local usando os dados versionados e a identidade SHA-256 esperada;
- não baixar nem copiar pesos;
- validar dimensão 768, finitude e normalização L2.

#### `nemotron_gguf_evaluation`

- backend llama.cpp;
- peso Nemotron 1B Q4_K_M identificado pelo SHA-256 do perfil;
- executar apenas em `evaluation_mode: true`;
- não alterar `enabled: false`;
- validar dimensão declarada no perfil, finitude e normalização L2.

#### `nemotron_nvfp4_evaluation`

- backend vLLM no ambiente isolado já existente;
- reutilizar `/tmp/vllm-env` somente se ele existir e for compatível;
- reutilizar kernels/cache já compilados;
- não iniciar nova compilação pesada de kernels nesta tarefa;
- se modelo, ambiente ou cache indispensável estiver ausente, registrar bloqueio exato e continuar os demais perfis;
- não usar Transformers, Sentence Transformers, Ollama ou llama.cpp como substituto silencioso do NVFP4;
- validar dimensão declarada no perfil, finitude e normalização L2.

#### `quality_external_optional`

- não chamar Voyage nem qualquer API externa;
- provar por teste que a execução é recusada sem autorização;
- provar que nenhum token é lido durante essa recusa;
- manter `enabled: false`.

### 3. Runner de integração

Crie um CLI, preferencialmente:

`benchmark/embedding-v3/production_profile_integration.py`

Com suporte mínimo a:

- `--profile <id>`;
- `--evaluation-mode`;
- `--input <json>` opcional;
- `--output <json>`;
- `--smoke`;
- `--dry-run`;
- `--allow-external-api`, que deve continuar sem uso nesta tarefa e exigir uma segunda condição de autorização definida em configuração ou ambiente; não aceite a flag isolada como autorização suficiente.

O modo `--dry-run` deve validar configuração, modelo esperado, runtime necessário e comando planejado sem carregar pesos.

O modo `--smoke` deve usar textos existentes do corpus congelado. Não gere nem altere corpus. Use uma amostra pequena e determinística de documentos e consultas em português.

### 4. Verificações do smoke test real

Para cada perfil local executável, valide:

- número de vetores igual ao número de textos;
- dimensão exatamente igual à configuração;
- todos os valores finitos;
- norma L2 dentro de tolerância documentada;
- execução repetida do mesmo texto com similaridade de cosseno próxima de 1;
- ausência de vetores vazios ou constantes;
- resposta compatível com o contrato uniforme;
- erro sanitizado e processo encerrado quando o runtime falhar;
- nenhum processo de modelo deixado ativo após o teste;
- startup e tempo total registrados apenas como diagnóstico, sem reinterpretar o benchmark de admissão.

Não compare qualidade entre os perfis nesta tarefa. Este é teste de integração, não novo benchmark.

### 5. Evidências versionadas

Crie, por execução real:

- `benchmark/embedding-v3/results/production_profile_integration/local_default.json`;
- `benchmark/embedding-v3/results/production_profile_integration/nemotron_gguf_evaluation.json`;
- `benchmark/embedding-v3/results/production_profile_integration/nemotron_nvfp4_evaluation.json`;
- `benchmark/embedding-v3/results/production_profile_integration/quality_external_optional_guard.json`;
- `benchmark/embedding-v3/results/production_profile_integration/summary.json`;
- `benchmark/embedding-v3/PRODUCTION_PROFILE_INTEGRATION_REPORT.md`.

Cada resultado deve conter:

- perfil e backend;
- estado: `PASSED`, `FAILED` ou `BLOCKED`;
- motivo sanitizado;
- revisão/identidade do peso quando aplicável;
- dimensão e quantidade de vetores;
- faixa de normas;
- métrica de repetibilidade;
- tempos diagnósticos;
- comando lógico executado, sem segredo e sem caminhos sensíveis desnecessários;
- versão do runtime;
- hardware relevante;
- SHA-256 do arquivo de peso já conhecido ou realmente conferido;
- nenhuma embedding completa.

O resumo deve indicar separadamente:

- `application_contract_ready`;
- `local_default_ready`;
- `nemotron_gguf_ready`;
- `nemotron_nvfp4_ready`;
- `external_api_guard_ready`;
- bloqueios reais.

### 6. Testes automatizados

Adicione testes unitários, preferencialmente em:

`benchmark/embedding-v3/tests/test_production_profile_runtime.py`

Cubra no mínimo:

- carregamento e seleção dos quatro perfis;
- ID inexistente;
- entrada vazia ou inválida;
- bloqueio de perfil desabilitado fora do modo de avaliação;
- bloqueio de API sem autorização;
- impossibilidade de a flag externa isolada liberar API;
- backend falso retornando contrato válido;
- dimensão divergente;
- NaN/Inf;
- normalização inválida;
- sanitização de erro;
- serialização das evidências sem embeddings completas.

Não faça testes unitários dependerem de GPU, modelos ou rede. Os testes reais de runtime ficam no smoke de integração.

## Decisões após os testes

- Não altere o campo `enabled` de nenhum perfil.
- Não torne Nemotron padrão nesta tarefa.
- Se `local_default` passar, registre-o como pronto para consumo pela aplicação.
- Se um perfil Nemotron passar, registre-o como pronto para integração experimental, mantendo-o desabilitado.
- Se o NVFP4 estiver bloqueado somente por cache/ambiente ausente, não compile nem reinstale automaticamente; documente o bloqueio exato.
- Se um defeito no código do runner for encontrado, corrija e repita somente as validações afetadas.
- Não altere resultados históricos do benchmark para fazer o smoke passar.

## Fora do escopo

- alterações em `Weltall-IA/infra-holoplay` ou outro repositório;
- deploy, systemd, containers de produção ou serviços persistentes;
- ativação de API paga;
- leitura de token Voyage;
- mudança do perfil padrão da aplicação;
- download, movimentação, reflink, conversão ou remoção de pesos;
- recompilação pesada de NVFP4;
- repetição dos benchmarks de 600 documentos e 150 consultas;
- alteração do corpus congelado;
- publicação de modelos.

## Validações obrigatórias

Execute as aplicáveis e corrija falhas do escopo:

1. `python -B .ai/validate_governance.py`;
2. suíte completa de testes em `benchmark/embedding-v3/tests`;
3. validação existente de `production_profiles.json`;
4. `python -m compileall -q benchmark/embedding-v3`;
5. parse de JSON e YAML alterados/gerados;
6. detecção de chaves YAML duplicadas;
7. `git diff --check`;
8. scan sanitizado de segredos no diff;
9. dry-run dos quatro perfis;
10. smoke real de `local_default`;
11. smoke real de `nemotron_gguf_evaluation`;
12. smoke real de `nemotron_nvfp4_evaluation`, quando ambiente/cache estiver disponível;
13. teste do bloqueio de `quality_external_optional` sem ler token;
14. confirmação de que nenhum processo de runtime ficou ativo;
15. revisão integral do diff final.

Não declare teste como aprovado sem execução real.

## Git e publicação

- trabalhe somente em `ai/retrieval-runtime-integration-v1`;
- inclua somente arquivos desta tarefa;
- não reescreva o commit que contém este `ORDER.md`;
- use commits objetivos;
- publique a branch sem force-push;
- abra PR para `master` com o título:

`feat(models): integrar runtime dos perfis de retrieval`

Se todos os gates rotineiros estiverem satisfeitos, não houver mudança de perfil habilitado, API, deploy, segredo, conflito ou ação destrutiva, retire do draft e faça merge normal no `master` sem nova confirmação.

Se houver condição sensível real, deixe o PR pronto e informe apenas o bloqueio concreto.

## Retorno obrigatório e curto

Retorne somente:

1. `Contrato`: criado e estado;
2. `Perfis`: uma linha por perfil com `PASSED`, `FAILED` ou `BLOCKED`;
3. `Testes`: total aprovado/falha;
4. `Arquivos principais`: lista curta;
5. `PR`: número e estado;
6. `Merge`: SHA ou bloqueio real;
7. `Próxima ação`: integração do contrato no repositório consumidor, caso o contrato esteja pronto.

Não repita a ordem, não liste todos os comandos e não produza relatório narrativo no chat.