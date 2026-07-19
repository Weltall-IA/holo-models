from __future__ import annotations

import argparse
import gc
import json
import os
import shutil
import socket
import subprocess
import time
import traceback
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .gate2 import (
    Gate2ModelSpec,
    ResolvedModel,
    _atomic_json,
    _document_text,
    _query_text,
    hash_weight_files,
)
from .metrics import DEFAULT_KS, evaluate_rankings


def _normalize_rows(matrix: Any) -> Any:
    import numpy as np

    array = np.asarray(matrix, dtype=np.float32)
    if array.ndim != 2:
        raise ValueError(f"matriz de embeddings inválida: shape={array.shape}")
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("embedding com norma zero")
    return array / norms


def _rankings_from_embeddings(
    document_embeddings: Any,
    query_embeddings: Any,
    chunk_ids: Sequence[str],
) -> list[list[str]]:
    import numpy as np

    documents = _normalize_rows(document_embeddings)
    queries = _normalize_rows(query_embeddings)
    scores = queries @ documents.T
    order = np.argsort(-scores, axis=1, kind="stable")
    return [[chunk_ids[int(index)] for index in row] for row in order]


def _peak_vram_bytes(device: str) -> int | None:
    if device != "cuda":
        return None
    try:
        import torch

        return int(torch.cuda.max_memory_allocated())
    except Exception:
        return None


def _model_dtype(model: Any) -> str | None:
    try:
        return str(next(model.parameters()).dtype)
    except Exception:
        return None


def _encode_sentence_transformer(
    model: Any,
    texts: Sequence[str],
    kind: str,
    spec: Gate2ModelSpec,
    batch_size: int,
) -> Any:
    kwargs = {
        "batch_size": batch_size,
        "show_progress_bar": True,
        "convert_to_numpy": True,
        "normalize_embeddings": True,
    }
    if spec.encode_api == "asymmetric":
        method_name = "encode_document" if kind == "document" else "encode_query"
        method = getattr(model, method_name, None)
        if callable(method):
            try:
                return method(list(texts), **kwargs)
            except TypeError:
                reduced = dict(kwargs)
                reduced.pop("normalize_embeddings", None)
                return method(list(texts), **reduced)
    return model.encode(list(texts), **kwargs)


