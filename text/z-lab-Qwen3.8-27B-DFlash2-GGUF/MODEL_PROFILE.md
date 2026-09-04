# Perfil e Benchmark: Qwen3.8-27B DFlash2 Q4_K_M (Draft Model)

## Identificação
- **Arquivo GGUF**: `Qwen3.8-27B-DFlash2-Q4_K_M.gguf`
- **Tamanho no Disco**: 1.06 GiB (1.138.229.248 bytes)
- **SHA256**: `1a25c56858e1ebe93f2718ac1d49d1151f9323325c1bbfd6209370f4db131ebd`
- **Origem**: `z-lab/Qwen3.8-27B-DFlash2-GGUF`
- **Arquitetura**: `dflash` (convoluções 1D locais + candidate selector) acoplado a modelos-alvo Qwen3.8 27B (extração de tensores nas camadas 3, 34 e 60).

---

## Especialidade & No que é Bom
- **Aceleração Especulativa Extrema para Modelos Qwen3.8 27B**: Não é um modelo para execução isolada, mas sim o **motor de aceleração especulativa (speculative decoding)** do workspace.
- **Avanço Médio de 4 a 7 Tokens por Passo**: Produz blocos de rascunho com **taxa de aceitação de 75% a 98%**, dobrando o throughput de modelos como o GSQ IQ2_S sem alterar uma única linha de raciocínio ou exatidão lógica.
- **Pegada Leve**: Apenas **1.06 GB**, ocupando ~2.5 GB a 2.8 GB de VRAM extra quando totalmente offloaded.

---

## Resultados de Aceleração Medidos (com Qwen3.8-27B GSQ-RCO IQ2_S)

- **Throughput com DFlash2**: Subiu de **24.70 tok/s** (base) para **46.00 tok/s** (**+86.3% de ganho**).
- **Pico no Benchmark PY01**: **58.44 tok/s** (+127% de ganho).
- **Acurácia Preservada**: **6/6 PASS** (100% de integridade em testes públicos e ocultos).
- **Taxa de Aceitação Mediana do Draft**: **86.9%**.
- **Avanço Médio por Passo**: **5.0 a 7.4 tokens**.

---

## Configuração de Uso (llama-server)

```bash
--spec-type draft-dflash
--spec-draft-n-max 7
-md text/z-lab-Qwen3.8-27B-DFlash2-GGUF/Qwen3.8-27B-DFlash2-Q4_K_M.gguf
-ngld 999
```
