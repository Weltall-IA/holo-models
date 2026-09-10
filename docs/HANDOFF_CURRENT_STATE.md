# HANDOFF — Estado atual dos benchmarks locais

Atualizado em 2026-09-10.

## Repositório e regra de trabalho

- Repositório: `Weltall-IA/holo-models`
- Branch canônica: `master`
- HEAD imediatamente antes deste handoff: `31b12d85e24cda074bb9e5c185e311ccf604f1f6`
- O ChatGPT é responsável por criar/modificar benchmark e semântica no repositório.
- A IA local é executora: pode preparar ambiente, baixar/compilar runtime quando explicitamente autorizado e executar os testes, mas não deve alterar perguntas, evaluator, regras, parâmetros ou benchmark para “fazer passar”.
- Antes de interpretar uma rodada, prefira artefatos brutos, evaluator, hidden tests e logs. Não trate `RESULTS.md` como autoridade causal.
- Antes de qualquer download, conversão, quantização ou benchmark de modelo, consultar obrigatoriamente `MODEL_HISTORY.md` e procurar summaries/benchmarks existentes pelo modelo, revisão e variante. Não redownloadar/retestar variante materialmente equivalente sem confirmação explícita do usuário, salvo mudança material documentada conforme `AGENTS.md`.

## Hardware / ambiente relevante

- Arch Linux
- GPU: RTX 5060 Ti 16 GB
- raiz dos modelos: `/home/alpha/Playstoria/models/`
- pesos de texto: `/home/alpha/Playstoria/models/text/`
- preferência prática: evitar mais de 8 CPU threads para não travar a máquina.

## Runtime llama.cpp / DFlash2 validado

Runtime válido usado nas campanhas atuais:

- upstream `llama.cpp`
- commit: `b96806d96061049a5b574269b049bf6241d63d46`
- versão: `0.3.0-dev`, build `10752`
- wrapper usado pelos benchmarks: `~/.local/bin/llama`
- binário real local histórico: `/home/alpha/Playstoria/models/engines/llama.cpp/build/bin/llama-server`

O erro histórico `wrong number of tensors; expected 81, got 58` não provava incompatibilidade GSQ + DFlash2; os runtimes anteriores eram anteriores ao suporte DFlash2 real.

Não voltar a usar para DFlash2 sem revalidação explícita:

- `/usr/bin/llama-server` build 10621
- `geo-llama` commit `3e62554`
- DeepGrove histórico.

## Estado-base estabelecido — GSQ worker + DFlash2

Target canônico:

`/home/alpha/Playstoria/models/text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-IQ2_S/Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf`

SHA256:

`16c9802111aa9ef3acde465188d6d601f8db128ee3d828ad983a5caca4135ecb`

Draft DFlash2:

`/home/alpha/Playstoria/models/text/z-lab-Qwen3.8-27B-DFlash2-GGUF/Qwen3.8-27B-DFlash2-Q4_K_M.gguf`

SHA256:

`1a25c56858e1ebe93f2718ac1d49d1151f9323325c1bbfd6209370f4db131ebd`

O `repo-worker-gsq-dflash2-v4` em `d12f0a7df20a7999ea620d4405ccdbbb3ae5f7b3` permanece histórico válido. No perfil Froggeric v22.4 medium sem hard budget B256, o resultado foi 7/8 estrito e 8/8 funcional; não rerodar o v4 apenas para confirmar esse estado.

## Chat / Writing Benchmark v1 — concluído

Diretório:

`benchmarks/chat-writing-v1/`

A suíte que o handoff de 2026-09-02 indicava como “próximo objetivo” já foi criada, executada e auditada. O estado canônico atual contém:

- 7 modelos realmente presentes no preflight;
- 2 prompts por modelo: neutral + adult consensual;
- 3 repetições por prompt;
- 42 gerações completas;
- reasoning OFF;
- resultados brutos, summary quantitativo, auditoria qualitativa e auditoria específica do leak de reasoning do GRUG.

Commits principais:

- configuração/contrato da suíte: `9a2bfb19ea3a8ad6e187680b6aed31b9deb694a5` até `203539103813b6d45393f4b6370573407dbd62f8`
- execução das 42 gerações: `43bb0a4a25b79418960200081929bacb808acfac`
- revisão qualitativa: `53b53e870d7c4f83902db740995ef04634bdb218`
- auditoria GRUG: `2c7a54986f266356447ea06accb9c6f1e19f0b9b`

Qualidade literária consolidada, sem misturar velocidade:

