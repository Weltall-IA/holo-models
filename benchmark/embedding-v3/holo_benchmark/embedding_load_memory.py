"""Isolated load-time measurement for operational top-10 embedding models.

Measures: file size, RAM, VRAM, and load time for each embedding model
in isolation, without reranker, without corpus, without API calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCH_ROOT = REPO_ROOT / "benchmark" / "embedding-v3"


@dataclass
class LoadResult:
    model_id: str
    embedding_full_name: str
    params_declared: str
    quantization: str
    backend: str
    backend_version: str
    weight_files: dict[str, dict[str, Any]] = field(default_factory=dict)
    total_bytes: int = 0
    total_mb: float = 0.0
    total_mib: float = 0.0
    ram_baseline_system_mib: float = 0.0
    ram_process_idle_mib: float = 0.0
    ram_delta_mib: float = 0.0
    ram_peak_load_mib: float = 0.0
    vram_baseline_system_mib: float = 0.0
    vram_process_idle_mib: float = 0.0
    vram_delta_mib: float = 0.0
    vram_peak_load_mib: float = 0.0
    load_seconds: float = 0.0
    smoke_status: str = "NOT_ATTEMPTED"
    smoke_output: str = ""
    status: str = "PENDING"
    error: str = ""


def get_system_ram_mib() -> float:
    try:
        import psutil
        return psutil.virtual_memory().used / (1024 * 1024)
    except Exception:
        return 0.0


def get_gpu_vram_used_mib() -> float:
    try:
        import pynvml
        pynvml.nvmlInit()
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        info = pynvml.nvmlDeviceGetMemoryInfo(h)
        used = info.used / (1024 * 1024)
        pynvml.nvmlShutdown()
        return used
    except Exception:
        return 0.0


def get_process_rss_mib(pid: int) -> float:
    try:
        import psutil
        p = psutil.Process(pid)
        return p.memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


def get_tree_rss_mib(pid: int) -> float:
    try:
        import psutil
        total = 0
        p = psutil.Process(pid)
        procs = [p] + p.children(recursive=True)
        for proc in procs:
            try:
                total += proc.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return total / (1024 * 1024)
    except Exception:
        return 0.0


def get_gpu_vram_for_pid(pid: int) -> float:
    try:
        import pynvml
        pynvml.nvmlInit()
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        procs = pynvml.nvmlDeviceGetComputeRunningProcesses_v3(h)
        used = 0
        for proc_info in procs:
            if proc_info.pid == pid:
                used += proc_info.used_gpu_memory
        pynvml.nvmlShutdown()
        return used / (1024 * 1024)
    except Exception:
        return 0.0


def measure_file_sizes(gguf_path: Path) -> dict:
    files = {}
    total = 0
    if gguf_path.is_file():
        sz = gguf_path.stat().st_size
        h = hashlib.sha256(gguf_path.read_bytes()).hexdigest()
        files[gguf_path.name] = {"bytes": sz, "sha256": h}
        total += sz
    else:
        for p in gguf_path.parent.glob("*.gguf"):
            sz = p.stat().st_size
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            files[p.name] = {"bytes": sz, "sha256": h}
            total += sz
    return {
        "files": files,
        "total_bytes": total,
        "total_mb": round(total / 1_000_000, 2),
        "total_mib": round(total / 1_048_576, 2),
    }


def run_with_memory(cmd: list[str], smoke_text: str = "test query") -> dict:
    """Run a command, measure RAM/VRAM during execution, return metrics."""
    ram_before = get_system_ram_mib()
    vram_before = get_gpu_vram_used_mib()

    t0 = time.time()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    pid = proc.pid

    ram_samples = []
    vram_samples = []
    smoke_ok = False

    for _ in range(200):  # ~50s at 250ms intervals
        if proc.poll() is not None:
            break
        time.sleep(0.25)
        ram_samples.append(get_tree_rss_mib(pid))
        vram_samples.append(get_gpu_vram_for_pid(pid))

    # Wait for stabilization
    time.sleep(5)

    idle_ram = get_tree_rss_mib(pid)
    idle_vram = get_gpu_vram_for_pid(pid)

    # Smoke test via HTTP if server mode
    try:
        import urllib.request
        req = urllib.request.Request(
            "http://127.0.0.1:18080/v1/embeddings",
            data=json.dumps({"input": [smoke_text]}).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        if result.get("data"):
            smoke_ok = True
    except Exception:
        pass

    t1 = time.time()

    # Graceful shutdown
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=10)
    except Exception:
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:
            pass

    time.sleep(2)
    final_ram = get_tree_rss_mib(pid)
    final_vram = get_gpu_vram_for_pid(pid)

    return {
        "ram_baseline_mib": ram_before,
        "ram_idle_mib": idle_ram,
        "ram_peak_mib": max(ram_samples) if ram_samples else 0,
        "ram_final_mib": final_ram,
        "ram_delta_mib": round(idle_ram - ram_before, 2),
        "vram_baseline_mib": vram_before,
        "vram_idle_mib": idle_vram,
        "vram_peak_mib": max(vram_samples) if vram_samples else 0,
        "vram_final_mib": final_vram,
        "vram_delta_mib": round(idle_vram - vram_before, 2),
        "load_seconds": round(t1 - t0, 2),
        "smoke_ok": smoke_ok,
    }


def measure_embedding_load(
    model_id: str,
    embedding_name: str,
    params_declared: str,
    quantization: str,
    gguf_path: Path,
    port: int = 18080,
) -> dict:
    """Measure isolated load memory for an embedding model via llama-server."""
    if not gguf_path.is_file():
        return {"model_id": model_id, "status": "BLOCKED_MISSING_LOCAL_WEIGHT",
                "error": f"GGUF not found: {gguf_path}"}

    sizes = measure_file_sizes(gguf_path)

    cmd = [
        "/home/alpha/llama.cpp/build/bin/llama-server",
        "-m", str(gguf_path),
        "--embedding", "--pooling", "mean",
        "--embd-normalize", "2",
        "--host", "127.0.0.1", "--port", str(port),
        "-ngl", "99", "-c", "2048", "-np", "1",
    ]

    print(f"  Loading {embedding_name}...", flush=True)
    try:
        metrics = run_with_memory(cmd)
    except Exception as e:
        return {"model_id": model_id, "status": "ERROR", "error": str(e), **sizes}

    status = "PASS" if metrics["smoke_ok"] else "SMOKE_FAILED"

    return {
        "model_id": model_id,
        "embedding_full_name": embedding_name,
        "params_declared": params_declared,
        "quantization": quantization,
        "backend": "llama.cpp",
        "backend_version": "9972 (c92e806d1)",
        "weight_files": sizes["files"],
        "total_bytes": sizes["total_bytes"],
        "total_mb": sizes["total_mb"],
        "total_mib": sizes["total_mib"],
        "ram_baseline_system_mib": metrics["ram_baseline_mib"],
        "ram_process_idle_mib": metrics["ram_idle_mib"],
        "ram_delta_mib": metrics["ram_delta_mib"],
        "ram_peak_load_mib": metrics["ram_peak_mib"],
        "vram_baseline_system_mib": metrics["vram_baseline_mib"],
        "vram_process_idle_mib": metrics["vram_idle_mib"],
        "vram_delta_mib": metrics["vram_delta_mib"],
        "vram_peak_load_mib": metrics["vram_peak_mib"],
        "load_seconds": metrics["load_seconds"],
        "smoke_status": status,
        "status": status,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="benchmark/embedding-v3/results/load-memory/top10_embedding_load_memory.json")
    args = parser.parse_args()

    results = []
    seen_weights = set()
    base_port = 18080

    models = [
        ("qwen3_embedding_4b_q8_0", "Qwen3-Embedding-4B-Q8_0", "4B", "Q8_0",
         REPO_ROOT / "embed/Qwen3-Embedding-4B-Q8_0/Qwen3-Embedding-4B-Q8_0.gguf"),
        ("nomic_embed_text_v2_moe_q4", "nomic-embed-text-v2-moe-Q4_K_M", "137M MoE", "Q4_K_M",
         REPO_ROOT / "embed/nomic-embed-text-v2-moe-Q4_K_M/nomic-embed-text-v2-moe.Q4_K_M.gguf"),
        ("nemotron_3_embed_1b_nvfp4", "Nemotron-3-Embed-1B-NVFP4", "1B", "NVFP4",
         REPO_ROOT / "embed/Nemotron-3-Embed-1B-NVFP4/Nemotron-3-Embed-1B-NVFP4.nvfp4"),
        ("nemotron_8b_abiray_q4_audit_1024", "Nemotron-3-Embed-8B-Abiray-Q4_K_M", "8B", "Q4_K_M",
         REPO_ROOT / "runtimes/nemotron-8b-audit/abiray/1ffb81e403311c4dc6879b9c3cbb6ebfa18b86df/Nemotron-3-Embed-8B-Q4_K_M.gguf"),
        ("colibri_ptbr", "Colibri 1.5B", "1.5B", "Q8_0",
         REPO_ROOT / "embed/colibri_ptbr/Colibri-1.5B-PT-BR-Q8_0.gguf"),
        ("embeddinggemma", "EmbeddingGemma 300M", "300M", "Q8_0",
         REPO_ROOT / "embed/embeddinggemma_gguf/EmbeddingGemma-300M-Q8_0.gguf"),
    ]

    for model_id, emb_name, params, quant, gguf in models:
        if gguf.exists():
            weight_key = str(gguf.resolve())
            if weight_key in seen_weights:
                print(f"  SKIP {model_id} (same weight as already measured)", flush=True)
                continue
            seen_weights.add(weight_key)

        port = base_port + len(results)
        result = measure_embedding_load(model_id, emb_name, params, quant, gguf, port)
        results.append(result)
        print(f"  {model_id}: {result.get('status')} ({result.get('load_seconds', 0):.1f}s)", flush=True)
        time.sleep(5)  # cooldown between models

    # Remote/API entry
    results.append({
        "model_id": "voyage_4_large_1024_float32",
        "embedding_full_name": "Voyage-4-Large-1024",
        "params_declared": "N/A",
        "quantization": "N/A",
        "backend": "REMOTE_API_NO_LOCAL_LOAD",
        "backend_version": "rerank-2.5",
        "weight_files": {},
        "total_bytes": 0,
        "total_mb": 0.0,
        "total_mib": 0.0,
        "ram_baseline_system_mib": 0.0,
        "ram_process_idle_mib": 0.0,
        "ram_delta_mib": 0.0,
        "ram_peak_load_mib": 0.0,
        "vram_baseline_system_mib": 0.0,
        "vram_process_idle_mib": 0.0,
        "vram_delta_mib": 0.0,
        "vram_peak_load_mib": 0.0,
        "load_seconds": 0.0,
        "smoke_status": "REMOTE_API_NO_LOCAL_LOAD",
        "status": "REMOTE_API_NO_LOCAL_LOAD",
    })

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2) + "\n")
    print(f"\nResults saved to {output}")
    print(f"Models measured: {len([r for r in results if r['status'] == 'PASS'])}")
    print(f"Models failed: {len([r for r in results if r['status'] not in ('PASS', 'REMOTE_API_NO_LOCAL_LOAD')])}")


if __name__ == "__main__":
    main()
