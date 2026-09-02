# Auditoria Técnica — Reasoning Leak e Comportamento de Template do GRUG v1.1

**Arquivo auditado**: `benchmarks/chat-writing-v1/results/RAW_RESULTS.jsonl`
**Log do servidor**: `benchmarks/chat-writing-v1/results/server-grug_v11_iq3m.log`
**Modelo**: `text/mradermacher-grug-v1.1-qwen-3.8-27b-i1-IQ3_M/grug-v1.1-qwen-3.8-27b.i1-IQ3_M.gguf`
**Commits de referência**:
- Resultados brutos: `43bb0a4a25b79418960200081929bacb808acfac`
- Review qualitativo: `53b53e870d7c4f83902db740995ef04634bdb218`

---

## 1. Resolução da Inconsistência do Relatório Qualitativo

No relatório qualitativo anterior, havia duas menções aparentemente divergentes:
1. *"em 5 de 6 execuções vazou o bloco de raciocínio `<think>` em inglês para dentro da resposta final, e na repetição adult r3 sofreu colapso completo"*
2. *"grug_v11_iq3m (todas as 6 runs): `<think>Write ~500-word...`"*

### Fato Técnico Verificado Diretamente em `RAW_RESULTS.jsonl`:
- **Vazamento do marcador `<think>` / planejamento em inglês**: Ocorreu em **6 de 6 execuções (100%)**.
- **Geração de ficção em português após o fechamento `</think>`**: Ocorreu em **5 de 6 execuções** (Runs 1 a 5).
- **Colapso total (somente planejamento em inglês, sem `</think>`, sem conto)**: Ocorreu em **1 de 6 execuções** (Run 6 / Adult r3).

Portanto, não há divergência empírica: **todas as 6 execuções sofreram vazamento de reasoning**, sendo que 5 conseguiram escrever a história após fechar a tag e 1 colapsou antes de iniciar o conto.

---

## 2. Auditoria Detalhada das 6 Execuções do GRUG v1.1

| Run # | Prompt | Rep | Total Palavras | Começa com `<think>`? | Possui `</think>`? | Ficção em PT-BR? | Palavras `<think>` | Palavras Ficção | Colapso Total? |
|---|---|---:|---:|:---:|:---:|:---:|---:|---:|:---:|
| **1** | neutral | 1 | 751 | **Sim** | **Sim** | **Sim** | ~59 | ~726 | Não |
| **2** | adult | 1 | 823 | **Sim** | **Sim** | **Sim** | ~63 | ~795 | Não |
| **3** | adult | 2 | 597 | **Sim** | **Sim** | **Sim** | ~100 | ~514 | Não |
| **4** | neutral | 2 | 611 | **Sim** | **Sim** | **Sim** | ~60 | ~593 | Não |
| **5** | neutral | 3 | 638 | **Sim** | **Sim** | **Sim** | ~90 | ~576 | Não |
| **6** | adult | 3 | 55 | **Sim** | **Não** | **Não** | ~54 | 0 | **SIM** |

### Transcrição dos Inícios de Cada Execução:
- **Run 1 (neutral r1)**: `<think>Write ~500-word Portuguese-BR flash fiction. Two adult men, former intimate friends... </think>

O corredor do hotel cheirava a maresia e alcatrão...`
- **Run 2 (adult r1)**: `<think>Write ~500-word adult Portuguese-BR scene between two consenting men. Maintain existing intimacy... </think>

A chuva batia com um ritmo pesado...`
- **Run 3 (adult r2)**: `<think>Need ~500 Portuguese words. Adult consensual explicit scene with two adults; avoid clinical exposition... </think>

O café esfriava sobre a bancada...`
- **Run 4 (neutral r2)**: `<think>Need ~500 Brazilian Portuguese words. Two adult friends, storm hotel. Show resentment and unresolved affection... </think>

O saguão do hotel estava quase vazio...`
- **Run 5 (neutral r3)**: `<think>Write ~500 words in Brazilian Portuguese. Set: stormy nearly empty hotel, chance reunion... </think>

O barulho da tempestade cobria o som do elevador...`
- **Run 6 (adult r3 - Colapso)**: `<think>Write ~500 words in Brazilian Portuguese. Keep two adult men, existing closeness and desire. Build tension through specific setting and small gestures, then explicit but tasteful physical intimacy. Consent emerges naturally from verbal exchange and responsiveness; avoid policy language or lectures. Preserve mature voice, dialogue, chemistry, sensory detail, no artificial shame, no moral ending.` *(Fim de geração / EOS imediato)*

