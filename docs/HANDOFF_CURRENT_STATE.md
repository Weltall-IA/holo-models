# HANDOFF — Estado atual dos benchmarks locais

Atualizado em 2026-09-02.

## Repositório e regra de trabalho

- Repositório: `Weltall-IA/holo-models`
- Branch canônica: `master`
- HEAD imediatamente antes deste handoff: `d12f0a7df20a7999ea620d4405ccdbbb3ae5f7b3`
- O ChatGPT é responsável por criar/modificar benchmark e semântica no repositório.
- A IA local é executora: pode preparar ambiente, baixar/compilar runtime quando explicitamente autorizado e executar os testes, mas não deve alterar perguntas, evaluator, regras, parâmetros ou benchmark para “fazer passar”.
- Antes de interpretar uma rodada, prefira artefatos brutos, evaluator, hidden tests e logs. Não trate `RESULTS.md` como autoridade causal.

## Hardware / ambiente relevante

- Arch Linux
- GPU: RTX 5060 Ti 16 GB
- raiz dos modelos: `/home/alpha/Playstoria/models/`
- pesos de texto: `/home/alpha/Playstoria/models/text/`
- preferência prática: evitar mais de 8 CPU threads para não travar a máquina.

## Runtime DFlash2 que finalmente funcionou

O erro histórico `wrong number of tensors; expected 81, got 58` NÃO provava incompatibilidade GSQ + DFlash2. Os runtimes testados antes eram anteriores ao suporte DFlash2 real.

Runtime válido usado na rodada v4:

- upstream `llama.cpp`
- commit: `b96806d96061049a5b574269b049bf6241d63d46`
- versão: `0.3.0-dev`, build `10752`
- wrapper usado pelo benchmark: `~/.local/bin/llama`
- binário real local: `/home/alpha/Playstoria/models/engines/llama.cpp/build/bin/llama-server`

Houve um incidente em que o `build/bin/llama-server` foi sobrescrito por um wrapper recursivo que chamava a si mesmo. A causa foi diagnosticada pelo `strace`; o target `llama-server` foi relinkado/reconstruído. Não interpretar aquele timeout como falha CUDA.

Não voltar a usar para DFlash2:

- `/usr/bin/llama-server` build 10621
- `geo-llama` commit `3e62554` (anterior à PR DFlash2 real)
- DeepGrove histórico sem revalidação explícita.

## Target, draft e template do v4

Target:

`/home/alpha/Playstoria/models/text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-IQ2_S/Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf`

SHA256:

`16c9802111aa9ef3acde465188d6d601f8db128ee3d828ad983a5caca4135ecb`

DFlash2 draft:

`/home/alpha/Playstoria/models/text/z-lab-Qwen3.8-27B-DFlash2-GGUF/Qwen3.8-27B-DFlash2-Q4_K_M.gguf`

SHA256:

`1a25c56858e1ebe93f2718ac1d49d1151f9323325c1bbfd6209370f4db131ebd`

Froggeric:

- versão: `qwen3.8-froggeric-v22.4`
- revisão: `e649070`
- template local: `/home/alpha/Playstoria/models/text/froggeric-Qwen-Fixed-Chat-Templates-v22.4/chat_template.jinja`

## Repo-worker GSQ + DFlash2 v4

Diretório:

`benchmarks/repo-worker-gsq-dflash2-v4/`

Commit dos resultados:

`d12f0a7df20a7999ea620d4405ccdbbb3ae5f7b3`

Fonte de tarefas:

- source repo HEAD: `5a7720c3d4874524e4b8fda6c7be5ae456208fdd`
- seed: `9137`
- 16/16 runs concluídas
- infra errors: `0`

Perfis:

1. `iq2-dflash-frog-medium`
2. `iq2-dflash-frog-medium-b256`

Configuração principal:

- ctx 32768
- np 1
- full GPU
- FA on
- fit off
- K cache q8_0
- V cache q4_0
- threads / batch threads 2 / 2
- DFlash2 `draft-dflash`, `spec-draft-n-max=7`
- Froggeric v22.4
- reasoning on
- reasoning effort medium
- temperature 0.2
- top_p 0.95

Resultados objetivos versionados:

| perfil | estrito | hidden | protocol failures | recovery | mediana | tool errors | peak VRAM | server decode |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| medium | 7/8 | 5/5 | 1 | 1/1 | 148.4s | 2 | 14793 MiB | 18.12 tok/s |
| medium + B256 | 7/8 | 4/5 | 1 | 1/1 | 131.8s | 3 | 15361 MiB | 18.63 tok/s |

### Correção qualitativa importante do v4

No perfil `medium`, a única falha estrita foi T4 por protocolo/finalização. A implementação terminou funcionalmente correta e public + hidden deram `10 passed`; o modelo não conseguiu emitir `done` antes do request timeout. Portanto a leitura prática é:

- `medium`: 7/8 estrito, **8/8 funcional**.
- `medium+B256`: 7/8 estrito e **7/8 funcional**; em T4 houve falha real (o modelo removeu `return value`, tentou corrigir, gerou patch inválido e terminou com hidden tests falhando).

Conclusão operacional atual: para worker, preferir **Froggeric medium sem hard budget B256**.

### Caveats do v4

- `DFLASH_METRICS.json` ficou nulo porque o parser antigo não reconheceu o formato atual das métricas speculative; isso não significa que o draft não foi usado.
- A IA local adicionou ao runner um `direct_request_json` durante a execução. Isso foi uma modificação operacional não desejada e deve ser tratada como contaminação de procedimento, embora perguntas/evaluator não tenham sido mudados por isso.
- `CONTROLLED_CONFIG.json` registra `runtime_source` como “official llama.app prebuilt CUDA binary”, mas o runtime efetivo foi o upstream `llama.cpp` compilado localmente no commit `b96806d`, exposto pelo wrapper `~/.local/bin/llama`. Não rerodar apenas para corrigir esse metadado.

