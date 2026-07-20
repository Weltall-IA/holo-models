from __future__ import annotations

import gc
import subprocess
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Sequence

from .gate2_runtime import _document_text, _query_text
from .gate2_worker import _find_llama_server, _wait_server
from .reranker_runtime import (
    ResourceSampler,
    _candidate_payload,
    _free_port,
    _normalise_rows,
    cosine_scores,
    directory_weight_files,
    llama_cpp_encode,
    path_size_bytes,
    read_json,
    sha256_file,
)


def generate_embeddinggemma_candidates(
    project_root: Path,
    repo_root: Path,
    chunks: Sequence[dict[str, Any]],
    queries: Sequence[dict[str, Any]],
    top_k: int,
    batch_size: int,
    device: str,
) -> dict[str, Any]:
    prompts = read_json(project_root / "config" / "prompts.json")
    model_dir = repo_root / "embed" / "embeddinggemma_gguf"
    model_file = model_dir / "embeddinggemma-300M-Q8_0.gguf"
    if not model_file.is_file():
        raise RuntimeError(f"EmbeddingGemma GGUF missing: {model_file}")
    llama_server = _find_llama_server()
    port = _free_port()
    command = [
        llama_server,
        "-m",
        str(model_file),
        "--embedding",
        "--pooling",
        "mean",
        "--embd-normalize",
        "2",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "-np",
        "1",
        "-ngl",
        "99" if device == "cuda" else "0",
        "-c",
        "2048",
        "-b",
        "512",
        "-ub",
        "512",
    ]
    documents = [
        _document_text(dict(row), "embeddinggemma", prompts, "embeddinggemma")
        for row in chunks
    ]
    query_texts = [
        _query_text(dict(row), "embeddinggemma", prompts, "embeddinggemma")
        for row in queries
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    started = time.monotonic()
    with ResourceSampler() as resources:
        try:
            load_started = time.monotonic()
            _wait_server(port, process)
            load_seconds = time.monotonic() - load_started
            doc_started = time.monotonic()
            doc_embeddings = llama_cpp_encode(port, documents, batch_size)
            doc_seconds = time.monotonic() - doc_started
            query_started = time.monotonic()
            query_embeddings = llama_cpp_encode(port, query_texts, batch_size)
            query_seconds = time.monotonic() - query_started
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=15)
    scores = cosine_scores(doc_embeddings, query_embeddings)
    runtime = {
        "device": device,
        "backend": "llama.cpp",
        "llama_server": llama_server,
        "command": command,
        "load_seconds": round(load_seconds, 4),
        "document_encode_seconds": round(doc_seconds, 4),
        "query_encode_seconds": round(query_seconds, 4),
        "total_seconds": round(time.monotonic() - started, 4),
        **resources.as_dict(),
    }
    return _candidate_payload(
        "embeddinggemma_768_float32",
        {
            "id": "embeddinggemma_gguf",
            "file": str(model_file),
            "file_bytes": model_file.stat().st_size,
            "file_sha256": sha256_file(model_file),
            "dimension": 768,
            "vector_dtype": "float32",
            "quantization": "Q8_0 model weights",
        },
        scores,
        chunks,
        queries,
        top_k,
        runtime,
    )


def _truncate_and_normalise(matrix: Any, dimension: int) -> Any:
    import numpy as np

    array = np.asarray(matrix, dtype=np.float32)
    if array.shape[1] < dimension:
        raise RuntimeError(
            f"embedding has {array.shape[1]} dimensions, expected >= {dimension}"
        )
    return _normalise_rows(array[:, :dimension])


