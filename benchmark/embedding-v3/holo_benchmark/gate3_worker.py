from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .gate2_runtime import _atomic_json, _document_text, _query_text
from .gate2_worker import (
    _extract_embedding_rows,
    _free_port,
    _post_json,
    _rankings_from_embeddings,
    _wait_server,
)
from .gate3 import Gate3ModelSpec, Gate3ResolvedModel
from .metrics import DEFAULT_KS, evaluate_rankings


def _truncate_and_normalize(matrix: Any, dimension: int) -> np.ndarray:
    array = np.asarray(matrix, dtype=np.float32)
    if array.ndim != 2 or array.shape[1] < dimension:
        raise ValueError(f"matriz inválida para truncamento: shape={array.shape}, alvo={dimension}")
    array = array[:, :dimension]
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("embedding com norma zero")
    return array / norms


def _quantization_from_filename(filename: str) -> str:
    stem = Path(filename).stem.upper()
    for marker in ("Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "F16", "BF16"):
        if marker in stem:
            return marker
    return "UNKNOWN"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _find_llama_server() -> str:
    explicit = os.environ.get("LLAMA_SERVER")
    candidates = [
        shutil.which(explicit) if explicit else None,
        explicit if explicit and Path(explicit).exists() else None,
        shutil.which("llama-server"),
        shutil.which("llama-server-cuda"),
    ]
    server = next((str(path) for path in candidates if path), None)
    if server is None:
        raise RuntimeError("llama-server não encontrado")
    return server


class _VramSampler:
    def __init__(self, pid: int, device_index: int = 0) -> None:
        self.pid = pid
        self.device_index = device_index
        self.peak_mib: int | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _sample(self) -> None:
        while not self._stop.is_set():
            try:
                proc = subprocess.run(
                    [
                        "nvidia-smi",
                        f"--id={self.device_index}",
                        "--query-compute-apps=pid,used_memory",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=3,
                )
                for line in proc.stdout.splitlines():
                    parts = [part.strip() for part in line.split(",", 1)]
                    if len(parts) != 2 or not parts[0].isdigit() or int(parts[0]) != self.pid:
                        continue
                    memory = parts[1].split()[0]
                    if memory.isdigit():
                        self.peak_mib = max(self.peak_mib or 0, int(memory))
            except Exception:
                pass
            self._stop.wait(0.25)

    def __enter__(self) -> "_VramSampler":
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_: Any) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)


def _encode(port: int, texts: Sequence[str], batch_size: int) -> np.ndarray:
    rows: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        payload = _post_json(
            f"http://127.0.0.1:{port}/v1/embeddings",
            {"input": list(texts[start:start + batch_size]), "encoding_format": "float"},
            timeout=900,
        )
        rows.extend(_extract_embedding_rows(payload))
    return np.asarray(rows, dtype=np.float32)


def _server_version(server: str) -> str:
    proc = subprocess.run([server, "--version"], capture_output=True, text=True, check=False, timeout=30)
    return (proc.stdout or proc.stderr).strip()


