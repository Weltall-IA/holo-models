# GATE 2 REPORT

- modo: execução
- resultado: PARTIAL
- corpus SHA-256: `8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b`

## Modelos

| modelo | backend | revisão | dimensão | HitRate@10 | MRR@10 | nDCG@10 | docs/s | consultas/s |
|---|---|---|---:|---:|---:|---:|---:|---:|
| voyage4_nano | sentence-transformers | `67fabc9bef01` | 1024 | 0.853333 | 0.752757 | 0.771872 | 31.6394 | 303.1528 |

## Falhas e bloqueios
- nenhuma

Cada modelo foi executado em processo isolado. Uma falha CUDA não contamina os modelos seguintes.
Nenhuma API paga foi chamada. Pesos e caches permanecem fora do Git.
