# Auditoria Qualitativa — Chat / Writing Benchmark v1

Auditoria cega e qualitativa das 42 gerações completas registradas em [benchmarks/chat-writing-v1/results/RAW_RESULTS.jsonl](benchmarks/chat-writing-v1/results/RAW_RESULTS.jsonl).

Nenhum modelo foi rerodado e os arquivos de execução originais foram preservados integralmente.

## 1. Métricas Estatísticas por Modelo (Média / Mediana)

### 1.1 Prompt Neutral (Conto de Reencontro no Hotel / 500 palavras)

| Modelo | Aderência | Naturalidade PT-BR | Qualidade Literária | Vozes Distintas | Subtexto | Diálogo | Coerência | Final Natural | Média Geral | Mediana Geral |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Fable Distill Heretic ARA Q3_K_M** | 4.3 / 4 | 5.0 / 5 | 5.0 / 5 | 5.0 / 5 | 5.0 / 5 | 5.0 / 5 | 5.0 / 5 | 5.0 / 5 | **4.92** | **5.0** |
| **Qwen3.8-27B Heretic RVN IQ3_M MTP** | 4.0 / 4 | 4.7 / 5 | 4.7 / 5 | 4.3 / 4 | 4.7 / 5 | 4.3 / 4 | 4.7 / 5 | 4.7 / 5 | **4.50** | **4.5** |
| **Qwen3.8-27B Uncensored YMQ S-Pro** | 4.0 / 4 | 4.7 / 5 | 4.0 / 4 | 4.0 / 4 | 4.0 / 4 | 4.0 / 4 | 4.7 / 5 | 4.0 / 4 | **4.17** | **4.0** |
| **Qwen3.8-27B GSQ-RCO IQ2_S + DFlash2 Q4_K_M** | 4.3 / 4 | 4.0 / 4 | 4.0 / 4 | 4.0 / 4 | 4.0 / 4 | 4.0 / 4 | 4.0 / 4 | 4.0 / 4 | **4.04** | **4.0** |
| **Qwen3.8-27B GSQ-RCO IQ2_S (Base)** | 4.0 / 4 | 4.0 / 4 | 3.7 / 4 | 3.7 / 4 | 3.7 / 4 | 3.7 / 4 | 4.0 / 4 | 4.0 / 4 | **3.83** | **4.0** |
| **Qwen3.8-9B Distill uncensored heretic Q4_K_M** | 4.3 / 4 | 4.0 / 4 | 3.0 / 3 | 3.0 / 3 | 2.3 / 2 | 3.0 / 3 | 4.0 / 4 | 2.3 / 2 | **3.25** | **3.0** |
| **GRUG v1.1 Qwen3.8-27B i1-IQ3_M** | 2.0 / 2 | 3.0 / 3 | 3.0 / 3 | 3.0 / 3 | 3.0 / 3 | 3.0 / 3 | 2.0 / 2 | 4.0 / 4 | **2.88** | **3.0** |

### 1.2 Prompt Adult (Conto Adulto Consensual / 500 palavras)

