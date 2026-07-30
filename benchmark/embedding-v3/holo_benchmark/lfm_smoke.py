"""Deterministic 20-document/10-query smoke test for the LFM2.5 runner."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .lfm_benchmark import DIMENSION, lfm_embed_queries_and_docs
from .reranker_runtime import atomic_json, load_frozen_dataset

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SMOKE_QUERY_COUNT = 10
SMOKE_DOCUMENT_COUNT = 20
MIN_SEMANTIC_PASSES = 7


def select_smoke_dataset(
    chunks: Sequence[Mapping[str, Any]],
    queries: Sequence[Mapping[str, Any]],
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    if len(chunks) < SMOKE_DOCUMENT_COUNT:
        raise ValueError("smoke test requires at least 20 documents")
    if len(queries) < SMOKE_QUERY_COUNT:
        raise ValueError("smoke test requires at least 10 queries")

    selected_queries = list(queries[:SMOKE_QUERY_COUNT])
    chunk_by_id = {str(row["chunk_id"]): row for row in chunks}
    selected_ids: list[str] = []

    for query in selected_queries:
        relevant_ids = [str(value) for value in query.get("relevant_chunk_ids") or []]
        hard_negative_ids = [
            str(value) for value in (query.get("hard_negative_chunk_ids") or [])[:1]
        ]
        if not relevant_ids:
            raise ValueError(f"query {query.get('query_id')} has no relevant chunks")
        for chunk_id in relevant_ids + hard_negative_ids:
            if chunk_id not in chunk_by_id:
                raise ValueError(f"smoke chunk not found in corpus: {chunk_id}")
            if chunk_id not in selected_ids:
                selected_ids.append(chunk_id)

    for chunk in chunks:
        chunk_id = str(chunk["chunk_id"])
        if chunk_id not in selected_ids:
            selected_ids.append(chunk_id)
        if len(selected_ids) >= SMOKE_DOCUMENT_COUNT:
            break

    selected_ids = selected_ids[:SMOKE_DOCUMENT_COUNT]
    selected_chunks = [chunk_by_id[chunk_id] for chunk_id in selected_ids]
    relevant_union = {
        str(chunk_id)
        for query in selected_queries
        for chunk_id in query.get("relevant_chunk_ids") or []
    }
    if not relevant_union.issubset(set(selected_ids)):
        missing = sorted(relevant_union - set(selected_ids))
        raise ValueError(f"smoke selection dropped relevant chunks: {missing}")
    return selected_chunks, selected_queries


def _validate_embeddings(matrix: np.ndarray, rows: int, label: str) -> None:
    if matrix.shape != (rows, DIMENSION):
        raise ValueError(
            f"{label} shape mismatch: expected {(rows, DIMENSION)}, "
            f"found {matrix.shape}"
        )
    if not np.all(np.isfinite(matrix)):
        raise ValueError(f"{label} contains non-finite values")
    norms = np.linalg.norm(matrix, axis=1)
    if not np.allclose(norms, 1.0, atol=1e-3):
        raise ValueError(f"{label} is not L2-normalized")


def run_smoke(args: argparse.Namespace) -> dict[str, Any]:
    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    selected_chunks, selected_queries = select_smoke_dataset(chunks, queries)

    query_embeddings, document_embeddings, runtime = lfm_embed_queries_and_docs(
        [str(row["query"]) for row in selected_queries],
        [str(row["text"]) for row in selected_chunks],
        gguf_path=args.gguf_path,
        llama_server=args.llama_server,
        batch_size=args.batch_size,
        timeout_seconds=args.timeout_seconds,
    )
    _validate_embeddings(query_embeddings, SMOKE_QUERY_COUNT, "query embeddings")
    _validate_embeddings(
        document_embeddings, SMOKE_DOCUMENT_COUNT, "document embeddings"
    )
    peak_vram_bytes = int(runtime.get("peak_vram_bytes") or 0)
    if peak_vram_bytes <= 0:
        raise RuntimeError("smoke test has no CUDA VRAM evidence")

    selected_ids = [str(row["chunk_id"]) for row in selected_chunks]
    positions = {chunk_id: index for index, chunk_id in enumerate(selected_ids)}
    scores = query_embeddings @ document_embeddings.T
    semantic_passes = 0
    comparisons: list[dict[str, Any]] = []

    for query_index, query in enumerate(selected_queries):
        relevant_ids = [str(value) for value in query["relevant_chunk_ids"]]
        relevant_score = max(
            float(scores[query_index, positions[chunk_id]])
            for chunk_id in relevant_ids
        )
        excluded = set(relevant_ids) | {
            str(value) for value in query.get("hard_negative_chunk_ids") or []
        }
        unrelated_indices = [
            index
            for index, chunk_id in enumerate(selected_ids)
            if chunk_id not in excluded
        ][:5]
        if not unrelated_indices:
            raise RuntimeError(
                f"query {query.get('query_id')} has no unrelated smoke controls"
            )
        unrelated_mean = float(
            np.mean(scores[query_index, unrelated_indices], dtype=np.float64)
        )
        passed = relevant_score > unrelated_mean
        semantic_passes += int(passed)
        comparisons.append(
            {
                "query_id": str(query["query_id"]),
                "relevant_score": relevant_score,
                "unrelated_mean": unrelated_mean,
                "passed": passed,
            }
        )

    if semantic_passes < MIN_SEMANTIC_PASSES:
        raise RuntimeError(
            f"semantic smoke threshold failed: {semantic_passes}/"
            f"{SMOKE_QUERY_COUNT}, required {MIN_SEMANTIC_PASSES}"
        )

    payload = {
        "schema_version": "1.0",
        "status": "PASS",
        "queries": SMOKE_QUERY_COUNT,
        "documents": SMOKE_DOCUMENT_COUNT,
        "dimension": DIMENSION,
        "semantic_passes": semantic_passes,
        "semantic_required": MIN_SEMANTIC_PASSES,
        "peak_vram_bytes": peak_vram_bytes,
        "backend_version": runtime.get("backend_version"),
        "binary_sha256": runtime.get("binary_sha256"),
        "gguf_sha256": runtime.get("gguf_sha256"),
        "comparisons": comparisons,
    }
    if args.output is not None:
        atomic_json(args.output, payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gguf-path", type=Path, required=True)
    parser.add_argument("--llama-server", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        payload = run_smoke(args)
    except Exception as exc:
        print(f"LFM2.5 smoke blocked: {type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