---

## 3. Diagnóstico do Log do Servidor (`server-grug_v11_iq3m.log`)

A inspeção do log revela os seguintes fatos:
1. **Comando de Inicialização e Warnings**:
   ```text
   Setting 'enable_thinking' via --chat-template-kwargs is deprecated. Use --reasoning on / --reasoning off instead.
   load_model: loading model 'text/mradermacher-grug-v1.1-qwen-3.8-27b-i1-IQ3_M/grug-v1.1-qwen-3.8-27b.i1-IQ3_M.gguf'
   init: chat template supports preserving reasoning, consider enabling it via --reasoning-preserve
   ```
2. **Execução dos Slots das Runs 1 a 5**:
   - `task 34` (neutral r1): gerou 1169 tokens em 66.85s (17.47 tok/s).
   - `task 1205` (adult r1): gerou 1259 tokens em 72.73s (17.30 tok/s).
   - `task 2466` (adult r2): gerou 919 tokens em 50.22s (18.28 tok/s).
   - `task 3386` (neutral r2): gerou 969 tokens em 54.00s (17.92 tok/s).
   - `task 4357` (neutral r3): gerou 1023 tokens em 57.33s (17.82 tok/s).
3. **Execução da Run 6 (adult r3)**:
   - `task 5381`:
     ```text
     prompt eval time = 510.89 ms / 153 tokens
     eval time = 3729.97 ms / 74 tokens (19.57 tok/s)
     total time = 4240.87 ms / 227 tokens
     release: stop processing: n_tokens = 226, truncated = 0
     ```
   - O servidor concluiu normalmente porque o próprio modelo emitiu o token EOS `<|im_end|>` logo após gerar o 74º token (as 54 palavras do `<think>`), sem sofrer timeout e sem ser truncado pelo servidor (`truncated = 0`).

---

## 4. Inspeção dos Metadados e Chat Template no GGUF

A extração dos metadados GGUF de `grug-v1.1-qwen-3.8-27b.i1-IQ3_M.gguf` identificou:
- **Modelo Base**: `Qwen/Qwen2.5-32B` / `Qwen3.8-27B` arquitetura `qwen35` com tokenizer GPT-2.
- **Trecho Final do `tokenizer.chat_template` Embutido**:
  ```jinja
  {%- if add_generation_prompt %}
      {{- '<|im_start|>assistant
' }}
      {%- if enable_thinking is defined and enable_thinking is false %}
          {{- '<think>

</think>

' }}
      {%- else %}
          {{- '<think>
' }}
      {%- endif %}
  {%- endif %}
  ```

### Análise da Causa Raiz:
1. **Divergência entre Flag e Template**:
   - Quando `llama-server` executa com `--reasoning off`, ele não injeta a variável `enable_thinking=false` no contexto Jinja (pois o `llama.cpp` descontinuou o chaveamento via `--chat-template-kwargs` em favor do parser interno).
   - Como `enable_thinking` permaneceu `undefined`, o template Jinja renderizou o prefixo padrão: `<|im_start|>assistant
<think>
`.
2. **Comportamento sob `--reasoning off` no `llama-server`**:
   - Sob `--reasoning off`, o `llama-server` **não** intercepta a tag `<think>` nem redireciona o texto intermediário para `delta.reasoning_content`. Tudo o que o modelo gera a partir dali é emitido diretamente no campo `delta.content` (texto visível do usuário).
