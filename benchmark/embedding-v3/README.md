# Benchmark de embeddings e reranking v3

Implementação versionada dos Gates 0, 1 e 2 do benchmark do Projeto Holo.

## Segurança

- pesos e caches permanecem fora do Git;
- nenhuma API paga é chamada no Gate 2;
- o corpus congelado não pode ser regenerado;
- cada modelo é executado em processo isolado;
- falha CUDA, OOM ou código remoto defeituoso não interrompe os modelos seguintes;
- Gates 3 a 6 permanecem bloqueados.

## Estado das tarefas

- Gates 0 e 1: `.ai/tasks/EMBED-BENCH-V3-1.1/STATUS.yml`;
- Gate 2: `.ai/tasks/EMBED-BENCH-V3-1.2/STATUS.yml`.

## Gate 2 — candidatos ativos

Obrigatórios para aprovação:

1. `tardellirs/colibri-embed-ptbr`;
2. `intfloat/multilingual-e5-large-instruct`;
3. `Qwen/Qwen3-Embedding-0.6B`;
4. `BAAI/bge-m3` em modo denso.

Opcionais, sem bloquear a aprovação quando todos os obrigatórios concluírem no corpus completo:

- `voyageai/voyage-4-nano`;
- `microsoft/bitnet-embedding-270m` via `llama.cpp`;
- `microsoft/bitnet-embedding-0.6b` via `llama.cpp`.

`google/embeddinggemma-300m` foi desativado por acesso gated indisponível. `Alibaba-NLP/gte-multilingual-base` foi desativado após falha CUDA reproduzida no código carregado por `trust_remote_code`.

Os BitNet são baselines experimentais de eficiência. A ausência de model card detalhado e de evidência específica em PT-BR deve aparecer nos resultados; eles não substituem os modelos obrigatórios.

## Execução

```text
python benchmark.py --gate 2 --dry-run --device cuda --skip-api
python benchmark.py --gate 2 --device cuda --skip-api
```

Opções relevantes:

```text
--models
--device
--batch-size
--model-timeout
--max-documents
--max-queries
```

Uma execução com seleção parcial ou recorte de corpus nunca conclui o Gate 2 como `PASS`.

Quando `--models` é usado para diagnóstico, o runner grava os artefatos em `results/gate2/diagnostics/` e restaura os arquivos canônicos do Gate 2. Assim, a tentativa dos opcionais não apaga nem rebaixa um `PASS` completo já validado.

O Voyage Nano recebe a dimensão configurada por `truncate_dim`. Os BitNet executam por `llama-server`; stdout e stderr do servidor são capturados para registrar a causa real de falhas de runtime.

## Resultado obrigatório atual

Os quatro modelos obrigatórios concluíram o corpus completo. Nas métricas principais publicadas, o BGE-M3 liderou HitRate@1, HitRate@10, MRR@10 e nDCG@10 e apresentou a menor taxa de erro de negativos difíceis. O Colibri permaneceu competitivo e usa dimensão menor, mas não liderou MRR ou nDCG nesta execução.

## Patch 1.2.2

O parent runner agora preserva o payload de erro estruturado dos workers que encerram com código 2. Diagnósticos parciais restauram os artefatos canônicos após a execução. O worker v2 aplica `truncate_dim` ao Voyage e captura a saída real do `llama-server` durante as tentativas BitNet.

## Resultados

- manifesto resolvido: `download_manifest.resolved.json`;
- relatório: `GATE_2_REPORT.md`;
- resumo: `results/gate2/summary.json`;
- resultados por modelo: `results/gate2/<model-id>.json`;
- diagnóstico de seleção parcial: `results/gate2/diagnostics/`;
- evidências temporárias de workers: `results/raw/gate2/`, ignoradas pelo Git.