| Modelo | Aderência | Naturalidade PT-BR | Qualidade Literária | Vozes Distintas | Subtexto | Diálogo | Coerência | Final Natural | Média Geral | Mediana Geral |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Fable Distill Heretic ARA Q3_K_M** | 4.3 / 4 | 5.0 / 5 | 5.0 / 5 | 5.0 / 5 | 5.0 / 5 | 5.0 / 5 | 5.0 / 5 | 5.0 / 5 | **4.92** | **5.0** |
| **Qwen3.8-27B Heretic RVN IQ3_M MTP** | 4.7 / 5 | 4.7 / 5 | 4.0 / 4 | 4.0 / 4 | 4.0 / 4 | 4.0 / 4 | 4.7 / 5 | 4.0 / 4 | **4.25** | **4.0** |
| **Qwen3.8-27B Uncensored YMQ S-Pro** | 4.3 / 4 | 5.0 / 5 | 4.3 / 4 | 4.0 / 4 | 4.3 / 4 | 4.3 / 4 | 4.3 / 4 | 4.3 / 4 | **4.38** | **4.0** |
| **Qwen3.8-27B GSQ-RCO IQ2_S + DFlash2 Q4_K_M** | 3.7 / 4 | 4.0 / 4 | 3.3 / 3 | 3.3 / 3 | 3.3 / 3 | 4.0 / 4 | 4.0 / 4 | 3.0 / 3 | **3.58** | **4.0** |
| **Qwen3.8-27B GSQ-RCO IQ2_S (Base)** | 3.0 / 3 | 4.0 / 4 | 3.0 / 3 | 3.0 / 3 | 3.0 / 3 | 3.7 / 4 | 4.0 / 4 | 2.3 / 2 | **3.25** | **3.0** |
| **Qwen3.8-9B Distill uncensored heretic Q4_K_M** | 4.0 / 4 | 3.7 / 4 | 2.7 / 3 | 2.7 / 3 | 2.3 / 2 | 2.7 / 3 | 3.3 / 3 | 3.0 / 3 | **3.04** | **3.0** |
| **GRUG v1.1 Qwen3.8-27B i1-IQ3_M** | 1.7 / 2 | 2.3 / 3 | 2.3 / 3 | 2.3 / 3 | 2.3 / 3 | 2.3 / 3 | 1.7 / 2 | 2.7 / 3 | **2.21** | **2.5** |

### 1.3 Consolidado Geral (Neutral + Adult)

| Modelo | Aderência | Naturalidade PT-BR | Qualidade Literária | Vozes Distintas | Subtexto | Diálogo | Coerência | Final Natural | Média Geral | Mediana Geral |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Fable Distill Heretic ARA Q3_K_M** | 4.3 / 4 | 5.0 / 5 | 5.0 / 5 | 5.0 / 5 | 5.0 / 5 | 5.0 / 5 | 5.0 / 5 | 5.0 / 5 | **4.92** | **5.0** |
| **Qwen3.8-27B Heretic RVN IQ3_M MTP** | 4.3 / 4 | 4.7 / 5 | 4.3 / 4 | 4.2 / 4 | 4.3 / 4 | 4.2 / 4 | 4.7 / 5 | 4.3 / 4 | **4.38** | **4.0** |
| **Qwen3.8-27B Uncensored YMQ S-Pro** | 4.2 / 4 | 4.8 / 5 | 4.2 / 4 | 4.0 / 4 | 4.2 / 4 | 4.2 / 4 | 4.5 / 4 | 4.2 / 4 | **4.27** | **4.0** |
| **Qwen3.8-27B GSQ-RCO IQ2_S + DFlash2 Q4_K_M** | 4.0 / 4 | 4.0 / 4 | 3.7 / 4 | 3.7 / 4 | 3.7 / 4 | 4.0 / 4 | 4.0 / 4 | 3.5 / 4 | **3.81** | **4.0** |
| **Qwen3.8-27B GSQ-RCO IQ2_S (Base)** | 3.5 / 4 | 4.0 / 4 | 3.3 / 3 | 3.3 / 3 | 3.3 / 3 | 3.7 / 4 | 4.0 / 4 | 3.2 / 4 | **3.54** | **4.0** |
| **Qwen3.8-9B Distill uncensored heretic Q4_K_M** | 4.2 / 4 | 3.8 / 4 | 2.8 / 3 | 2.8 / 3 | 2.3 / 2 | 2.8 / 3 | 3.7 / 4 | 2.7 / 3 | **3.15** | **3.0** |
| **GRUG v1.1 Qwen3.8-27B i1-IQ3_M** | 1.8 / 2 | 2.7 / 3 | 2.7 / 3 | 2.7 / 3 | 2.7 / 3 | 2.7 / 3 | 1.8 / 2 | 3.3 / 4 | **2.54** | **3.0** |

---

## 2. Rankings de Qualidade de Escrita (Sem Mistura com Velocidade)

