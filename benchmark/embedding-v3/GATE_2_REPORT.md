# GATE 2 REPORT

- modo: execução
- resultado: PASS
- corpus SHA-256: `8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b`

## Modelos

| modelo | backend | revisão | dimensão | HitRate@10 | MRR@10 | nDCG@10 | docs/s | consultas/s |
|---|---|---|---:|---:|---:|---:|---:|---:|
| colibri_ptbr | sentence-transformers | `95a4d4f3a1c0` | 768 | 0.846667 | 0.696611 | 0.725809 | 43.388 | 164.4016 |
| multilingual_e5_large_instruct | sentence-transformers | `274baa43b0e1` | 1024 | 0.846667 | 0.632894 | 0.678763 | 108.6642 | 582.9771 |
| qwen3_embedding_06 | sentence-transformers | `97b0c614be4d` | 1024 | 0.826667 | 0.616349 | 0.663419 | 33.8949 | 222.2551 |
| bge_m3_dense | sentence-transformers | `5617a9f61b02` | 1024 | 0.880000 | 0.718167 | 0.749013 | 33.3037 | 355.1136 |

## Falhas e bloqueios
- `voyage4_nano` (opcional): WorkerProcessError: worker terminou com código 2; o próximo modelo continuará em processo limpo
- `bitnet_270m` (opcional): WorkerProcessError: worker terminou com código 2; o próximo modelo continuará em processo limpo
- `bitnet_06b` (opcional): WorkerProcessError: worker terminou com código 2; o próximo modelo continuará em processo limpo

Cada modelo foi executado em processo isolado. Uma falha CUDA não contamina os modelos seguintes.
Nenhuma API paga foi chamada. Pesos e caches permanecem fora do Git.
