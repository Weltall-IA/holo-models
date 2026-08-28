import json
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from runner.server_manager import LlamaServerProcess
from runner.benchmark_runner import run_round1
from runner.phase2_runner import run_phase2_for_model

def smoke_test_models():
    models_file = os.path.join(BASE_DIR, "models.json")
    with open(models_file, "r") as f:
        models = json.load(f)
        
    print(f"\n=======================================================")
    print(f"Smoke testing all {len(models)} models in llama.cpp...")
    print(f"=======================================================")
    
    for m in models:
        print(f"Testing model: {m['name']} ({m['quant']})...")
        server = LlamaServerProcess(
            model_path=m["local_path"],
            ctx_size=2048,
            port=8089,
            kv_cache_type="q4_0",
            flash_attn=True,
            ngl=999
        )
        try:
            server.start()
            server.warmup()
            server.stop()
            print(f"  [PASS] {m['name']} booted and inferred successfully.")
        except Exception as e:
            print(f"  [FAIL] {m['name']}: {e}")
            raise

def generate_round1_markdown(summary: dict, out_path: str):
    # Sort models by weighted_score descending
    sorted_models = sorted(
        summary.values(),
        key=lambda x: (
            x.get("weighted_score", 0),
            (x.get("coding_score", 0) + x.get("tools_score", 0) + x.get("recovery_score", 0)),
            -x.get("invalid_tool_schemas", 999),
            -x.get("total_retries", 999),
            x.get("avg_tok_s", 0),
            -x.get("peak_vram_mib", 99999)
        ),
        reverse=True
    )
    
    lines = [
        "# Leaderboard — Fase 1 (Qwen3.8-27B / RTX 5060 Ti 16 GB Quick Benchmark v1)",
        "",
        "Configuração Comum: `llama.cpp b1-8ce8ca6`, Contexto: `16384`, KV: `q4_0`, Flash Attention: `ON`, Seeds: `42` e `1337` (40 tentativas/modelo).",
        "",
        "| Rank | Modelo | Quant | Score Total (%) | Coding (35%) | Tools (30%) | Recovery (20%) | Reasoning (10%) | Non-Refusal (5%) | tok/s | TTFT (s) | Peak VRAM (MiB) | Tool/JSON Fails | Retries |",
        "| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    
    for rank, m in enumerate(sorted_models, start=1):
        lines.append(
            f"| {rank} | **{m['name']}** | `{m['quant']}` | **{m.get('weighted_score', 0):.2f}%** | "
            f"{m.get('coding_score', 0):.1f}% | {m.get('tools_score', 0):.1f}% | {m.get('recovery_score', 0):.1f}% | "
            f"{m.get('reasoning_score', 0):.1f}% | {m.get('non_refusal_score', 0):.1f}% | "
            f"{m.get('avg_tok_s', 0):.1f} | {m.get('avg_ttft', 0):.3f} | {m.get('peak_vram_mib', 0)} | "
            f"{m.get('invalid_tool_schemas', 0)} | {m.get('total_retries', 0)} |"
        )
        
    lines.append("")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Round 1 Leaderboard written to {out_path}")

def generate_failures_report(raw_file_path: str, out_path: str):
    failures = []
    if os.path.exists(raw_file_path):
        with open(raw_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                rec = json.loads(line.strip())
                if rec.get("success") == 0 or rec.get("error"):
                    failures.append(rec)
                    
    lines = [
        "# Relatório de Falhas e Erros — Qwen3.8-27B Benchmark",
        f"Total de falhas registradas: {len(failures)}",
        ""
    ]
    for f in failures:
        lines.append(f"### Model: {f.get('model_name')} | Phase: {f.get('phase')} | Case: {f.get('case_id')} ({f.get('category')}) | Seed: {f.get('seed')}")
        lines.append(f"- **Erro**: `{f.get('error')}`")
        if f.get("response_excerpt"):
            lines.append(f"- **Excerpt**: `{f.get('response_excerpt')[:200]}`")
        lines.append("")
        
    with open(out_path, "w", encoding="utf-8") as f_out:
        f_out.write("\n".join(lines))
    print(f"Failures report written to {out_path}")

def generate_runbook():
    runbook_path = os.path.join(BASE_DIR, "RUNBOOK.md")
    content = """# Runbook de Reprodução — Qwen3.8-27B 16GB Quick Benchmark v1

Este documento descreve os passos exatos para reproduzir 100% deste benchmark local de forma determinística e isolada.

## 1. Requisitos de Ambiente
- GPU NVIDIA RTX 5060 Ti 16 GB (ou compatível com 16 GB VRAM)
- Driver NVIDIA >= 610.x, CUDA UMD 13.x
- Linux x86_64
- Python 3.11+ com `huggingface_hub`, `pytest`, `requests`
- `llama-server` compilado com suporte CUDA e Flash Attention

## 2. Estrutura Canônica de Modelos
Os modelos devem ser baixados estritamente na pasta canônica `text/<origem-quantizacao>/`:
- `text/armand0e-Qwen3.8-27B-Fable-Distill-Heretic-ara-Q3_K_M/`
- `text/mradermacher-Qwen3.8-27B-Uncensored-Heretic-T10-BF16-i1-IQ3_M/`
- `text/Bucoid-Qwen3.8-27B-Heretic-Ara-IQ4_XS/`
- `text/mradermacher-grug-v1.1-qwen-3.8-27b-i1-IQ3_M/`
- `text/mradermacher-Ektome-Qwen3.8-27B-PristinelyUncensored-i1-IQ3_M/`
- `text/0bserverx-Qwen3.8-27B-Heretic-Abliterated-Uncensored-Q3_K_M/`

## 3. Comandos de Execução
```bash
# 1. Download e validação SHA256
python3 tasks/qwen38-27b-16gb-quick-v1/download_models.py

# 2. Execução completa automatizada (Fase 1 + Seleção Top 3 + Fase 2 32K/64K)
python3 tasks/qwen38-27b-16gb-quick-v1/run_benchmark.py
```
"""
    with open(runbook_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Runbook written to {runbook_path}")

def main():
    generate_runbook()
    
    # 1. Run Round 1
    print("\n>>> INICIANDO FASE 1 DO BENCHMARK (40 TENTATIVAS POR MODELO) <<<", flush=True)
    summary = run_round1()
    
    leaderboard_path = os.path.join(BASE_DIR, "results", "leaderboard.md")
    failures_path = os.path.join(BASE_DIR, "results", "failures.md")
    generate_round1_markdown(summary, leaderboard_path)
    
    raw_results_file = os.path.join(BASE_DIR, "results", "raw.jsonl")
    generate_failures_report(raw_results_file, failures_path)
    
    # 2. Select Top 3
    sorted_models = sorted(
        summary.values(),
        key=lambda x: (
            x.get("weighted_score", 0),
            (x.get("coding_score", 0) + x.get("tools_score", 0) + x.get("recovery_score", 0)),
            -x.get("invalid_tool_schemas", 999),
            -x.get("total_retries", 999),
            x.get("avg_tok_s", 0),
            -x.get("peak_vram_mib", 99999)
        ),
        reverse=True
    )
    
    top3 = sorted_models[:3]
    print(f"\n=======================================================")
    print("TOP 3 SELECIONADOS PARA A FASE 2 (32K / 64K):")
    for i, m in enumerate(top3, 1):
        print(f"  {i}. {m['name']} ({m['quant']}) — Score: {m['weighted_score']}%")
    print(f"=======================================================")
    
    models_file = os.path.join(BASE_DIR, "models.json")
    with open(models_file, "r") as f:
        all_models = json.load(f)
    top3_models_info = [next(m for m in all_models if m["id"] == t["model_id"]) for t in top3]
    
    # 3. Run Round 2 on Top 3
    print("\n>>> INICIANDO FASE 2 (LONG CONTEXT STRESS: 32K E 64K) <<<")
    raw_file = open(raw_results_file, "a", encoding="utf-8")
    phase2_summaries = []
    
    for ctx in [32768, 65536]:
        for m_info in top3_models_info:
            p2_sum = run_phase2_for_model(m_info, ctx, raw_file)
            phase2_summaries.append(p2_sum)
            
    raw_file.close()
    
    # Save Phase 2 summary
    p2_path = os.path.join(BASE_DIR, "results", "phase2_summary.json")
    with open(p2_path, "w", encoding="utf-8") as f:
        json.dump(phase2_summaries, f, indent=2)
        
    generate_failures_report(raw_results_file, failures_path)
    print("\n>>> TODAS AS ETAPAS FORAM CONCLUÍDAS COM SUCESSO! <<<")

if __name__ == "__main__":
    main()