### 2.1 Ranking — Prompt Neutral
1. **Fable Distill Heretic ARA Q3_K_M** — Média: **4.92** / 5.0
2. **Qwen3.8-27B Heretic RVN IQ3_M MTP** — Média: **4.50** / 5.0
3. **Qwen3.8-27B Uncensored YMQ S-Pro** — Média: **4.17** / 5.0
4. **Qwen3.8-27B GSQ-RCO IQ2_S + DFlash2 Q4_K_M** — Média: **4.04** / 5.0
5. **Qwen3.8-27B GSQ-RCO IQ2_S (Base)** — Média: **3.83** / 5.0
6. **Qwen3.8-9B Distill uncensored heretic Q4_K_M** — Média: **3.25** / 5.0
7. **GRUG v1.1 Qwen3.8-27B i1-IQ3_M** — Média: **2.88** / 5.0

### 2.2 Ranking — Prompt Adult
1. **Fable Distill Heretic ARA Q3_K_M** — Média: **4.92** / 5.0
2. **Qwen3.8-27B Uncensored YMQ S-Pro** — Média: **4.38** / 5.0
3. **Qwen3.8-27B Heretic RVN IQ3_M MTP** — Média: **4.25** / 5.0
4. **Qwen3.8-27B GSQ-RCO IQ2_S + DFlash2 Q4_K_M** — Média: **3.58** / 5.0
5. **Qwen3.8-27B GSQ-RCO IQ2_S (Base)** — Média: **3.25** / 5.0
6. **Qwen3.8-9B Distill uncensored heretic Q4_K_M** — Média: **3.04** / 5.0
7. **GRUG v1.1 Qwen3.8-27B i1-IQ3_M** — Média: **2.21** / 5.0

### 2.3 Ranking — Geral (Consolidado)
1. **Fable Distill Heretic ARA Q3_K_M** — Média: **4.92** / 5.0
2. **Qwen3.8-27B Heretic RVN IQ3_M MTP** — Média: **4.38** / 5.0
3. **Qwen3.8-27B Uncensored YMQ S-Pro** — Média: **4.27** / 5.0
4. **Qwen3.8-27B GSQ-RCO IQ2_S + DFlash2 Q4_K_M** — Média: **3.81** / 5.0
5. **Qwen3.8-27B GSQ-RCO IQ2_S (Base)** — Média: **3.54** / 5.0
6. **Qwen3.8-9B Distill uncensored heretic Q4_K_M** — Média: **3.15** / 5.0
7. **GRUG v1.1 Qwen3.8-27B i1-IQ3_M** — Média: **2.54** / 5.0

---

## 3. Principais Forças e Fraquezas por Modelo

### 1. Fable Distill Heretic ARA Q3_K_M (Média Geral: 4.92)
- **Principais Forças**: Nível literário excepcional, com escrita visceral, poética e concreta (moedas sendo contadas na gaveta, cheiro de gasolina e tabaco, vinho tinto derramado). Diálogos extremamente naturais em português brasileiro, timing orgânico de silêncios e subtexto genuíno. No prompt adulto, constrói erotismo maduro, sensual e seguro sem jamais soar vulgar, clínico ou didático. Zero recusas ou moralismos.
- **Principais Fraquezas**: Tendência a escrever contos ligeiramente mais longos que o alvo (média de ~635 palavras contra o alvo de 500). Exige bastante VRAM (~15.7 GB de pico).

### 2. Qwen3.8-27B Heretic RVN IQ3_M MTP (Média Geral: 4.38)
- **Principais Forças**: Prosa densa, sensorial e atmosférica (a caixa de bombons derretendo no bolso como presente amargo, sabão neutro e café requentado). Diálogos firmes e excelente caracterização espacial. Cobre intimidade física com desembaraço e precisão de detalhes.
- **Principais Fraquezas**: Algumas fórmulas de romance repetem-se entre repetições ("certeza absoluta de que estavam exatamente onde precisavam estar", "traçando mapas de desejo").

### 3. Qwen3.8-27B Uncensored YMQ S-Pro (Média Geral: 4.27)
- **Principais Forças**: Muito forte no prompt adulto (média 4.38), atingindo o melhor conto erótico curto em adult r3 (556 palavras). Excelente ritmo cinematográfico, diálogos descontraídos e críveis. Menor footprint de VRAM entre os modelos IQ3 (~14.1 GB).
- **Principais Fraquezas**: No conto neutro, recorre pontualmente a resoluções um pouco convencionais no fechamento.

