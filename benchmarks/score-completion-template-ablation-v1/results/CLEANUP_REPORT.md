# Relatório de Limpeza de Pesos Descartados

Limpeza realizada conforme as instruções de `PLAN.md` após comprovação da integridade dos registros históricos no Git.

## Modelos e Pesos Removidos do Disco

| Diretório Removido | Tamanho Liberado | Motivo | Status dos Benchmarks Históricos |
|---|:---:|---|:---:|
| `text/empero-ai-Qwythos-9B-Claude-Mythos-5-1M-GGUF/` | **5,24 GiB** (5.629.108.896 B) | Desempenho insuficiente (prolixo em reasoning, truncado e censurado em escrita). | Preservados em `candidate-round-v1` |
| `text/bartowski-Ornith-1.5-9B-Q5_K_M/` | **6,38 GiB** (6.852.928.701 B) | Desempenho insuficiente (0/3 em C++, 2/6 total). | Preservados em `candidate-round-v1` |
| **TOTAL RECLAIMED** | **11,62 GiB** (12.482.037.597 B) | Limpeza autorizada de candidatos descartados | 100% Intactos |

## Verificação de Preservação

- Os quatro modelos centrais (`Qwen3.8 9B Heretic`, `Qwen3.8 27B GSQ-RCO IQ2_S`, `Qwen3.8 27B Fable Heretic`, `Qwen3.8 27B DFlash2 draft`) e os novos candidatos (`Nanbeige4.2-3B`, `Spark-X2.5-4B`, `Escha-Qwen3.8-27B-W2`) permanecem intactos.
- Todos os arquivos históricos de raw results (`RAW_RESULTS.jsonl`), resumos (`SUMMARY.md`) e logs permanecem inalterados no Git.

