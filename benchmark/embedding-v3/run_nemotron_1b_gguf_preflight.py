#!/usr/bin/env python3
"""Run a bounded llama.cpp preflight for the Nemotron 1B GGUF."""

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
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-compute-apps=pid,used_memory",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    total = 0.0
    for line in completed.stdout.splitlines():
        fields = [field.strip() for field in line.split(",")]
        if len(fields) == 2 and fields[0].isdigit() and int(fields[0]) in pids:
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
    with urllib.request.urlopen(request, timeout=30) as response:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18082)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    log_path = args.output / "gguf_llama_cpp.log"
    result_path = args.output / "gguf_preflight.json"
    command = [
        str(args.binary.resolve()),
        "--model",
        str(args.model.resolve()),
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
        str(args.port),
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
            while time.monotonic() - started < args.timeout_seconds:
                if process.poll() is not None:
                    raise RuntimeError(
                        f"llama-server exited with code {process.returncode}"
                    )
                pids = descendants(process.pid)
                peak_rss_mib = max(peak_rss_mib, rss_mib(pids))
                peak_vram_mib = max(peak_vram_mib, gpu_mib(pids))
                try:
                    request_json(f"http://127.0.0.1:{args.port}/health")
                    ready_at = time.monotonic()
                    break
                except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                    time.sleep(0.1)
            if ready_at is None:
                raise TimeoutError(
                    f"startup exceeded {args.timeout_seconds} seconds"
                )

            embed_started = time.monotonic()
            response = request_json(
                f"http://127.0.0.1:{args.port}/v1/embeddings",
                {"model": "nemotron-3-embed-1b", "input": TEXTS},
            )
            embed_seconds = time.monotonic() - embed_started
            pids = descendants(process.pid)
            peak_rss_mib = max(peak_rss_mib, rss_mib(pids))
            peak_vram_mib = max(peak_vram_mib, gpu_mib(pids))
            embeddings = [item["embedding"] for item in response["data"]]
            prompt_tokens = int(response.get("usage", {}).get("prompt_tokens", 0))
            result = {
                "state": "EXECUTED",
                "backend": "llama.cpp",
                "model": str(args.model.resolve()),
                "command": command,
                "startup_seconds": ready_at - started,
                "embedding_seconds": embed_seconds,
                "embeddings_per_second": len(embeddings) / embed_seconds,
                "prompt_tokens": prompt_tokens,
                "tokens_per_second": (
                    prompt_tokens / embed_seconds if prompt_tokens else None
                ),
                "embedding_count": len(embeddings),
                "embedding_dimensions": [len(vector) for vector in embeddings],
                "embeddings": embeddings,
                "embedding_prefixes": [vector[:8] for vector in embeddings],
                "peak_rss_mib": peak_rss_mib,
                "peak_vram_mib": peak_vram_mib,
                "log": str(log_path.resolve()),
            }
            result_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(json.dumps(result, ensure_ascii=False), flush=True)
            return 0
        finally:
            terminate(process)


if __name__ == "__main__":
    raise SystemExit(main())