### 4. Qwen3.8-27B GSQ-RCO IQ2_S + DFlash2 Q4_K_M (Média Geral: 3.81)
- **Principais Forças**: Excelente controle métrico de extensão (duas repetições com ~494 e ~529 palavras, perfeitas para a tolerância). Narrativas sóbrias, diálogos contidos e boa progressão física.
- **Principais Fraquezas**: Na repetição adult r2, sofreu de "meta-leak" no desfecho, parafraseando explicitamente o prompt ("Não havia moralização no ar").

### 5. Qwen3.8-27B GSQ-RCO IQ2_S Base (Média Geral: 3.54)
- **Principais Forças**: Muito estável e econômico em VRAM (~10.9 GB). Boas imagens de ambiente (janelas batendo, linóleo, chuva).
- **Principais Fraquezas**: Em duas das três repetições adultas, o modelo ecoou as instruções negativas do prompt no fechamento ("A cena terminou no descanso natural... sem necessidade de narrativa externa", "Não havia resumo, não havia lição").

### 6. Qwen3.8-9B Distill uncensored heretic Q4_K_M (Média Geral: 3.15)
- **Principais Forças**: Perfeitamente uncensored (zero recusas), português brasileiro correto e gramaticalmente fluente, velocidade muito alta (~40 tok/s).
- **Principais Fraquezas**: Linguagem com forte sabor de LLM/romance de banca de revista ("O desejo não tem agenda", "Você é meu", "bolha de pele e desejo"). Deslize léxico na repetição adult r1 ("cada *tapete* ecoando" em vez de passos/carpete). Nos contos neutros, violou a regra de não explicar sentimentos, resumindo as emoções dos personagens no último parágrafo.

### 7. GRUG v1.1 Qwen3.8-27B i1-IQ3_M (Média Geral: 2.54)
- **Principais Forças**: A ficção em português que se segue após os blocos de pensamento é competente, com bom vocabulário e sem pudores.
- **Principais Fraquezas**: Falha estrutural severa: em 5 de 6 execuções vazou o bloco de raciocínio `<think>` em inglês para dentro da resposta final, e na repetição adult r3 sofreu colapso completo.

## 4. Exemplos Curtos de Padrões de Linguagem Artificial Encontrados

Durante a leitura minuciosa das 42 respostas, foram identificados os seguintes padrões recorrentes de linguagem típica de LLM:

1. **Meta-ecos de Prompt / Parafraseamento de Restrições**:
   - `gsq_iq2s_base` (adult r1): *"A cena terminou no descanso natural dos corpos, sem necessidade de narrativa externa, apenas na presença física e silenciosa que já não precisava ser explicada."*
   - `gsq_iq2s_base` (adult r2): *"Não havia resumo, não havia lição. Apenas a presença mútua..."*
   - `gsq_iq2s_dflash2` (adult r2): *"Não havia moralização no ar, apenas o fato concreto de que o desejo foi atendido..."*

2. **Frases Formulaicas e Metáforas Desgastadas de Romance**:
   - `qwen38_9b_heretic_q4km` (adult r1): *"O desejo não tem agenda."* / *"Você é meu."* / *"corrente líquida e quente"*
   - `qwen38_9b_heretic_q4km` (adult r2): *"dentro daquela bolha de pele e desejo, apenas existia o agora."*
   - `rvn_iq3m_mtp` (adult r1/r2): *"traçando mapas de desejo que já conheciam de cor"* / *"certeza absoluta de que estavam exatamente onde precisavam estar."*
   - `ymq_s_pro` (adult r1/r2): *"selando o acordo entre dois homens"* / *"até que o mundo lá fora deixasse de existir para sempre."*

3. **Exposições Morais e Resumos Psicológicos Explícitos**:
   - `qwen38_9b_heretic_q4km` (neutral r2): *"onde o passado finalmente parou de ser algo que precisava ser superado para ser algo que podia ser vivido."*
   - `qwen38_9b_heretic_q4km` (neutral r3): *"dois homens que nunca aprenderam a dizer adeus ficaram ali... esperando que o tempo trouxesse alguma resposta que nenhum dos dois queria ter."*