def _scalar_int8_roundtrip(
    documents: Any,
    queries: Any,
) -> tuple[Any, Any, dict[str, Any]]:
    """Calibrate scalar int8 on the frozen corpus and dequantize for quality scoring."""
    import numpy as np

    docs = np.asarray(documents, dtype=np.float32)
    qrys = np.asarray(queries, dtype=np.float32)
    starts = docs.min(axis=0)
    ends = docs.max(axis=0)
    steps = (ends - starts) / 255.0
    zero_steps = steps == 0
    steps[zero_steps] = 1.0

    def quantize(values: Any) -> tuple[Any, int]:
        scaled = (np.asarray(values, dtype=np.float32) - starts) / steps - 128.0
        out_of_range = int(np.count_nonzero((scaled < -128.0) | (scaled > 127.0)))
        quantized = np.clip(np.rint(scaled), -128, 127).astype(np.int8)
        return quantized, out_of_range

    q_docs, doc_oob = quantize(docs)
    q_queries, query_oob = quantize(qrys)

    def dequantize(values: Any) -> Any:
        signed = np.asarray(values, dtype=np.int16).astype(np.float32)
        return (signed + 128.0) * steps + starts

    return dequantize(q_docs), dequantize(q_queries), {
        "method": "per-dimension scalar int8",
        "calibration_documents": int(docs.shape[0]),
        "stored_dtype": "int8",
        "stored_dimension": int(docs.shape[1]),
        "stored_bytes_per_vector": int(docs.shape[1]),
        "zero_range_dimensions": int(np.count_nonzero(zero_steps)),
        "document_values_clipped": doc_oob,
        "query_values_clipped": query_oob,
        "quality_scoring": "dequantized cosine using corpus-calibrated ranges",
        "native_vector_database_latency_measured": False,
    }


