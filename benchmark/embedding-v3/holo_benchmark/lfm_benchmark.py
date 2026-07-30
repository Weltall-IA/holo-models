"""Canonical full-corpus benchmark entrypoint for the official LFM2.5 350M GGUF."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .bitnet_benchmark import (
    _stable_rankings,
    build_candidate_payload,
    remove_stale_candidate,
    validate_candidate_payload,
)
from .gate2_worker import _free_port, _wait_server
from .gate3_worker import _VramSampler, _encode, _truncate_and_normalize
from .metrics import DEFAULT_KS, evaluate_rankings
from .reranker_runtime import CORPUS_SHA256, atomic_json, load_frozen_dataset

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = PROJECT_ROOT / "results" / "gate3"
CANDIDATE_DIR = PROJECT_ROOT / "results" / "reranker" / "candidates"

PROFILE_ID = "lfm_25_embedding_350m_q4_k_m_official"
REPOSITORY = "LiquidAI/LFM2.5-Embedding-350M-GGUF"
DIMENSION = 1024
GATE_HIT_RATE_AT_50 = 0.94
REVISION = "a80de9c5b941d429104f0038292a0ef5a860e486"
LICENSE = "Apache-2.0"
EXPECTED_GGUF_SHA256 = "4d7aa9dc6406a10fc3dec2c11f8f06781af063bf49211b8e4132e9b876d3f32a"
EXPECTED_GGUF_BYTES = 229311232
DOCUMENT_PREFIX = "document: "
QUERY_PREFIX = "query: "


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _require_file(path: Path, label: str, *, executable: bool = False) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"{label} is not a regular file: {resolved}")
    if executable and not os.access(resolved, os.X_OK):
        raise PermissionError(f"{label} is not executable: {resolved}")
    return resolved


def _child_peak_ram_bytes() -> int:
    # Linux reports ru_maxrss in KiB.
    return int(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) * 1024


def _single_line(text: str) -> str:
    if "\x00" in text:
        raise ValueError("input text contains a NUL byte")
    return " ".join(str(text).splitlines())


def _prefixed_inputs(
    queries: Sequence[str], documents: Sequence[str]
) -> tuple[list[str], list[str]]:
    if not queries or not documents:
        raise ValueError("queries and documents must both be non-empty")
    prefixed_documents = [DOCUMENT_PREFIX + _single_line(text) for text in documents]
    prefixed_queries = [QUERY_PREFIX + _single_line(text) for text in queries]
    return prefixed_queries, prefixed_documents


def _sanitize_log(text: str, *paths: Path) -> str:
    cleaned = text
    replacements = [str(path) for path in paths]
    replacements.extend(
        value
        for value in (
            os.environ.get("HOME", ""),
            os.environ.get("USERPROFILE", ""),
        )
        if value
    )
    for value in sorted(set(replacements), key=len, reverse=True):
        cleaned = cleaned.replace(value, "<redacted>")
        cleaned = cleaned.replace(value.replace("/", "\\"), "<redacted>")
    return cleaned


def _reject_unexpected_duplicates(
    matrix: np.ndarray, inputs: Sequence[str], label: str
) -> None:
    if matrix.shape[0] != len(inputs):
        raise ValueError(f"{label} embedding count does not match inputs")
    seen: dict[bytes, tuple[int, str]] = {}
    for index, (row, text) in enumerate(zip(matrix, inputs, strict=True)):
        key = np.ascontiguousarray(row).tobytes()
        previous = seen.get(key)
        if previous is not None and previous[1] != text:
            raise ValueError(
                f"{label} produced an identical vector for distinct inputs "
                f"at indices {previous[0]} and {index}"
            )
        seen[key] = (index, text)


def _server_version(server: Path) -> str:
    result = subprocess.run(
        [str(server), "--version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return (result.stdout or result.stderr or "").strip()


def lfm_embed_queries_and_docs(
    queries: Sequence[str],
    documents: Sequence[str],
    *,
    gguf_path: Path,
    llama_server: Path,
    batch_size: int = 16,
    timeout_seconds: int = 21600,
    context_size: int = 2048,
    server_batch_size: int = 512,
    server_ubatch_size: int = 512,
    gpu_layers: int = 99,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Encode the frozen query/document partition through llama.cpp on CUDA."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if context_size <= 0 or server_batch_size <= 0 or server_ubatch_size <= 0:
        raise ValueError("server sizing arguments must be positive")
    if gpu_layers <= 0:
        raise ValueError("gpu_layers must be positive; CPU fallback is not allowed")

    binary = _require_file(llama_server, "llama-server", executable=True)
    model = _require_file(gguf_path, "LFM2.5 GGUF")
    model_size = model.stat().st_size
    if model_size != EXPECTED_GGUF_BYTES:
        raise RuntimeError(
            f"LFM2.5 GGUF size mismatch: expected {EXPECTED_GGUF_BYTES}, "
            f"found {model_size}"
        )
    model_sha256 = _sha256(model)
    if model_sha256 != EXPECTED_GGUF_SHA256:
        raise RuntimeError(
            "LFM2.5 GGUF SHA-256 mismatch: "
            f"expected {EXPECTED_GGUF_SHA256}, found {model_sha256}"
        )
    prefixed_queries, prefixed_documents = _prefixed_inputs(queries, documents)

    port = _free_port()
    actual_command = [
        str(binary),
        "-m",
        str(model),
        "--embedding",
        "--pooling",
        "cls",
        "--embd-normalize",
        "2",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "-np",
        "1",
        "-ngl",
        str(gpu_layers),
        "-c",
        str(context_size),
        "-b",
        str(server_batch_size),
        "-ub",
        str(server_ubatch_size),
    ]
    sanitized_command = [
        "<llama-server>",
        "-m",
        "<gguf>",
        "--embedding",
        "--pooling",
        "cls",
        "--embd-normalize",
        "2",
        "--host",
        "127.0.0.1",
        "--port",
        "<ephemeral-port>",
        "-np",
        "1",
        "-ngl",
        str(gpu_layers),
        "-c",
        str(context_size),
        "-b",
        str(server_batch_size),
        "-ub",
        str(server_ubatch_size),
    ]

    started = time.monotonic()
    failure: BaseException | None = None
    load_seconds = 0.0
    document_seconds = 0.0
    query_seconds = 0.0
    document_raw: np.ndarray | None = None
    query_raw: np.ndarray | None = None
    process: subprocess.Popen[str] | None = None
    peak_vram_bytes: int | None = None

    with tempfile.TemporaryDirectory(prefix="lfm25-llama-") as tmp:
        log_path = Path(tmp) / "llama-server.log"
        with log_path.open("w", encoding="utf-8") as log_handle:
            process = subprocess.Popen(
                actual_command,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
            )
            with _VramSampler(process.pid) as vram:
                try:
                    load_started = time.monotonic()
                    _wait_server(port, process, timeout=min(timeout_seconds, 300))
                    load_seconds = time.monotonic() - load_started

                    document_started = time.monotonic()
                    document_raw = _encode(port, prefixed_documents, batch_size)
                    document_seconds = time.monotonic() - document_started

                    query_started = time.monotonic()
                    query_raw = _encode(port, prefixed_queries, batch_size)
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
                    peak_vram_bytes = (
                        vram.peak_mib * 1024 * 1024
                        if vram.peak_mib is not None
                        else None
                    )
                    log_handle.flush()

        if failure is not None:
            log_tail = log_path.read_text(
                encoding="utf-8", errors="replace"
            )[-12000:]
            cleaned = _sanitize_log(log_tail, binary, model)
            raise RuntimeError(
                f"LFM2.5 llama.cpp benchmark failed: {failure}\n"
                f"llama-server log tail:\n{cleaned}"
            ) from failure

    if process is None or document_raw is None or query_raw is None:
        raise RuntimeError("llama.cpp benchmark did not produce embeddings")
    if peak_vram_bytes is None or peak_vram_bytes <= 0:
        raise RuntimeError(
            "CUDA offload was not evidenced by the VRAM sampler; "
            "CPU fallback is not accepted"
        )

    document_embeddings = _truncate_and_normalize(document_raw, DIMENSION)
    query_embeddings = _truncate_and_normalize(query_raw, DIMENSION)
    _reject_unexpected_duplicates(
        document_embeddings, prefixed_documents, "document encoder"
    )
    _reject_unexpected_duplicates(query_embeddings, prefixed_queries, "query encoder")

    total_seconds = time.monotonic() - started
    runtime: dict[str, Any] = {
        "backend": "llama.cpp",
        "device": "cuda",
        "backend_version": _server_version(binary),
        "dtype": "gguf",
        "quantization": "Q4_K_M",
        "dimension": DIMENSION,
        "pooling": "cls",
        "normalization": "l2",
        "document_prefix": DOCUMENT_PREFIX,
        "query_prefix": QUERY_PREFIX,
        "batch_size": batch_size,
        "context_size": context_size,
        "server_batch_size": server_batch_size,
        "server_ubatch_size": server_ubatch_size,
        "gpu_layers": gpu_layers,
        "load_seconds": round(load_seconds, 6),
        "document_encode_seconds": round(document_seconds, 6),
        "query_encode_seconds": round(query_seconds, 6),
        "documents_per_second": round(len(documents) / document_seconds, 6),
        "queries_per_second": round(len(queries) / query_seconds, 6),
        "total_seconds": round(total_seconds, 6),
        "peak_ram_bytes": _child_peak_ram_bytes(),
        "peak_vram_bytes": peak_vram_bytes,
        "command": sanitized_command,
        "benchmark_exit_code": 0,
        "server_shutdown_returncode": process.returncode,
        "binary_sha256": _sha256(binary),
        "gguf_sha256": model_sha256,
        "gguf_size_bytes": model_size,
    }
    return query_embeddings, document_embeddings, runtime


def _load_hardware(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("hardware JSON must contain an object")
    return payload


def benchmark_profile(args: argparse.Namespace) -> dict[str, Any]:
    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    if len(chunks) != 600 or len(queries) != 150:
        raise RuntimeError("frozen dataset counts do not match 600/150")

    documents = [str(chunk["text"]) for chunk in chunks]
    query_texts = [str(query["query"]) for query in queries]
    chunk_ids = [str(chunk["chunk_id"]) for chunk in chunks]

    query_embeddings, document_embeddings, runtime = lfm_embed_queries_and_docs(
        query_texts,
        documents,
        gguf_path=args.gguf_path,
        llama_server=args.llama_server,
        batch_size=args.batch_size,
        timeout_seconds=args.timeout_seconds,
        context_size=args.context_size,
        server_batch_size=args.server_batch_size,
        server_ubatch_size=args.server_ubatch_size,
        gpu_layers=args.gpu_layers,
    )
    rankings, ranked_scores = _stable_rankings(
        document_embeddings, query_embeddings, chunk_ids
    )
    metrics = evaluate_rankings(queries, rankings, DEFAULT_KS)
    summary = metrics["summary"]
    gate_pass = (
        float(summary["HitRate@50"]) >= GATE_HIT_RATE_AT_50
        and int(summary["queries_without_relevant"]) <= 5
    )

    model_identity = {
        "repository": REPOSITORY,
        "revision": REVISION,
        "file": args.gguf_path.name,
        "bytes": args.gguf_path.stat().st_size,
        "sha256": runtime["gguf_sha256"],
        "license": LICENSE,
        "quantization": "Q4_K_M",
        "native_dimension": DIMENSION,
        "configured_dimension": DIMENSION,
    }
    completed_at = datetime.now(timezone.utc).isoformat()
    result_payload = {
        "schema_version": "1.0",
        "id": PROFILE_ID,
        "gate": 3,
        "status": "COMPLETED",
        "gate_result": "PASS" if gate_pass else "FAIL",
        "model": {"id": PROFILE_ID, **model_identity},
        "dataset": {
            "corpus_version": "holo_fake_scenes_v3",
            "combined_sha256": CORPUS_SHA256,
            "documents": len(chunks),
            "queries": len(queries),
        },
        "hardware": _load_hardware(args.hardware_json),
        "runtime": runtime,
        "metrics": metrics,
        "completed_at": completed_at,
    }
    result_path = args.result_output or RESULT_DIR / f"{PROFILE_ID}.json"
    atomic_json(result_path, result_payload)

    candidate_target = args.candidate_output or CANDIDATE_DIR / f"{PROFILE_ID}.json"
    candidate_path: Path | None = None
    stale_candidate_removed = False
    if gate_pass:
        candidate_payload = build_candidate_payload(
            profile_id=PROFILE_ID,
            queries=queries,
            rankings=rankings,
            ranked_scores=ranked_scores,
            candidate_top_k=args.candidate_top_k,
            model_identity=model_identity,
            runtime=runtime,
        )
        candidate_payload["ranking_source"] = {
            "backend": runtime["backend"],
            "backend_version": runtime["backend_version"],
            "binary_sha256": runtime["binary_sha256"],
            "gguf_sha256": runtime["gguf_sha256"],
        }
        query_ids = [str(query["query_id"]) for query in queries]
        validate_candidate_payload(
            candidate_payload,
            expected_profile_id=PROFILE_ID,
            expected_query_ids=query_ids,
            expected_top_k=args.candidate_top_k,
        )
        candidate_path = candidate_target
        atomic_json(candidate_path, candidate_payload)
        if args.validate_canonical_loader:
            import reranker_execution

            original_candidate_dir = reranker_execution.CANDIDATE_DIR
            try:
                reranker_execution.CANDIDATE_DIR = candidate_path.parent
                loaded = reranker_execution.load_candidate_payloads(
                    [PROFILE_ID], args.candidate_top_k
                )
            finally:
                reranker_execution.CANDIDATE_DIR = original_candidate_dir
            if PROFILE_ID not in loaded:
                raise RuntimeError("canonical candidate loader did not return profile")
    else:
        stale_candidate_removed = remove_stale_candidate(candidate_target, PROFILE_ID)

    return {
        "status": "PASS" if gate_pass else "FAIL",
        "profile_id": PROFILE_ID,
        "result_path": str(result_path),
        "candidate_path": str(candidate_path) if candidate_path else None,
        "stale_candidate_removed": stale_candidate_removed,
        "metrics": summary,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gguf-path", type=Path, required=True)
    parser.add_argument("--llama-server", type=Path, required=True)
    parser.add_argument("--candidate-top-k", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--timeout-seconds", type=int, default=21600)
    parser.add_argument("--context-size", type=int, default=2048)
    parser.add_argument("--server-batch-size", type=int, default=512)
    parser.add_argument("--server-ubatch-size", type=int, default=512)
    parser.add_argument("--gpu-layers", type=int, default=99)
    parser.add_argument("--hardware-json", type=Path)
    parser.add_argument("--result-output", type=Path)
    parser.add_argument("--candidate-output", type=Path)
    parser.add_argument(
        "--validate-canonical-loader",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        payload = benchmark_profile(args)
    except Exception as exc:
        print(f"LFM2.5 benchmark blocked: {type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