1. Fable Distill Heretic ARA Q3_K_M — 4.92/5
2. RVN IQ3_M multilingual MTP — 4.38/5
3. YMQ S-Pro — 4.27/5
4. GSQ IQ2_S + DFlash2 — 3.81/5
5. GSQ IQ2_S base — 3.54/5
6. Qwen3.8 9B Heretic Q4_K_M — 3.15/5
7. GRUG v1.1 IQ3_M — 2.54/5

Medianas de geração do benchmark de escrita, neutral/adult:

- GSQ IQ2_S base: 20.13 / 20.63 tok/s
- GSQ IQ2_S + DFlash2: 13.72 / 12.51 tok/s
- RVN IQ3_M MTP: 17.34 / 18.00 tok/s
- Fable Heretic Q3_K_M: 15.89 / 15.69 tok/s
- GRUG v1.1 IQ3_M: 17.82 / 18.28 tok/s
- YMQ S-Pro: 17.56 / 18.02 tok/s
- Qwen3.8 9B Heretic Q4_K_M: 40.09 / 39.75 tok/s

Conclusão importante: não assumir que DFlash2 acelera chat/escrita contínua só porque acelera outros workloads. Nesta suíte, o braço GSQ+DFlash2 mediu menos tok/s que GSQ base.

## Froggeric v22.5 — ablação limpa concluída

Diretório:

`benchmarks/gsq-froggeric-v225-clean-retest-v1/`

Commit de execução:

`5bbd55a357700bcf51e40a57c0d7bdc874aadf3b`

Estado canônico:

- GSQ Native coding: 6/6
- GSQ + Froggeric v22.5 coding: 6/6
- GSQ + DFlash2 Native coding: 6/6
- GSQ + DFlash2 + Froggeric v22.5 coding: 6/6
- writing Native vs Froggeric: mesmos textos e mesma qualidade canônica, 3.54/5
- DFlash2 median acceptance: 86.9% nos braços comparáveis
- efeitos de velocidade observados entre templates são inconclusivos como causalidade por causa do desenho sequencial single-pass
- decisão de deployment para chat/coding não-tool: `KEEP_NATIVE`, por simplicidade; Froggeric v22.5 é funcionalmente compatível na condição não-thinking testada.

Não rerodar só para atribuir causalidade de velocidade ao template; isso exigiria outro benchmark interleaved/repeated e só vale criar se essa pergunta se tornar importante.

## Agent / tool-calling — Native vs Froggeric v22.5 concluído

Diretório:

`benchmarks/gsq-froggeric-agent-tools-v1/`

Commits principais:

- definição: `e95c8ae5ad6df93cd65c1678f4faa383d425bd52`
- execução: `99233bfc5111dde233d3bf1bf68a8ec768915a76`
- interpretação final: `967e64c2698d83a2e52dcf68433c6fddee6ff678`

Resultado no path efetivamente testado (`llama-server` OpenAI JSON tools):

- Native: 7/8 STRICT PASS, 70/80
- Froggeric v22.5: 4/8, 49/80
- classificação: `NATIVE_AGENT_CLEAR_WIN`

Nuance obrigatória: tool selection/sequence accuracy ficou empatada em 87.5%; perdas extras do Froggeric em T03/T05/T06 vieram de argumentos estruturados malformados/repetitivos e falha do parser JSON do `llama-server`. Portanto, a conclusão válida é que Native é materialmente mais confiável para a integração OpenAI/JSON atual; não extrapolar isso para “Froggeric raciocina pior em agentes” de forma independente do parser/runtime.

T07 foi fraqueza compartilhada de recovery após `FILE_NOT_FOUND`.

Preset atual para agente/tool calling nesse deployment: **Native**.

## Rerank — Jina v3.5 avaliado; liderança mantida

Campanha de 2026-09-04 avaliou `jina-reranker-v3.5` no painel realmente medido de 150 queries × top-8 embeddings × 50 candidatos, totalizando 60.000 pares query-documento.

Correção metodológica final em:

`d99861336ae1c119b8fc4adf1f7b0c8c254f2251`

Resultados médios medidos no painel 150q:

- llama-nemotron-rerank-1b-v2: 0.8221 MRR
- qwen3-reranker-0.6B: 0.8180 MRR
- jina-reranker-v3.5: 0.8087 MRR

No mDenseOn do mesmo painel:

- Nemotron: 0.8138
- Qwen3-0.6B: 0.8001
- Jina v3.5: 0.8043

Conclusão: Nemotron 1B v2 segue líder; Qwen3-0.6B segue alternativa leve; Jina v3.5 `NÃO_COMPENSA` como substituto nesse pipeline. As antigas projeções sintéticas para 240 queries foram removidas e não são evidência canônica; o dataset intermediário histórico de 240q não está versionado/reexecutável.

## Candidatos de coding compactados / rejeitados

Consultar `MODEL_HISTORY.md` antes de qualquer ação. O ledger atual registra:

