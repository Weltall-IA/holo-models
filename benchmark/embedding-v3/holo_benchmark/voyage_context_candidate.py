"""Materialize a canonical voyage-context-4 candidate from local checkpoints."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .artifact_portability import assert_portable_payload
from .bitnet_benchmark import _ranking_sha256
from .gate2_worker import _rankings_from_embeddings
from .metrics import DEFAULT_KS, evaluate_rankings
from .reranker_runtime import CORPUS_SHA256, atomic_json, load_frozen_dataset, read_json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_ID = "voyage-context-4"
DIMENSION = 1024
CANDIDATE_TOP_K = 50
DEFAULT_DOCUMENTS_CHECKPOINT = (
    PROJECT_ROOT / "results" / "raw" / "voyage" / PROFILE_ID / "documents.json"
)
DEFAULT_QUERIES_CHECKPOINT = (
    PROJECT_ROOT / "results" / "raw" / "voyage" / PROFILE_ID / "queries.json"
)
DEFAULT_PUBLISHED_RESULT = PROJECT_ROOT / "results" / "voyage" / f"{PROFILE_ID}.json"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "results" / "reranker" / "candidates" / f"{PROFILE_ID}.json"
)

_SUMMARY_KEYS = tuple(
    [f"{metric}@{k}" for k in DEFAULT_KS for metric in ("HitRate", "Recall")]
    + [
        "MRR@10",
        "nDCG@10",
        "mean_first_relevant_rank",
        "median_first_relevant_rank",
        "queries_without_relevant",
        "hard_negative_error_rate",
    ]
)
_TYPE_KEYS = ("count", "HitRate@10", "MRR@10", "nDCG@10", "hard_negative_error_rate")
_PER_QUERY_KEYS = tuple(
    [f"{metric}@{k}" for k in DEFAULT_KS for metric in ("HitRate", "Recall")]
    + [
        "MRR@10",
        "nDCG@10",
        "first_relevant_rank",
        "relevant_ranks",
        "best_hard_negative_rank",
        "hard_negative_error",
    ]
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _portable_path(path: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return f"<external>/{resolved.name}"


def _assert_equal(actual: Any, expected: Any, label: str) -> None:
    if isinstance(expected, list):
        if list(actual) != expected:
            raise ValueError(f"{label} mismatch")
        return
    if expected is None or isinstance(expected, (str, bool)):
        if actual != expected:
            raise ValueError(f"{label} mismatch: expected {expected!r}, found {actual!r}")
        return
    if isinstance(expected, int) and not isinstance(expected, bool):
        if int(actual) != expected:
            raise ValueError(f"{label} mismatch: expected {expected}, found {actual}")
        return
    if not math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"{label} mismatch: expected {expected}, found {actual}")


def _checkpoint_matrix(
    path: Path,
    *,
    input_type: str,
    expected_ids: Sequence[str],
) -> tuple[Any, dict[str, Any]]:
    import numpy as np

    payload = read_json(path)
    if payload.get("schema_version") != "1.0":
        raise ValueError(f"{input_type} checkpoint schema mismatch")
    if payload.get("model") != PROFILE_ID:
        raise ValueError(f"{input_type} checkpoint model mismatch")
    if payload.get("input_type") != input_type:
        raise ValueError(f"{input_type} checkpoint input type mismatch")
    if int(payload.get("dimension") or 0) != DIMENSION:
        raise ValueError(f"{input_type} checkpoint dimension mismatch")

    rows = payload.get("rows")
    if not isinstance(rows, Mapping):
        raise ValueError(f"{input_type} checkpoint rows are missing")
    expected_set = set(expected_ids)
    actual_set = {str(item_id) for item_id in rows}
    if actual_set != expected_set:
        missing = sorted(expected_set - actual_set)
        unexpected = sorted(actual_set - expected_set)
        raise ValueError(
            f"{input_type} checkpoint ids mismatch: "
            f"missing={missing[:3]}, unexpected={unexpected[:3]}"
        )

    matrix = np.asarray([rows[item_id] for item_id in expected_ids], dtype=np.float32)
    if matrix.shape != (len(expected_ids), DIMENSION):
        raise ValueError(
            f"{input_type} checkpoint matrix shape mismatch: {matrix.shape}"
        )
    if not np.isfinite(matrix).all():
        raise ValueError(f"{input_type} checkpoint contains non-finite values")
    if np.any(np.linalg.norm(matrix, axis=1) == 0):
        raise ValueError(f"{input_type} checkpoint contains zero-norm vectors")
    return matrix, dict(payload)


def _matrix_sha256(item_ids: Sequence[str], matrix: Any) -> str:
    import numpy as np

    array = np.asarray(matrix, dtype="<f4")
    digest = hashlib.sha256()
    for item_id, row in zip(item_ids, array, strict=True):
        digest.update(str(item_id).encode("utf-8"))
        digest.update(b"\0")
        digest.update(row.tobytes(order="C"))
    return digest.hexdigest()


def _validate_published_result(
    payload: Mapping[str, Any],
    rankings: Sequence[Sequence[str]],
    queries: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    if payload.get("schema_version") != "1.0":
        raise ValueError("published Voyage result schema mismatch")
    model = payload.get("model") or {}
    expected_model = {
        "id": PROFILE_ID,
        "provider": "Voyage AI",
        "backend": "voyage-api",
        "endpoint": "Client.contextualized_embed",
        "dimension": DIMENSION,
        "dtype": "float",
        "auto_chunking": False,
    }
    for key, expected in expected_model.items():
        _assert_equal(model.get(key), expected, f"published model {key}")
    sdk_version = str(model.get("sdk_version") or "")
    if not sdk_version:
        raise ValueError("published Voyage SDK version is missing")

    dataset = payload.get("dataset") or {}
    if dataset.get("combined_sha256") != CORPUS_SHA256:
        raise ValueError("published Voyage corpus hash mismatch")
    if int(dataset.get("documents") or 0) != 600:
        raise ValueError("published Voyage document count mismatch")
    if int(dataset.get("queries") or 0) != 150:
        raise ValueError("published Voyage query count mismatch")

    recomputed = evaluate_rankings(list(queries), rankings, DEFAULT_KS)
    source_metrics = payload.get("metrics") or {}
    source_summary = source_metrics.get("summary") or {}
    for key in _SUMMARY_KEYS:
        _assert_equal(recomputed["summary"].get(key), source_summary.get(key), f"summary {key}")

    source_types = source_metrics.get("by_query_type") or {}
    if set(source_types) != set(recomputed["by_query_type"]):
        raise ValueError("published Voyage query-type set mismatch")
    for query_type, values in recomputed["by_query_type"].items():
        expected_values = source_types.get(query_type) or {}
        for key in _TYPE_KEYS:
            _assert_equal(values.get(key), expected_values.get(key), f"{query_type} {key}")

    source_per_query = list(source_metrics.get("per_query") or [])
    recomputed_per_query = list(recomputed.get("per_query") or [])
    if len(source_per_query) != len(queries):
        raise ValueError("published Voyage per-query count mismatch")
    for actual, expected in zip(recomputed_per_query, source_per_query, strict=True):
        _assert_equal(actual.get("query_id"), expected.get("query_id"), "per-query query_id")
        _assert_equal(actual.get("query_type"), expected.get("query_type"), "per-query query_type")
        _assert_equal(actual.get("difficulty"), expected.get("difficulty"), "per-query difficulty")
        for key in _PER_QUERY_KEYS:
            _assert_equal(actual.get(key), expected.get(key), f"{actual.get('query_id')} {key}")
    return recomputed


def _embedding_identity(
    published_model: Mapping[str, Any],
    document_vector_sha256: str,
    query_vector_sha256: str,
) -> str:
    material = {
        "profile_id": PROFILE_ID,
        "corpus_sha256": CORPUS_SHA256,
        "model": {
            "provider": published_model.get("provider"),
            "backend": published_model.get("backend"),
            "endpoint": published_model.get("endpoint"),
            "sdk_version": published_model.get("sdk_version"),
            "dimension": published_model.get("dimension"),
            "dtype": published_model.get("dtype"),
            "auto_chunking": published_model.get("auto_chunking"),
        },
        "document_vectors_sha256": document_vector_sha256,
        "query_vectors_sha256": query_vector_sha256,
    }
    encoded = json.dumps(
        material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def materialize_profile(
    *,
    documents_checkpoint: Path = DEFAULT_DOCUMENTS_CHECKPOINT,
    queries_checkpoint: Path = DEFAULT_QUERIES_CHECKPOINT,
    published_result: Path = DEFAULT_PUBLISHED_RESULT,
    output: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    chunk_ids = [str(chunk["chunk_id"]) for chunk in chunks]
    query_ids = [str(query["query_id"]) for query in queries]
    if len(chunk_ids) != 600 or len(query_ids) != 150:
        raise RuntimeError("frozen corpus counts do not match 600/150")

    document_matrix, _ = _checkpoint_matrix(
        documents_checkpoint,
        input_type="document",
        expected_ids=chunk_ids,
    )
    query_matrix, _ = _checkpoint_matrix(
        queries_checkpoint,
        input_type="query",
        expected_ids=query_ids,
    )
    rankings_full = _rankings_from_embeddings(document_matrix, query_matrix, chunk_ids)
    published_payload = read_json(published_result)
    _validate_published_result(published_payload, rankings_full, queries)
    rankings = [list(row[:CANDIDATE_TOP_K]) for row in rankings_full]

    document_vector_sha256 = _matrix_sha256(chunk_ids, document_matrix)
    query_vector_sha256 = _matrix_sha256(query_ids, query_matrix)
    model = dict(published_payload["model"])
    identity_sha256 = _embedding_identity(
        model, document_vector_sha256, query_vector_sha256
    )
    payload = {
        "schema_version": "1.0",
        "variant": PROFILE_ID,
        "embedding": {
            "profile_id": PROFILE_ID,
            "provider": model["provider"],
            "backend": model["backend"],
            "endpoint": model["endpoint"],
            "sdk_version": model["sdk_version"],
            "dimension": model["dimension"],
            "dtype": model["dtype"],
            "auto_chunking": model["auto_chunking"],
            "sha256": identity_sha256,
            "sha256_scope": "model_endpoint_and_effective_checkpoint_vectors",
            "identity_sha256": identity_sha256,
        },
        "dataset": {
            "corpus_version": "holo_fake_scenes_v3",
            "corpus_sha256": CORPUS_SHA256,
            "documents": 600,
            "queries": 150,
        },
        "candidate_top_k": CANDIDATE_TOP_K,
        "ranking_sha256": _ranking_sha256(query_ids, rankings),
        "ranking_source": {
            "documents_checkpoint": _portable_path(documents_checkpoint),
            "documents_checkpoint_sha256": _sha256(documents_checkpoint),
            "documents_vectors_sha256": document_vector_sha256,
            "queries_checkpoint": _portable_path(queries_checkpoint),
            "queries_checkpoint_sha256": _sha256(queries_checkpoint),
            "queries_vectors_sha256": query_vector_sha256,
            "published_result": _portable_path(published_result),
            "published_result_sha256": _sha256(published_result),
            "field": "checkpoint embeddings recomputed with cosine similarity",
            "score_semantics": "rank_only",
            "source_backend": model["backend"],
        },
        "queries": [
            {
                "query_id": query_id,
                "candidates": [
                    {"chunk_id": chunk_id, "rank": rank}
                    for rank, chunk_id in enumerate(ranking, start=1)
                ],
            }
            for query_id, ranking in zip(query_ids, rankings, strict=True)
        ],
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    assert_portable_payload(payload)
    atomic_json(output, payload)
    return {
        "status": "PASS",
        "profile_id": PROFILE_ID,
        "output": str(output),
        "ranking_sha256": payload["ranking_sha256"],
        "embedding_identity_sha256": identity_sha256,
        "documents_checkpoint_sha256": payload["ranking_source"][
            "documents_checkpoint_sha256"
        ],
        "queries_checkpoint_sha256": payload["ranking_source"][
            "queries_checkpoint_sha256"
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--documents-checkpoint", type=Path, default=DEFAULT_DOCUMENTS_CHECKPOINT
    )
    parser.add_argument(
        "--queries-checkpoint", type=Path, default=DEFAULT_QUERIES_CHECKPOINT
    )
    parser.add_argument("--published-result", type=Path, default=DEFAULT_PUBLISHED_RESULT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    print(
        materialize_profile(
            documents_checkpoint=args.documents_checkpoint,
            queries_checkpoint=args.queries_checkpoint,
            published_result=args.published_result,
            output=args.output,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