def _sentence_transformer_embeddings(
    model_path: Path,
    spec: Gate2ModelSpec,
    documents: Sequence[str],
    queries: Sequence[str],
    device: str,
    batch_size: int,
) -> tuple[Any, Any, dict[str, Any]]:
    import torch
    from sentence_transformers import SentenceTransformer

    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    kwargs: dict[str, Any] = {
        "trust_remote_code": spec.trust_remote_code,
        "device": device,
    }
    load_started = time.monotonic()
    model = SentenceTransformer(str(model_path), **kwargs)
    load_seconds = time.monotonic() - load_started
    dtype = _model_dtype(model)
    doc_started = time.monotonic()
    doc_embeddings = _encode_sentence_transformer(
        model, documents, "document", spec, batch_size
    )
    doc_seconds = time.monotonic() - doc_started
    query_started = time.monotonic()
    query_embeddings = _encode_sentence_transformer(
        model, queries, "query", spec, batch_size
    )
    query_seconds = time.monotonic() - query_started
    peak_vram = _peak_vram_bytes(device)
    del model
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()
    return doc_embeddings, query_embeddings, {
        "dtype": dtype,
        "load_seconds": round(load_seconds, 4),
        "document_encode_seconds": round(doc_seconds, 4),
        "query_encode_seconds": round(query_seconds, 4),
        "peak_vram_bytes": peak_vram,
    }


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _find_llama_server() -> str:
    explicit = os.environ.get("LLAMA_SERVER")
    candidates = [
        explicit,
        shutil.which("llama-server"),
        shutil.which("llama-server-cuda"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    raise RuntimeError(
        "llama-server não encontrado; defina LLAMA_SERVER para o binário estável"
    )


def _post_json(url: str, payload: dict[str, Any], timeout: int = 300) -> Any:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_server(port: int, process: subprocess.Popen[str], timeout: int = 180) -> None:
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{port}/health"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"llama-server encerrou com código {process.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.5)
    raise TimeoutError("llama-server não ficou pronto")


def _extract_embedding_rows(payload: Any) -> list[list[float]]:
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, list):
        return [list(map(float, row["embedding"])) for row in data]
    if isinstance(payload, list):
        rows: list[list[float]] = []
        for item in payload:
            if isinstance(item, dict) and "embedding" in item:
                rows.append(list(map(float, item["embedding"])))
            elif isinstance(item, list):
                rows.append(list(map(float, item)))
        if rows:
            return rows
    raise RuntimeError("resposta de embeddings do llama-server não reconhecida")


def _llama_cpp_encode(port: int, texts: Sequence[str], batch_size: int) -> Any:
    rows: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = list(texts[start : start + batch_size])
        payload = _post_json(
            f"http://127.0.0.1:{port}/v1/embeddings",
            {"input": batch, "encoding_format": "float"},
            timeout=900,
        )
        rows.extend(_extract_embedding_rows(payload))
    return rows


def _llama_cpp_embeddings(
    model_path: Path,
    spec: Gate2ModelSpec,
    documents: Sequence[str],
    queries: Sequence[str],
    device: str,
    batch_size: int,
) -> tuple[Any, Any, dict[str, Any]]:
    if not spec.file:
        raise RuntimeError("arquivo GGUF não configurado")
    model_file = model_path / spec.file
    if not model_file.exists():
        raise RuntimeError(f"arquivo GGUF ausente: {model_file}")
    server = _find_llama_server()
    port = _free_port()
    pooling = spec.pooling or "last"
    command = [
        server,
        "-m",
        str(model_file),
        "--embedding",
        "--pooling",
        pooling,
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "-np",
        "1",
        "-ngl",
        "99" if device == "cuda" else "0",
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        load_started = time.monotonic()
        _wait_server(port, process)
        load_seconds = time.monotonic() - load_started
        doc_started = time.monotonic()
        doc_embeddings = _llama_cpp_encode(port, documents, batch_size)
        doc_seconds = time.monotonic() - doc_started
        query_started = time.monotonic()
        query_embeddings = _llama_cpp_encode(port, queries, batch_size)
        query_seconds = time.monotonic() - query_started
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=15)
    return doc_embeddings, query_embeddings, {
        "dtype": "gguf-i2_s/bf16",
        "load_seconds": round(load_seconds, 4),
        "document_encode_seconds": round(doc_seconds, 4),
        "query_encode_seconds": round(query_seconds, 4),
        "peak_vram_bytes": None,
        "llama_server": server,
        "pooling": pooling,
    }


def benchmark_model(request: dict[str, Any]) -> dict[str, Any]:
    resolved = ResolvedModel(**request["resolved"])
    spec = Gate2ModelSpec(**request["spec"])
    model_path = Path(request["model_path"])
    chunks = list(request["chunks"])
    queries = list(request["queries"])
    prompts = dict(request["prompts"])
    device = str(request["device"])
    batch_size = int(request["batch_size"])
    corpus_hash = str(request["corpus_hash"])

    chunk_ids = [str(chunk["chunk_id"]) for chunk in chunks]
    document_texts = [
        _document_text(chunk, spec.id, prompts, spec.prompt_profile)
        for chunk in chunks
    ]
    query_texts = [
        _query_text(query, spec.id, prompts, spec.prompt_profile)
        for query in queries
    ]

    started = time.monotonic()
    if spec.backend == "sentence-transformers":
        document_embeddings, query_embeddings, runtime = _sentence_transformer_embeddings(
            model_path,
            spec,
            document_texts,
            query_texts,
            device,
            batch_size,
        )
    elif spec.backend == "llama.cpp":
        document_embeddings, query_embeddings, runtime = _llama_cpp_embeddings(
            model_path,
            spec,
            document_texts,
            query_texts,
            device,
            batch_size,
        )
    else:
        raise RuntimeError(f"backend não suportado: {spec.backend}")

    rankings = _rankings_from_embeddings(
        document_embeddings, query_embeddings, chunk_ids
    )
    evaluation = evaluate_rankings(queries, rankings, DEFAULT_KS)
    actual_dimension = int(_normalize_rows(document_embeddings).shape[1])
    if spec.dimension > 0 and actual_dimension != spec.dimension:
        raise RuntimeError(
            f"dimensão divergente para {spec.id}: "
            f"esperada={spec.dimension} obtida={actual_dimension}"
        )
    total_seconds = time.monotonic() - started
    doc_seconds = float(runtime["document_encode_seconds"])
    query_seconds = float(runtime["query_encode_seconds"])
    runtime.update(
        {
            "device": device,
            "normalization": "l2",
            "batch_size": batch_size,
            "documents_per_second": (
                round(len(chunks) / doc_seconds, 4) if doc_seconds else None
            ),
            "queries_per_second": (
                round(len(queries) / query_seconds, 4) if query_seconds else None
            ),
            "total_seconds": round(total_seconds, 4),
        }
    )
    return {
        "schema_version": "1.1",
        "gate": 2,
        "model": {
            "id": spec.id,
            "repo": spec.repo,
            "revision": resolved.revision,
            "backend": spec.backend,
            "mode": spec.mode,
            "required": spec.required,
            "configured_dimension": spec.dimension,
            "actual_dimension": actual_dimension,
            "trust_remote_code": spec.trust_remote_code,
            "license": resolved.license,
            "gated": resolved.gated,
            "file": resolved.file,
            "weight_files": hash_weight_files(model_path),
        },
        "dataset": {
            "corpus_version": "holo_fake_scenes_v3",
            "combined_sha256": corpus_hash,
            "documents": len(chunks),
            "queries": len(queries),
        },
        "runtime": runtime,
        "metrics": evaluation,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    try:
        request = json.loads(Path(args.request).read_text(encoding="utf-8"))
        payload = {"status": "ok", "result": benchmark_model(request)}
        _atomic_json(output, payload)
        return 0
    except BaseException as exc:
        payload = {
            "status": "error",
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
        }
        _atomic_json(output, payload)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
