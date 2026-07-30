"""Materialize canonical rank-only candidates from audited admission artifacts."""
from __future__ import annotations

import argparse
import hashlib
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .artifact_portability import assert_portable_payload
from .bitnet_benchmark import _ranking_sha256
from .metrics import DEFAULT_KS, evaluate_rankings
from .reranker_runtime import CORPUS_SHA256, atomic_json, load_frozen_dataset, read_json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_DIR = PROJECT_ROOT / "results" / "reranker" / "candidates"
CANDIDATE_TOP_K = 50

PROFILE_CONFIG: dict[str, dict[str, Any]] = {
    "nemotron_3_embed_1b_nvfp4": {
        "source": (
            PROJECT_ROOT
            / "results"
            / "nemotron_audit_1_0_5"
            / "admission_nvfp4_full_cached_20260723.json"
        ),
        "source_backend": "nvfp4",
        "runtime_backend": "vllm",
        "weight_file": "model.safetensors",
        "bytes": 1027789672,
        "sha256": "f2753954c89055eb679a45b7dfea27a3e05c04ecbdb1f4e6c086180fe8c32bc7",
        "license": "OpenMDW-1.1",
        "quantization": "NVFP4",
    },
    "nemotron_3_embed_1b_q4_k_m_gguf": {
        "source": (
            PROJECT_ROOT
            / "results"
            / "nemotron_audit_1_0_5"
            / "admission_gguf_full_20260723_attempt2.json"
        ),
        "source_backend": "gguf",
        "runtime_backend": "llama.cpp",
        "weight_file": "nemotron-3-embed-1b-q4_k_m.gguf",
        "bytes": 749352096,
        "sha256": "9a74166f51dbc280073748fa199bea49283bd21f7f9280f2dec2b4d975ddfd1d",
        "license": "OpenMDW-1.1",
        "quantization": "Q4_K_M",
    },
}

_COMPARABLE_SUMMARY_KEYS = tuple(
    [f"{metric}@{k}" for k in DEFAULT_KS for metric in ("HitRate", "Recall")]
    + ["MRR@10", "nDCG@10"]
)
_COMPARABLE_TYPE_KEYS = ("count", "HitRate@10", "MRR@10", "nDCG@10")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _assert_close(actual: Any, expected: Any, label: str) -> None:
    if isinstance(expected, int) and not isinstance(expected, bool):
        if int(actual) != expected:
            raise ValueError(f"{label} mismatch: expected {expected}, found {actual}")
        return
    if not math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"{label} mismatch: expected {expected}, found {actual}")