## v2 de referência

`benchmarks/repo-worker-challenger-v2/`

Ponto útil para comparação:

- GSQ IQ2_S Thinking OFF: server decode ~14.42 tok/s, mediana 59.1s, peak 12995 MiB.
- GSQ IQ3_XXS Thinking OFF: server decode ~14.05 tok/s, mediana 54.7s, peak 14069 MiB.

O T7 original tinha falso negativo no evaluator; a colocação correta é policy-only. Para leituras qualitativas, a correção manual histórica é IQ2 OFF 8/8 e IQ3 OFF 8/8.

Não comparar diretamente o `server_decode_tps` de workload agente com tok/s de chat puro ou `llama-bench`.

## Velocidade: por que apareceu ~25 tok/s em modelos antigos

Existe `tasks/speed_benchmark.py` no repositório. Ele mede chat simples com:

- ctx 4096
- 8 threads
- short prompt
- 256 tokens de geração
- `timings.predicted_per_second` da API

Esse cenário é muito mais próximo de “chat/escrita contínua” do que o repo-worker, cujo contexto cresce após tool calls.

Logo, números antigos de RVN/Hauhau perto de 20–25 tok/s não devem ser comparados diretamente aos ~18 tok/s médios do v4 agente.

## Teste ad hoc local recente de DFlash2

A IA local criou/rodou localmente um comparativo de velocidade sob condições simplificadas, aparentemente não versionado no master na hora desta anotação. Reportou:

| modelo | decode reportado |
|---|---:|
| GSQ IQ2_S + DFlash2 | 13.16 tok/s |
| GSQ IQ2_S base | 5.24 tok/s |
| GRUG IQ3_M | 4.96 tok/s |
| YMQ uncensored | 4.77 tok/s |
| Fable Q3_K_M | 3.77 tok/s |

Também reportou acceptance DFlash2 de 46.8% e ganho interno de ~2.51x versus GSQ base no mesmo script.

Tratar esses números como **provisórios até auditar a fórmula/métrica exata**, porque o GSQ base de 5.24 diverge bastante do server decode de 14.42 tok/s observado no v2. Não usar esse teste para concluir “RVN é mais rápido/lento” sem padronizar a métrica.

## Próximo objetivo definido pelo usuário: benchmark de chat/escrita

O usuário quer medir a velocidade que realmente sente ao conversar/escrever histórias, não velocidade de agente/código.

Teste desejado:

- **dois contos de aproximadamente 500 palavras por modelo**;
- um conto neutro/normal;
- um conto adulto “sem censura”, destinado a observar recusa, suavização/moralização e liberdade de escrita;
- medir tok/s de geração de chat, não repo-worker;
- reasoning OFF para este benchmark de escrita;
- mesmas condições entre modelos;
- idealmente repetir cada prompt 3 vezes para reduzir ruído.

Métricas desejadas por saída:

- `timings.predicted_per_second` / métrica de geração escolhida e documentada;
- completion tokens;
- wall time;
- palavras geradas;
- TTFT/prompt TPS como secundárias;
- recusou diretamente?;
- suavizou/moralizou?;
- completou o conto próximo de 500 palavras?;
- VRAM pico.

O par de prompts deve ter complexidade narrativa semelhante para que a principal variável entre eles seja sensibilidade/censura, não dificuldade linguística.

Há scripts antigos de escrita no repositório (`tasks/run_writing_benchmark.py` e `tasks/run_writing_benchmark_rerun.py`). Eles já contêm prompts de escrita adulta e modelos como RVN/Hauhau, mas usam runtime/configurações antigas. **Não reutilizar cegamente**: ler primeiro e aproveitar apenas o que fizer sentido para o novo benchmark controlado.

## Modelos/candidatos relevantes para o benchmark de chat

Confirmar os paths existentes antes de criar a suíte final. Candidatos discutidos recentemente:

- GSQ-RCO IQ2_S base
- GSQ-RCO IQ2_S + DFlash2
- RVN IQ3_M multilingual MTP
- HauhauCS Aggressive IQ3_XS
- Fable Distill Heretic Q3_K_M
- GRUG v1.1 IQ3_M
- YMQ Uncensored
- Qwen3.8 9B Heretic pode entrar como referência de velocidade, se útil.

Não reintroduzir Bonsai, Vireqo ou Minitron sem pedido explícito do usuário.

## Instrução para o próximo ChatGPT

Ao retomar em um novo chat:

1. Leia este arquivo inteiro.
2. Leia `AGENTS.md`.
3. Inspecione os artefatos versionados do v4 e o histórico relevante antes de modificar benchmark.
4. Não use a síntese subjetiva da IA local como autoridade quando os JSON/logs permitem reconstruir o resultado.
5. Mantenha a IA local como executor, não autora da semântica do benchmark.
6. O próximo trabalho esperado é **desenhar/versionar o benchmark de chat com dois contos de ~500 palavras (neutro + adulto/sem suavização), reasoning OFF, métrica de tok/s padronizada**, e só depois enviar uma ordem de execução para a IA local.
7. Antes de criar a nova suíte, verifique os modelos e paths realmente existentes e audite `tasks/speed_benchmark.py` / scripts de writing antigos para não duplicar trabalho nem misturar métricas.

Não rerode o repo-worker v4 apenas para “confirmar” o que já está estabelecido.
