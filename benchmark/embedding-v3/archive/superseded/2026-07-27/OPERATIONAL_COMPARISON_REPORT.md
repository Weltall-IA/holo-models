# Comparação Operacional — Seleção do Pipeline Padrão

## Resumo

Comparação objetiva de dois pipelines de embedding + reranker no hardware local
(RTX 5060 Ti 16 GB, 16 cores, 31 GB RAM). Medidas reais de carregamento,
indexação, latência de consulta, VRAM/RAM, estabilidade e erros. Qualidade
reutilizada dos artefatos de benchmark já concluídos (sem recálculo).

| Pipeline | Embedding | Reranker |
|----------|-----------|----------|
| A | qwen3_embedding_4b_q8_0 (Q8_0, 4.3 GB GGUF) | Qwen3-Reranker-0.6B |
| B | nomic_embed_text_v2_moe_q4 (Q4_K_M, 344 MB GGUF) | Qwen3-Reranker-0.6B |

- Frozen corpus: 600 docs / 150 queries (`corpus_sha256` validado).
- Candidatos: top-50 por consulta (reutilizados, sem recálculo de embeddings).
- Reranker: Qwen3-Reranker-0.6B (cache local, sem download externo).

## Resultados Medidos

| Métrica | qwen3_4b + qwen_local | nomic_moe + qwen_local |
|---------|----------------------:|------------------------:|
| **Qualidade MRR@10** | **0.8243** | 0.8229 |
| HitRate@10 | 0.8867 | 0.8800 |
| nDCG@10 | 0.8316 | 0.8290 |
| | | |
| **Carregamento embedding** | 2.1 s | 3.0 s |
| **Indexação (600 docs)** | **75.6 s** | **7.1 s** |
| Docs/segundo | 7.9 | **84.6** |
| | | |
| **Latência combinada (embed+rerank)** | | |
|   p50 | 4 240 ms | 4 644 ms |
|   p95 | 4 720 ms | 4 787 ms |
|   máxima | **7 200 ms** | 4 928 ms |
| QPS | 0.24 | 0.22 |
| | | |
| **Pico GPU** | 15.27 GB | 15.14 GB |
| **Pico RAM (RSS)** | 5.62 GB | 5.89 GB |
| **Erros** | **5 / 150** | **0 / 150** |
| **Estável** | **Não** | **Sim** |

## Análise

### Qualidade

- **qwen3_4b**: MRR@10 = 0.8243 (+0.17% sobre nomic). Diferença
  marginal dentro da variância do benchmark.
- **nomic_moe**: MRR@10 = 0.8229. Praticamente equivalente.

### Desempenho de Indexação

- **nomic_moe**: 84.6 docs/s — **10.7× mais rápido** que qwen3_4b.
  Modelo 12.5× menor (344 MB vs 4.3 GB) permite indexação quase 12× mais
  rápida. Em produção com corpus maior, essa diferença é decisiva.
- **qwen3_4b**: 7.9 docs/s — lento para 4.3 GB de pesos; cada batch
  de 64 docs leva ~6 s no servidor.

### Latência de Consulta

- **p50**: qwen3_4b (4 240 ms) é ~9% mais rápido que nomic (4 644 ms).
- **p95**: Ambos próximos (~4.7 s). Reranker domina o custo.
- **máxima**: qwen3_4b atinge 7 200 ms (81% acima da mediana) —
  outlier causado por pressão de VRAM compartilhada. nomic é mais
  consistente (máx 4 928 ms).
- O **reranker Qwen3-Reranker-0.6B** é o gargalo dominante em ambos os
  pipelines (~4.5 s por consulta de 50 pares). O tempo de embedding da
  consulta é marginal (~50 ms).

### VRAM / RAM

- Ambos os pipelines atingem ~15 GB de VRAM (embedding server + CrossEncoder
  co-residentes na RTX 5060 Ti 16 GB). Não há margem para crescimento.
- RAM: ~5.6–5.9 GB (processo Python + filhos). Não é limitante.

### Estabilidade

- **qwen3_4b**: 5 erros (3.3% das consultas). Causa provável: pressão de
  VRAM (15.27 GB em 16 GB disponível) causando falhas intermitentes no
  reranker ou no servidor de embedding. Pipeline **instável**.
- **nomic_moe**: 0 erros, 150/150 consultas concluídas. Pipeline **estável**.

## Recomendação

| Critério | Vencedor | Motivo |
|----------|----------|--------|
| Melhor qualidade | qwen3_4b (+0.17% MRR) | Diferença marginal |
| Melhor desempenho | **nomic_moe** | 10.7× mais rápido na indexação, 0 erros |
| Melhor equilíbrio | **nomic_moe** | Qualidade equivalente + estabilidade total + indexação 10× mais rápida |
| **Pipeline recomendado** | **nomic_embed_text_v2_moe_q4 + qwen_local** | Estabilidade, desempenho e qualidade Equivalentes |
| Pipeline de fallback | qwen3_embedding_4b_q8_0 + qwen_local | Para cenários onde ~0.2% MRR extra justifica risco de instabilidade |

### Justificativa da Recomendação

O **nomic_embed_text_v2_moe_q4 + qwen_local** é o pipeline recomendado para
produção porque:

1. **Estabilidade**: 0 erros vs 5 erros do qwen3_4b. Em produção, 3.3% de
   falha é inaceitável.
2. **Indexação 10× mais rápida**: 7.1 s vs 75.6 s para 600 docs. Em corpus
   maiores, a diferença é cúbica.
3. **Qualidade equivalente**: MRR@10 0.8229 vs 0.8243 — diferença de 0.17%,
   dentro da variância do benchmark.
4. **Latência mais consistente**: máximo 4 928 ms vs 7 200 ms (outlier).
5. **Modelo menor**: 344 MB vs 4.3 GB — mais fácil de distribuir e atualizar.

O qwen3_4b permanece como fallback para pesquisas ou cenários onde a máxima
qualidade é o único critério e a instabilidade pode ser mitigada por retry.

## Artefatos

- `results/operational/operational_comparison.json`: medições brutas (150
  latências por pipeline, VRAM/RAM amostrados, tempos por fase).
- `operational_compare.py`: harness de medição (reutiliza
  `holo_benchmark.reranker_runtime` e `gate2_worker`).

## Metodologia

1. Para cada variante:
   - Servidor de embedding (llama.cpp, `--embedding --pooling mean`) carregado
     e medido via `_wait_server`.
   - Indexação: 600 documentos codificados via `llama_cpp_encode` em batches de
     64.
   - Consultas: 150 queries codificadas (embedding) + rerank (CrossEncoder) em
     sequência; latência combinada medida por consulta.
2. `ResourceSampler` (psutil + pynvml) amostra VRAM/RAM do processo + filhos a
   cada 0.3 s durante todo o pipeline.
3. Qualidade extraída dos artefatos `results/reranker/pipelines/qwen_local/`
   (benchmark anterior, sem recálculo).
4. Nenhuma chamada externa (Voyage, download de modelo). Cache local
   Qwen3-Reranker-0.6B utilizado.
