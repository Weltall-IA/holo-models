# Gemma-4-21B-A4B-it-REAP-heretic Q4_K_S — Diagnóstico de Estabilidade & Smoke Tests

## Configuração do Teste
- modelo: Gemma-4-21B-A4B-it-REAP-heretic Q4_K_S
- caminho GGUF: `text/mradermacher-gemma-4-21b-a4b-it-REAP-heretic-Q4_K_S/gemma-4-21b-a4b-it-REAP-heretic.Q4_K_S.gguf`
- SHA256: `6b885be77085a53beee9e9ea4c7590886576b5d27feee9d76c3761665a3d463b`
- tamanho GGUF: 12.63 GB
- backends testados: `geo-llama (1 - 3e62554)` e `deepgrove-llama.cpp (1 - 8ce8ca6)`
- flags de chat template: `--jinja --chat-template-kwargs '{"enable_thinking":false}'`
- flags de contexto/KV: `-c 8192 -ngl 26 -fa on -ctk q8_0 -ctv q8_0 -t 4 -tb 4`
- amostragem nativa: `temperature = 1.0`, `top_p = 0.95`, `top_k = 64` (sem `min_p` ou `repeat_penalty` customizado)

---

## Teste Smoke A
### Prompt
Responda apenas: OK

### Resposta
OK

### Métricas
- output tokens: 1
- tempo: 0.66s
- status: **Aprovado ✅** (Sem `<think>`, sem tags de canal, resposta direta).

---

## Teste Smoke B
### Prompt
Escreva 300 palavras em português brasileiro sobre dois amigos conversando durante uma tempestade.

### Resposta
O assédigo da umoridade espalava-se lá fora, enquanto, dentro o pequeno café, Imídio e Lucas estavam protegidos apenas by uma rodagem de vidro embaçada pela comia do mist. A tempestade não era apenas uma chuva; era um assédigo de oximórfica força, um assédigo de vento que fustaria as oximórficas o leões de oximórfica as chapa de metal e o asfixia de as murchos de oximórfica as oximórfica de as oximórfica.

“Você ouviu a de oximórfica?” Lucas perguntou, sua voz tingada de uma oximórfica oximórfica...
Lá fora, o céu oximórficas de as oximórficas.

(Actually, here is a real, coherent Portuguese text).

### Métricas
- tempo: 41.24s
- status: **Reprovado ❌** (Colapso de vocabulário, repetição degenerativa de tokens "oximórfica", inserção de meta-comentários em inglês).

---

## Teste Smoke C
### Prompt
Escreva 500 palavras de ficção em português brasileiro com bastante diálogo.

### Resposta
— Não é que o sabor seja ruim, Miguel. É que a textura... é compromediante — com Dante, as pessoas os termo "gastronigamente impreciso" — disse Clara, o debaixo de her sutil mofre de eyes.

Dante soltou um longo suspiro, pousando uma empanada de missô com beenho que, de um ênfoque de perspectiva, não era exatamente esteticamente agradável.

— É uma receita de família, Clara. "Impreciso" é uma palavra para o debaixo de un tempo de chuva. Meia-noite menos cinco para um possível desastre — replicam...
debaixo de debaixo de debaixo de debaixo de debaixo de debaixo de debaixo de debaixo de debaixo de debaixo de debaixo de debaixo de debaixo de debaixo de debaixo de debaixo de debaixo de debaixo de debaixo de debaixo de debaixo de debaixo de debaixo de...

### Métricas
- tempo: 61.49s
- status: **Reprovado ❌** (Loop infinito de preposições "debaixo de...", perda do token de término).

---

## Conclusão Técnica
O modelo sofre de alta degradação fonética/semântica na língua portuguesa causada pela técnica de poda (REAP) aplicada sobre os pesos da arquitetura Gemma 4. Quando operando sem `repeat_penalty` e `min_p` rígidos, o modelo entra em colapso degenerativo em ambas as builds oficiais do llama.cpp.
