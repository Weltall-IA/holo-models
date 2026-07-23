#!/usr/bin/env python3
"""Run alternating, isolated llama.cpp startup checks for two Nemotron GGUFs."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


def read_rss_mib(pid: int) -> float:
    try:
        status = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError):
        return 0.0
    for line in status.splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) / 1024
    return 0.0


def read_gpu_mib(pid: int) -> float:
    command = [
        "nvidia-smi",
        "--query-compute-apps=pid,used_memory",
        "--format=csv,noheader,nounits",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    total = 0.0
    for line in completed.stdout.splitlines():
        fields = [field.strip() for field in line.split(",")]
        if len(fields) == 2 and fields[0] == str(pid):
            total += float(fields[1])
    return total


def request_json(url: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if data is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read())


def terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)


def run_once(
    *,
    binary: Path,
    model: Path,
    converter: str,
    run_number: int,
    port: int,
    logs_dir: Path,
    timeout_seconds: int,
) -> dict:
    log_path = logs_dir / f"{run_number:02d}_{converter}.log"
    command = [
        str(binary),
        "--model",
        str(model),
        "--embedding",
        "--pooling",
        "mean",
        "--gpu-layers",
        "all",
        "--ctx-size",
        "512",
        "--batch-size",
        "512",
        "--ubatch-size",
        "512",
        "--threads",
        "2",
        "--threads-batch",
        "2",
        "--parallel",
        "1",
        "--no-warmup",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--no-webui",
    ]
    started = time.monotonic()
    peak_rss_mib = 0.0
    peak_vram_mib = 0.0
    ready_at: float | None = None
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        try:
            while time.monotonic() - started < timeout_seconds:
                if process.poll() is not None:
                    raise RuntimeError(f"llama-server exited with code {process.returncode}")
                peak_rss_mib = max(peak_rss_mib, read_rss_mib(process.pid))
                peak_vram_mib = max(peak_vram_mib, read_gpu_mib(process.pid))
                try:
                    request_json(f"http://127.0.0.1:{port}/health")
                    ready_at = time.monotonic()
                    break
                except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                    time.sleep(0.25)
            if ready_at is None:
                raise TimeoutError(f"startup exceeded {timeout_seconds} seconds")

            embed_started = time.monotonic()
            response = request_json(
                f"http://127.0.0.1:{port}/v1/embeddings",
                {
                    "model": "nemotron-3-embed-8b",
                    "input": [
                        "query: Onde está a chave azul?",
                        "passage: A chave azul está sobre a mesa da cozinha.",
                    ],
                },
            )
            embed_seconds = time.monotonic() - embed_started
            peak_rss_mib = max(peak_rss_mib, read_rss_mib(process.pid))
            peak_vram_mib = max(peak_vram_mib, read_gpu_mib(process.pid))
            embeddings = [item["embedding"] for item in response["data"]]
            prompt_tokens = int(response.get("usage", {}).get("prompt_tokens", 0))
            return {
                "run": run_number,
                "converter": converter,
                "model": str(model),
                "state": "EXECUTED",
                "startup_seconds": ready_at - started,
                "embedding_seconds": embed_seconds,
                "embeddings_per_second": len(embeddings) / embed_seconds,
                "prompt_tokens": prompt_tokens,
                "tokens_per_second": (
                    prompt_tokens / embed_seconds if prompt_tokens else None
                ),
                "embedding_count": len(embeddings),
                "embedding_dimensions": [len(vector) for vector in embeddings],
                "peak_rss_mib": peak_rss_mib,
                "peak_vram_mib": peak_vram_mib,
                "log": str(log_path),
                "command": command,
            }
        finally:
            terminate(process)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--abiray", type=Path, required=True)
    parser.add_argument("--aqua00", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--port", type=int, default=18081)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    logs_dir = args.output / "gguf_startup_logs"
    logs_dir.mkdir(exist_ok=True)
    sequence = [
        ("abiray", args.abiray),
        ("aqua00", args.aqua00),
    ] * 5
    results = []
    for index, (converter, model) in enumerate(sequence, start=1):
        result = run_once(
            binary=args.binary.resolve(),
            model=model.resolve(),
            converter=converter,
            run_number=index,
            port=args.port,
            logs_dir=logs_dir,
            timeout_seconds=args.timeout_seconds,
        )
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)

    payload = {
        "state": "EXECUTED",
        "order": [converter for converter, _ in sequence],
        "runs": results,
    }
    destination = args.output / "gguf_startups.json"
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