def validate_admission_source(
    profile_id: str,
    payload: Mapping[str, Any],
    chunks: Sequence[Mapping[str, Any]],
    queries: Sequence[Mapping[str, Any]],
) -> list[list[str]]:
    if profile_id not in PROFILE_CONFIG:
        raise ValueError(f"unsupported admission profile: {profile_id}")
    config = PROFILE_CONFIG[profile_id]
    if payload.get("state") != "EXECUTED":
        raise ValueError("admission artifact is not EXECUTED")
    if payload.get("backend") != config["source_backend"]:
        raise ValueError("admission backend mismatch")

    model = payload.get("model") or {}
    weight_name = Path(str(model.get("weight_file") or "")).name
    if weight_name != config["weight_file"]:
        raise ValueError("admission weight filename mismatch")
    for key in ("bytes", "sha256", "license"):
        if model.get(key) != config[key]:
            raise ValueError(f"admission model {key} mismatch")

    dataset = payload.get("dataset") or {}
    if dataset.get("combined_sha256") != CORPUS_SHA256:
        raise ValueError("admission corpus hash mismatch")
    if int(dataset.get("documents") or 0) != 600 or int(dataset.get("queries") or 0) != 150:
        raise ValueError("admission corpus counts mismatch")
    if dataset.get("document_prefix") != "passage: " or dataset.get("query_prefix") != "query: ":
        raise ValueError("admission prompt prefixes mismatch")

    evaluation = payload.get("evaluation") or {}
    metrics = evaluation.get("metrics") or {}
    per_query = list(metrics.get("per_query") or [])
    expected_query_ids = [str(query["query_id"]) for query in queries]
    if [str(row.get("query_id")) for row in per_query] != expected_query_ids:
        raise ValueError("admission per-query order mismatch")

    rankings = [
        [str(chunk_id) for chunk_id in row]
        for row in list(evaluation.get("rankings_top50") or [])
    ]
    if len(rankings) != len(queries):
        raise ValueError("admission ranking query count mismatch")
    known_chunks = {str(chunk["chunk_id"]) for chunk in chunks}
    for query_id, ranking in zip(expected_query_ids, rankings, strict=True):
        if len(ranking) != CANDIDATE_TOP_K:
            raise ValueError(f"admission ranking {query_id} is not top 50")
        if len(ranking) != len(set(ranking)):
            raise ValueError(f"admission ranking {query_id} contains duplicates")
        missing = [chunk_id for chunk_id in ranking if chunk_id not in known_chunks]
        if missing:
            raise ValueError(f"admission ranking {query_id} references unknown chunks")

    recomputed = evaluate_rankings(list(queries), rankings, DEFAULT_KS)
    source_summary = metrics.get("summary") or {}
    for key in _COMPARABLE_SUMMARY_KEYS:
        _assert_close(recomputed["summary"][key], source_summary[key], f"summary {key}")
    source_types = metrics.get("by_query_type") or {}
    for query_type, values in recomputed["by_query_type"].items():
        expected_values = source_types.get(query_type) or {}
        for key in _COMPARABLE_TYPE_KEYS:
            _assert_close(values[key], expected_values[key], f"{query_type} {key}")
    return rankings


def build_candidate_payload(
    profile_id: str,
    source_path: Path,
    source_payload: Mapping[str, Any],
    queries: Sequence[Mapping[str, Any]],
    rankings: Sequence[Sequence[str]],
) -> dict[str, Any]:
    config = PROFILE_CONFIG[profile_id]
    try:
        source_artifact = str(source_path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError as exc:
        raise ValueError("admission source must be inside the benchmark project") from exc
    query_ids = [str(query["query_id"]) for query in queries]
    dataset = source_payload["dataset"]
    payload = {
        "schema_version": "1.0",
        "variant": profile_id,
        "embedding": {
            "profile_id": profile_id,
            "backend": config["runtime_backend"],
            "weight_file": config["weight_file"],
            "bytes": config["bytes"],
            "sha256": config["sha256"],
            "license": config["license"],
            "quantization": config["quantization"],
            "document_prefix": dataset["document_prefix"],
            "query_prefix": dataset["query_prefix"],
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
            "artifact": source_artifact,
            "artifact_sha256": _sha256(source_path),
            "field": "evaluation.rankings_top50",
            "score_semantics": "rank_only",
            "source_backend": source_payload["backend"],
        },
        "queries": [
            {
                "query_id": query_id,
                "candidates": [
                    {"chunk_id": str(chunk_id), "rank": rank}
                    for rank, chunk_id in enumerate(ranking, start=1)
                ],
            }
            for query_id, ranking in zip(query_ids, rankings, strict=True)
        ],
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    assert_portable_payload(payload)
    return payload


def materialize_profile(
    profile_id: str,
    *,
    source: Path | None = None,
    output: Path | None = None,
) -> dict[str, Any]:
    config = PROFILE_CONFIG[profile_id]
    source_path = source or Path(config["source"])
    output_path = output or CANDIDATE_DIR / f"{profile_id}.json"
    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    source_payload = read_json(source_path)
    rankings = validate_admission_source(profile_id, source_payload, chunks, queries)
    candidate = build_candidate_payload(
        profile_id, source_path, source_payload, queries, rankings
    )
    atomic_json(output_path, candidate)
    return {
        "status": "PASS",
        "profile_id": profile_id,
        "source": str(source_path),
        "output": str(output_path),
        "ranking_sha256": candidate["ranking_sha256"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-id", choices=sorted(PROFILE_CONFIG), required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    print(
        materialize_profile(
            args.profile_id,
            source=args.source,
            output=args.output,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
