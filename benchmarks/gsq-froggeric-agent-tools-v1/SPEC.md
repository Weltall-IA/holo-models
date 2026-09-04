# GSQ Froggeric Agent / Tool-Calling Benchmark v1

## Objetivo

Medir se o **Froggeric v22.5** melhora o comportamento agentic/tool-calling do `Qwen3.8-27B GSQ-RCO IQ2_S` em relação ao template nativo embutido no GGUF.

Este benchmark é deliberadamente pequeno: **8 casos canônicos × 2 condições = 16 execuções**.

Não adicionar casos, seeds, variantes de template, DFlash2 ou repetições nesta rodada.

## Fonte canônica dos casos

Use exatamente:

`benchmarks/gsq-froggeric-agent-tools-v1/CASES.json`

Os 8 casos e seus stubs de ferramentas foram definidos canonicamente no GitHub. O executor local pode implementar o runner/evaluator, mas **não pode inventar, substituir, reescrever ou enfraquecer casos, resultados de ferramentas, critérios ou expectativas**.

## Modelo e runtime

Target:

`/home/alpha/Playstoria/models/text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-IQ2_S/Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf`

Runtime:

`/home/alpha/.local/bin/llama`

Envelope comum aos dois braços:

- `ctx=8192`
- `np=1`
- `-ngl 999`
- Flash Attention ON
- `--fit off`
- KV K `q8_0`
- KV V `q4_0`
- 8 threads / 8 batch threads
- `--jinja`
- `--reasoning-format deepseek`
- reasoning final OFF
- mesma versão/build/commit do runtime nos dois braços
- um servidor por vez
- sem DFlash2

## Froggeric upstream fixado

Use o arquivo já versionado localmente:

`/home/alpha/Playstoria/models/text/froggeric-Qwen-Fixed-Chat-Templates-v22.5/chat_template.jinja`

Esperado:

- repo: `froggeric/Qwen-Fixed-Chat-Templates`
- revisão: `4ea21db90694e60d002500dae85ebff26e4b23ad`
- versão interna: `qwen3.8-froggeric-v22.5`
- SHA256 local versionado: `e57684bae4156211a55473c5a63be976a405a37ab5be5ae0e5abf1df5349c4b2`

Validar tudo antes da geração.

### Formato de tool call para llama.cpp

O Froggeric usa XML como formato canônico padrão, mas fornece `tool_call_format="json"` especificamente como override para setups cujo parser interno exige Hermes-style JSON, caso do harness OpenAI-compatible do `llama-server` usado aqui.

Portanto, para **ambos os braços**, passe os mesmos kwargs de template:

```json
{"enable_thinking":false,"reasoning_effort":"none","tool_call_format":"json"}
```

Isso mantém os kwargs constantes e isola a troca do arquivo de template tanto quanto o runtime permite.

Não editar o Jinja.

## Braço N — GSQ template nativo

Servidor com o template embutido no GGUF.

Usar:

- `--jinja`
- `--reasoning-format deepseek`
- `--chat-template-kwargs '{"enable_thinking":false,"reasoning_effort":"none","tool_call_format":"json"}'`
- `--reasoning off`

**Não** passar `--chat-template-file` neste braço.

Executar T01–T08 exatamente uma vez cada.

Total: **8 execuções**.

## Braço F — GSQ + Froggeric v22.5

Mesmo envelope do Braço N, alterando somente a seleção explícita do template externo:

- `--chat-template-file /home/alpha/Playstoria/models/text/froggeric-Qwen-Fixed-Chat-Templates-v22.5/chat_template.jinja`

Manter os mesmos kwargs:

```json
{"enable_thinking":false,"reasoning_effort":"none","tool_call_format":"json"}
```

Executar T01–T08 exatamente uma vez cada.

Total: **8 execuções**.

## Protocolo OpenAI-compatible de ferramentas

Cada caso deve ser enviado a `/v1/chat/completions` usando o campo real `tools` da API, construído a partir do `tool_catalog` e da lista `tools` do caso em `CASES.json`.

Não serializar os schemas manualmente dentro do user prompt.

Request inicial por caso:

- `messages`: system canônico + user do caso
- `tools`: somente as ferramentas listadas naquele caso
- `tool_choice: "auto"`
- `temperature: 0.0`
- `top_p: 1.0`
- `seed: 9137`
- `max_tokens: 384` por turno de assistant
- stream pode ser ligado ou desligado, mas deve ser idêntico nos dois braços

Quando o assistant retornar `tool_calls`:

1. validar nome e argumentos;
2. executar **somente o stub canônico** correspondente em `CASES.json`;
3. anexar a resposta como mensagem `role=tool`, preservando `tool_call_id` e nome quando o runtime/API exigir;
4. chamar novamente o modelo com o histórico completo;
5. continuar até resposta final ou limite de 4 rounds de ferramentas.

Nunca executar ferramentas reais do sistema para responder aos casos. Os stubs de `CASES.json` são o mundo fechado do benchmark.

Se uma chamada não corresponder a nenhum stub, retornar exatamente o `default_unmatched_tool_result` definido em `CASES.json` e registrar a violação.

### Dependência entre chamadas

