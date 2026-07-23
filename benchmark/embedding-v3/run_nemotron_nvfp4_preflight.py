#!/usr/bin/env python3
"""Run and monitor a vLLM-only preflight for Nemotron NVFP4."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path


TEXTS = [
    "query: Onde está a chave azul?",
    "passage: A chave azul está sobre a mesa da cozinha.",
    "passage: O casaco vermelho está pendurado atrás da porta.",
]


def descendants(root_pid: int) -> set[int]:
    found = {root_pid}
    changed = True
    while changed:
        changed = False
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                stat = (entry / "stat").read_text(encoding="utf-8").split()
                pid = int(stat[0])
                parent = int(stat[3])
            except (FileNotFoundError, PermissionError, ValueError, IndexError):
                continue
            if parent in found and pid not in found:
                found.add(pid)
                changed = True
    return found


def rss_mib(pids: set[int]) -> float:
    total_kib = 0
    for pid in pids:
        try:
            status = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
        except (FileNotFoundError, PermissionError):
            continue
        for line in status.splitlines():
            if line.startswith("VmRSS:"):
                total_kib += int(line.split()[1])
                break
    return total_kib / 1024


def gpu_mib(pids: set[int]) -> float:
    command = [
        "nvidia-smi",
        "--query-compute-apps=pid,used_memory",
        "--format=csv,noheader,nounits",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    total = 0.0
    for line in completed.stdout.splitlines():
        fields = [field.strip() for field in line.split(",")]
        if len(fields) == 2 and fields[0].isdigit() and int(fields[0]) in pids:
            total += float(fields[1])
    return total


def worker(model: Path, result_path: Path) -> int:
    started = time.monotonic()
    from vllm import LLM

    import_seconds = time.monotonic() - started
    load_started = time.monotonic()
    llm = LLM(
        model=str(model),
        runner="pooling",
        max_model_len=512,
        max_num_batched_tokens=512,
        max_num_seqs=4,
        gpu_memory_utilization=0.70,
        enforce_eager=True,
        compilation_config=0,
        disable_log_stats=True,
    )
    load_seconds = time.monotonic() - load_started
    embed_started = time.monotonic()
    outputs = llm.embed(TEXTS, use_tqdm=False)
    embed_seconds = time.monotonic() - embed_started
    embeddings = [output.outputs.embedding for output in outputs]
    token_counts = [
        len(getattr(output, "prompt_token_ids", []) or []) for output in outputs
    ]
    result = {
        "state": "EXECUTED",
        "backend": "vllm",
        "model": str(model),
        "import_seconds": import_seconds,
        "load_seconds": load_seconds,
        "embedding_seconds": embed_seconds,
        "embeddings_per_second": len(embeddings) / embed_seconds,
        "prompt_tokens": sum(token_counts),
        "tokens_per_second": (
            sum(token_counts) / embed_seconds if sum(token_counts) else None
        ),
        "embedding_count": len(embeddings),
        "embedding_dimensions": [len(vector) for vector in embeddings],
        "embeddings": embeddings,
        "embedding_prefixes": [vector[:8] for vector in embeddings],
        "vllm_version": __import__("vllm").__version__,
    }
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0


def relay_output(process: subprocess.Popen[str], log_path: Path) -> None:
    assert process.stdout is not None
    with log_path.open("w", encoding="utf-8") as log:
        for line in process.stdout:
            log.write(line)
            log.flush()
            print(line, end="", flush=True)


def terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)


def monitor(model: Path, output: Path, timeout_seconds: int) -> int:
    output.mkdir(parents=True, exist_ok=True)
    worker_result = output / "nvfp4_worker_result.json"
    log_path = output / "nvfp4_vllm.log"
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        "--model",
        str(model.resolve()),
        "--worker-result",
        str(worker_result.resolve()),
    ]
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    relay = threading.Thread(target=relay_output, args=(process, log_path), daemon=True)
    relay.start()
    peak_rss_mib = 0.0
    peak_vram_mib = 0.0
    samples = []
    timed_out = False
    try:
        while process.poll() is None:
            elapsed = time.monotonic() - started
            pids = descendants(process.pid)
            current_rss = rss_mib(pids)
            current_vram = gpu_mib(pids)
            peak_rss_mib = max(peak_rss_mib, current_rss)
            peak_vram_mib = max(peak_vram_mib, current_vram)
            samples.append(
                {
                    "elapsed_seconds": elapsed,
                    "rss_mib": current_rss,
                    "vram_mib": current_vram,
                    "process_count": len(pids),
                }
            )
            if elapsed >= timeout_seconds:
                timed_out = True
                terminate(process)
                break
            time.sleep(1)
    finally:
        terminate(process)
        relay.join(timeout=5)

    return_code = process.returncode
    state = "EXECUTED" if return_code == 0 and worker_result.exists() else "BLOCKED"
    summary = {
        "state": state,
        "backend": "vllm",
        "isolated_environment": "/tmp/vllm-env",
        "command": command,
        "timeout_seconds": timeout_seconds,
        "timed_out": timed_out,
        "return_code": return_code,
        "wall_seconds": time.monotonic() - started,
        "peak_rss_mib": peak_rss_mib,
        "peak_vram_mib": peak_vram_mib,
        "samples": samples,
        "log": str(log_path),
        "worker_result": str(worker_result) if worker_result.exists() else None,
    }
    (output / "nvfp4_preflight.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0 if state == "EXECUTED" else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--worker-result", type=Path)
    args = parser.parse_args()
    if args.worker:
        if args.worker_result is None:
            parser.error("--worker-result is required with --worker")
        return worker(args.model.resolve(), args.worker_result.resolve())
    if args.output is None:
        parser.error("--output is required")
    return monitor(args.model.resolve(), args.output.resolve(), args.timeout_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
