"""Canonical CrossEncoder reranking panel for LAMAR and Ettin native models.

LAMAR-600m and the Ettin rerankers are native sentence-transformers
CrossEncoder snapshots (safetensors).  No NVFP4/Q4 artifact exists in the
official repositories and every model has at most 1B parameters, so the
native-precision exception applies.  This runner loads them with
``sentence_transformers.CrossEncoder`` and produces the same canonical score
and pipeline artifacts as the Mixedbread panel.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .artifact_portability import assert_portable_payload, sanitize_host_payload
from .bitnet_benchmark import _ranking_sha256
from .reranker_metrics import (
    candidate_ids,
    evaluate_reranker_effect,
    scores_to_rankings,
)
from .reranker_runtime import (
    CORPUS_SHA256,
    DEFAULT_RERANK_INSTRUCTION,
    ResourceSampler,
    atomic_json,
    load_frozen_dataset,
    read_json,
    rerank_query_text,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_TOP_K = 50
RERANK_TOP_K = 20

PANEL_MODELS = {
    "lamar_600m": {
        "model_id": "lamar_600m",
        "repository": "nlpai-lab/LAMAR-600m",
        "license": "MIT",
        "parameters": "0.6B",
        "quantization": "native_fp32",
        "weight_file": "model.safetensors",
    },
    "ettin_reranker_150m_v1": {
        "model_id": "ettin_reranker_150m_v1",
        "repository": "cross-encoder/ettin-reranker-150m-v1",
        "license": "Apache-2.0",
        "parameters": "0.15B",
        "quantization": "native_fp32",
        "weight_file": "model.safetensors",
    },
    "ettin_reranker_68m_v1": {
        "model_id": "ettin_reranker_68m_v1",
        "repository": "cross-encoder/ettin-reranker-68m-v1",
        "license": "Apache-2.0",
        "parameters": "0.068B",
        "quantization": "native_fp32",
        "weight_file": "model.safetensors",
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def validate_model(model_id: str, path: Path) -> tuple[Path, dict[str, Any]]:
    spec = PANEL_MODELS.get(model_id)
    if spec is None:
        raise ValueError(f"unknown panel model: {model_id}")
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        raise FileNotFoundError(f"model directory missing: {resolved}")
    weight = resolved / spec["weight_file"]
    if not weight.is_file():
        raise FileNotFoundError(f"weight file missing: {weight}")
    return resolved, {
        "id": spec["model_id"],
        "repository": spec["repository"],
        "license": spec["license"],
        "parameters": spec["parameters"],
        "quantization": spec["quantization"],
        "weight_file": spec["weight_file"],
        "weight_bytes": weight.stat().st_size,
        "weight_sha256": _sha256(weight),
        "revision": read_local_revision(resolved, spec["weight_file"]),
        "backend": "sentence-transformers.CrossEncoder",
    }


def read_local_revision(model_path: Path, relative_path: str) -> str | None:
    metadata = (
        model_path
        / ".cache"
        / "huggingface"
        / "download"
        / f"{relative_path}.metadata"
    )
    if not metadata.is_file():
        return None
    first = metadata.read_text(encoding="utf-8").splitlines()
    return first[0].strip() if first else None


def score_cross_encoder(
    model_path: Path,
    queries: Sequence[dict[str, Any]],
    union_ids: Sequence[Sequence[str]],
    chunk_text_by_id: Mapping[str, str],
    batch_size: int,
    instruction: str,
) -> tuple[list[dict[str, float]], dict[str, Any]]:
    try:
        import numpy as np
        import torch
        from sentence_transformers import CrossEncoder
    except ImportError as exc:
        raise RuntimeError(
            "LAMAR/Ettin require numpy, torch and sentence-transformers"
        ) from exc

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable")
    torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
    latencies: list[float] = []
    score_rows: list[dict[str, float]] = []
    with ResourceSampler() as resources:
        load_started = time.monotonic()
        model = CrossEncoder(str(model_path), device="cuda", trust_remote_code=True)
        load_seconds = time.monotonic() - load_started
        tokenizer = getattr(model, "tokenizer", None)
        for query, chunk_ids in zip(queries, union_ids, strict=True):
            pairs = [
                (rerank_query_text(query, instruction), chunk_text_by_id[chunk_id])
                for chunk_id in chunk_ids
            ]
            request_started = time.monotonic()
            raw_scores = model.predict(
                pairs, batch_size=batch_size, show_progress_bar=False
            )
            latencies.append(time.monotonic() - request_started)
            values = np.asarray(raw_scores)
            row: dict[str, float] = {}
            for chunk_id, value in zip(chunk_ids, values, strict=True):
                flattened = np.asarray(value).reshape(-1)
                if flattened.size != 1:
                    raise RuntimeError("CrossEncoder returned multiple logits per pair")
                score = float(flattened[0])
                if not math.isfinite(score):
                    raise RuntimeError("CrossEncoder returned a non-finite score")
                row[chunk_id] = score
            score_rows.append(row)
        peak_vram = int(torch.cuda.max_memory_allocated())

    ordered = sorted(latencies)

    def percentile(fraction: float) -> float | None:
        if not ordered:
            return None
        index = min(len(ordered) - 1, int((len(ordered) - 1) * fraction))
        return ordered[index]

    runtime = {
        "backend": "sentence-transformers.CrossEncoder",
        "backend_version": importlib.metadata.version("sentence-transformers"),
        "device": "cuda",
        "load_seconds": round(load_seconds, 4),
        "score_seconds": round(sum(latencies), 4),
        "total_seconds": round(time.monotonic() - started, 4),
        "queries": len(queries),
        "pairs": sum(len(row) for row in union_ids),
        "batch_size": batch_size,
        "latency_p50_seconds": round(percentile(0.50), 4),
        "latency_p95_seconds": round(percentile(0.95), 4),
        "latency_max_seconds": round(max(latencies), 4),
        "peak_vram_bytes": peak_vram,
        **resources.as_dict(),
    }
    if peak_vram <= 0:
        raise RuntimeError("no positive CUDA memory evidence")
    return score_rows, runtime


def benchmark_profile(args: argparse.Namespace) -> dict[str, Any]:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_DATASETS_OFFLINE", "1")

    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    query_ids = [str(query["query_id"]) for query in queries]
    chunk_text_by_id = {str(chunk["chunk_id"]): str(chunk["text"]) for chunk in chunks}
    canonical = read_json(args.canonical)
    rows, candidate_provenance, embedding_identity = load_candidate(
        args.candidate, args.profile_id, query_ids, set(chunk_text_by_id), canonical
    )
    ids = candidate_ids(rows)
    model_path, model_identity = validate_model(args.model_id, args.model_path)
    score_rows, runtime = score_cross_encoder(
        model_path, queries, ids, chunk_text_by_id, args.batch_size, args.instruction
    )
    if len(score_rows) != len(queries) or any(
        set(row) != set(ids[index]) for index, row in enumerate(score_rows)
    ):
        raise RuntimeError("score candidate set mismatch")
    if runtime.get("device") != "cuda" or int(runtime.get("pairs") or 0) != 7500:
        raise RuntimeError("runtime evidence mismatch")

    completed_at = datetime.now(timezone.utc).isoformat()
    dataset = {
        "corpus_version": "holo_fake_scenes_v3",
        "combined_sha256": CORPUS_SHA256,
        "documents": len(chunks),
        "queries": len(queries),
    }
    score_payload = {
        "schema_version": "1.0",
        "reranker_id": args.model_id,
        "model": model_identity,
        "dataset": dataset,
        "candidate": candidate_provenance,
        "instruction": args.instruction,
        "runtime": runtime,
        "queries": [
            {
                "query_id": query_id,
                "candidate_ids": list(candidate_ids_row),
                "scores": {
                    chunk_id: float(score_map[chunk_id])
                    for chunk_id in candidate_ids_row
                },
            }
            for query_id, candidate_ids_row, score_map in zip(
                query_ids, ids, score_rows, strict=True
            )
        ],
        "completed_at": completed_at,
    }
    reranked_full = scores_to_rankings(rows, score_rows)
    reranked_top = [ranking[:RERANK_TOP_K] for ranking in reranked_full]
    evaluation = evaluate_reranker_effect(
        queries, ids, reranked_top, CANDIDATE_TOP_K
    )
    try:
        score_artifact = str(
            args.score_output.resolve().relative_to(PROJECT_ROOT.resolve())
        )
    except ValueError:
        score_artifact = f"<external>/{args.score_output.name}"
    pipeline_payload = {
        "schema_version": "1.0",
        "pipeline_id": f"{args.profile_id}__{args.model_id}",
        "embedding_variant": args.profile_id,
        "embedding": embedding_identity,
        "candidate_ranking_sha256": candidate_provenance["ranking_sha256"],
        "reranker_id": args.model_id,
        "reranker": model_identity,
        "dataset": dataset,
        "candidate_top_k": CANDIDATE_TOP_K,
        "rerank_top_k": RERANK_TOP_K,
        "score_artifact": score_artifact,
        "evaluation": evaluation,
        "completed_at": completed_at,
    }
    assert_portable_payload(score_payload)
    assert_portable_payload(pipeline_payload)
    atomic_json(args.score_output, score_payload)
    atomic_json(args.pipeline_output, pipeline_payload)
    return {
        "status": "PASS",
        "pipeline_id": pipeline_payload["pipeline_id"],
        "ranking_sha256": candidate_provenance["ranking_sha256"],
        "pairs": runtime["pairs"],
        "base_HitRate@1": evaluation["base_metrics"]["summary"]["HitRate@1"],
        "reranked_HitRate@1": evaluation["reranked_metrics"]["summary"]["HitRate@1"],
    }


def load_candidate(
    path: Path,
    profile_id: str,
    query_ids: Sequence[str],
    known_chunk_ids: set[str],
    canonical: Mapping[str, Any],
) -> tuple[list[list[dict[str, Any]]], dict[str, Any], dict[str, Any]]:
    from .mxbai_panel_benchmark import load_candidate as _load

    return _load(path, profile_id, query_ids, known_chunk_ids, canonical)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", choices=tuple(PANEL_MODELS), required=True)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument(
        "--canonical", type=Path, default=PROJECT_ROOT / "ALL_BENCHMARK_RESULTS.json"
    )
    parser.add_argument("--score-output", type=Path, required=True)
    parser.add_argument("--pipeline-output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--instruction", default=DEFAULT_RERANK_INSTRUCTION)
    return parser


def main() -> int:
    print(benchmark_profile(build_parser().parse_args()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
