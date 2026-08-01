#!/usr/bin/env python3
"""Regenerate the single canonical embedding and reranker benchmark document."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from holo_benchmark.artifact_portability import (
    assert_portable_payload,
    sanitize_host_payload,
)

EXPECTED_PIPELINE_COUNT = 126
EXPECTED_PIPELINE_EMBEDDINGS = 39
EXPECTED_RAW_PROFILE_COUNT = 42
EXPECTED_RERANKER_COUNTS = {
    "ettin_reranker_150m_v1": 14,
    "ettin_reranker_68m_v1": 14,
    "jina_reranker_v3_noncommercial": 12,
    "kalm_reranker_v1_nano": 12,
    "kalm_reranker_v1_small": 12,
    "lamar_600m": 1,
    "llama_nemotron_rerank_1b_v2": 1,
    "mxbai_rerank_base_v2": 9,
    "querit_reranker_4b": 12,
    "qwen_local": 39,
}
EXPECTED_RAW_SOURCE_COUNTS = {
    "gate2": 11,
    "gate3": 22,
    "historical_raw_none": 5,
    "nemotron_admission": 2,
    "voyage_raw": 2,
}
REQUIRED_RAW_PROFILE_IDS = {
    "bitnet_06b_current",
    "bitnet_270m_current",
    "lfm_25_embedding_350m_q4_k_m_official",
    "qwen3_embedding_4b_q8_0",
}
STRICT_CANONICAL_RERANKERS = {
    "llama_nemotron_rerank_1b_v2",
    "mxbai_rerank_base_v2",
}

METRIC_ALIASES = {
    "hit_rate_at_1": ("HitRate@1", "hit_rate_at_1", "hr1", "hit1"),
    "hit_rate_at_3": ("HitRate@3", "hit_rate_at_3", "hr3"),
    "hit_rate_at_5": ("HitRate@5", "hit_rate_at_5", "hr5"),
    "hit_rate_at_10": ("HitRate@10", "hit_rate_at_10", "hr10"),
    "hit_rate_at_20": ("HitRate@20", "hit_rate_at_20", "hr20"),
    "mrr_at_10": ("MRR@10", "mrr_at_10", "mrr10"),
    "ndcg_at_10": ("nDCG@10", "ndcg_at_10", "ndcg10"),
    "hard_negative_error_rate": (
        "hard_negative_error_rate",
        "HardNegativeErrorRate",
    ),
}
REQUIRED_METRICS = (
    "mrr_at_10",
    "hit_rate_at_1",
    "hit_rate_at_10",
)
OMIT_KEYS = {
    "per_query",
    "per_query_effect",
    "queries",
    "scores",
    "rankings",
    "candidates",
    "documents",
    "results",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def pick(mapping: Mapping[str, Any], canonical: str) -> Any:
    for alias in METRIC_ALIASES[canonical]:
        if alias in mapping:
            return mapping[alias]
    return None


def normalize_metrics(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {name: pick(summary, name) for name in METRIC_ALIASES}


def missing_required(metrics: Mapping[str, Any]) -> list[str]:
    return [name for name in REQUIRED_METRICS if metrics.get(name) is None]


def compact(value: Any, depth: int = 0) -> Any:
    if depth > 8:
        return "<depth-limit>"
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, child in value.items():
            key = str(key)
            if key in OMIT_KEYS:
                if isinstance(child, (list, tuple, dict)):
                    result[f"{key}_omitted"] = len(child)
                continue
            result[key] = compact(child, depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        if len(value) > 50:
            return {"items_omitted": len(value)}
        return [compact(item, depth + 1) for item in value]
    return value


def metric_container(
    data: Mapping[str, Any],
    *,
    pipeline: bool,
) -> tuple[str, Mapping[str, Any], Mapping[str, Any]]:
    evaluation = data.get("evaluation")
    if pipeline and isinstance(evaluation, Mapping):
        reranked = evaluation.get("reranked_metrics")
        if isinstance(reranked, Mapping):
            summary = reranked.get("summary")
            if not isinstance(summary, Mapping):
                raise ValueError("pipeline reranked_metrics.summary is missing")
            return "$.evaluation.reranked_metrics.summary", summary, reranked

    preferred: Sequence[tuple[str, Any, Any]] = (
        (
            "$.metrics.summary",
            data.get("metrics", {}).get("summary")
            if isinstance(data.get("metrics"), Mapping)
            else None,
            data.get("metrics"),
        ),
        ("$.summary", data.get("summary"), data),
        ("$.metrics", data.get("metrics"), data.get("metrics")),
        ("$.metrics_summary", data.get("metrics_summary"), data),
    )
    for path, summary, container in preferred:
        if not isinstance(summary, Mapping):
            continue
        metrics = normalize_metrics(summary)
        if not missing_required(metrics):
            return (
                path,
                summary,
                container if isinstance(container, Mapping) else {},
            )
    raise ValueError("complete metric summary was not found")


def pipeline_embedding_id(data: Mapping[str, Any], path: Path) -> str:
    value = data.get("embedding_variant") or data.get("embedding_model")
    if isinstance(value, str) and value:
        return value
    embedding = data.get("embedding")
    if isinstance(embedding, str) and embedding:
        return embedding
    if isinstance(embedding, Mapping):
        for key in ("profile_id", "id", "model_id"):
            candidate = embedding.get(key)
            if isinstance(candidate, str) and candidate:
                return candidate
    return path.stem


def validate_strict_pipeline(
    data: Mapping[str, Any],
    reranker: str,
) -> None:
    if reranker not in STRICT_CANONICAL_RERANKERS:
        return
    evaluation = data.get("evaluation")
    if not isinstance(evaluation, Mapping):
        raise ValueError(f"{reranker} pipeline has no evaluation object")
    base = evaluation.get("base_metrics")
    reranked = evaluation.get("reranked_metrics")
    if not isinstance(base, Mapping) or not isinstance(reranked, Mapping):
        raise ValueError(f"{reranker} pipeline lacks base/reranked metrics")
    for label, section in (("base", base), ("reranked", reranked)):
        per_query = section.get("per_query")
        by_type = section.get("by_query_type")
        if not isinstance(per_query, list) or len(per_query) != 150:
            raise ValueError(
                f"{reranker} {label} per_query must contain 150 rows"
            )
        if not isinstance(by_type, Mapping) or len(by_type) != 7:
            raise ValueError(
                f"{reranker} {label} by_query_type must contain 7 types"
            )
    if int(data.get("candidate_top_k", 0)) != 50:
        raise ValueError(f"{reranker} candidate_top_k must be 50")
    if int(data.get("rerank_top_k", 0)) != 20:
        raise ValueError(f"{reranker} rerank_top_k must be 20")
    effects = evaluation.get("per_query_effect")
    if not isinstance(effects, list) or len(effects) != 150:
        raise ValueError(
            f"{reranker} per_query_effect must contain 150 rows"
        )


def pipeline_record(root: Path, path: Path) -> dict[str, Any]:
    data = load_json(path)
    if not isinstance(data, Mapping):
        raise ValueError("pipeline JSON root must be an object")
    reranker = str(data.get("reranker_id") or path.parent.name)
    validate_strict_pipeline(data, reranker)
    summary_path, summary, container = metric_container(data, pipeline=True)
    metrics = normalize_metrics(summary)
    missing = missing_required(metrics)
    if missing:
        raise ValueError(f"pipeline is missing metrics: {missing}")

    embedding = pipeline_embedding_id(data, path)
    pipeline_id = str(
        data.get("pipeline_id")
        or data.get("id")
        or f"{embedding}__{reranker}"
    )
    by_query_type = (
        container.get("by_query_type")
        if isinstance(container.get("by_query_type"), Mapping)
        else {}
    )
    return {
        "pipeline_id": pipeline_id,
        "embedding": embedding,
        "reranker": reranker,
        "source_path": path.relative_to(root).as_posix(),
        "metric_summary_path": summary_path,
        "metrics": metrics,
        "metrics_summary_original": compact(summary),
        "metrics_by_query_type": compact(by_query_type),
        "missing_required_metrics": [],
        "metadata": compact(data),
    }


def rank_key(item: Mapping[str, Any]) -> tuple[float, float, float, float, str]:
    metrics = item["metrics"]

    def number(name: str) -> float:
        value = metrics.get(name)
        return float(value) if isinstance(value, (int, float)) else -1.0

    return (
        -number("mrr_at_10"),
        -number("ndcg_at_10"),
        -number("hit_rate_at_1"),
        -number("hit_rate_at_10"),
        str(item.get("pipeline_id", item.get("profile_id", ""))),
    )


def raw_profile_id(data: Mapping[str, Any], path: Path) -> str:
    for value in (data.get("id"), data.get("profile_id")):
        if isinstance(value, str) and value:
            return value
    model = data.get("model")
    if isinstance(model, Mapping):
        value = model.get("id")
        if isinstance(value, str) and value:
            return value
    return path.stem


def raw_record(root: Path, path: Path, source_group: str) -> dict[str, Any]:
    data = load_json(path)
    if not isinstance(data, Mapping):
        raise ValueError("raw JSON root must be an object")
    summary_path, summary, _ = metric_container(data, pipeline=False)
    metrics = normalize_metrics(summary)
    missing = missing_required(metrics)
    if missing:
        raise ValueError(f"raw profile is missing metrics: {missing}")
    profile_id = raw_profile_id(data, path)
    metadata = {
        "model": compact(data.get("model")),
        "id": data.get("id"),
        "gate": data.get("gate"),
        "status": data.get("status") or data.get("state"),
        "gate_result": data.get("gate_result"),
        "dataset": compact(data.get("dataset")),
        "metric_summary_path": summary_path,
    }
    return {
        "profile_id": profile_id,
        "source_group": source_group,
        "source_path": path.relative_to(root).as_posix(),
        "metrics": metrics,
        "runtime": compact(data.get("runtime") or {}),
        "metadata": metadata,
    }


def direct_result_files(directory: Path) -> Iterable[Path]:
    for path in sorted(directory.glob("*.json")):
        if path.name == "summary.json":
            continue
        yield path


def build_indices(
    pipelines: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped_embeddings: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_rerankers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in pipelines:
        grouped_embeddings[item["embedding"]].append(item)
        grouped_rerankers[item["reranker"]].append(item)

    embedding_index: list[dict[str, Any]] = []
    for embedding, items in sorted(grouped_embeddings.items()):
        ranked = sorted(items, key=rank_key)
        embedding_index.append(
            {
                "embedding": embedding,
                "pipeline_count": len(ranked),
                "rerankers": sorted(item["reranker"] for item in ranked),
                "best_published_pipeline": {
                    "pipeline_id": ranked[0]["pipeline_id"],
                    "rank_by_mrr_at_10": ranked[0]["rank_by_mrr_at_10"],
                    "metrics": ranked[0]["metrics"],
                },
            }
        )

    reranker_index: list[dict[str, Any]] = []
    for reranker, items in sorted(grouped_rerankers.items()):
        ranked = sorted(items, key=rank_key)
        reranker_index.append(
            {
                "reranker": reranker,
                "pipeline_count": len(ranked),
                "best_published_pipeline": {
                    "pipeline_id": ranked[0]["pipeline_id"],
                    "rank_by_mrr_at_10": ranked[0]["rank_by_mrr_at_10"],
                    "metrics": ranked[0]["metrics"],
                },
            }
        )
    return embedding_index, reranker_index


def current_commit(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    value = completed.stdout.strip()
    if len(value) != 40:
        raise RuntimeError("git rev-parse HEAD did not return a full SHA")
    return value


def build_document(
    root: Path,
    bench: Path,
    baseline: Mapping[str, Any],
    *,
    generated_at: str,
    source_commit: str,
    expected_pipeline_count: int = EXPECTED_PIPELINE_COUNT,
    expected_pipeline_embeddings: int = EXPECTED_PIPELINE_EMBEDDINGS,
    expected_raw_profile_count: int = EXPECTED_RAW_PROFILE_COUNT,
    expected_reranker_counts: Mapping[str, int] = EXPECTED_RERANKER_COUNTS,
    expected_raw_source_counts: Mapping[str, int] = EXPECTED_RAW_SOURCE_COUNTS,
    required_raw_profile_ids: set[str] = REQUIRED_RAW_PROFILE_IDS,
) -> dict[str, Any]:
    pipeline_dir = bench / "results" / "reranker" / "pipelines"
    pipeline_paths = sorted(pipeline_dir.glob("*/*.json"))
    pipelines = [pipeline_record(root, path) for path in pipeline_paths]
    counts = Counter(item["reranker"] for item in pipelines)
    embeddings = sorted({item["embedding"] for item in pipelines})
    pipelines.sort(key=rank_key)
    for rank, item in enumerate(pipelines, start=1):
        item["rank_by_mrr_at_10"] = rank

    existing_raw = baseline.get(
        "raw_embedding_profiles_ranked_by_mrr_at_10", []
    )
    raw_by_id: dict[str, dict[str, Any]] = {}
    if isinstance(existing_raw, list):
        for item in existing_raw:
            if not isinstance(item, Mapping):
                continue
            if item.get("source_group") in {"gate2", "gate3"}:
                continue
            profile_id = item.get("profile_id")
            if isinstance(profile_id, str) and profile_id:
                preserved = deepcopy(dict(item))
                preserved.pop("rank_by_mrr_at_10", None)
                raw_by_id[profile_id] = preserved

    for source_group in ("gate2", "gate3"):
        for path in direct_result_files(bench / "results" / source_group):
            record = raw_record(root, path, source_group)
            profile_id = record["profile_id"]
            if profile_id in raw_by_id:
                raise ValueError(f"duplicate raw profile id: {profile_id}")
            raw_by_id[profile_id] = record

    raw_profiles = list(raw_by_id.values())
    raw_profiles.sort(key=rank_key)
    for rank, item in enumerate(raw_profiles, start=1):
        item["rank_by_mrr_at_10"] = rank
    raw_source_counts = Counter(
        str(item["source_group"]) for item in raw_profiles
    )

    actual_counts = dict(sorted(counts.items()))
    actual_raw_counts = dict(sorted(raw_source_counts.items()))
    raw_ids = set(raw_by_id)
    checks = {
        f"pipeline_count_{expected_pipeline_count}": len(pipelines)
        == expected_pipeline_count,
        f"embedding_count_{expected_pipeline_embeddings}": len(embeddings)
        == expected_pipeline_embeddings,
        "reranker_counts_match": actual_counts
        == dict(sorted(expected_reranker_counts.items())),
        "parse_errors_zero": True,
        "missing_required_metrics_zero": True,
        "reranked_metric_selection_corrected": all(
            item["metric_summary_path"]
            == "$.evaluation.reranked_metrics.summary"
            for item in pipelines
            if item["reranker"] in STRICT_CANONICAL_RERANKERS
        ),
        f"raw_profile_count_{expected_raw_profile_count}": len(raw_profiles)
        == expected_raw_profile_count,
        "raw_source_counts_match": actual_raw_counts
        == dict(sorted(expected_raw_source_counts.items())),
        "required_raw_profiles_present": required_raw_profile_ids <= raw_ids,
        "raw_and_reranked_separated": True,
        "portable_payload": True,
    }

    embedding_index, reranker_index = build_indices(pipelines)
    local_pipelines = [
        item
        for item in pipelines
        if item["reranker"] != "voyage_rerank_2_5"
    ]

    replaced = {
        "schema_version",
        "title",
        "repository",
        "generated_at",
        "source_commit",
        "validation",
        "canonical_scope",
        "source_of_truth_policy",
        "inventory",
        "leaders_published",
        "published_pipelines_ranked_by_mrr_at_10",
        "embedding_index",
        "reranker_index",
        "notes",
        "correction",
        "raw_embedding_profiles_ranked_by_mrr_at_10",
        "raw_embedding_profiles_by_id",
    }
    document = {
        key: deepcopy(value)
        for key, value in baseline.items()
        if key not in replaced
    }
    document.update(
        {
            "schema_version": "2.0.0",
            "title": "Holo — Complete Consolidated Embedding and Reranker Benchmark Results",
            "repository": "Weltall-IA/holo-models",
            "generated_at": generated_at,
            "source_commit": source_commit,
            "validation": {
                "status": "PASS" if all(checks.values()) else "INCOMPLETE",
                "checks": checks,
                "parse_errors": [],
                "missing_required_metrics": [],
                "expected_reranker_counts": dict(
                    sorted(expected_reranker_counts.items())
                ),
                "actual_reranker_counts": actual_counts,
                "reranked_metric_paths": sum(
                    item["metric_summary_path"]
                    == "$.evaluation.reranked_metrics.summary"
                    for item in pipelines
                ),
                "raw_profile_count": len(raw_profiles),
                "raw_profile_source_counts": actual_raw_counts,
            },
            "canonical_scope": {
                "published_pipeline_artifacts": len(pipelines),
                "unique_embeddings": len(embeddings),
                "rerankers": len(counts),
                "corpus_documents": 600,
                "corpus_queries": 150,
                "corpus_sha256": "8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b",
                "candidate_top_k": 50,
                "rerank_top_k": 20,
                "published_reranked_pipeline_artifacts": len(pipelines),
                "raw_embedding_profiles": len(raw_profiles),
                "benchmark_records_total": len(pipelines) + len(raw_profiles),
            },
            "source_of_truth_policy": {
                "published_pipeline_metrics": "individual JSON artifacts under benchmark/embedding-v3/results/reranker/pipelines",
                "raw_artifacts_remain_authoritative": True,
                "published_and_stash_results_are_not_merged": True,
                "missing_values_are_never_estimated": True,
                "ranking_primary_metric": "MRR@10",
                "ranking_tie_breakers": [
                    "nDCG@10",
                    "HitRate@1",
                    "HitRate@10",
                    "pipeline_id",
                ],
                "raw_embedding_metrics": "Gate 2, Gate 3, Voyage raw, Nemotron admission, and historical reranker_id=none artifacts",
                "raw_and_reranked_are_ranked_separately": True,
            },
            "inventory": {
                "published_pipeline_count": len(pipelines),
                "unique_embedding_count": len(embeddings),
                "published_pipeline_count_by_reranker": actual_counts,
                "score_artifact_count": len(
                    list(
                        (bench / "results" / "reranker" / "scores").glob(
                            "*/*.json"
                        )
                    )
                ),
                "candidate_artifact_count": len(
                    list(
                        (bench / "results" / "reranker" / "candidates").glob(
                            "*.json"
                        )
                    )
                ),
            },
            "leaders_published": {
                "best_by_mrr_at_10": pipelines[0] if pipelines else None,
                "best_fully_local_recorded_reference": (
                    {
                        "pipeline_id": local_pipelines[0]["pipeline_id"],
                        "metrics": local_pipelines[0]["metrics"],
                    }
                    if local_pipelines
                    else None
                ),
                "selected_operational_pipeline": deepcopy(
                    baseline.get("leaders_published", {}).get(
                        "selected_operational_pipeline"
                    )
                ),
            },
            "published_pipelines_ranked_by_mrr_at_10": pipelines,
            "embedding_index": embedding_index,
            "reranker_index": reranker_index,
            "notes": [
                "Single consolidated lookup requested by the repository operator.",
                "No benchmark was rerun by the consolidation step.",
                "All published pipeline summaries are read from individual source JSON files.",
                "Raw embedding metrics and reranked pipeline metrics remain separate.",
                "The canonical document was regenerated only after the individual artifacts were closed.",
            ],
            "correction": {
                "reason": "Historical pipeline artifacts contain both base_metrics and reranked_metrics; ranking uses reranked_metrics.",
                "affected_scope": "published ranking and best-pipeline indices",
                "raw_artifacts_changed": False,
            },
            "raw_embedding_profiles_ranked_by_mrr_at_10": raw_profiles,
            "raw_embedding_profiles_by_id": {
                item["profile_id"]: item for item in raw_profiles
            },
        }
    )
    document = _reconcile_voyage_status(document, bench)
    document = sanitize_host_payload(document)
    assert_portable_payload(document)
    if document["validation"]["status"] != "PASS":
        failed = [name for name, passed in checks.items() if not passed]
        raise ValueError(f"canonical validation failed: {failed}")
    return document


def _reconcile_voyage_status(
    document: Mapping[str, Any],
    bench: Path,
) -> dict[str, Any]:
    """Make the Voyage Nemotron status block reference only existing files.

    The checkpoint is a transient git-ignored artifact under ``results/raw/``
    that is not part of the checkout.  Instead of leaving a broken reference,
    record the absence explicitly with a verifiable flag so tests can assert
    either existence or explicit handling of the missing checkpoint.
    """
    result = deepcopy(dict(document))
    block = result.get("voyage_nemotron_8b_status")
    if not isinstance(block, Mapping):
        return result
    status = str(block.get("status") or "")
    checkpoint = block.get("checkpoint")
    checkpoint_available = bool(checkpoint) and (bench / str(checkpoint)).is_file()
    score_artifact = block.get("score_artifact")
    score_available = bool(score_artifact) and (
        bench / str(score_artifact)
    ).is_file()
    reconciled = deepcopy(dict(block))
    if not checkpoint_available:
        reconciled["checkpoint"] = (
            str(checkpoint) if checkpoint and (bench / str(checkpoint)).is_file() else None
        )
        reconciled["checkpoint_available"] = False
        reconciled["checkpoint_missing_reason"] = (
            "transient git-ignored batch checkpoint absent from checkout"
        )
    else:
        reconciled["checkpoint_available"] = True
        reconciled.pop("checkpoint_missing_reason", None)
    if not score_available:
        reconciled["score_artifact"] = None
        reconciled["score_artifact_available"] = False
    else:
        reconciled["score_artifact_available"] = True
    if status == "COMPLETED_BATCH":
        reconciled["status_evidence_verified"] = score_available
    result["voyage_nemotron_8b_status"] = reconciled
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--generated-at")
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    bench = root / "benchmark" / "embedding-v3"
    output = args.output or (bench / "ALL_BENCHMARK_RESULTS.json")
    baseline = load_json(output)
    generated_at = args.generated_at or datetime.now(timezone.utc).isoformat()
    source_commit = args.source_commit or current_commit(root)
    document = build_document(
        root,
        bench,
        baseline,
        generated_at=generated_at,
        source_commit=source_commit,
    )
    if not args.validate_only:
        write_json(output, document)
    print(
        json.dumps(
            {
                "status": document["validation"]["status"],
                "output": output.relative_to(root).as_posix(),
                "pipelines": document["canonical_scope"][
                    "published_pipeline_artifacts"
                ],
                "embeddings": document["canonical_scope"][
                    "unique_embeddings"
                ],
                "rerankers": document["inventory"][
                    "published_pipeline_count_by_reranker"
                ],
                "raw_profiles": document["canonical_scope"][
                    "raw_embedding_profiles"
                ],
                "records_total": document["canonical_scope"][
                    "benchmark_records_total"
                ],
                "validate_only": args.validate_only,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
