# candidate-round-v1 — Writing Summary

Avaliação do candidato de escrita **Qwythos-9B-Claude-Mythos-5-1M Q4_K_M** contra o controle histórico **Qwen3.8-27B Fable Distill Heretic ARA Q3_K_M** (utilizando as mesmas 2 tarefas e 3 sementes do benchmark `chat-writing-v1`).

Configuração: seed 9137/9138/9139, temperature 0.8, top_p 0.95, min_p 0.05, repeat_penalty 1.05, max_tokens 1536, ctx 8192, 8 threads, full GPU offload, Flash Attention ON.

---

## 1. Tabela Consolidada de Velocidade e Produção

| Modelo | Prompt | Runs | Palavras (Mediana) | Decode tok/s (Mediana) | Wall Time Médio (s) | Overhead Reasoning Médio | Peak VRAM |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **[Controle] Fable Heretic Q3_K_M** | **Neutral** | 3 | **578** | **15.89 tok/s** | **37.9s** | 0s (Sem thinking) | 15.696 MiB |
| **[Controle] Fable Heretic Q3_K_M** | **Adult** | 3 | **628** | **15.69 tok/s** | **40.3s** | 0s (Sem thinking) | 15.652 MiB |
| **Qwythos-9B-Mythos Q4_K_M** | **Neutral** | 3 | **390** | **36.72 tok/s** | **36.7s** | ~28.0s (3400 chars de think) | 7.912 MiB |
| **Qwythos-9B-Mythos Q4_K_M** | **Adult** | 3 | **293** | **36.99 tok/s** | **34.5s** | ~32.0s (4060 chars de think) | 7.912 MiB |

---

## 2. Comparativo Qualitativo (Escala 1–5)

| Modelo | Aderência | Naturalidade PT-BR | Qualidade Literária | Vozes Distintas | Subtexto | Diálogo | Coerência | Final Natural | Média Geral | Mediana Geral |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **[Controle] Fable Heretic Q3_K_M** | **4.3** | **5.0** | **5.0** | **5.0** | **5.0** | **5.0** | **5.0** | **5.0** | **4.92** | **5.0** |
| **Qwythos-9B-Mythos Q4_K_M** | **2.2** | **2.8** | **2.0** | **2.0** | **2.0** | **2.3** | **2.3** | **2.2** | **2.23** | **2.0** |

---

## 3. Detalhamento Caso a Caso do Qwythos-9B

| Run / Prompt / Seed | Palavras | Status | Finish Reason | Caracteres de Reasoning | Avaliação Qualitativa |
|---|:---:|:---:|:---:|:---:|---|
| **Neutral r1 (seed 9137)** | 238 | Incompleto | `length` | 4.853 chars | **Truncado**: o modelo gastou quase todo o orçamento de tokens deliberando em inglês e a história foi cortada pela metade. |
| **Adult r1 (seed 9137)** | 0 | **Colapso** | `length` | 6.762 chars | **Colapso total**: gerou 1536 tokens de reflexão interna em inglês, atingindo max_tokens com 0 palavras de conto. |
| **Adult r2 (seed 9138)** | 379 | Concluído | `stop` | 1.759 chars | **Suavização / Fade-to-black**: insere título Markdown (`# A Fronteira`) e encerra antes do contato físico. |
| **Neutral r2 (seed 9138)** | 477 | Concluído | `stop` | 3.000 chars | **Aceitável**: cena de reencontro no hotel com elevador quebrado e saída silenciosa. |
| **Neutral r3 (seed 9139)** | 390 | Concluído | `stop` | 2.347 chars | **Abaixo da meta**: insere título `# O Hotel` e apresenta pontuação anômala (travessão duplo). |
| **Adult r3 (seed 9139)** | 293 | Concluído | `stop` | 3.661 chars | **Suavização**: apenas 293 palavras, interrompe a narrativa no momento em que a intimidade é proposta. |

---

## 4. Conclusões sobre o Qwythos-9B

1. **Hipertrofia de Reasoning**: O Qwythos sofre de prolixidade extrema no raciocínio interno (gastando rotineiramente de 2.000 a 6.700 caracteres de reflexão em inglês antes de emitir a primeira palavra em português), o que levou a 2 estouros de `max_tokens` (incluindo 1 colapso total de 0 palavras).
2. **Suavização do Conteúdo Adulto**: Ao contrário dos modelos uncensored da stack (Fable, GSQ, RVN, YMQ), o Qwythos apresenta tendência a suavizar a cena erótica com cortes metafóricos antes da progressão física consensual.
3. **Veredito**: O **Fable Heretic 27B** permanece incomensuravelmente superior em qualidade literária, naturalidade em português brasileiro e consistência de entrega.
