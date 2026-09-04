# Perfil e Benchmark: Qwen3.8-27B GSQ-RCO IQ2_S

## Identificação
- **Arquivo GGUF**: `Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf`
- **Tamanho no Disco**: 8.62 GiB (9.255.432.192 bytes)
- **SHA256**: `16c9802111aa9ef3acde465188d6d601f8db128ee3d828ad983a5caca4135ecb`
- **Origem**: `ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-IQ2_S`
- **Arquitetura**: Qwen3.8 (dense 27B) com quantização avançada GSQ-RCO IQ2_S (~2.15 bpw).

---

## Especialidade & No que é Bom
- **Modelo Principal de Código do Workspace**: É o modelo mais consistente e preciso para desenvolvimento de software, algoritmos e refatoração.
- **Eficiência Extrema de VRAM**: 27 bilhões de parâmetros ocupando apenas ~8.6 GB de pesos físicos e ~11.2 GB de VRAM ativa em contexto 8k.
- **Excelente Compatibilidade com Speculative Decoding**: Atinge até **58.4 tok/s** quando acoplado ao `DFlash2 Q4_K_M` (`--spec-type draft-dflash --spec-draft-n-max 7`).

---

## Resultados em Benchmarks Locais (RTX 5060 Ti 16 GB)

### 1. Código (`coding-mini-v1` — 3 Python, 3 C++20)
- **Score**: **6/6 PASS (100% de Acurácia)**
  - Python: 3/3 (TTLCache, Retry Decorator, Dependency Order)
  - C++20: 3/3 (Range Normalizer, Monotonic Deque, Lazy Segment Tree Affine)
- **Velocidade Nativa**: **24.70 tok/s** (mediana)
- **Velocidade com DFlash2 (`n_max=7`)**: **46.00 tok/s** (mediana) / **58.44 tok/s** (pico PY01) — **+86.3% de ganho**
- **Pico de VRAM**: 11.216 MiB (base) / 14.086 MiB (com DFlash2)

### 2. Escrita Criativa (`chat-writing-v1`)
- **Nota Geral**: **3.54 / 5.0** (Neutral: 3.83, Adult: 3.25)
- **Comportamento**: Estável, sem recusas, porém com prosa mais direta e menos ornamental que o Fable.

---

## Configuração Recomendada de Execução

```bash
llama serve \
  -m text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-IQ2_S/Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf \
  -md text/z-lab-Qwen3.8-27B-DFlash2-GGUF/Qwen3.8-27B-DFlash2-Q4_K_M.gguf \
  --spec-type draft-dflash \
  --spec-draft-n-max 7 \
  -ngl 999 -ngld 999 -fa on --fit off \
  -ctk q8_0 -ctv q4_0 \
  -c 8192 -np 1 -t 8 \
  --jinja --reasoning off
```
