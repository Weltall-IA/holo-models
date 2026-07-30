"""Canonical full-corpus benchmark entrypoint for the two BitNet profiles."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .bitnet_parser import detect_bitnet_dim
from .bitnet_runner import bitnet_embed_queries_and_docs
from .metrics import DEFAULT_KS, evaluate_rankings
from .reranker_runtime import CORPUS_SHA256, atomic_json, load_frozen_dataset

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = PROJECT_ROOT / "results" / "gate3"
CANDIDATE_DIR = PROJECT_ROOT / "results" / "reranker" / "candidates"

PROFILE_CONFIG: dict[str, dict[str, Any]] = {
    "bitnet_06b_current": {
        "repository": "microsoft/bitnet-embedding-0.6b",
        "query_instruction": (
            "query: Given a query, retrieve scenes that answer it by matching events, "
            "dialogue, characters, emotional intention and context. "
        ),
        "gate_hit_rate_at_50": 0.94,
    },
    "bitnet_270m_current": {
        "repository": "microsoft/bitnet-embedding-270m",
        "query_instruction": (
            "query: Given a query, retrieve scenes that answer it by matching events, "
            "dialogue, characters, emotional intention and context. "
        ),
        "gate_hit_rate_at_50": 0.94,
    },
}


def _stable_rankings(
    document_embeddings: np.ndarray,
    query_embeddings: np.ndarray,
    chunk_ids: Sequence[str],
) -> tuple[list[list[str]], list[list[float]]]:
    if document_embeddings.ndim != 2 or query_embeddings.ndim != 2:
        raise ValueError("embedding matrices must be two-dimensional")
    if document_embeddings.shape[0] != len(chunk_ids):
        raise ValueError("document embedding count does not match chunk IDs")
    if document_embeddings.shape[1] != query_embeddings.shape[1]:
        raise ValueError("document and query dimensions differ")
    similarities = np.matmul(query_embeddings, document_embeddings.T)
    order = np.argsort(-similarities, axis=1, kind="stable")
    rankings = [[str(chunk_ids[index]) for index in row] for row in order]
    ranked_scores = [
        [float(similarities[query_index, index]) for index in row]
        for query_index, row in enumerate(order)
    ]
    return rankings, ranked_scores


def _ranking_sha256(
    query_ids: Sequence[str], rankings: Sequence[Sequence[str]]
) -> str:
    if len(query_ids) != len(rankings):
        raise ValueError("query ID and ranking counts differ")
    digest = hashlib.sha256()
    for query_id, ranking in zip(query_ids, rankings, strict=True):
        digest.update(str(query_id).encode("utf-8"))
        digest.update(b"\0")
        for chunk_id in ranking:
            digest.update(str(chunk_id).encode("utf-8"))
            digest.update(b"\0")
        digest.update(b"\n")
    return digest.hexdigest()


def build_candidate_payload(
    *,
    profile_id: str,
    queries: Sequence[Mapping[str, Any]],
    rankings: Sequence[Sequence[str]],
    ranked_scores: Sequence[Sequence[float]],
    candidate_top_k: int,
    model_identity: Mapping[str, Any],
    runtime: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the candidate schema consumed by ``load_candidate_payloads``."""
    if candidate_top_k < 50:
        raise ValueError("candidate_top_k must be at least 50")
    if not (len(queries) == len(rankings) == len(ranked_scores) == 150):
        raise ValueError("canonical candidate output requires exactly 150 queries")

    query_ids = [str(query["query_id"]) for query in queries]
    rows: list[dict[str, Any]] = []
    for query_id, ranking, scores in zip(
        query_ids, rankings, ranked_scores, strict=True
    ):
        if len(ranking) < candidate_top_k or len(scores) < candidate_top_k:
            raise ValueError(f"ranking for {query_id} has insufficient candidates")
        selected_ids = [str(chunk_id) for chunk_id in ranking[:candidate_top_k]]
        if len(selected_ids) != len(set(selected_ids)):
            raise ValueError(f"ranking for {query_id} contains duplicate chunk IDs")
        rows.append(
            {
                "query_id": query_id,
                "candidates": [
                    {"chunk_id": chunk_id, "score": float(score)}
                    for chunk_id, score in zip(
                        selected_ids, scores[:candidate_top_k], strict=True
                    )
                ],
            }
        )

    return {
        "schema_version": "1.0",
        "variant": profile_id,
        "embedding": {
            "profile_id": profile_id,
            **dict(model_identity),
        },
        "dataset": {
            "corpus_version": "holo_fake_scenes_v3",
            "corpus_sha256": CORPUS_SHA256,
            "documents": 600,
            "queries": 150,
        },
        "candidate_top_k": candidate_top_k,
        "ranking_sha256": _ranking_sha256(query_ids, rankings),
        "ranking_source": {
            "backend": runtime.get("backend"),
            "binary_sha256": runtime.get("binary_sha256"),
            "gguf_sha256": runtime.get("gguf_sha256"),
            "bitnet_commit": runtime.get("bitnet_commit"),
        },
        "queries": rows,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_candidate_payload(
    payload: Mapping[str, Any],
    *,
    expected_profile_id: str,
    expected_query_ids: Sequence[str],
    expected_top_k: int,
) -> None:
    if payload.get("variant") != expected_profile_id:
        raise ValueError("candidate variant mismatch")
    dataset = payload.get("dataset") or {}
    if dataset.get("corpus_sha256") != CORPUS_SHA256:
        raise ValueError("candidate corpus hash mismatch")
    if int(payload.get("candidate_top_k") or 0) < expected_top_k:
        raise ValueError("candidate top-k is insufficient")
    rows = list(payload.get("queries") or [])
    if [str(row.get("query_id")) for row in rows] != list(expected_query_ids):
        raise ValueError("candidate query order mismatch")
    for row in rows:
        candidates = list(row.get("candidates") or [])
        if len(candidates) < expected_top_k:
            raise ValueError(f"candidate row {row.get('query_id')} is too short")
        chunk_ids = [str(item.get("chunk_id")) for item in candidates[:expected_top_k]]
        if any(not chunk_id or chunk_id == "None" for chunk_id in chunk_ids):
            raise ValueError(f"candidate row {row.get('query_id')} has missing chunk ID")
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError(f"candidate row {row.get('query_id')} has duplicate chunk IDs")


def _load_hardware(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("hardware JSON must contain an object")
    return payload


def _candidate_profile_ids(payload: Mapping[str, Any]) -> set[str]:
    identities: set[str] = set()
    for key in ("variant", "id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            identities.add(value)
    embedding = payload.get("embedding")
    if isinstance(embedding, str) and embedding:
        identities.add(embedding)
    elif isinstance(embedding, Mapping):
        for key in ("profile_id", "id"):
            value = embedding.get(key)
            if isinstance(value, str) and value:
                identities.add(value)
    return identities


def remove_stale_candidate(path: Path, profile_id: str) -> bool:
    """Remove a candidate for a profile that no longer passes its embedding gate.

    Refuse to delete an unreadable file or an artifact that belongs to another
    profile. This prevents a failed rerun from leaving a stale candidate that can
    be consumed by a later reranker invocation.
    """
    if not path.exists():
        return False
    if not path.is_file():
        raise RuntimeError(f"candidate path is not a regular file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot validate stale candidate before removal: {path}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"stale candidate payload is not an object: {path}")
    identities = _candidate_profile_ids(payload)
    if profile_id not in identities:
        raise RuntimeError(
            f"refusing to remove candidate with mismatched identity: {path}; "
            f"expected {profile_id}, found {sorted(identities)}"
        )
    path.unlink()
    return True


def benchmark_profile(args: argparse.Namespace) -> dict[str, Any]:
    config = PROFILE_CONFIG[args.profile_id]
    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    if len(chunks) != 600 or len(queries) != 150:
        raise RuntimeError("frozen dataset counts do not match 600/150")

    documents = [str(chunk["text"]) for chunk in chunks]
    query_texts = [str(query["query"]) for query in queries]
    chunk_ids = [str(chunk["chunk_id"]) for chunk in chunks]
    query_embeddings, document_embeddings, runtime = bitnet_embed_queries_and_docs(
        query_texts,
        documents,
        profile_id=args.profile_id,
        gguf_path=args.gguf_path,
        bitnet_bin=args.bitnet_bin,
        bitnet_commit=args.bitnet_commit,
        query_instruction=str(config["query_instruction"]),
        timeout_seconds=args.timeout_seconds,
    )
    rankings, ranked_scores = _stable_rankings(
        document_embeddings, query_embeddings, chunk_ids
    )
    metrics = evaluate_rankings(queries, rankings, DEFAULT_KS)
    summary = metrics["summary"]
    gate_pass = (
        float(summary["HitRate@50"]) >= float(config["gate_hit_rate_at_50"])
        and int(summary["queries_without_relevant"]) <= 5
    )

    model_identity = {
        "repository": str(config["repository"]),
        "revision": args.revision,
        "file": args.gguf_path.name,
        "bytes": args.gguf_path.stat().st_size,
        "sha256": runtime["gguf_sha256"],
        "license": args.license,
        "quantization": "I2_S",
        "native_dimension": detect_bitnet_dim(args.profile_id),
        "configured_dimension": detect_bitnet_dim(args.profile_id),
    }
    completed_at = datetime.now(timezone.utc).isoformat()
    result_payload = {
        "schema_version": "1.0",
        "id": args.profile_id,
        "gate": 3,
        "status": "COMPLETED",
        "gate_result": "PASS" if gate_pass else "FAIL",
        "model": {"id": args.profile_id, **model_identity},
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
    result_path = args.result_output or RESULT_DIR / f"{args.profile_id}.json"
    atomic_json(result_path, result_payload)

    candidate_target = (
        args.candidate_output or CANDIDATE_DIR / f"{args.profile_id}.json"
    )
    candidate_path: Path | None = None
    stale_candidate_removed = False
    if gate_pass:
        candidate_payload = build_candidate_payload(
            profile_id=args.profile_id,
            queries=queries,
            rankings=rankings,
            ranked_scores=ranked_scores,
            candidate_top_k=args.candidate_top_k,
            model_identity=model_identity,
            runtime=runtime,
        )
        query_ids = [str(query["query_id"]) for query in queries]
        validate_candidate_payload(
            candidate_payload,
            expected_profile_id=args.profile_id,
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
                    [args.profile_id], args.candidate_top_k
                )
            finally:
                reranker_execution.CANDIDATE_DIR = original_candidate_dir
            if args.profile_id not in loaded:
                raise RuntimeError("canonical candidate loader did not return profile")
    else:
        stale_candidate_removed = remove_stale_candidate(
            candidate_target, args.profile_id
        )

    return {
        "status": "PASS" if gate_pass else "FAIL",
        "profile_id": args.profile_id,
        "result_path": str(result_path),
        "candidate_path": str(candidate_path) if candidate_path else None,
        "stale_candidate_removed": stale_candidate_removed,
        "metrics": summary,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-id", choices=sorted(PROFILE_CONFIG), required=True)
    parser.add_argument("--gguf-path", type=Path, required=True)
    parser.add_argument("--bitnet-bin", type=Path, required=True)
    parser.add_argument("--bitnet-commit", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--license", required=True)
    parser.add_argument("--candidate-top-k", type=int, default=50)
    parser.add_argument("--timeout-seconds", type=int, default=21600)
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
        print(f"BitNet benchmark blocked: {type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
