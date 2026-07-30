"""Canonical Qwen3-Reranker-0.6B evaluation for any admitted candidate profile."""
from __future__ import annotations

import argparse
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .artifact_portability import assert_portable_payload
from .lfm_qwen_benchmark import (
    CANDIDATE_TOP_K,
    QWEN_RERANKER_ID,
    RERANK_TOP_K,
    _validate_score_rows,
    validate_qwen_model,
)
from .reranker_backends import score_qwen_cross_encoder
from .reranker_metrics import candidate_ids, evaluate_reranker_effect, scores_to_rankings
from .reranker_runtime import (
    CORPUS_SHA256,
    DEFAULT_RERANK_INSTRUCTION,
    atomic_json,
    load_frozen_dataset,
    read_json,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _candidate_rows(
    payload: Mapping[str, Any],
    expected_query_ids: Sequence[str],
    expected_profile_id: str,
) -> list[list[dict[str, Any]]]:
    if payload.get("schema_version") != "1.0":
        raise ValueError("candidate schema mismatch")
    if payload.get("variant") != expected_profile_id:
        raise ValueError("candidate profile mismatch")
    dataset = payload.get("dataset") or {}
    if dataset.get("corpus_sha256") != CORPUS_SHA256:
        raise ValueError("candidate corpus mismatch")
    if int(payload.get("candidate_top_k") or 0) < CANDIDATE_TOP_K:
        raise ValueError("candidate top-k is insufficient")
    embedding = payload.get("embedding")
    if not isinstance(embedding, Mapping) or embedding.get("profile_id") != expected_profile_id:
        raise ValueError("candidate embedding identity mismatch")
    embedding_sha = str(embedding.get("sha256") or "")
    if len(embedding_sha) != 64:
        raise ValueError("candidate embedding SHA-256 is missing")
    ranking_sha256 = str(payload.get("ranking_sha256") or "")
    if len(ranking_sha256) != 64:
        raise ValueError("candidate ranking SHA-256 is missing")

    query_rows = list(payload.get("queries") or [])
    if [str(row.get("query_id")) for row in query_rows] != list(expected_query_ids):
        raise ValueError("candidate query order mismatch")

    rows: list[list[dict[str, Any]]] = []
    for row in query_rows:
        candidates = list(row.get("candidates") or [])[:CANDIDATE_TOP_K]
        if len(candidates) != CANDIDATE_TOP_K:
            raise ValueError(f"candidate row {row.get('query_id')} is incomplete")
        ids = [str(item.get("chunk_id")) for item in candidates]
        if any(not chunk_id or chunk_id == "None" for chunk_id in ids):
            raise ValueError("candidate row contains a missing chunk ID")
        if len(ids) != len(set(ids)):
            raise ValueError("candidate row contains duplicate chunk IDs")
        for position, item in enumerate(candidates, start=1):
            has_score = item.get("score") is not None
            has_rank = item.get("rank") is not None
            if not has_score and not has_rank:
                raise ValueError("candidate item has neither score nor rank")
            if has_score and not math.isfinite(float(item["score"])):
                raise ValueError("candidate row contains a non-finite score")
            if has_rank and int(item["rank"]) != position:
                raise ValueError("candidate row rank is inconsistent with order")
        rows.append(candidates)
    return rows


def benchmark_profile(args: argparse.Namespace) -> dict[str, Any]:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_DATASETS_OFFLINE", "1")

    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    query_ids = [str(query["query_id"]) for query in queries]
    candidate_payload = read_json(args.candidate)
    rows = _candidate_rows(candidate_payload, query_ids, args.profile_id)
    ids = candidate_ids(rows)
    chunk_text_by_id = {str(chunk["chunk_id"]): str(chunk["text"]) for chunk in chunks}
    missing = sorted({chunk_id for row in ids for chunk_id in row} - set(chunk_text_by_id))
    if missing:
        raise ValueError(f"candidate references unknown chunks: {missing[:3]}")

    model_path, model_identity = validate_qwen_model(args.model_path)
    score_rows, runtime = score_qwen_cross_encoder(
        model_path,
        queries,
        ids,
        chunk_text_by_id,
        "cuda",
        args.batch_size,
        args.instruction,
    )
    _validate_score_rows(rows, score_rows)
    if runtime.get("device") != "cuda":
        raise RuntimeError("Qwen reranker did not run on CUDA")
    if int(runtime.get("peak_vram_bytes") or 0) <= 0:
        raise RuntimeError("Qwen reranker has no positive CUDA memory evidence")
    if int(runtime.get("pairs") or 0) != len(queries) * CANDIDATE_TOP_K:
        raise RuntimeError("Qwen reranker pair count mismatch")

    completed_at = datetime.now(timezone.utc).isoformat()
    dataset = {
        "corpus_version": "holo_fake_scenes_v3",
        "combined_sha256": CORPUS_SHA256,
        "documents": len(chunks),
        "queries": len(queries),
    }
    score_payload = {
        "schema_version": "1.0",
        "reranker_id": QWEN_RERANKER_ID,
        "model": model_identity,
        "dataset": dataset,
        "candidate": {
            "variant": args.profile_id,
            "ranking_sha256": candidate_payload["ranking_sha256"],
            "candidate_top_k": CANDIDATE_TOP_K,
        },
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
        queries,
        ids,
        reranked_top,
        CANDIDATE_TOP_K,
    )
    try:
        score_artifact = str(
            args.score_output.resolve().relative_to(PROJECT_ROOT.resolve())
        )
    except ValueError:
        score_artifact = f"<external>/{args.score_output.name}"
    pipeline_payload = {
        "schema_version": "1.0",
        "pipeline_id": f"{args.profile_id}__{QWEN_RERANKER_ID}",
        "embedding_variant": args.profile_id,
        "embedding": dict(candidate_payload["embedding"]),
        "candidate_ranking_sha256": candidate_payload["ranking_sha256"],
        "reranker_id": QWEN_RERANKER_ID,
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
        "candidate_ranking_sha256": candidate_payload["ranking_sha256"],
        "score_output": str(args.score_output),
        "pipeline_output": str(args.pipeline_output),
        "pairs": runtime["pairs"],
        "base_HitRate@1": evaluation["base_metrics"]["summary"]["HitRate@1"],
        "reranked_HitRate@1": evaluation["reranked_metrics"]["summary"]["HitRate@1"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--score-output", type=Path, required=True)
    parser.add_argument("--pipeline-output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--instruction", default=DEFAULT_RERANK_INSTRUCTION)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    print(benchmark_profile(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
