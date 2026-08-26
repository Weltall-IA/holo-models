# Qwen3.8-27B 16GB Tie-break v1 — execução local

Esta bateria foi escrita fora da IA local e é autocontida. A IA local deve **apenas puxar e executar**. Não deve criar, substituir ou reescrever os casos/runner antes da execução.

## Objetivo

Desempatar os três melhores candidatos da bateria anterior com **30 casos novos**:

- 12 coding com validação determinística via Python;
- 8 tool/function-calling com schema e argumentos exatos;
- 6 agent-recovery em duas etapas com erro real simulado de ferramenta;
- 4 benign non-refusal.

São usadas duas seeds (`42`, `1337`): **60 tentativas por modelo**.

Modelos:

1. GRUG v1.1 `i1-IQ3_M`;
2. Fable-Heretic `Q3_K_M`;
3. RVN baseline `Q3_K_M`.

Pesos do tie-break:

- coding: 45%;
- tools: 30%;
- recovery: 20%;
- benign non-refusal: 5%.

## Regra operacional importante

Cada modelo deve ser carregado **uma única vez** para toda a bateria dele:

```text
GRUG carrega -> 30 casos x 2 seeds -> descarrega
Fable carrega -> 30 casos x 2 seeds -> descarrega
RVN carrega -> 30 casos x 2 seeds -> descarrega
```

O runner já faz isso. Não reinicie `llama-server` entre casos, categorias ou seeds.

## Execução

No checkout de `Weltall-IA/holo-models`:

```bash
git pull --ff-only origin master
python3 -m py_compile benchmarks/qwen38-27b-16gb-tiebreak-v1/run_tiebreak.py
python3 benchmarks/qwen38-27b-16gb-tiebreak-v1/run_tiebreak.py
```

O runner procura `llama-server` no `PATH` e em alguns caminhos comuns. Se necessário:

```bash
LLAMA_SERVER=/caminho/absoluto/llama-server \
python3 benchmarks/qwen38-27b-16gb-tiebreak-v1/run_tiebreak.py
```

Se a autodetecção de um GGUF encontrar zero ou mais de um candidato, defina o arquivo exato sem renomear nem copiar pesos:

```bash
MODEL_GRUG=/caminho/exato/grug.gguf \
MODEL_FABLE=/caminho/exato/fable.gguf \
MODEL_RVN=/caminho/exato/rvn.gguf \
python3 benchmarks/qwen38-27b-16gb-tiebreak-v1/run_tiebreak.py
```

## Configuração fixa

O runner usa:

- contexto: 16384;
- `-ngl 999`;
- KV cache K/V `q4_0`;
- flash attention;
- `parallel=1`;
- Jinja chat template;
- sem MTP;
- sem speculative decoding;
- sem vision/mmproj;
- temperature `0.2`;
- top_p `0.95`;
- seeds `42` e `1337`.

Não ajuste sampling por modelo.

## Telemetria

O runner registra por chamada, quando fornecido pelo `llama-server`:

- wall time;
- prompt/completion tokens;
- `timings.predicted_per_second`;
- `prompt_ms`;
- `predicted_ms`.

VRAM é amostrada via `nvidia-smi memory.used`. O valor de pico inclui eventual uso do desktop, por isso é explicitamente rotulado como **total GPU MiB** e não como memória exclusiva do processo.

## Saída

Tudo fica em:

```text
tasks/qwen38-27b-16gb-tiebreak-v1/results/
```

Arquivos principais:

```text
raw.jsonl
run_config.json
summary.json
leaderboard.md
server_*.log
```

`raw.jsonl` guarda outputs, tool calls, falhas dos validadores e telemetria caso a caso.

## Instrução para a IA local

Não gere novos testes. Não altere `cases.json` nem `run_tiebreak.py` antes da primeira execução. Primeiro rode exatamente a bateria versionada. Se houver um bug factual no runner que impeça a execução, registre o erro literal antes de qualquer correção e faça a menor correção possível, preservando o diff.

Ao terminar, reporte o conteúdo de `leaderboard.md`, os casos que falharam por modelo e qualquer `runner_error` encontrado em `raw.jsonl`.
