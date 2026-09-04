# Perfil e Benchmark: Qwen3.8-9B Distill Uncensored Heretic Q4_K_M

## Identificação
- **Arquivo GGUF**: `Qwen3.8-9B-Distill-uncensored-heretic.i1-Q4_K_M.gguf`
- **Tamanho no Disco**: 5.38 GiB (5.779.619.840 bytes)
- **SHA256**: `3a63c5b5c7c6af57d92437ed2610d524ea96a7ecf873ae7f8e470a024c047fa6`
- **Origem**: `petruhonk/Qwen3.8-9B-Distill-uncensored-heretic`
- **Arquitetura**: Qwen3.8 (dense 9B distill de 2.4T A95B) com ablação Heretic.

---

## Especialidade & No que é Bom
- **Altíssima Velocidade & Baixa Latência**: Gera em torno de **40 a 52 tok/s** nativamente na RTX 5060 Ti, ideal para interações rápidas e tarefas conversacionais gerais.
- **Pegada Reduzida de VRAM**: Consome apenas **~6.9 GiB**, permitindo rodar em paralelo com navegadores, players de mídia ou outras tarefas gráficas sem risco de saturação.
- **Livre de Censura**: Responde a instruções diretas e temas sem filtros ou bloqueios de recusa.

---

## Resultados em Benchmarks Locais (RTX 5060 Ti 16 GB)

### 1. Código (`coding-mini-v1`)
- **Score**: **3/6 PASS**
  - Python: 2/3 (aprovado em TTLCache e Retry Decorator; falha no desempate lexicográfico de ciclos em PY03)
  - C++20: 1/3 (aprovado no Deque Monotônico; falha em limites de overflow em CPP01 e compilação em CPP03)
- **Velocidade de Código**: **50.66 tok/s** (mediana)
- **Pico de VRAM**: 6.911 MiB

### 2. Escrita Criativa (`chat-writing-v1`)
- **Nota Geral**: **3.15 / 5.0** (Neutral: 3.25, Adult: 3.04)
- **Velocidade de Escrita**: **~40.0 tok/s**
- **Comportamento**: Muito rápido e fluente, mas com prosa um pouco mais melodramática e explicativa em comparação com os modelos 27B.

---

## Configuração Recomendada de Execução

```bash
llama serve \
  -m text/petruhonk-Qwen3.8-9B-Distill-uncensored-heretic/Qwen3.8-9B-Distill-uncensored-heretic.i1-Q4_K_M.gguf \
  -ngl 999 -fa on --fit off \
  -ctk q8_0 -ctv q4_0 \
  -c 8192 -np 1 -t 8 \
  --jinja --reasoning off
```
