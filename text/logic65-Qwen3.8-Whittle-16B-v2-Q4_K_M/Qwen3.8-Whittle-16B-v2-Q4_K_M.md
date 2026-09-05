# Qwen3.8-Whittle-16B-v2-Q4_K_M

## Identificação técnica

- Arquivo GGUF: `Qwen3.8-Whittle-16B-v2-Q4_K_M.gguf`
- Tamanho local registrado: `10142250656` bytes (`9.45 GiB`)
- SHA256: `335627718b0893a1b077728cd40b4a6b75e2850a6058eb564945f7a2b6265bd2`
- Origem: `logic65/Qwen3.8-Whittle-16B`
- Revisão HF: `d18db969059b15423be91f5d4fd119c8c907801c`
- Caminho canônico: `text/logic65-Qwen3.8-Whittle-16B-v2-Q4_K_M/Qwen3.8-Whittle-16B-v2-Q4_K_M.gguf`
- Arquitetura: `qwen35` dense pruned (44 layers, 5120 embed, 24 heads, context 262144) — Qwen3.8 27B → ~16.8B healed
- Quantização: `Q4_K_M` (file_type 15, ~4.5 bpw, quantization_version 2)
- GGUF metadados: `general.name=Q38Whittle2_Hf`, `general.size_label=16B`, `tokenizer=gpt2`
- Status no workspace: candidato avaliado 2026-09-04 / classificação WHITTLE16B_REJECT

## Especialidade, pontos fortes e trade-offs

- **0/6** no coding-mini-v1 — rejeitado para código principal.
- Mediana AUTHOR_RECIPE: 19.83 tok/s (não comparável diretamente a leaderboard same-protocol 24.70 GSQ).
- Pico VRAM Stage A: 11076 MiB.
- DFlash2 não avaliado (gate).
- Agent não executado (gate 6/6 required).
- Limitações: poda estrutural impede assumir compatibilidade speculative; throughput AUTHOR_RECIPE não é sama-protocol; benchmark limitado a 6 casos coding + 8 agent.

## MEDIDO LOCALMENTE

Hardware: NVIDIA GeForce RTX 5060 Ti 16 GB.

Runtime: `0.3.0-dev (build 10752, commit b96806d96) — GNU 16.2.1 for Linux x86_64`; 8 threads; full GPU offload; Flash Attention ON; ctx 8192; KV q8_0/q4_0; fit off.

Data validação: `2026-09-04`.

Proveniência: `benchmarks/whittle16b-candidate-v1/results/` — commit `9f38f42fc2` → ver novo SHA após push + RUN_MANIFEST.json

### Código — Whittle 16B v2 Q4_K_M AUTHOR_RECIPE (Stage A)

Fonte: `benchmarks/whittle16b-candidate-v1/results/WHITTLE16B_NATIVE_CODING.jsonl` — receita autora (`--jinja --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 4 --repeat-penalty 1.15 --repeat-last-n 512 temp 0.7 top_p 0.95 min_p 0.05`, thinking ON, max_tokens ≥3072).

- Score: **0/6**
- Python: **0/3**
- C++: **0/3**
- Mediana decode AUTHOR_RECIPE: **19.83 tok/s**
- Pico VRAM: **11076 MiB**
- Casos:
  - PY01 ttl_cache_injected_clock (python medium): **FAIL** compile True public True hidden False tok/s 22.112737479908297 wall 34.5731 TTFT 15.2499 trunc False loop False thinking_finished True
  - PY02 retry_decorator_repair (python medium): **FAIL** compile False public False hidden False tok/s 19.94074647210679 wall 85.548 TTFT 34.3869 trunc False loop False thinking_finished True
  - PY03 deterministic_dependency_order (python hard): **FAIL** compile True public False hidden False tok/s 21.729163202330895 wall 41.9117 TTFT 19.7747 trunc False loop False thinking_finished True
  - CPP01 normalize_int64_ranges (cpp medium): **FAIL** compile False public False hidden False tok/s 19.72484941008421 wall 72.7066 TTFT 30.3512 trunc False loop False thinking_finished True
  - CPP02 sliding_window_statistics_repair (cpp medium): **FAIL** compile False public False hidden False tok/s 16.201184567901343 wall 168.4739 TTFT 136.412 trunc False loop False thinking_finished True
  - CPP03 lazy_segment_tree_affine (cpp hard): **FAIL** compile False public False hidden False tok/s 16.028770656862882 wall 193.3724 TTFT 46.5257 trunc True loop False thinking_finished False

### Código — Whittle 16B + DFlash2

- N/A / não testado (gate 0–4/6 skip per SPEC)

### Agent — Whittle 16B

- N/A / não testado (gate: requer 6/6 coding estável). Se Stage A foi 5/6, agente não é elegível.

## DECLARADO PELO AUTOR/ORIGEM

- Origem HF: `logic65/Qwen3.8-Whittle-16B` (pruned 27B→~16.8B healed), recomendado GGUF `gguf/Qwen3.8-Whittle-16B-v2-Q4_K_M.gguf`.
- Receita autora: `--jinja --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 4 --repeat-penalty 1.15 --repeat-last-n 512 --temp 0.7 --top-p 0.95 --min-p 0.05` + thinking model.
- Autor afirma THINKING MODEL; benchmark usou reasoning ON nativo com orçamento ≥2048 tokens (3072 usado).
- Modelo estruturalmente podado → DFlash2 compatibility NÃO assumida.
- Scores externos do card não foram usados para classificação; apenas medições locais.

## Preset recomendado

```bash
# Whittle 16B v2 Q4_K_M — receita autora (coding) — NÃO é preset padrão atual por gate 0–4/6 ou 5/6
/home/alpha/.local/bin/llama serve \
  -m /home/alpha/Playstoria/models/text/logic65-Qwen3.8-Whittle-16B-v2-Q4_K_M/Qwen3.8-Whittle-16B-v2-Q4_K_M.gguf \
  -c 8192 -np 1 -ngl 999 -fa on --fit off -ctk q8_0 -ctv q4_0 -t 8 -tb 8 \
  --jinja --reasoning on --reasoning-format auto --chat-template-kwargs '{"enable_thinking":true}' \
  --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 4 --repeat-penalty 1.15 --repeat-last-n 512
```
- **Não usar como coder principal** até atingir 6/6 estável. GSQ continua preset padrão (ver `text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-IQ2_S/`).

## Limitações

- Benchmark limitado a 0/6 coding + N/A/8 agent; não cobre chat geral, escrita longa, ou tarefas repo-level.
- Throughput AUTHOR_RECIPE não comparável a histórico same-protocol; usar apenas para custo operacional.
- Poda estrutural — não assumir compatibilidade com futuros drafts speculative sem teste.
- Amostras de GPU preflight em `results/gpu-preflight/`; todas passaram gate <25% SM.
- Classificação final: **WHITTLE16B_REJECT** — não promover com base em card HF.

## Proveniência & validação

- Benchmark raiz: `benchmarks/whittle16b-candidate-v1/SPEC.md`
- Resultados: `benchmarks/whittle16b-candidate-v1/results/`
- Manifest: `benchmarks/whittle16b-candidate-v1/results/RUN_MANIFEST.json`
- Data: 2026-09-04 / hardware NVIDIA GeForce RTX 5060 Ti 16 GB / runtime `0.3.0-dev (build 10752, commit b96806d96)`