### JackAgentLead/Jack-3.8-27B-Coder-16GB-VRAM

- variante: `Jack-3.8-27B-Coder-16GB-VRAM.gguf`
- `coding-mini-v1`: 4/6
- 7.92 tok/s
- pico 13049 MiB
- status: `NÃO_COMPENSA`
- pesos removidos
- evidência: `benchmarks/coding-mini-v1/results/CANDIDATES_ROUND_JACK_WHITTLE_SUMMARY.md`

### logic65/Qwen3.8-Whittle-MoE-27B-A17.8B-GGUF

- variante: `Whittle-MoE-27B-A18B-v2.2.1-Q3_K_M.gguf`
- `coding-mini-v1`: 1/6
- 19.39 tok/s
- pico 15194 MiB
- status: `NÃO_COMPENSA`
- pesos removidos
- não confundir com Whittle 16B dense-pruned.

### logic65/Qwen3.8-Whittle-16B — campanha mais recente

Diretório:

`benchmarks/whittle16b-candidate-v1/`

Variante testada:

`Qwen3.8-Whittle-16B-v2-Q4_K_M.gguf`

HF revision:

`d18db969059b15423be91f5d4fd119c8c907801c`

Resultado com a recipe upstream do autor:

- Stage A coding: 0/6 (0/3 Python, 0/3 C++20)
- mediana: 19.83 tok/s (`AUTHOR_RECIPE`)
- pico VRAM: 11076 MiB
- classificação: `WHITTLE16B_REJECT`
- pelo gate do SPEC, DFlash2 e Agent Stage foram corretamente pulados

Execução completa original:

`c9823c3952666ae054610a404b3d4a2cafd4e553`

Remoção/documentação:

`5563f043c6e4b99a6f937399f76975508350bed8`

Compactação/handoff histórico atual culminou em:

`31b12d85e24cda074bb9e5c185e311ccf604f1f6`

Pesos, symlink/runtime profile, raw JSONL volumoso, server log, preflight snapshot e runner exclusivo foram removidos do branch atual conforme política de compactação. Permanecem `SPEC.md`, `SUMMARY.md`, `RUN_MANIFEST.json`, `MODEL_HISTORY.md` e os SHAs dos commits recuperáveis no histórico.

**Não redownloadar/retestar esta exata v2 Q4_K_M automaticamente.**

## Estado operacional atual

As campanhas que estavam abertas no handoff anterior foram encerradas. Em particular:

- benchmark de chat/escrita: concluído e auditado;
- Froggeric v22.5 chat/coding: concluído;
- Froggeric v22.5 agent/tool calling: concluído;
- Jina reranker v3.5: concluído e não destronou Nemotron;
- Jack Coder: rejeitado/removido;
- Whittle-MoE 27B A18B: rejeitado/removido;
- Whittle 16B v2 Q4_K_M: rejeitado/removido/compactado.

Não há, neste HEAD, uma campanha de benchmark parcialmente executada que deva ser retomada, nem um novo candidato autorizado pendente de download. **Não inventar um próximo modelo e não iniciar download/reteste por conta própria.**

O próximo trabalho deve nascer de um objetivo/candidato materialmente novo do usuário ou de uma pergunta de capacidade diferente. Quando isso acontecer, primeiro cruzar `MODEL_HISTORY.md` + summaries existentes para decidir se é benchmark novo, extensão válida de campanha ou reteste redundante.

## Instrução para o próximo ChatGPT

Ao retomar em novo chat:

1. Leia este arquivo inteiro.
2. Leia `AGENTS.md`.
3. Leia `MODEL_HISTORY.md` antes de qualquer download/benchmark.
4. Confirme o `master`/HEAD atual; se estiver à frente do SHA deste handoff, reconstrua a diferença antes de agir.
5. Não rerode campanhas fechadas apenas para confirmar números já estabelecidos.
6. Para agente/tool calling no deployment `llama-server` + OpenAI JSON atual, partir do preset Native; Froggeric v22.5 não é o preset recomendado nesse path.
7. Para rerank, partir de Nemotron 1B v2 como líder medido; Qwen3-0.6B é a alternativa leve.
8. Para chat/escrita, preservar os resultados canônicos de `chat-writing-v1`; Fable lidera qualidade, RVN/YMQ vêm em seguida, e Qwen3.8 9B é a referência de velocidade entre os sete modelos daquela suíte.
9. Não confundir throughput de chat, coding-mini, repo-worker e agent/tool calling: são workloads distintos e não devem ser mesclados em um único ranking de tok/s.
10. Se surgir candidato novo, versionar primeiro um SPEC com identidade/revisão/quantização, gate e artefatos exigidos; só então enviar ordem de execução à IA local.
