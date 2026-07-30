"""Canonical Qwen3-Reranker-0.6B evaluation for the LFM2.5 candidate artifact."""
from __future__ import annotations

import argparse
import hashlib
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .artifact_portability import assert_portable_payload
from .lfm_benchmark import EXPECTED_GGUF_SHA256, PROFILE_ID
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
DEFAULT_CANDIDATE = (
    PROJECT_ROOT / "results" / "reranker" / "candidates" / f"{PROFILE_ID}.json"
)
DEFAULT_SCORE = (
    PROJECT_ROOT / "results" / "reranker" / "scores" / "qwen_local" / f"{PROFILE_ID}.json"
)
DEFAULT_PIPELINE = (
    PROJECT_ROOT / "results" / "reranker" / "pipelines" / "qwen_local" / f"{PROFILE_ID}.json"
)

QWEN_RERANKER_ID = "qwen_local"
QWEN_MODEL_ID = "qwen3_reranker_0.6B"
QWEN_REPOSITORY = "Qwen/Qwen3-Reranker-0.6B"
QWEN_REVISION = "e61197ed45024b0ed8a2d74b80b4d909f1255473"
QWEN_WEIGHT_FILE = "model.safetensors"
QWEN_WEIGHT_BYTES = 1191588280
QWEN_WEIGHT_SHA256 = "27cd75a405b9c1b46b59abfd88aaa209e6fed2a1972cde9b70e7659537c5e65b"
CANDIDATE_TOP_K = 50
RERANK_TOP_K = 20


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def validate_qwen_model(path: Path) -> tuple[Path, dict[str, Any]]:
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        raise FileNotFoundError(f"Qwen reranker directory is missing: {resolved}")
    if resolved.name != QWEN_REVISION:
        raise ValueError(
            f"Qwen snapshot revision mismatch: expected {QWEN_REVISION}, found {resolved.name}"
        )
    weight = resolved / QWEN_WEIGHT_FILE
    if not weight.is_file():
        raise FileNotFoundError(f"Qwen weight is missing: {weight}")
    if weight.stat().st_size != QWEN_WEIGHT_BYTES:
        raise ValueError("Qwen weight byte count mismatch")
    weight_sha256 = _sha256(weight)
    if weight_sha256 != QWEN_WEIGHT_SHA256:
        raise ValueError("Qwen weight SHA-256 mismatch")
    return resolved, {
        "id": QWEN_MODEL_ID,
        "repository": QWEN_REPOSITORY,
        "revision": QWEN_REVISION,
        "backend": "sentence-transformers.CrossEncoder",
        "weight_files": [
            {
                "file": QWEN_WEIGHT_FILE,
                "bytes": QWEN_WEIGHT_BYTES,
                "sha256": weight_sha256,
            }
        ],
    }


def _candidate_rows(
    payload: Mapping[str, Any], expected_query_ids: Sequence[str]
) -> list[list[dict[str, Any]]]:
    if payload.get("schema_version") != "1.0":
        raise ValueError("candidate schema mismatch")
    if payload.get("variant") != PROFILE_ID:
        raise ValueError("candidate profile mismatch")
    dataset = payload.get("dataset") or {}
    if dataset.get("corpus_sha256") != CORPUS_SHA256:
        raise ValueError("candidate corpus mismatch")
    if int(payload.get("candidate_top_k") or 0) < CANDIDATE_TOP_K:
        raise ValueError("candidate top-k is insufficient")
    embedding = payload.get("embedding") or {}
    if embedding.get("sha256") != EXPECTED_GGUF_SHA256:
        raise ValueError("candidate embedding identity mismatch")
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
        for item in candidates:
            if not math.isfinite(float(item.get("score"))):
                raise ValueError("candidate row contains a non-finite score")
        rows.append(candidates)
    return rows


def _validate_score_rows(
    rows: Sequence[Sequence[Mapping[str, Any]]],
    score_rows: Sequence[Mapping[str, float]],
) -> None:
    if len(rows) != len(score_rows):
        raise ValueError("Qwen score query count mismatch")
    for candidates, scores in zip(rows, score_rows, strict=True):
        expected = {str(item["chunk_id"]) for item in candidates}
        actual = set(map(str, scores))
        if actual != expected:
            raise ValueError("Qwen score candidate set mismatch")
        if any(not math.isfinite(float(score)) for score in scores.values()):
            raise ValueError("Qwen produced a non-finite score")


def benchmark_profile(args: argparse.Namespace) -> dict[str, Any]:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    query_ids = [str(query["query_id"]) for query in queries]
    candidate_payload = read_json(args.candidate)
    rows = _candidate_rows(candidate_payload, query_ids)
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
    score_payload = {
        "schema_version": "1.0",
        "reranker_id": QWEN_RERANKER_ID,
        "model": model_identity,
        "dataset": {
            "corpus_version": "holo_fake_scenes_v3",
            "combined_sha256": CORPUS_SHA256,
            "documents": len(chunks),
            "queries": len(queries),
        },
        "candidate": {
            "variant": PROFILE_ID,
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
        score_artifact = str(args.score_output.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        score_artifact = f"<external>/{args.score_output.name}"
    pipeline_payload = {
        "schema_version": "1.0",
        "pipeline_id": f"{PROFILE_ID}__{QWEN_RERANKER_ID}",
        "embedding_variant": PROFILE_ID,
        "embedding": dict(candidate_payload["embedding"]),
        "candidate_ranking_sha256": candidate_payload["ranking_sha256"],
        "reranker_id": QWEN_RERANKER_ID,
        "reranker": model_identity,
        "dataset": score_payload["dataset"],
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
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--score-output", type=Path, default=DEFAULT_SCORE)
    parser.add_argument("--pipeline-output", type=Path, default=DEFAULT_PIPELINE)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--instruction", default=DEFAULT_RERANK_INSTRUCTION)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    print(benchmark_profile(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
