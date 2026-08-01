"""Canonical Mixedbread reranking for the fixed six-profile light panel."""
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
from .reranker_metrics import candidate_ids, evaluate_reranker_effect, scores_to_rankings
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
MODEL_ID = "mxbai_rerank_base_v2"
MODEL_REPOSITORY = "mixedbread-ai/mxbai-rerank-base-v2"
MODEL_REVISION = "2cae013cb0d1dc0d16409ebd405e35875576d78e"
MODEL_WEIGHT_FILE = "model.safetensors"
MODEL_WEIGHT_SHA256 = "c01649fe56b3fe32e52da43c69e084dff7c2252cf231a38c56d5a291a674338f"
MODEL_LICENSE = "Apache-2.0"
CANDIDATE_TOP_K = 50
RERANK_TOP_K = 20
PANEL_PROFILES = (
    "nemotron_3_embed_1b_nvfp4",
    "nomic_embed_text_v2_moe_q4",
    "qwen3_embedding_4b_q8_0",
    "embeddinggemma",
    "colibri_ptbr",
    "granite_embedding_311m_r2",
    "embeddinggemma_768_float32",
    "qwen3_embedding_0_6b_1024",
    "voyage4_nano",
)
_REQUIRED_MODEL_FILES = (MODEL_WEIGHT_FILE, "config.json", "tokenizer.json")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _payload_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_model(path: Path) -> tuple[Path, dict[str, Any]]:
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        raise FileNotFoundError(f"Mixedbread model directory is missing: {resolved}")
    missing = [name for name in _REQUIRED_MODEL_FILES if not (resolved / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Mixedbread repository is incomplete: {missing}")
    weight = resolved / MODEL_WEIGHT_FILE
    weight_sha256 = _sha256(weight)
    if weight_sha256 != MODEL_WEIGHT_SHA256:
        raise ValueError(
            "Mixedbread weight SHA-256 mismatch: "
            f"expected {MODEL_WEIGHT_SHA256}, found {weight_sha256}"
        )
    return resolved, {
        "id": MODEL_ID,
        "repository": MODEL_REPOSITORY,
        "revision": MODEL_REVISION,
        "backend": "sentence-transformers.CrossEncoder",
        "license": MODEL_LICENSE,
        "weight_files": [
            {
                "file": MODEL_WEIGHT_FILE,
                "bytes": weight.stat().st_size,
                "sha256": weight_sha256,
            }
        ],
    }


def _raw_profile_identity(canonical: Mapping[str, Any], profile_id: str) -> dict[str, Any]:
    by_id = canonical.get("raw_embedding_profiles_by_id")
    if not isinstance(by_id, Mapping):
        raise ValueError("canonical raw embedding index is missing")
    record = by_id.get(profile_id)
    if not isinstance(record, Mapping):
        raise ValueError(f"raw embedding profile is missing: {profile_id}")
    metrics = record.get("metrics")
    if not isinstance(metrics, Mapping) or metrics.get("mrr_at_10") is None:
        raise ValueError(f"raw embedding profile has no measured metrics: {profile_id}")
    metadata = record.get("metadata") if isinstance(record.get("metadata"), Mapping) else {}
    runtime = record.get("runtime") if isinstance(record.get("runtime"), Mapping) else {}
    identity = {
        "profile_id": profile_id,
        "source_group": record.get("source_group"),
        "source_path": record.get("source_path"),
        "evidence_sha256": _payload_sha256(record),
        "model": metadata.get("model"),
        "backend": runtime.get("backend"),
        "backend_version": runtime.get("backend_version"),
    }
    return sanitize_host_payload(identity)


def _validate_rankings(
    rankings: Sequence[Sequence[str]],
    query_ids: Sequence[str],
    known_chunk_ids: set[str],
) -> list[list[dict[str, Any]]]:
    if len(rankings) != len(query_ids):
        raise ValueError("candidate query count mismatch")
    rows: list[list[dict[str, Any]]] = []
    for query_id, ranking in zip(query_ids, rankings, strict=True):
        ids = [str(value) for value in list(ranking)[:CANDIDATE_TOP_K]]
        if len(ids) != CANDIDATE_TOP_K:
            raise ValueError(f"candidate row {query_id} is not top 50")
        if len(ids) != len(set(ids)):
            raise ValueError(f"candidate row {query_id} contains duplicates")
        unknown = [chunk_id for chunk_id in ids if chunk_id not in known_chunk_ids]
        if unknown:
            raise ValueError(f"candidate row {query_id} references unknown chunks")
        rows.append(
            [
                {"chunk_id": chunk_id, "rank": rank}
                for rank, chunk_id in enumerate(ids, start=1)
            ]
        )
    return rows


def load_candidate(
    path: Path,
    profile_id: str,
    query_ids: Sequence[str],
    known_chunk_ids: set[str],
    canonical: Mapping[str, Any],
) -> tuple[list[list[dict[str, Any]]], dict[str, Any], dict[str, Any]]:
    payload = read_json(path)
    if payload.get("schema_version") == "1.0":
        if payload.get("variant") != profile_id:
            raise ValueError("candidate profile mismatch")
        dataset = payload.get("dataset") or {}
        if dataset.get("corpus_sha256") != CORPUS_SHA256:
            raise ValueError("candidate corpus mismatch")
        query_rows = list(payload.get("queries") or [])
        if [str(row.get("query_id")) for row in query_rows] != list(query_ids):
            raise ValueError("candidate query order mismatch")
        rankings = [
            [str(item.get("chunk_id")) for item in list(row.get("candidates") or [])]
            for row in query_rows
        ]
        rows = _validate_rankings(rankings, query_ids, known_chunk_ids)
        ranking_sha256 = _ranking_sha256(query_ids, rankings)
        if payload.get("ranking_sha256") != ranking_sha256:
            raise ValueError("candidate ranking SHA-256 mismatch")
        embedding = payload.get("embedding")
        if not isinstance(embedding, Mapping):
            raise ValueError("candidate embedding identity is missing")
        embedding_identity = sanitize_host_payload(dict(embedding))
        source_schema = "1.0"
    else:
        if payload.get("id") != profile_id:
            raise ValueError("legacy candidate profile mismatch")
        candidates = payload.get("candidates")
        if not isinstance(candidates, Mapping):
            raise ValueError("legacy candidate mapping is missing")
        if set(map(str, candidates)) != set(query_ids):
            raise ValueError("legacy candidate query set mismatch")
        rankings = [list(candidates[query_id]) for query_id in query_ids]
        rows = _validate_rankings(rankings, query_ids, known_chunk_ids)
        ranking_sha256 = _ranking_sha256(query_ids, rankings)
        embedding_identity = _raw_profile_identity(canonical, profile_id)
        source_schema = "legacy-id-candidates"

    try:
        source_artifact = str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError as exc:
        raise ValueError("candidate source must be inside the benchmark project") from exc
    provenance = {
        "variant": profile_id,
        "source_artifact": source_artifact,
        "source_artifact_sha256": _sha256(path),
        "source_schema": source_schema,
        "ranking_sha256": ranking_sha256,
        "candidate_top_k": CANDIDATE_TOP_K,
    }
    return rows, provenance, embedding_identity


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
        raise RuntimeError("Mixedbread requires numpy, torch and sentence-transformers") from exc

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable for Mixedbread")
    torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
    latencies: list[float] = []
    score_rows: list[dict[str, float]] = []
    with ResourceSampler() as resources:
        load_started = time.monotonic()
        try:
            model = CrossEncoder(str(model_path), device="cuda", trust_remote_code=True)
        except TypeError:
            model = CrossEncoder(
                str(model_path),
                device="cuda", model_kwargs={"trust_remote_code": True}
            )
        load_seconds = time.monotonic() - load_started
        tokenizer = getattr(model, "tokenizer", None)
        effective_max_length = getattr(model, "max_length", None)
        tokenizer_max_length = getattr(tokenizer, "model_max_length", None)
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
            if values.shape[0] != len(chunk_ids):
                raise RuntimeError("Mixedbread score count mismatch")
            row: dict[str, float] = {}
            for chunk_id, value in zip(chunk_ids, values, strict=True):
                flattened = np.asarray(value).reshape(-1)
                if flattened.size != 1:
                    raise RuntimeError("Mixedbread returned multiple logits per pair")
                score = float(flattened[0])
                if not math.isfinite(score):
                    raise RuntimeError("Mixedbread returned a non-finite score")
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
        "tokenizer_class": type(tokenizer).__name__ if tokenizer is not None else None,
        "tokenizer_model_max_length": tokenizer_max_length,
        "effective_max_length": effective_max_length,
        "truncation": "CrossEncoder tokenizer truncation enabled",
        "latency_p50_seconds": round(percentile(0.50), 4),
        "latency_p95_seconds": round(percentile(0.95), 4),
        "latency_max_seconds": round(max(latencies), 4),
        "peak_vram_bytes": peak_vram,
        **resources.as_dict(),
    }
    if peak_vram <= 0:
        raise RuntimeError("Mixedbread has no positive CUDA memory evidence")
    return score_rows, runtime


def benchmark_profile(args: argparse.Namespace) -> dict[str, Any]:
    if args.profile_id not in PANEL_PROFILES:
        raise ValueError(f"profile is not in the fixed Mixedbread panel: {args.profile_id}")
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
    model_path, model_identity = validate_model(args.model_path)
    score_rows, runtime = score_cross_encoder(
        model_path, queries, ids, chunk_text_by_id, args.batch_size, args.instruction
    )
    if len(score_rows) != len(queries) or any(
        set(row) != set(ids[index]) for index, row in enumerate(score_rows)
    ):
        raise RuntimeError("Mixedbread score candidate set mismatch")
    if runtime.get("device") != "cuda" or int(runtime.get("pairs") or 0) != 7500:
        raise RuntimeError("Mixedbread runtime evidence mismatch")

    completed_at = datetime.now(timezone.utc).isoformat()
    dataset = {
        "corpus_version": "holo_fake_scenes_v3",
        "combined_sha256": CORPUS_SHA256,
        "documents": len(chunks),
        "queries": len(queries),
    }
    score_payload = {
        "schema_version": "1.0",
        "reranker_id": MODEL_ID,
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
        "pipeline_id": f"{args.profile_id}__{MODEL_ID}",
        "embedding_variant": args.profile_id,
        "embedding": embedding_identity,
        "candidate_ranking_sha256": candidate_provenance["ranking_sha256"],
        "reranker_id": MODEL_ID,
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-id", choices=PANEL_PROFILES, required=True)
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
