#!/usr/bin/env python3
"""Evaluate one Nemotron 1B backend on the frozen Holo retrieval corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import signal
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from holo_benchmark.metrics import DEFAULT_KS, evaluate_rankings
from holo_benchmark.reranker_runtime import (
    CORPUS_SHA256,
    load_frozen_dataset,
    sha256_file,
)


def descendants(root_pid: int) -> set[int]:
    found = {root_pid}
    changed = True
    while changed:
        changed = False
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                fields = (entry / "stat").read_text(encoding="utf-8").split()
                pid = int(fields[0])
                parent = int(fields[3])
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


class ResourceSampler:
    def __init__(self, root_pid: int, interval_seconds: float = 0.25) -> None:
        self.root_pid = root_pid
        self.interval_seconds = interval_seconds
        self.peak_rss_mib = 0.0
        self.peak_vram_mib = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _sample(self) -> None:
        while not self._stop.is_set():
            pids = descendants(self.root_pid)
            self.peak_rss_mib = max(self.peak_rss_mib, rss_mib(pids))
            self.peak_vram_mib = max(self.peak_vram_mib, gpu_mib(pids))
            self._stop.wait(self.interval_seconds)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)


def matrix_hash(matrix: np.ndarray) -> str:
    canonical = np.asarray(matrix, dtype="<f4", order="C")
    return hashlib.sha256(canonical.tobytes()).hexdigest()


def normalized(matrix: Sequence[Sequence[float]]) -> np.ndarray:
    array = np.asarray(matrix, dtype=np.float32)
    if array.ndim != 2:
        raise ValueError(f"embedding matrix must be 2-D, got {array.shape}")
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("zero-norm embedding")
    return array / norms


def evaluate(
    chunks: Sequence[dict[str, Any]],
    queries: Sequence[dict[str, Any]],
    document_embeddings: Sequence[Sequence[float]],
    query_embeddings: Sequence[Sequence[float]],
) -> dict[str, Any]:
    documents = normalized(document_embeddings)
    query_rows = normalized(query_embeddings)
    scores = query_rows @ documents.T
    order = np.argsort(-scores, axis=1, kind="stable")
    chunk_ids = [str(chunk["chunk_id"]) for chunk in chunks]
    rankings = [[chunk_ids[int(index)] for index in row] for row in order]
    metrics = evaluate_rankings(queries, rankings, DEFAULT_KS)
    return {
        "metrics": metrics,
        "rankings_top50": [row[:50] for row in rankings],
        "document_embedding_sha256": matrix_hash(documents),
        "query_embedding_sha256": matrix_hash(query_rows),
        "dimension": int(documents.shape[1]),
    }


def embed_vllm(
    model: Path,
    documents: Sequence[str],
    queries: Sequence[str],
) -> tuple[list[list[float]], list[list[float]], dict[str, Any]]:
    from vllm import LLM

    load_started = time.monotonic()
    llm = LLM(
        model=str(model.resolve()),
        runner="pooling",
        max_model_len=1024,
        max_num_batched_tokens=4096,
        max_num_seqs=16,
        gpu_memory_utilization=0.70,
        enforce_eager=True,
        compilation_config=0,
        disable_log_stats=True,
    )
    load_seconds = time.monotonic() - load_started

    document_started = time.monotonic()
    document_outputs = llm.embed(list(documents), use_tqdm=True)
    document_seconds = time.monotonic() - document_started

    query_started = time.monotonic()
    query_outputs = llm.embed(list(queries), use_tqdm=True)
    query_seconds = time.monotonic() - query_started

    document_embeddings = [
        output.outputs.embedding for output in document_outputs
    ]
    query_embeddings = [output.outputs.embedding for output in query_outputs]
    return document_embeddings, query_embeddings, {
        "backend": "vllm",
        "version": __import__("vllm").__version__,
        "load_seconds": load_seconds,
        "document_encode_seconds": document_seconds,
        "query_encode_seconds": query_seconds,
        "documents_per_second": len(documents) / document_seconds,
        "queries_per_second": len(queries) / query_seconds,
        "configuration": {
            "runner": "pooling",
            "max_model_len": 1024,
            "max_num_batched_tokens": 4096,
            "max_num_seqs": 16,
            "gpu_memory_utilization": 0.70,
            "enforce_eager": True,
            "compilation_config": 0,
        },
    }


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request_json(url: str, payload: dict[str, Any] | None = None) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if data is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=900) as response:
        return json.loads(response.read())


def wait_server(port: int, process: subprocess.Popen[str], timeout: int) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"llama-server exited with code {process.returncode}")
        try:
            request_json(f"http://127.0.0.1:{port}/health")
            return
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(0.1)
    raise TimeoutError(f"llama-server startup exceeded {timeout} seconds")


def terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)


def llama_encode(
    port: int,
    texts: Sequence[str],
    request_batch_size: int,
) -> list[list[float]]:
    rows: list[list[float]] = []
    for start in range(0, len(texts), request_batch_size):
        payload = request_json(
            f"http://127.0.0.1:{port}/v1/embeddings",
            {
                "input": list(texts[start : start + request_batch_size]),
                "encoding_format": "float",
            },
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            raise ValueError("invalid llama.cpp embeddings response")
        ordered = sorted(data, key=lambda item: int(item.get("index", 0)))
        rows.extend([list(item["embedding"]) for item in ordered])
    return rows


def embed_gguf(
    binary: Path,
    model: Path,
    documents: Sequence[str],
    queries: Sequence[str],
    log_path: Path,
) -> tuple[list[list[float]], list[list[float]], dict[str, Any]]:
    port = free_port()
    command = [
        str(binary.resolve()),
        "--model",
        str(model.resolve()),
        "--embedding",
        "--pooling",
        "mean",
        "--embd-normalize",
        "2",
        "--gpu-layers",
        "all",
        "--ctx-size",
        "1024",
        "--batch-size",
        "2048",
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
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        try:
            load_started = time.monotonic()
            wait_server(port, process, timeout=180)
            load_seconds = time.monotonic() - load_started

            document_started = time.monotonic()
            document_embeddings = llama_encode(port, documents, 4)
            document_seconds = time.monotonic() - document_started

            query_started = time.monotonic()
            query_embeddings = llama_encode(port, queries, 4)
            query_seconds = time.monotonic() - query_started
        finally:
            terminate(process)

    version = subprocess.run(
        [str(binary.resolve()), "--version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return document_embeddings, query_embeddings, {
        "backend": "llama.cpp",
        "version": (version.stdout or version.stderr).strip(),
        "load_seconds": load_seconds,
        "document_encode_seconds": document_seconds,
        "query_encode_seconds": query_seconds,
        "documents_per_second": len(documents) / document_seconds,
        "queries_per_second": len(queries) / query_seconds,
        "command": command,
        "request_batch_size": 4,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=("nvfp4", "gguf"), required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    project_root = Path(__file__).resolve().parent
    chunks, queries = load_frozen_dataset(project_root)
    documents = [f"passage: {chunk['text']}" for chunk in chunks]
    query_texts = [f"query: {query['query']}" for query in queries]

    sampler = ResourceSampler(os.getpid())
    sampler.start()
    total_started = time.monotonic()
    try:
        if args.backend == "nvfp4":
            document_embeddings, query_embeddings, runtime = embed_vllm(
                args.model,
                documents,
                query_texts,
            )
            model_file = args.model / "model.safetensors"
        else:
            if args.binary is None:
                parser.error("--binary is required for the GGUF backend")
            document_embeddings, query_embeddings, runtime = embed_gguf(
                args.binary,
                args.model,
                documents,
                query_texts,
                args.output.with_suffix(".log"),
            )
            model_file = args.model
        evaluation = evaluate(
            chunks,
            queries,
            document_embeddings,
            query_embeddings,
        )
    finally:
        sampler.stop()

    runtime["total_seconds"] = time.monotonic() - total_started
    runtime["peak_rss_mib"] = sampler.peak_rss_mib
    runtime["peak_vram_mib"] = sampler.peak_vram_mib
    payload = {
        "state": "EXECUTED",
        "purpose": "Nemotron 1B full-corpus admission benchmark",
        "backend": args.backend,
        "model": {
            "path": str(args.model.resolve()),
            "weight_file": str(model_file.resolve()),
            "bytes": model_file.stat().st_size,
            "sha256": sha256_file(model_file),
            "license": "OpenMDW-1.1",
        },
        "dataset": {
            "name": "holo_fake_scenes_v3",
            "combined_sha256": CORPUS_SHA256,
            "documents": len(chunks),
            "queries": len(queries),
            "document_prefix": "passage: ",
            "query_prefix": "query: ",
        },
        "runtime": runtime,
        "evaluation": evaluation,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = payload["evaluation"]["metrics"]["summary"]
    print(
        json.dumps(
            {
                "state": payload["state"],
                "backend": args.backend,
                "runtime": runtime,
                "metrics": summary,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
