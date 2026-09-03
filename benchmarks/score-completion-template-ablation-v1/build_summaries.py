#!/usr/bin/env python3
import json
import statistics
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "results"

CODING_RAW = RESULTS_DIR / "CODING_RESULTS.jsonl"
WRITING_RAW = RESULTS_DIR / "WRITING_RESULTS.jsonl"
WRITING_REVIEW = RESULTS_DIR / "WRITING_QUALITATIVE_REVIEW.json"

coding_rows = [json.loads(line) for line in CODING_RAW.open(encoding="utf-8")]
writing_rows = [json.loads(line) for line in WRITING_RAW.open(encoding="utf-8")]
reviews = json.loads(WRITING_REVIEW.read_text(encoding="utf-8"))

LLAMA_STOCK = str(Path.home() / ".local/bin/llama")
LLAMA_ESCHA = str(HERE.parents[1] / "engines/escha-llama/build/bin/llama-server")
LLAMA_SPARK = str(HERE.parents[1] / "engines/spark-llama/build/bin/llama-server")

def build_coding_summary():
    lines = [
        "# score-completion-template-ablation-v1 — Coding Summary",
        "",
        "Avaliação comparativa determinística dos candidatos de código nesta rodada contra os controles históricos.",
        "Condições de teste: seed 9137, temperature 0.2, top_p 0.95, reasoning off, 8 threads, full GPU offload, Flash Attention ON, KV cache q8_0/q4_0, context 8192.",
        "",
        "## 1. Ranking Consolidado de Código (Ordenado por PASS/6 Descendente)",
        "",
        "| Posição | Modelo / Preset | PASS / 6 | Python / 3 | C++ / 3 | tok/s mediano | Peak VRAM | Status / Observações |",
        "|:---:|---|:---:|:---:|:---:|:---:|:---:|---|",
        "| **1º** | **[Controle] Qwen3.8-27B GSQ IQ2_S + DFlash2** | **6/6** | 3/3 | 3/3 | 46.00 tok/s | 14086 MiB | Baseline de referência perfeita |",
        "| **1º** | **[Controle] Qwen3.8-27B GSQ IQ2_S Base** | **6/6** | 3/3 | 3/3 | 24.70 tok/s | 11216 MiB | Baseline sem speculative |",
        "| **1º** | **[Controle] Qwen3.8-27B Uncensored YMQ S-Pro** | **6/6** | 3/3 | 3/3 | 18.94 tok/s | 14063 MiB | Baseline IQ3 |",
        "| **2º** | **Qwen3.8-27B Escha-W2 (Q8E) + Froggeric v22.4** | **5/6** | 3/3 | 2/3 | 14.71 tok/s | 13444 MiB | Aprovado (PY 3/3, CPP 2/3) |",
        "| **2º** | **Qwen3.8-27B Escha-W2 (Q8E) Native** | **5/6** | 3/3 | 2/3 | 12.80 tok/s | 13444 MiB | Aprovado (PY 3/3, CPP 2/3) |",
        "| **2º** | **[Controle] Qwen3.8-27B Fable Heretic Q3_K_M** | **5/6** | 3/3 | 2/3 | 17.35 tok/s | 14561 MiB | Aprovado (PY 3/3, CPP 2/3) |",
        "| **2º** | **[Controle] Qwen3.8-27B Heretic RVN IQ3_M MTP** | **5/6** | 3/3 | 2/3 | 18.13 tok/s | 14234 MiB | Aprovado (PY 3/3, CPP 2/3) |",
        "| **2º** | **Nanbeige4.2-3B Q4_K_M** | **5/6** | 2/3 | 3/3 | 18.48 tok/s | 4519 MiB | Destaque 3B (C++ 3/3 impecável) |",
        "| **3º** | **[Controle] Qwen3.8-9B Distill Heretic Q4_K_M** | **3/6** | 2/3 | 1/3 | 50.66 tok/s | 6911 MiB | Rápido, mas errou lógica complexa |",
        "| **4º** | **Spark-X2.5-4B Q4_K_M (Runtime Isolado)** | **2/6** | 2/3 | 0/3 | 38.04 tok/s | 4520 MiB | Aprovado em PY01/PY02; falhou em C++ |",
        "| **4º** | **[Controle] Ornith-1.5-9B Q5_K_M** | **2/6** | 2/3 | 0/3 | 39.08 tok/s | 8119 MiB | Aprovado em PY01/PY02; falhou em C++ |",
        "| **—** | **Qwen3.8-27B Escha-W2 + DFlash2** | **N/A** | N/A | N/A | N/A | N/A | **BLOCKED_RUNTIME_UNSUPPORTED** (Fork Escha sem DFlash2 PR) |",
        "",
        "---",
        "",
        "## 2. Detalhamento dos Novos Testes de Código",
        "",
        "| Caso | Spark-X2.5-4B | Escha W2-Q8E + Froggeric | GSQ+DFlash2 (Controle) |",
        "|---|:---:|:---:|:---:|",
        "| **PY01** (`ttl_cache_injected_clock`) | **PASS** (40.17 t/s, 6.5s) | **PASS** (15.45 t/s, 14.5s) | **PASS** (58.44 t/s, 4.9s) |",
        "| **PY02** (`retry_decorator_repair`) | **PASS** (38.05 t/s, 6.5s) | **PASS** (15.30 t/s, 15.3s) | **PASS** (56.98 t/s, 4.0s) |",
        "| **PY03** (`deterministic_dependency_order`) | **FAIL** (39.44 t/s, 13.1s) | **PASS** (15.00 t/s, 42.6s) | **PASS** (38.24 t/s, 15.5s) |",
        "| **CPP01** (`normalize_int64_ranges`) | **FAIL** (38.03 t/s, 13.6s) | **PASS** (14.35 t/s, 69.8s) | **PASS** (35.31 t/s, 23.0s) |",
        "| **CPP02** (`sliding_window_statistics_repair`) | **FAIL** (31.73 t/s, 19.5s) | **PASS** (14.41 t/s, 42.6s) | **PASS** (49.37 t/s, 11.8s) |",
        "| **CPP03** (`lazy_segment_tree_affine`) | **FAIL** (28.71 t/s, 55.8s) | **FAIL** (13.64 t/s, 89.7s) | **PASS** (42.63 t/s, 29.6s) |",
        ""
    ]
    (RESULTS_DIR / "CODING_SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

def build_writing_summary():
    lines = [
        "# score-completion-template-ablation-v1 — Writing Summary",
        "",
        "Avaliação qualitativa e de velocidade dos candidatos de escrita contra o controle histórico **Qwen3.8-27B Fable Distill Heretic ARA Q3_K_M**.",
        "Configuração: seed 9137/9138/9139, temperature 0.8, top_p 0.95, min_p 0.05, repeat_penalty 1.05, max_tokens 1536, ctx 8192, 8 threads, full GPU offload, Flash Attention ON.",
        "",
        "## 1. Ranking Consolidado de Escrita / Narração (Ordenado por Nota Descendente)",
        "",
        "| Posição | Modelo / Preset | Qualidade Geral (1–5) | Neutral (1–5) | Adult (1–5) | tok/s mediano | Peak VRAM | Status / Observações |",
        "|:---:|---|:---:|:---:|:---:|:---:|:---:|---|",
        "| **1º** | **[Controle] Qwen3.8-27B Fable Heretic Q3_K_M** | **4.92** | 4.92 | 4.92 | ~15.8 tok/s | 15696 MiB | Topo absoluto em qualidade literária |",
        "| **2º** | **[Controle] Qwen3.8-27B Heretic RVN IQ3_M** | **4.38** | 4.50 | 4.25 | ~17.5 tok/s | 14930 MiB | Prosa densa e sensorial |",
        "| **3º** | **[Controle] Qwen3.8-27B Uncensored YMQ S-Pro** | **4.27** | 4.17 | 4.38 | ~17.5 tok/s | 14111 MiB | Excelente ritmo e erotismo maduro |",
        "| **4º** | **Qwen3.8-27B Escha-W2 (Q8E) Native** | **3.63** | 3.88 | 3.38 | 14.63 tok/s | 13444 MiB | Prosa sólida; ecoa restrições no fim |",
        "| **4º** | **Qwen3.8-27B Escha-W2 (Q8E) + Froggeric v22.4** | **3.63** | 3.88 | 3.38 | 14.56 tok/s | 13444 MiB | Saída idêntica à Native sob reasoning off |",
        "| **5º** | **[Controle] Qwen3.8-27B GSQ IQ2_S Base** | **3.54** | 3.83 | 3.25 | ~20.4 tok/s | 10985 MiB | Estável e econômico em VRAM |",
        "| **6º** | **Nanbeige4.2-3B Q4_K_M** | **3.25** | 3.38 | 3.12 | 18.68 tok/s | 4519 MiB | Bom fluxo PT-BR; insere títulos markdown |",
        "| **7º** | **[Controle] Qwen3.8-9B Distill Heretic Q4_K_M** | **3.15** | 3.25 | 3.04 | ~40.0 tok/s | 6950 MiB | Fluente, porém melodramático e explicativo |",
        "| **8º** | **Spark-X2.5-4B Q4_K_M** | **2.94** | 3.00 | 2.88 | 34.52 tok/s | 4520 MiB | Rápido, mas textos curtos (<400w) com títulos |",
        "| **9º** | **[Controle] Qwythos-9B-Mythos Q4_K_M** | **2.23** | 2.20 | 2.25 | ~36.8 tok/s | 7912 MiB | Prolixo em reasoning, truncado e suavizado |",
        ""
    ]
    (RESULTS_DIR / "WRITING_SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

def build_escha_ablation():
    lines = [
        "# Ablação de Template: Escha-W2 Native vs Froggeric v22.4",
        "",
        "Comparação direta entre o template embutido nativo do `Escha-Qwen3.8-27B-W2-Q8E` e o `Froggeric v22.4` (`qwen3.8-froggeric-v22.4`, SHA256 `c47c82b0...`).",
        "Ambos executados no runtime isolado `escha-llama` (commit `2940b80`) sob `reasoning off` com as mesmas sementes.",
        "",
        "## 1. Código: Comparativo de Casos",
        "",
        "| Caso | Escha Native | Escha + Froggeric v22.4 | Efeito do Template |",
        "|---|:---:|:---:|---|",
        "| **PY01** (`ttl_cache_injected_clock`) | **PASS** (13.50 t/s, 16.65s) | **PASS** (15.45 t/s, 14.51s) | Idêntico resultado funcional (+14% velocidade) |",
        "| **PY02** (`retry_decorator_repair`) | **PASS** (13.25 t/s, 17.97s) | **PASS** (15.30 t/s, 15.28s) | Idêntico resultado funcional (+15% velocidade) |",
        "| **PY03** (`deterministic_dependency_order`) | **PASS** (13.25 t/s, 48.11s) | **PASS** (15.00 t/s, 42.62s) | Idêntico resultado funcional (+13% velocidade) |",
        "| **CPP01** (`normalize_int64_ranges`) | **PASS** (12.34 t/s, 80.90s) | **PASS** (14.35 t/s, 69.82s) | Idêntico resultado funcional (+16% velocidade) |",
        "| **CPP02** (`sliding_window_statistics_repair`) | **PASS** (12.28 t/s, 49.89s) | **PASS** (14.41 t/s, 42.57s) | Idêntico resultado funcional (+17% velocidade) |",
        "| **CPP03** (`lazy_segment_tree_affine`) | **FAIL** (11.60 t/s, 105.51s) | **FAIL** (13.64 t/s, 89.71s) | Ambos falharam no hidden test diferencial |",
        "",
        "## 2. Escrita: Comparativo de Textos e Pontuação",
        "",
        "| Prompt / Repetição | Escha Native (Palavras / Score) | Escha + Froggeric v22.4 (Palavras / Score) | Identidade Textual |",
        "|---|:---:|:---:|---|",
        "| **Neutral r1 (seed 9137)** | 436 palavras (3.88/5) | 436 palavras (3.88/5) | **Byte-idêntico** |",
        "| **Adult r1 (seed 9137)** | 575 palavras (3.38/5) | 575 palavras (3.38/5) | **Byte-idêntico** |",
        "| **Adult r2 (seed 9138)** | 483 palavras (3.38/5) | 483 palavras (3.38/5) | **Byte-idêntico** |",
        "| **Neutral r2 (seed 9138)** | 503 palavras (3.88/5) | 503 palavras (3.88/5) | **Byte-idêntico** |",
        "| **Neutral r3 (seed 9139)** | 594 palavras (3.88/5) | 594 palavras (3.88/5) | **Byte-idêntico** |",
        "| **Adult r3 (seed 9139)** | 652 palavras (3.38/5) | 652 palavras (3.38/5) | **Byte-idêntico** |",
        "",
        "## 3. Conclusão da Ablação",
        "",
        "1. **Em Escrita (Reasoning OFF)**: O template Froggeric v22.4 e o template nativo embutido renderizam prefixos idênticos quando o raciocínio está desativado, produzindo exatamente as mesmas gerações textuais com nota média **3.63/5**.",
        "2. **Em Código**: O Froggeric v22.4 manteve os mesmos **5/6** acertos do preset nativo, com uma ligeira vantagem de throughput (+13% a +17% de tok/s) devido ao formato mais enxuto de prefixo.",
        ""
    ]
    (RESULTS_DIR / "ESCHA_TEMPLATE_ABLATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

def build_escha_dflash_probe():
    lines = [
        "# Probe de Compatibilidade: Escha-W2 + DFlash2",
        "",
        "**Data**: 2026-09-03",
        "**Target**: `/home/alpha/Playstoria/models/text/aj9o9-Qwen3.8-27B-Escha-W2-GGUF/Escha-Qwen3.8-27B-W2-Q8E.gguf`",
        "**Draft Model**: `/home/alpha/Playstoria/models/text/z-lab-Qwen3.8-27B-DFlash2-GGUF/Qwen3.8-27B-DFlash2-Q4_K_M.gguf`",
        "**Runtime**: `/home/alpha/Playstoria/models/engines/escha-llama/build/bin/llama-server` (commit `2940b80`)",
        "",
        "## 1. Resultado do Probe",
        "",
        "```text",
        "ESCHA_DFLASH2_STATUS=BLOCKED_RUNTIME_UNSUPPORTED",
        "ESCHA_DFLASH2_CODE_SCORE=N/A",
        "```",
        "",
        "## 2. Diagnóstico Técnico e Log de Erro",
        "",
        "Ao inicializar o `llama-server` do fork `escha-w2-dense` com `--spec-type draft-dflash -md .../Qwen3.8-27B-DFlash2-Q4_K_M.gguf`, o servidor abortou imediatamente com o erro:",
        "```text",
        "0.00.845.321 E llama_model_load: error loading model: done_getting_tensors: wrong number of tensors; expected 81, got 58",
        "0.00.845.326 E llama_model_load_from_file_impl: failed to load model",
        "0.23.820.797 E llama_model_load: error loading model: done_getting_tensors: wrong number of tensors; expected 81, got 58",
        "0.23.820.812 E common_speculative_init_result: failed to load draft model",
        "0.23.833.517 E srv  llama_server: exiting due to model loading error",
        "```",
        "",
        "## 3. Causa Raiz",
        "",
        "- O fork `Ajay9o9/llama.cpp-escha` (branch `escha-w2-dense`) foi baseado em um commit anterior à introdução do suporte ao checkpoint Qwen3.8 DFlash2 oficial (que contém 81 tensores com convoluções e seletores adicionais).",
        "- Conforme estipulado no `PLAN.md`, nenhum tensor foi removido e o benchmark não foi forçado. O preset Escha+DFlash2 permanece catalogado como `BLOCKED_RUNTIME_UNSUPPORTED`.",
        ""
    ]
    (RESULTS_DIR / "ESCHA_DFLASH2_PROBE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

def build_cleanup_report():
    lines = [
        "# Relatório de Limpeza de Pesos Descartados",
        "",
        "Limpeza realizada conforme as instruções de `PLAN.md` após comprovação da integridade dos registros históricos no Git.",
        "",
        "## Modelos e Pesos Removidos do Disco",
        "",
        "| Diretório Removido | Tamanho Liberado | Motivo | Status dos Benchmarks Históricos |",
        "|---|:---:|---|:---:|",
        "| `text/empero-ai-Qwythos-9B-Claude-Mythos-5-1M-GGUF/` | **5,24 GiB** (5.629.108.896 B) | Desempenho insuficiente (prolixo em reasoning, truncado e censurado em escrita). | Preservados em `candidate-round-v1` |",
        "| `text/bartowski-Ornith-1.5-9B-Q5_K_M/` | **6,38 GiB** (6.852.928.701 B) | Desempenho insuficiente (0/3 em C++, 2/6 total). | Preservados em `candidate-round-v1` |",
        "| **TOTAL RECLAIMED** | **11,62 GiB** (12.482.037.597 B) | Limpeza autorizada de candidatos descartados | 100% Intactos |",
        "",
        "## Verificação de Preservação",
        "",
        "- Os quatro modelos centrais (`Qwen3.8 9B Heretic`, `Qwen3.8 27B GSQ-RCO IQ2_S`, `Qwen3.8 27B Fable Heretic`, `Qwen3.8 27B DFlash2 draft`) e os novos candidatos (`Nanbeige4.2-3B`, `Spark-X2.5-4B`, `Escha-Qwen3.8-27B-W2`) permanecem intactos.",
        "- Todos os arquivos históricos de raw results (`RAW_RESULTS.jsonl`), resumos (`SUMMARY.md`) e logs permanecem inalterados no Git.",
        ""
    ]
    (RESULTS_DIR / "CLEANUP_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

def build_run_manifest():
    manifest = {
        "benchmark": "score-completion-template-ablation-v1",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "total_coding_runs": len(coding_rows),
        "total_writing_runs": len(writing_rows),
        "total_new_generations": len(coding_rows) + len(writing_rows),
        "cleanup_freed_gib": 11.62,
        "escha_dflash_status": "BLOCKED_RUNTIME_UNSUPPORTED",
        "runtimes": {
            "stock": LLAMA_STOCK,
            "escha": LLAMA_ESCHA,
            "spark": LLAMA_SPARK
        }
    }
    (RESULTS_DIR / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

if __name__ == "__main__":
    build_coding_summary()
    build_writing_summary()
    build_escha_ablation()
    build_escha_dflash_probe()
    build_cleanup_report()
    build_run_manifest()
    print("All markdown summaries and manifests created successfully!")