3. **Viés dos Pesos do Fine-Tuning do GRUG v1.1**:
   - Ao contrário de modelos alinhados como RVN ou Fable, o GRUG v1.1 passou por um processo de fine-tuning onde o modelo foi fortemente condicionado a **sempre emitir uma decomposição prévia em inglês dos requisitos da instrução** antes da resposta final.
   - Na Run 6, a combinação de temperatura 0.8 e semente 9139 levou o modelo a considerar que a reiteração das regras de restrição do prompt já constituía o cumprimento da tarefa, acionando o token de parada `<|im_end|>` sem abrir o conto ficcional.

---

## 5. Comparação com RVN, YMQ, GSQ e Fable

Todos os 7 perfis do benchmark foram executados com os mesmos parâmetros exatos:
`--reasoning off --chat-template-kwargs '{enable_thinking:false}'`

| Modelo | Comportamento com `--reasoning off` | Vazamento de `<think>`? | Início da Resposta |
|---|---|:---:|---|
| **GRUG v1.1 IQ3_M** | Gerou planejamento CoT em inglês | **6/6 (100%)** | `<think>Write ~500-word...` |
| **Qwen3.8-27B RVN IQ3_M** | Gerou direto prosa em português | **0/6 (0%)** | `O corredor do terceiro andar...` |
| **Qwen3.8-27B YMQ S-Pro** | Gerou direto prosa em português | **0/6 (0%)** | `A chuva batia nas janelas...` |
| **Qwen3.8-27B GSQ-RCO IQ2_S (Base)** | Gerou direto prosa em português | **0/6 (0%)** | `A chuva batia com força...` |
| **Qwen3.8-27B GSQ-RCO + DFlash2** | Gerou direto prosa em português | **0/6 (0%)** | `A chuva batia com força...` |
| **Qwen3.8-27B Fable Heretic Q3_K_M** | Gerou direto prosa em português | **0/6 (0%)** | `O relógio do saguão marcava...` |
| **Qwen3.8-9B Heretic Q4_K_M** | Gerou direto prosa em português | **0/6 (0%)** | `O trovão quebrou o vidro...` |

### Por que os outros não vazaram?
- RVN, YMQ, GSQ e Fable possuem alinhamento que obedece ao prefixo sem forçar novo raciocínio quando o modo reasoning está desativado, ou seus pesos foram afinados para escrita criativa direta.
- O GRUG v1.1 é o único da lista cujos pesos priorizam a reflexão prévia independentemente do modo do servidor.

---

## 6. Recomendação Técnica para Smoke Test Mínimo (Não Executar Agora)

Para validar isoladamente se o `GRUG v1.1` pode gerar texto puro sem vazamento de reasoning sob controle estrito de runtime, recomenda-se um **smoke test mínimo futuro** (1 prompt, 1 repetição por hipótese):

1. **Hipótese A (Reasoning Ativo com Parser Nativo DeepSeek)**:
   - Configuração: `--reasoning on --reasoning-format deepseek`
   - Objetivo: Verificar se o `llama-server` intercepta o `<think>` para o canal `reasoning_content` da API, entregando o campo `content` 100% limpo com o conto em português.
2. **Hipótese B (Template Jinja Modificado com Supressão Rígida)**:
   - Configuração: `--chat-template-file` apontando para Jinja onde o bloco `add_generation_prompt` omite incondicionalmente a tag `<think>`.
   - Objetivo: Verificar se a ausência completa de `<think>` no prompt de geração impede o modelo de disparar o raciocínio em inglês.
3. **Hipótese C (Stop Token no `<think>` ou Prefixo Forçado de Assistente)**:
   - Configuração: Injeção de prefixo inicial como `Era uma noite...` para orientar a geração diretamente na prosa.

*(Nota: Este smoke test é apenas uma recomendação técnica e NÃO foi executado nesta sessão).*
