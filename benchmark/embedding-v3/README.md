# Benchmark de embeddings e reranking v3

Implementação versionada dos Gates 0, 1, 2 e 3 do benchmark do Projeto Holo.

## Segurança

- pesos e caches permanecem fora do Git;
- nenhuma API paga é chamada nos Gates 2 ou 3;
- o corpus congelado não pode ser regenerado;
- cada modelo é executado em processo isolado;
- falha CUDA, OOM, erro de modelo ou falha do `llama-server` não interrompe os modelos seguintes;
- Gates 4 a 6 permanecem bloqueados até autorização explícita.

## Estado das tarefas

- Gates 0 e 1: `.ai/tasks/EMBED-BENCH-V3-1.1/STATUS.yml`;
- Gate 2: `.ai/tasks/EMBED-BENCH-V3-1.2/STATUS.yml`;
- Gate 3: `.ai/tasks/EMBED-BENCH-V3-1.3/STATUS.yml`.

## Gate 2 — modelos locais compactos

Obrigatórios para aprovação:

1. `tardellirs/colibri-embed-ptbr`;
2. `intfloat/multilingual-e5-large-instruct`;
3. `Qwen/Qwen3-Embedding-0.6B`;
4. `BAAI/bge-m3` em modo denso.

O Voyage Nano foi executado como opcional e reproduzido com `transformers==4.57.6`. Os BitNet 270M e 0.6B foram testados, mas os GGUF oficiais são incompatíveis com o llama.cpp 9972 por usarem o tipo removido `TYPE_IQ4_NL_4_4`.

O Gate 2 canônico permanece `PASS`.

## Gate 3 — embeddings GGUF no llama.cpp

O Gate 3 compara três rotas GGUF executadas pelo `llama-server` estável:

1. `Qwen/Qwen3-Embedding-8B-GGUF`, preferencialmente `Q8_0`, com `Q6_K` permitido apenas como fallback registrado;
2. `ggml-org/embeddinggemma-300M-GGUF` em `Q8_0`;
3. `Qwen/Qwen3-Embedding-0.6B-GGUF` em `Q8_0`.

Os três modelos são obrigatórios para `PASS`. A execução completa exige:

- Gates 0, 1 e 2 em `PASS`;
- corpus completo de 600 documentos e 150 consultas;
- dispositivo CUDA;
- revisão imutável, licença, arquivo GGUF, tamanho e SHA-256 registrados;
- modelo executado em processo e servidor isolados;
- versão do `llama-server`, pooling, quantização, dimensão, throughput e pico de VRAM registrados.

Qwen3 usa pooling `last` e instrução de consulta. O modelo 8B retorna até 4096 dimensões; o benchmark usa as primeiras 1024 dimensões Matryoshka e normaliza novamente em L2. EmbeddingGemma usa pooling `mean`, dimensão 768 e os prompts assimétricos oficiais de consulta e documento.

Uma seleção parcial com `--models`, execução em CPU ou recorte do corpus nunca conclui o Gate 3 como `PASS`. Diagnósticos parciais são gravados em `results/gate3/diagnostics/` sem substituir os artefatos canônicos.

## Perfis Nemotron 1B admitidos

Os perfis `nvidia/Nemotron-3-Embed-1B-NVFP4` em vLLM e
`zenmagnets/Nemotron-3-Embed-1B-Q4_K_M-GGUF` em llama.cpp permanecem separados
no benchmark completo. A configuração canônica está em
`config/nemotron_1b_profiles.json`; ambos usam o corpus congelado completo,
prefixos `query: ` e `passage: `, pooling mean e normalização L2.

O NVFP4 deve ser executado somente com vLLM em ambiente isolado. O GGUF é o
perfil de menor consumo e cold start; o NVFP4 é o perfil de maior throughput
em lote no host medido. Resultados, limites e evidências da admissão estão em
`NEMOTRON_AUDIT_1_0_5_REPORT.md`.

## Execução

```text
python benchmark.py --gate 2 --dry-run --device cuda --skip-api
python benchmark.py --gate 2 --device cuda --skip-api

python benchmark.py --gate 3 --dry-run --device cuda --skip-api
python benchmark.py --gate 3 --device cuda --batch-size 16 --skip-api
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

## Resultados

Gate 2:

- manifesto resolvido: `download_manifest.resolved.json`;
- relatório: `GATE_2_REPORT.md`;
- resumo: `results/gate2/summary.json`;
- resultados por modelo: `results/gate2/<model-id>.json`;
- diagnósticos: `results/gate2/diagnostics/`.

Gate 3:

- manifesto resolvido: `download_manifest_gate3.resolved.json`;
- relatório: `GATE_3_REPORT.md`;
- resumo: `results/gate3/summary.json`;
- resultados por modelo: `results/gate3/<model-id>.json`;
- diagnósticos: `results/gate3/diagnostics/`.

Evidências temporárias de workers permanecem em `results/raw/` e são ignoradas pelo Git.
