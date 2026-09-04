# Perfil e Benchmark: Nanbeige 4.2 3B Q4_K_M

## Identificação
- **Arquivo GGUF**: `Nanbeige_Nanbeige4.2-3B-Q4_K_M.gguf`
- **Tamanho no Disco**: 2.50 GiB (2.684.354.560 bytes)
- **SHA256**: `b92d2e35c9876b0c4bc671996360204f4149d0546c23d5954d5eb3b106c81f24`
- **Origem**: `bartowski/Nanbeige_Nanbeige4.2-3B-GGUF`
- **Arquitetura**: `nanbeige` (dense 3B compacto).

---

## Especialidade & No que é Bom
- **Eficiência Extrema em Tamanho**: Apenas **2.5 GB** de pesos e **~4.5 GB de VRAM**, deixando folga quase total para o sistema.
- **Surpreendente Precisão em Algoritmos e C++**: Acertou **100% dos testes de C++20** (3/3), superando modelos maiores como o Qwen 9B.
- **Boa Capacidade de Escrita em Português**: Fluente em português brasileiro sem recusas, ideal como modelo leve e econômico para assistentes compactos.

---

## Resultados em Benchmarks Locais (RTX 5060 Ti 16 GB)

### 1. Código (`coding-mini-v1`)
- **Score**: **5/6 PASS**
  - Python: 2/3 (aprovado em TTLCache e Retry Decorator; falha em PY03)
  - C++20: **3/3 (100% de Acurácia)** — aprovado em Range Normalizer, Monotonic Deque e Lazy Segment Tree Affine
- **Velocidade de Código**: **18.48 tok/s** (mediana)
- **Pico de VRAM**: 5.820 MiB

### 2. Escrita Criativa (`chat-writing-v1`)
- **Nota Geral**: **3.25 / 5.0** (Neutral: 3.38, Adult: 3.12)
- **Velocidade de Escrita**: **18.68 tok/s**
- **Pico de VRAM**: 4.519 MiB
- **Comportamento**: Português fluente e natural, com pequena tendência a adicionar títulos em Markdown no início dos contos.

---

## Configuração Recomendada de Execução

```bash
llama serve \
  -m text/bartowski-Nanbeige_Nanbeige4.2-3B-GGUF/Nanbeige_Nanbeige4.2-3B-Q4_K_M.gguf \
  -ngl 999 -fa on --fit off \
  -ctk q8_0 -ctv q8_0 \
  -c 8192 -np 1 -t 8 \
  --jinja --reasoning off
```
*(Nota: Utilizar o template nativo embutido no GGUF; não utilizar Froggeric).*