Nos casos T05, T06 e T07 existem chamadas dependentes de resultados anteriores. Uma chamada dependente emitida antes de o modelo receber o resultado necessário deve ser marcada como erro de sequência, mesmo que o argumento acabe coincidindo por sorte.

## Clean-GPU gate

Corretude agentic é a métrica primária; throughput é secundário. Ainda assim, para tornar a telemetria comparável:

Antes de cada braço:

1. registrar `nvidia-smi`;
2. coletar 5 amostras de `nvidia-smi pmon`;
3. se processo externo sustentar `>=25% SM` em 3 ou mais amostras, esperar e repetir o preflight;
4. salvar snapshots em `results/gpu-preflight/`.

Não fechar/tunar aplicações normais se elas não violarem o gate. Não alterar clocks, power limit ou driver.

## Avaliação canônica

Cada caso vale **10 pontos**:

- **3 pontos — seleção e sequência de tools**: sequência exatamente conforme `expected.tool_sequence`, incluindo dependências entre turnos;
- **3 pontos — argumentos e schema**: JSON parseável, válido contra JSON Schema, sem campos extras e satisfazendo todas as `argument_rules`;
- **3 pontos — resposta final grounded**: contém todos os `final_must_include`, não contém nenhum `final_must_not_include` e não contradiz os resultados das tools;
- **1 ponto — higiene de protocolo**: sem tool inexistente, tool call malformada, tool call extra, raw `<tool_call>` vazando na resposta final, reasoning vazando como conteúdo final ou loop até o limite.

Para T04, os 3 pontos de seleção/ordem exigem **zero chamadas de ferramenta** e os 3 pontos de argumentos são concedidos apenas se nenhuma chamada for feita.

Um caso é **STRICT PASS** somente com `10/10`.

Métricas primárias por braço:

- STRICT PASS: `/8`
- total component score: `/80`
- tool selection/sequence accuracy
- argument/schema accuracy
- grounded final-answer accuracy
- protocol violations
- malformed tool calls
- hallucinated tool names
- unnecessary tool calls
- recovery success em T07

Métricas secundárias:

- wall time por caso
- TTFT
- decode tok/s
- pico de VRAM
- número de assistant turns
- número total de tool calls

Não misturar velocidade no score de qualidade.

## Casos cobertos

- T01: chamada única e arquivo exato
- T02: escolher `find_symbol` em vez de busca textual genérica
- T03: argumentos/schema e intervalo de linhas exato
- T04: não chamar ferramenta quando não é necessário
- T05: `search_repo -> read_file` com dependência
- T06: `list_dir -> read_file`, selecionando o perfil mais recente
- T07: recuperar de `FILE_NOT_FOUND`, buscar caminho correto e continuar
- T08: confiar no resultado da ferramenta quando contradiz a premissa do usuário

## Comparação e classificação

O `SUMMARY.md` deve mostrar tabela T01–T08 lado a lado para Native e Froggeric, com:

- STRICT PASS/FAIL
- score `/10`
- sequência de ferramentas observada
- motivo de qualquer perda de ponto

Classificação final:

- `FROGGERIC_AGENT_CLEAR_WIN`: Froggeric vence por >=2 STRICT PASS, ou por >=10 pontos no total sem aumentar violações de protocolo;
- `FROGGERIC_AGENT_EDGE`: Froggeric vence por 1 STRICT PASS ou 5–9 pontos sem aumentar violações;
- `AGENT_PARITY`: diferença <5 pontos e mesmo número de STRICT PASS;
- `NATIVE_AGENT_EDGE`: simétrico ao edge acima;
- `NATIVE_AGENT_CLEAR_WIN`: simétrico ao clear win acima.

Se os critérios de pass-count e component-score apontarem em direções opostas, não force classificação: use `MIXED_AGENT_RESULT` e explique.

## Artefatos obrigatórios

Salvar em:

`benchmarks/gsq-froggeric-agent-tools-v1/results/`

No mínimo:

- `NATIVE_RESULTS.jsonl`
- `FROGGERIC_RESULTS.jsonl`
- `SUMMARY.md`
- `RUN_MANIFEST.json`
- `gpu-preflight/arm_native.txt`
- `gpu-preflight/arm_froggeric.txt`
- logs de servidor de ambos os braços

Cada linha de resultado deve preservar:

- case id
- arm/template
- request inicial relevante
- tool calls estruturadas por turno
- argumentos parseados
- tool results retornados pelos stubs
- resposta final
- component scores
- STRICT PASS
- violações/protocol errors
- wall/TTFT/tok/s/VRAM quando disponíveis

## Integridade

Não:

- criar casos extras;
- alterar prompts;
- alterar tool schemas;
- alterar stubs;
- alterar expected sequences;
- adicionar system prompt permissivo ou dica de solução;
- rerodar um caso porque um braço foi mal;
- usar DFlash2 nesta rodada;
- habilitar thinking;
- comparar com resultados históricos como substituto dos 16 runs novos.

Rerun somente se houver falha real de infraestrutura, resposta truncada por erro do runner, servidor morto ou preflight de GPU inválido. Documentar qualquer rerun.

Ao terminar, atualizar os perfis Markdown do GSQ/Froggeric somente com fatos efetivamente medidos e versionados, seguindo `AGENTS.md`.
