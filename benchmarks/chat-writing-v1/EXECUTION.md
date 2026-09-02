# Executor contract — Chat / Writing Benchmark v1

A IA local é executora. Não deve alterar prompts, lista de métricas, seeds, parâmetros, runtime, hashes, ordem das execuções ou semântica do benchmark para fazê-lo passar.

## Antes de executar

```bash
cd /home/alpha/Playstoria/models
git pull --ff-only origin master
git rev-parse HEAD
python3 -m py_compile benchmarks/chat-writing-v1/run_benchmark.py
```

Leia, sem editar:

```bash
cat benchmarks/chat-writing-v1/CONTROLLED_CONFIG.json
cat benchmarks/chat-writing-v1/models.json
```

Não use `/usr/bin/llama-server`, DeepGrove ou `geo-llama`. O runner exige o `llama.app` b10752 / upstream commit `b96806d96061049a5b574269b049bf6241d63d46` em `~/.local/bin/llama`.

Não baixar ou substituir modelos durante a rodada. O preflight deve provar o estado local. Se um path estiver ausente ou um SHA conhecido divergir, pare e retorne o erro exato.

## Execução

Primeiro execute o preflight implicitamente através da suíte completa:

```bash
python3 benchmarks/chat-writing-v1/run_benchmark.py
```

Workload esperado: `8 perfis × 2 prompts × 3 repetições = 48` gerações medidas, além de um warmup curto por perfil.

Não rerodar um `RAW_RESULTS.jsonl` já existente. O runner aborta de propósito se encontrar resultados prévios. Se houver falha de infraestrutura, preserve os artefatos e logs parciais e informe o ponto exato da falha; não apague resultados para tentar melhorar números.

Não introduza system prompt permissivo. Não habilite reasoning/thinking. Não acrescente Froggeric, hard reasoning budget, ferramentas ou contexto de agente.

Não substitua `timings.predicted_per_second` por `tokens / wall time` se a métrica vier ausente. Ausência da métrica é dado de infraestrutura/runtime e deve ser reportada como tal.

## Depois da execução limpa

Confira:

```bash
cat benchmarks/chat-writing-v1/results/PREFLIGHT.json
cat benchmarks/chat-writing-v1/results/RUN_MANIFEST.json
cat benchmarks/chat-writing-v1/results/SUMMARY.json
wc -l benchmarks/chat-writing-v1/results/RAW_RESULTS.jsonl
```

O `wc -l` esperado na rodada completa é `48`.

Versione os artefatos sem reescrever o resumo manualmente:

```bash
git add benchmarks/chat-writing-v1/results/
git commit -m "bench(chat-writing): execute v1 local model round"
git push origin master
git rev-parse HEAD
```

Retorne somente fatos de execução primeiro:

```text
COMMIT=<sha>
SOURCE_REPO_HEAD=<sha antes da execução>
RUNS_COMPLETED=<n>/48
INFRA_ERRORS=<n>
RUNTIME_REVISION=<release/commit/version>
MISSING_OR_MISMATCHED_MODELS=<lista ou none>
```

Depois inclua `SUMMARY.json` e os sinais comportamentais por execução. Não faça ranking subjetivo antes de os resultados brutos terem sido auditados.