def generate_nano_candidates(
    project_root: Path,
    repo_root: Path,
    chunks: Sequence[dict[str, Any]],
    queries: Sequence[dict[str, Any]],
    top_k: int,
    batch_size: int,
    device: str,
) -> dict[str, dict[str, Any]]:
    model_dir = repo_root / "embed" / "voyage4_nano"
    if not model_dir.is_dir():
        raise RuntimeError(f"Voyage 4 Nano snapshot missing: {model_dir}")
    try:
        import torch
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("sentence-transformers and torch are required") from exc

    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
    with ResourceSampler() as resources:
        load_started = time.monotonic()
        model = SentenceTransformer(
            str(model_dir),
            trust_remote_code=True,
            truncate_dim=2048,
            device=device,
        )
        load_seconds = time.monotonic() - load_started
        documents = [str(row["text"]) for row in chunks]
        query_texts = [str(row["query"]) for row in queries]
        doc_started = time.monotonic()
        doc_embeddings = model.encode_document(
            documents,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,
            precision="float32",
            truncate_dim=2048,
        )
        doc_seconds = time.monotonic() - doc_started
        query_started = time.monotonic()
        query_embeddings = model.encode_query(
            query_texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,
            precision="float32",
            truncate_dim=2048,
        )
        query_seconds = time.monotonic() - query_started
        peak_vram = int(torch.cuda.max_memory_allocated()) if device == "cuda" else None

    weights = directory_weight_files(model_dir)
    model_metadata = {
        "id": "voyage4_nano",
        "repo": "voyageai/voyage-4-nano",
        "snapshot": str(model_dir),
        "snapshot_bytes": path_size_bytes(model_dir),
        "weight_files": [
            {
                "file": str(path.relative_to(model_dir)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in weights
        ],
    }
    common_runtime = {
        "device": device,
        "backend": "sentence-transformers",
        "load_seconds": round(load_seconds, 4),
        "document_encode_seconds": round(doc_seconds, 4),
        "query_encode_seconds": round(query_seconds, 4),
        "peak_vram_bytes": peak_vram,
        "total_seconds_shared": round(time.monotonic() - started, 4),
        **resources.as_dict(),
    }

    docs_2048 = _truncate_and_normalise(doc_embeddings, 2048)
    queries_2048 = _truncate_and_normalise(query_embeddings, 2048)
    docs_1024 = _truncate_and_normalise(doc_embeddings, 1024)
    queries_1024 = _truncate_and_normalise(query_embeddings, 1024)
    int8_docs, int8_queries, quantization = _scalar_int8_roundtrip(
        docs_2048,
        queries_2048,
    )

    variants = {
        "voyage4_nano_1024_float32": (
            docs_1024,
            queries_1024,
            {
                "dimension": 1024,
                "vector_dtype": "float32",
                "bytes_per_vector": 4096,
            },
        ),
        "voyage4_nano_2048_float32": (
            docs_2048,
            queries_2048,
            {
                "dimension": 2048,
                "vector_dtype": "float32",
                "bytes_per_vector": 8192,
            },
        ),
        "voyage4_nano_2048_int8": (
            int8_docs,
            int8_queries,
            {
                "dimension": 2048,
                "vector_dtype": "int8",
                "bytes_per_vector": 2048,
                "quantization": quantization,
            },
        ),
    }
    output: dict[str, dict[str, Any]] = {}
    for variant, (docs, qrys, extra) in variants.items():
        score_started = time.monotonic()
        scores = cosine_scores(docs, qrys)
        runtime = dict(common_runtime)
        runtime["score_seconds"] = round(time.monotonic() - score_started, 4)
        output[variant] = _candidate_payload(
            variant,
            {**model_metadata, **extra},
            scores,
            chunks,
            queries,
            top_k,
            runtime,
        )

    del model, doc_embeddings, query_embeddings
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()
    return output


def _checkpoint_rows(
    path: Path,
    model: str,
    input_type: str,
    dimension: int,
    expected_ids: Sequence[str],
) -> list[list[float]]:
    payload = read_json(path)
    if payload.get("model") != model or payload.get("input_type") != input_type:
        raise RuntimeError(f"incompatible Voyage checkpoint: {path}")
    if int(payload.get("dimension") or 0) != dimension:
        raise RuntimeError(f"Voyage checkpoint dimension diverged: {path}")
    rows = OrderedDict(payload.get("rows") or {})
    missing = [item_id for item_id in expected_ids if item_id not in rows]
    if missing:
        raise RuntimeError(f"Voyage checkpoint is missing rows: {missing[:3]}")
    return [[float(value) for value in rows[item_id]] for item_id in expected_ids]


def generate_voyage_large_candidates_from_checkpoint(
    project_root: Path,
    chunks: Sequence[dict[str, Any]],
    queries: Sequence[dict[str, Any]],
    top_k: int,
) -> dict[str, Any]:
    base = project_root / "results" / "raw" / "voyage" / "voyage-4-large"
    documents_path = base / "documents.json"
    queries_path = base / "queries.json"
    if not documents_path.is_file() or not queries_path.is_file():
        raise RuntimeError(
            "Voyage Large checkpoints are missing; do not call the API implicitly. "
            "Regenerate only with explicit director authorization."
        )
    started = time.monotonic()
    doc_embeddings = _checkpoint_rows(
        documents_path,
        "voyage-4-large",
        "document",
        1024,
        [str(row["chunk_id"]) for row in chunks],
    )
    query_embeddings = _checkpoint_rows(
        queries_path,
        "voyage-4-large",
        "query",
        1024,
        [str(row["query_id"]) for row in queries],
    )
    if len(doc_embeddings) != len(chunks) or len(query_embeddings) != len(queries):
        raise RuntimeError("Voyage Large checkpoint row counts diverge")
    scores = cosine_scores(doc_embeddings, query_embeddings)
    return _candidate_payload(
        "voyage_4_large_1024_float32",
        {
            "id": "voyage-4-large",
            "provider": "Voyage AI",
            "checkpoint_documents": str(documents_path),
            "checkpoint_queries": str(queries_path),
            "dimension": 1024,
            "vector_dtype": "float32",
            "bytes_per_vector": 4096,
            "source": "existing-voyage-4-large-checkpoint",
            "new_api_call": False,
        },
        scores,
        chunks,
        queries,
        top_k,
        {
            "device": "checkpoint",
            "backend": "voyage-api-checkpoint-reuse",
            "total_seconds": round(time.monotonic() - started, 4),
            "new_api_requests": 0,
            "new_api_tokens": 0,
        },
    )