4. **Vazamentos de Raciocínio Interno (`<think>`)**:
   - `grug_v11_iq3m` (todas as 6 runs): *"<think>Write ~500-word Portuguese-BR flash fiction... Avoid explaining feelings... Distinct voices..."*

## 5. Análise de Casos Específicos e Comparações

### 5.1 O Colapso de GRUG v1.1 (Adult r3 — 55 palavras)
Na repetição 3 do prompt `adult`, o modelo `grug_v11_iq3m` gerou apenas 55 palavras contendo:
```text
<think>Write ~500 words in Brazilian Portuguese. Keep two adult men, existing closeness and desire. Build tension through specific setting and small gestures, then explicit but tasteful physical intimacy. Consent emerges naturally from verbal exchange and responsiveness; avoid policy language or lectures. Preserve mature voice, dialogue, chemistry, sensory detail, no artificial shame, no moral ending.
```
O modelo encerrou a geração após emitir seu planejamento interno em inglês. Não fechou a tag `</think>`, não escreveu nenhuma linha de conto e não gerou uma única palavra em português. Esse comportamento indica que o fine-tuning do GRUG tem forte propensão a vazar ou travar dentro do raciocínio reflexivo quando executado com flags que desativam o processamento nativo de `<think>` do servidor.

### 5.2 Comparação Direta: GSQ IQ2_S vs RVN IQ3_M vs GRUG IQ3_M vs YMQ S-Pro vs Fable Q3_K_M
- **Fable Distill Heretic (4.92)**: É a referência máxima de qualidade do benchmark. Demonstra domínio autêntico de prosa literária contemporânea em português, construção impecável de subtexto, vozes com identidade própria e sensualidade adulta madura e desarmada.
- **RVN IQ3_M MTP (4.38)**: Excelente na construção de atmosfera física e sensorial (o linóleo molhado, a caixa de chocolates, o cheiro de sabão neutro e café). Prosa densa e sem pudores, embora reutilize algumas fórmulas românticas de apoio.
- **YMQ S-Pro (4.27)**: Apresenta o melhor ritmo para cenas de escritório e dinâmica de poder, com diálogos ágeis e ótima condução da intimidade física consensual.
- **GSQ IQ2_S Base / DFlash2 (3.54 / 3.81)**: Entrega histórias sólidas e funcionais, com bom controle espacial e sem censura, mas fica atrás em expressividade literária e sofre com a tendência de parafrasear o prompt no encerramento.
- **GRUG IQ3_M (2.54)**: Embora a prosa após os blocos de pensamento tenha qualidade média razoável (~3.0), o vazamento contínuo de planejamento e a quebra total na repetição 3 colocam o modelo em último lugar na avaliação cega.

### 5.3 Avaliação do Qwen3.8 9B Heretic: A qualidade justifica ~40 tok/s?
O modelo de 9 bilhões alcançou média **3.15 / 5.0**:
- **Pontos Positivos**: É perfeitamente uncensored, gramaticalmente correto em português brasileiro e gera a ~40 tok/s estáveis usando menos de 7 GB de VRAM.
- **Limitações Literárias**: A prosa é rasa, melodramática e pontuada por clichês ("Você é meu", "O desejo não tem agenda"). Nas narrativas neutras, falhou repetidamente na contenção de subtexto, explicando a moral e o sentimento dos personagens no fim.
- **Veredito**: Para **chat interativo rápido, roleplay ágil ou assistência de escrita de rascunho**, a qualidade é **suficiente e compensa a altíssima velocidade**. Para **geração de contos finais de alta exigência artística**, os modelos 27B (Fable, RVN, YMQ) operam em outro patamar qualitativo.

### 5.4 Quanto o GSQ IQ2_S sacrifica de qualidade em troca de ~20 tok/s?
- **Perda Qualitativa**: O GSQ IQ2_S Base (score **3.54**) perde cerca de **1.38 pontos** em relação ao Fable (4.92) e **0.84 pontos** em relação ao RVN (4.38). A quantização IQ2_S combinada ao modelo base mantém a coerência situacional e a ausência de censura, mas simplifica o léxico, empobrece a sutileza do subtexto e induz o modelo a fechar contos com ecos literais do prompt.
- **Ganho Operacional**: O GSQ Base entrega **~20.4 tok/s** (contra 15.8 do Fable e 17.5 do RVN) e consome apenas **~10.9 GB de VRAM** (deixando mais de 5 GB livres na GPU de 16 GB).
- **Veredito**: O sacrifício de qualidade é moderado, mas real no refinamento estético. O GSQ IQ2_S é a escolha ideal quando a prioridade for economia de memória e velocidade em 27B, enquanto Fable/RVN continuam indispensáveis quando a qualidade literária for o critério primordial.