def benchmark_model(request: dict[str, Any]) -> dict[str, Any]:
    resolved = Gate3ResolvedModel(**request["resolved"])
    spec = Gate3ModelSpec(**request["spec"])
    model_path = Path(request["model_path"])
    model_file = model_path / resolved.file
    if not model_file.exists():
        raise RuntimeError(f"GGUF ausente: {model_file}")
    chunks = list(request["chunks"])
    queries = list(request["queries"])
    prompts = dict(request["prompts"])
    device = str(request["device"])
    batch_size = int(request["batch_size"])
    corpus_hash = str(request["corpus_hash"])
    system_info = dict(request.get("system_info") or {})

    documents = [_document_text(chunk, spec.id, prompts, spec.prompt_profile) for chunk in chunks]
    query_texts = [_query_text(query, spec.id, prompts, spec.prompt_profile) for query in queries]
    chunk_ids = [str(chunk["chunk_id"]) for chunk in chunks]

    server = _find_llama_server()
    port = _free_port()
    command = [
        server,
        "-m",
        str(model_file),
        "--embedding",
        "--pooling",
        spec.pooling,
        "--embd-normalize",
        "2",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "-np",
        "1",
        "-ngl",
        str(spec.gpu_layers),
        "-c",
        str(spec.context_size),
        "-b",
        str(spec.server_batch_size),
        "-ub",
        str(spec.server_ubatch_size),
    ]
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix=f"{spec.id}-llama-") as tmp:
        log_path = Path(tmp) / "llama-server.log"
        with log_path.open("w", encoding="utf-8") as log_handle:
            process = subprocess.Popen(command, stdout=log_handle, stderr=subprocess.STDOUT, text=True)
            failure: BaseException | None = None
            with _VramSampler(process.pid) as vram:
                try:
                    load_started = time.monotonic()
                    _wait_server(port, process, timeout=300)
                    load_seconds = time.monotonic() - load_started
                    doc_started = time.monotonic()
                    doc_raw = _encode(port, documents, batch_size)
                    doc_seconds = time.monotonic() - doc_started
                    query_started = time.monotonic()
                    query_raw = _encode(port, query_texts, batch_size)
                    query_seconds = time.monotonic() - query_started
                except BaseException as exc:
                    failure = exc
                finally:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=15)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=15)
                    log_handle.flush()
        if failure is not None:
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-12000:]
            raise RuntimeError(f"{failure}\nllama-server log tail:\n{tail}") from failure

    document_embeddings = _truncate_and_normalize(doc_raw, spec.dimension)
    query_embeddings = _truncate_and_normalize(query_raw, spec.dimension)
    rankings = _rankings_from_embeddings(document_embeddings, query_embeddings, chunk_ids)
    evaluation = evaluate_rankings(queries, rankings, DEFAULT_KS)
    total_seconds = time.monotonic() - started
    runtime = {
        "device": device,
        "dtype": "gguf",
        "normalization": "l2-client-after-truncation",
        "pooling": spec.pooling,
        "batch_size": batch_size,
        "load_seconds": round(load_seconds, 4),
        "document_encode_seconds": round(doc_seconds, 4),
        "query_encode_seconds": round(query_seconds, 4),
        "documents_per_second": round(len(chunks) / doc_seconds, 4),
        "queries_per_second": round(len(queries) / query_seconds, 4),
        "total_seconds": round(total_seconds, 4),
        "peak_vram_bytes": vram.peak_mib * 1024 * 1024 if vram.peak_mib is not None else None,
        "llama_server": {"path": server, "version": _server_version(server)},
        "command": command,
    }
    return {
        "schema_version": "1.0",
        "gate": 3,
        "model": {
            "id": spec.id,
            "repo": spec.repo,
            "revision": resolved.revision,
            "file": resolved.file,
            "fallback_used": resolved.fallback_used,
            "backend": spec.backend,
            "license": resolved.license,
            "gated": resolved.gated,
            "quantization": _quantization_from_filename(resolved.file),
            "pooling": spec.pooling,
            "native_dimension": spec.native_dimension,
            "configured_dimension": spec.dimension,
            "actual_dimension": int(document_embeddings.shape[1]),
            "weight_files": [
                {
                    "file": resolved.file,
                    "bytes": model_file.stat().st_size,
                    "sha256": _sha256(model_file),
                }
            ],
        },
        "dataset": {
            "corpus_version": "holo_fake_scenes_v3",
            "combined_sha256": corpus_hash,
            "documents": len(chunks),
            "queries": len(queries),
        },
        "hardware": system_info,
        "runtime": runtime,
        "metrics": evaluation,
        "completed_at": time.time(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    try:
        request = json.loads(Path(args.request).read_text(encoding="utf-8"))
        _atomic_json(output, {"status": "ok", "result": benchmark_model(request)})
        return 0
    except BaseException as exc:
        _atomic_json(
            output,
            {
                "status": "error",
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                },
            },
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
