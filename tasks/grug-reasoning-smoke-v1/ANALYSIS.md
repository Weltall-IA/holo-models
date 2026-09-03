# Análise Técnica do Smoke Test — GRUG v1.1 (Template vs Pesos)

**Data**: 2026-09-03  
**Modelo**: `text/mradermacher-grug-v1.1-qwen-3.8-27b-i1-IQ3_M/grug-v1.1-qwen-3.8-27b.i1-IQ3_M.gguf`  
**Runtime**: `/home/alpha/.local/bin/llama` (build 10752 / commit `b96806d96061049a5b574269b049bf6241d63d46`)  
**Arquivo de dados brutos**: `tasks/grug-reasoning-smoke-v1/RESULTS.json`  

---

## 1. Resultados Consolidados dos 3 Perfis

| Perfil | Template | Flags de Reasoning | `content` (História) | `reasoning_content` | Começa com `<think>`? | Velocidade | Wall Time | Peak VRAM |
|---|---|---|---|---|:---:|---:|---:|---:|
| **Perfil A (Controle)** | GGUF Embutido | `--reasoning off` + `chat-template-kwargs` | Poluído com `<think>...</think>` | Vazio (`""`) | **SIM** | 20.26 tok/s | 5.25s | 15.028 MiB |
| **Perfil B (No-Think Template)** | `grug-no-think.jinja` | `--reasoning off` | **Limpo (PT-BR)** | Extraído (10 palavras) | **NÃO** | 21.48 tok/s | 4.55s | 15.014 MiB |
| **Perfil C (Parser Nativo)** | GGUF Embutido | `--reasoning on --reasoning-format deepseek` | **Limpo (PT-BR)** | Extraído (9 palavras) | **NÃO** | 22.25 tok/s | 3.76s | 14.948 MiB |

---

## 2. Respostas Explícitas às Perguntas Técnicas

### 1. O `<think>` vem do template?
**Sim e Não (Efeito Combinado):**
- **No Template**: O template Jinja embutido no GGUF contém, na cláusula `add_generation_prompt`, a instrução `{{- '<think>\n' }}` quando a variável `enable_thinking` não é explicitamente definida como `false` pelo parser Jinja do runtime. Como o `llama.cpp` descontinuou o repasse de `--chat-template-kwargs` em favor de seu parser nativo, o template injetava `<think>\n` diretamente como parte do **prompt de entrada**.
- **Nos Pesos**: O modelo GRUG v1.1 foi treinado com fine-tuning voltado a raciocínio (CoT), de modo que seus pesos têm fortíssima prioridade para raciocinar antes de responder.

### 2. Remover o prefixo `<think>` resolve o problema?
**Sim, para o consumidor da API:**
Ao remover `<think>\n` do template (Perfil B), o servidor passa o prompt terminando em `<|im_start|>assistant\n`. O modelo passa a emitir `<think>` como token gerado. O parser do `llama-server` detecta o início e o fim da tag gerada, extrai todo o planejamento para o campo `reasoning_content` da API e entrega o campo `content` **100% limpo** com a história em português brasileiro.

### 3. O modelo espontaneamente recria `<think>` mesmo quando o template não pede?
**Sim.**
No Perfil B, onde o template continha estritamente `<|im_start|>assistant\n` (sem qualquer menção a `<think>`), os pesos do modelo imediatamente geraram a tag `<think>`, emitiram o raciocínio (`Dois parágrafos curtos, homem esperando trem na chuva, só história.`) e fecharam com `</think>`. Isso comprova de forma definitiva que a necessidade de raciocínio prévio está gravada nos **pesos** do fine-tuning do GRUG v1.1.

### 4. O parser nativo consegue separar reasoning de content?
**Sim, perfeitamente.**
Tanto no Perfil B quanto no Perfil C (`--reasoning on --reasoning-format deepseek`), o parser do runtime interceptou as tags `<think>...</think>`, isolou o raciocínio em `delta.reasoning_content` e transmitiu a prosa limpa em `delta.content`. Em ambos os casos, a história final não contém nenhuma tag de pensamento, vazamento de planejamento ou palavras em inglês.

### 5. Existe ainda risco de EOS dentro de reasoning?
**Sim.**
Como demonstrado na Run 6 (Adult r3) do benchmark `chat-writing-v1`, se a temperatura for alta (ex.: 0.8), o prompt tiver muitas restrições negativas ou o orçamento de tokens for restrito, o modelo pode concluir seu processo deliberativo considerando que já atendeu a instrução no bloco de reflexão e emitir o token `<|im_end|>` sem abrir o bloco de conteúdo. Em tarefas de produção, recomenda-se orçamento de tokens suficiente para acomodar tanto o raciocínio quanto a resposta completa.

### 6. Qual configuração deve ser usada para GRUG em chat?
Para chat interativo, roleplay ou escrita criativa com GRUG v1.1:
```bash
llama serve \
  -m text/mradermacher-grug-v1.1-qwen-3.8-27b-i1-IQ3_M/grug-v1.1-qwen-3.8-27b.i1-IQ3_M.gguf \
  --reasoning on \
  --reasoning-format deepseek \
  --jinja \
  -c 4096 -ngl 999 -fa on -ctk q8_0 -ctv q4_0 -t 8 -tb 8 --no-webui
```
O cliente de chat consome o campo `content` para exibição ao usuário e opcionalmente exibe `reasoning_content` em uma aba retrátil.

### 7. Qual configuração deve ser usada para GRUG em um futuro benchmark de código/agente?
Para benchmarks de agentes autônomos (como `repo-worker`):
```bash
llama serve \
  -m text/mradermacher-grug-v1.1-qwen-3.8-27b-i1-IQ3_M/grug-v1.1-qwen-3.8-27b.i1-IQ3_M.gguf \
  --reasoning on \
  --reasoning-format deepseek \
  --reasoning-effort medium \
  --jinja \
  -c 32768 -ngl 999 -fa on -ctk q8_0 -ctv q4_0 -t 2 -tb 2 --no-webui
```
Isso garante que o raciocínio complexo de diagnóstico do repositório fique no canal `reasoning_content`, permitindo que o `content` emita estritamente o JSON puro das chamadas de ferramentas (`{"action":"read",...}`) sem quebras de protocolo.