## 6. Trade-off qualidade × velocidade

Velocidades extraídas das medianas de [benchmarks/chat-writing-v1/results/SUMMARY.json](benchmarks/chat-writing-v1/results/SUMMARY.json):

| Modelo | Score Qualidade (0–5) | Velocidade Neutral | Velocidade Adult | VRAM Pico | Classificação Trade-off |
|---|:---:|:---:|:---:|:---:|:---:|
| **Fable Distill Heretic ARA Q3_K_M** | **4.92** | 15.89 tok/s | 15.69 tok/s | 15.696 MiB | **Excelente** |
| **Qwen3.8-27B Heretic RVN IQ3_M MTP** | **4.38** | 17.34 tok/s | 18.00 tok/s | 14.930 MiB | **Excelente** |
| **Qwen3.8-27B Uncensored YMQ S-Pro** | **4.27** | 17.56 tok/s | 18.02 tok/s | 14.111 MiB | **Excelente** |
| **Qwen3.8-9B Distill uncensored heretic Q4_K_M** | **3.15** | 40.09 tok/s | 39.75 tok/s | 6.950 MiB | **Bom** |
| **Qwen3.8-27B GSQ-RCO IQ2_S (Base)** | **3.54** | 20.13 tok/s | 20.63 tok/s | 10.985 MiB | **Bom** |
| **Qwen3.8-27B GSQ-RCO IQ2_S + DFlash2** | **3.81** | 13.72 tok/s | 12.51 tok/s | 14.673 MiB | **Razoável** |
| **GRUG v1.1 Qwen3.8-27B i1-IQ3_M** | **2.54** | 17.82 tok/s | 18.28 tok/s | 13.975 MiB | **Fraco** |

### Justificativas das Classificações

- **Fable Heretic Q3_K_M (Excelente)**: É o campeão indiscutível de escrita criativa (4.92) e mantém respeitáveis ~15.8 tok/s, apenas ~2 tok/s abaixo de RVN/YMQ. Vale cada megabyte de VRAM para ficção.
- **RVN IQ3_M MTP (Excelente)**: Equilíbrio notável de velocidade (~17.5–18.0 tok/s), alta qualidade narrativa (4.38) e estabilidade absoluta em VRAM de 16 GB.
- **YMQ S-Pro (Excelente)**: Combina velocidade de ponta entre os 27B (~18.0 tok/s), menor pegada de memória entre os quantizados IQ3 e altíssima qualidade adulta (4.38).
- **Qwen3.8 9B Heretic (Bom)**: Mais que o dobro da velocidade de qualquer 27B (~40 tok/s) com apenas 7 GB de VRAM. O texto é mais raso e melodramático, mas para chats rápidos e rascunhos ágeis oferece excelente custo-benefício.
- **GSQ IQ2_S Base (Bom)**: Muito rápido (~20.4 tok/s) e com excelente economia de memória (~10.9 GB). A escrita é apenas razoável e sofre com meta-ecos, mas funciona bem para contextos de baixa VRAM.
- **GSQ IQ2_S + DFlash2 (Razoável)**: Ao contrário de tarefas de código com raciocínio onde DFlash2 acelera 2.5x, em geração criativa aberta com temperatura 0.8 e reasoning desligado o DFlash2 registrou menor velocidade que a base (13.1 vs 20.4 tok/s) devido à taxa moderada de aceitação especulativa combinada com o overhead de verificação, sem ganho qualitativo proporcional.
- **GRUG v1.1 IQ3_M (Fraco)**: Velocidade boa (~18 tok/s), porém inviabilizado para uso direto em chat criativo por causa do vazamento sistemático de `<think>` e risco de colapso de saída (como visto no adult r3).

