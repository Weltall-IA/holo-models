from __future__ import annotations

import hashlib
import json
import os
import socket
import threading
import urllib.request
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .gate2_worker import (
    _extract_embedding_rows,
    _find_llama_server,
)
from .reranker_metrics import stable_top_k

CORPUS_SHA256 = "8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b"
DEFAULT_RERANK_INSTRUCTION = (
    "Classifique as cenas pela correspondência com a consulta, considerando "
    "acontecimento, diálogo, personagens, intenção emocional e contexto. "
    "Não favoreça apenas sobreposição literal de palavras."
)

CANDIDATE_VARIANTS = (
    "embeddinggemma_768_float32",
    "voyage4_nano_1024_float32",
    "voyage4_nano_2048_float32",
    "voyage4_nano_2048_int8",
    "voyage_4_large_1024_float32",
)


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_frozen_dataset(
    project_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    data_dir = project_root / "data" / "holo_fake_scenes_v3"
    hashes = read_json(data_dir / "hashes.json")
    if hashes.get("combined_sha256") != CORPUS_SHA256:
        raise RuntimeError("frozen corpus hash diverged")
    chunks = read_jsonl(data_dir / "corpus.jsonl")
    queries = read_jsonl(data_dir / "queries.jsonl")
    if len(chunks) != 600 or len(queries) != 150:
        raise RuntimeError(
            f"invalid frozen corpus counts: {len(chunks)} documents, {len(queries)} queries"
        )
    return chunks, queries


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def directory_weight_files(path: Path) -> list[Path]:
    suffixes = {".safetensors", ".bin", ".pt", ".pth", ".gguf"}
    return [
        item
        for item in sorted(path.rglob("*"))
        if item.is_file() and item.suffix.lower() in suffixes
    ]


def path_size_bytes(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _normalise_rows(matrix: Any) -> Any:
    import numpy as np

    array = np.asarray(matrix, dtype=np.float32)
    if array.ndim != 2:
        raise ValueError(f"embedding matrix must be 2-D, got shape={array.shape}")
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("zero-norm embedding")
    return array / norms


def cosine_scores(document_embeddings: Any, query_embeddings: Any) -> Any:
    documents = _normalise_rows(document_embeddings)
    queries = _normalise_rows(query_embeddings)
    return queries @ documents.T


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def post_json(url: str, payload: dict[str, Any], timeout: int = 1800) -> Any:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def llama_cpp_encode(
    port: int,
    texts: Sequence[str],
    batch_size: int,
) -> list[list[float]]:
    rows: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        payload = post_json(
            f"http://127.0.0.1:{port}/v1/embeddings",
            {
                "input": list(texts[start : start + batch_size]),
                "encoding_format": "float",
            },
        )
        rows.extend(_extract_embedding_rows(payload))
    return rows


class ResourceSampler(AbstractContextManager["ResourceSampler"]):
    """Sample process-tree RSS, CPU and GPU memory."""

    def __init__(self, interval_seconds: float = 0.2) -> None:
        self.interval_seconds = interval_seconds
        self.peak_rss_bytes = 0
        self.peak_cpu_percent = 0.0
        self.peak_gpu_memory_bytes = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _sample(self) -> None:
        try:
            import psutil
        except ImportError:
            return

        pynvml = None
        handles: list[Any] = []
        try:
            import pynvml as _pynvml

            _pynvml.nvmlInit()
            pynvml = _pynvml
            handles = [
                _pynvml.nvmlDeviceGetHandleByIndex(index)
                for index in range(_pynvml.nvmlDeviceGetCount())
            ]
        except Exception:
            pynvml = None
            handles = []

        root = psutil.Process(os.getpid())
        root.cpu_percent(None)
        try:
            while not self._stop.wait(self.interval_seconds):
                processes = [root]
                try:
                    processes.extend(root.children(recursive=True))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                pids = {process.pid for process in processes}
                rss = 0
                cpu = 0.0
                for process in processes:
                    try:
                        rss += int(process.memory_info().rss)
                        cpu += float(process.cpu_percent(None))
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                gpu_memory = 0
                if pynvml is not None:
                    for handle in handles:
                        for getter_name in (
                            "nvmlDeviceGetComputeRunningProcesses_v3",
                            "nvmlDeviceGetComputeRunningProcesses",
                        ):
                            getter = getattr(pynvml, getter_name, None)
                            if not callable(getter):
                                continue
                            try:
                                entries = getter(handle)
                            except Exception:
                                continue
                            for entry in entries:
                                if int(getattr(entry, "pid", -1)) in pids:
                                    used = getattr(entry, "usedGpuMemory", 0)
                                    if isinstance(used, int) and used > 0:
                                        gpu_memory += used
                            break

                self.peak_rss_bytes = max(self.peak_rss_bytes, rss)
                self.peak_cpu_percent = max(self.peak_cpu_percent, cpu)
                self.peak_gpu_memory_bytes = max(
                    self.peak_gpu_memory_bytes,
                    gpu_memory,
                )
        finally:
            if pynvml is not None:
                try:
                    pynvml.nvmlShutdown()
                except Exception:
                    pass

    def __enter__(self) -> "ResourceSampler":
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def as_dict(self) -> dict[str, Any]:
        return {
            "peak_process_tree_rss_bytes": self.peak_rss_bytes or None,
            "peak_process_tree_cpu_percent": self.peak_cpu_percent or None,
            "peak_gpu_memory_bytes": self.peak_gpu_memory_bytes or None,
        }


def _candidate_payload(
    variant: str,
    metadata: Mapping[str, Any],
    scores: Any,
    chunks: Sequence[dict[str, Any]],
    queries: Sequence[dict[str, Any]],
    top_k: int,
    runtime: Mapping[str, Any],
) -> dict[str, Any]:
    rows = stable_top_k(scores, [str(row["chunk_id"]) for row in chunks], top_k)
    return {
        "schema_version": "1.0",
        "variant": variant,
        "model": dict(metadata),
        "dataset": {
            "corpus_sha256": CORPUS_SHA256,
            "documents": len(chunks),
            "queries": len(queries),
        },
        "candidate_top_k": top_k,
        "runtime": dict(runtime),
        "queries": [
            {
                "query_id": str(query["query_id"]),
                "candidates": candidates,
            }
            for query, candidates in zip(queries, rows, strict=True)
        ],
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


def discover_qwen_rerankers(repo_root: Path) -> list[dict[str, Any]]:
    roots = [repo_root / name for name in ("rerank", "reranker", "models", "embed")]
    found: dict[str, dict[str, Any]] = {}
    ignored_names = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        "cache",
    }

    def strength(name: str) -> float:
        lowered = name.lower()
        for label, value in (
            ("8b", 8.0),
            ("4b", 4.0),
            ("0.6b", 0.6),
            ("600m", 0.6),
        ):
            if label in lowered:
                return value
        return 0.0

    for root in roots:
        if not root.exists():
            continue
        for current, dirs, files in os.walk(root):
            dirs[:] = [
                name
                for name in dirs
                if name not in ignored_names and not name.startswith(".")
            ]
            current_path = Path(current)
            relative_depth = len(current_path.relative_to(root).parts)
            if relative_depth > 5:
                dirs[:] = []
                continue
            lowered = str(current_path).lower()
            if "rerank" in lowered and "config.json" in files:
                weights = directory_weight_files(current_path)
                if weights:
                    key = str(current_path.resolve())
                    found[key] = {
                        "path": key,
                        "backend": "cross-encoder",
                        "name": current_path.name,
                        "strength": strength(current_path.name),
                        "bytes": path_size_bytes(current_path),
                        "weight_files": [
                            str(item.relative_to(current_path)) for item in weights
                        ],
                    }
            for filename in files:
                if filename.lower().endswith(".gguf") and "rerank" in filename.lower():
                    path = current_path / filename
                    key = str(path.resolve())
                    found[key] = {
                        "path": key,
                        "backend": "llama.cpp",
                        "name": filename,
                        "strength": strength(filename),
                        "bytes": path.stat().st_size,
                        "weight_files": [filename],
                    }
    return sorted(
        found.values(),
        key=lambda item: (
            -float(item["strength"]),
            -int(item["bytes"]),
            str(item["path"]),
        ),
    )


def select_qwen_reranker(
    repo_root: Path,
    explicit_path: str | None,
) -> dict[str, Any]:
    if explicit_path and explicit_path != "auto":
        path = Path(explicit_path).expanduser().resolve()
        if not path.exists():
            raise RuntimeError(f"Qwen reranker path does not exist: {path}")
        backend = (
            "llama.cpp"
            if path.is_file() and path.suffix.lower() == ".gguf"
            else "cross-encoder"
        )
        return {
            "path": str(path),
            "backend": backend,
            "name": path.name,
            "bytes": path_size_bytes(path),
            "strength": 0.0,
            "weight_files": (
                [path.name]
                if path.is_file()
                else [
                    str(item.relative_to(path))
                    for item in directory_weight_files(path)
                ]
            ),
        }
    candidates = discover_qwen_rerankers(repo_root)
    if not candidates:
        raise RuntimeError(
            "no Qwen reranker was discovered under rerank/, reranker/, models/ or embed/"
        )
    return candidates[0]


def _parse_llama_rerank(payload: Any, documents: Sequence[str]) -> list[float]:
    rows = None
    if isinstance(payload, dict):
        rows = payload.get("results") or payload.get("data")
    if not isinstance(rows, list):
        raise RuntimeError("llama.cpp rerank response has no results/data list")
    scores: list[float | None] = [None] * len(documents)
    for item in rows:
        if not isinstance(item, dict):
            continue
        index = int(item.get("index"))
        score = item.get("relevance_score", item.get("score"))
        if score is None or not 0 <= index < len(scores):
            raise RuntimeError("invalid llama.cpp rerank row")
        scores[index] = float(score)
    if any(score is None for score in scores):
        raise RuntimeError("llama.cpp rerank response is incomplete")
    return [float(score) for score in scores if score is not None]


def rerank_query_text(query: Mapping[str, Any], instruction: str) -> str:
    text = str(query["query"])
    cleaned = instruction.strip()
    return f"Instruct: {cleaned}\nQuery: {text}" if cleaned else text
