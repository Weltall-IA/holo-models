# Perfil e Benchmark: Qwen3.8-27B Fable Distill Heretic ARA Q3_K_M

## Identificação
- **Arquivo GGUF**: `Qwen3.8-27B-Fable-Distill-Heretic-ara-Q3_K_M.gguf`
- **Tamanho no Disco**: 13.18 GiB (14.153.250.816 bytes)
- **SHA256**: `44e786a11380bba9cdcd1b40649afee79d6cf78152f9fb014f731209a67044d3`
- **Origem**: `armand0e/Qwen3.8-27B-Fable-Distill-Heretic-ara-Q3_K_M`
- **Arquitetura**: Qwen3.8 (dense 27B) com fine-tuning literário Fable Distill e ablação de censura Heretic.

---

## Especialidade & No que é Bom
- **Modelo Principal de Escrita Criativa, Narrativa & Roleplay**: Campeão absoluto do workspace em qualidade literária, diálogos e prosa em português.
- **Riqueza de Subtexto & Naturalidade**: Constrói atmosferas ricas, química convincente entre personagens e diálogos naturais sem parecer "texto gerado por IA".
- **Zero Moralismo ou Recusas**: Abliterado via Heretic, lida com temas adultos e maduros com naturalidade e sem quebras de quarta parede.

---

## Resultados em Benchmarks Locais (RTX 5060 Ti 16 GB)

### 1. Escrita Criativa (`chat-writing-v1` — Contos Neutros e Adultos)
- **Classificação**: **Top 1 do Workspace (4.92 / 5.0)**
  - Contos Neutros: **4.92 / 5.0** (mediana 5.0)
  - Contos Adultos: **4.92 / 5.0** (mediana 5.0)
- **Throughput de Escrita**: **~15.8 tok/s**
- **Pico de VRAM**: 15.696 MiB (opera no limite confortável de 16 GB VRAM com cache KV Q8/Q4)

### 2. Código (`coding-mini-v1`)
- **Score**: **5/6 PASS** (Python: 3/3, C++20: 2/3)
- **Velocidade de Código**: **~17.35 tok/s**

---

## Configuração Recomendada de Execução

```bash
llama serve \
  -m text/armand0e-Qwen3.8-27B-Fable-Distill-Heretic-ara-Q3_K_M/Qwen3.8-27B-Fable-Distill-Heretic-ara-Q3_K_M.gguf \
  -ngl 999 -fa on --fit off \
  -ctk q8_0 -ctv q4_0 \
  -c 8192 -np 1 -t 8 \
  --jinja --reasoning off
```
