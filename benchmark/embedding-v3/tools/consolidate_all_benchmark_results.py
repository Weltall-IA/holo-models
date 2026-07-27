#!/usr/bin/env python3
"""Generate one consolidated benchmark lookup from every published pipeline JSON."""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[3]
BENCH = ROOT / "benchmark" / "embedding-v3"
PIPELINES_DIR = BENCH / "results" / "reranker" / "pipelines"
OUTPUT = BENCH / "ALL_BENCHMARK_RESULTS.json"

EXPECTED_PIPELINES = 89
EXPECTED_EMBEDDINGS = 32
EXPECTED_BY_RERANKER = {
    "qwen_local": 32,
    "jina_reranker_v3_noncommercial": 12,
    "kalm_reranker_v1_small": 12,
    "kalm_reranker_v1_nano": 12,
    "querit_reranker_4b": 12,
    "voyage_rerank_2_5": 9,
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
REQUIRED = ("mrr_at_10", "hit_rate_at_1", "hit_rate_at_10", "ndcg_at_10")
OMIT_KEYS = {"per_query", "queries", "scores", "rankings", "candidates", "documents", "results"}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def pick(mapping: dict[str, Any], canonical: str) -> Any:
    for alias in METRIC_ALIASES[canonical]:
        if alias in mapping:
            return mapping[alias]
    return None


def metric_score(mapping: dict[str, Any]) -> int:
    return sum(pick(mapping, name) is not None for name in METRIC_ALIASES)


def walk_dicts(value: Any, path: str = "$", depth: int = 0) -> Iterator[tuple[str, dict[str, Any]]]:
    if depth > 7:
        return
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            if isinstance(child, (dict, list)):
                yield from walk_dicts(child, f"{path}.{key}", depth + 1)
    elif isinstance(value, list):
        for index, child in enumerate(value[:25]):
            if isinstance(child, (dict, list)):
                yield from walk_dicts(child, f"{path}[{index}]", depth + 1)


def find_metric_summary(data: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    preferred = [
        ("$.metrics.summary", data.get("metrics", {}).get("summary") if isinstance(data.get("metrics"), dict) else None),
        ("$.summary", data.get("summary")),
        ("$.metrics", data.get("metrics")),
        ("$.metrics_summary", data.get("metrics_summary")),
    ]
    candidates: list[tuple[int, int, str, dict[str, Any]]] = []
    for path, value in preferred:
        if isinstance(value, dict):
            candidates.append((metric_score(value), len(value), path, value))
    for path, mapping in walk_dicts(data):
        score = metric_score(mapping)
        if score:
            candidates.append((score, len(mapping), path, mapping))
    if not candidates:
        return None, {}
    _, _, path, mapping = max(candidates, key=lambda item: (item[0], item[1]))
    return path, mapping


def compact(value: Any, depth: int = 0) -> Any:
    if depth > 6:
        return "<depth-limit>"
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            if key in OMIT_KEYS:
                if isinstance(child, (list, dict)):
                    result[f"{key}_omitted"] = len(child)
                continue
            result[key] = compact(child, depth + 1)
        return result
    if isinstance(value, list):
        if len(value) > 50:
            return {"items_omitted": len(value)}
        return [compact(item, depth + 1) for item in value]
    return value


def pipeline_record(path: Path) -> dict[str, Any]:
    data = load_json(path)
    summary_path, summary = find_metric_summary(data)
    normalized = {name: pick(summary, name) for name in METRIC_ALIASES}
    missing = [name for name in REQUIRED if normalized.get(name) is None]
    embedding = data.get("embedding_model") or data.get("embedding") or path.stem
    pipeline_id = data.get("id") or data.get("pipeline_id") or f"{embedding}__{path.parent.name}"

    metadata = {
        key: compact(value)
        for key, value in data.items()
        if key not in {"metrics"}
    }
    by_query_type = {}
    metrics_value = data.get("metrics")
    if isinstance(metrics_value, dict) and isinstance(metrics_value.get("by_query_type"), dict):
        by_query_type = compact(metrics_value["by_query_type"])

    return {
        "pipeline_id": pipeline_id,
        "embedding": embedding,
        "reranker": path.parent.name,
        "source_path": str(path.relative_to(ROOT)),
        "metric_summary_path": summary_path,
        "metrics": normalized,
        "metrics_summary_original": compact(summary),
        "metrics_by_query_type": by_query_type,
        "missing_required_metrics": missing,
        "metadata": metadata,
    }


def rank_key(item: dict[str, Any]) -> tuple[float, float, float, float, str]:
    metrics = item["metrics"]
    def number(name: str) -> float:
        value = metrics.get(name)
        return float(value) if isinstance(value, (int, float)) else -1.0
    return (-number("mrr_at_10"), -number("ndcg_at_10"), -number("hit_rate_at_1"), -number("hit_rate_at_10"), item["pipeline_id"])


def optional_json(path: Path) -> Any:
    try:
        return load_json(path) if path.exists() else None
    except (OSError, json.JSONDecodeError) as exc:
        return {"source_path": str(path.relative_to(ROOT)), "load_error": str(exc)}


def stash_alternatives() -> list[dict[str, Any]]:
    return [
        {
            "pipeline_id": "embeddinggemma_768_float32__qwen_local",
            "metrics": {"mrr_at_10": 0.8172, "hit_rate_at_1": 0.7800, "hit_rate_at_10": 0.8933, "hit_rate_at_20": 1.0000, "ndcg_at_10": 0.8276},
            "published_mrr_at_10": 0.7911,
            "delta_mrr_at_10": 0.0261,
        },
        {
            "pipeline_id": "voyage4_nano_1024_float32__qwen_local",
            "metrics": {"mrr_at_10": 0.8223, "hit_rate_at_1": 0.7867, "hit_rate_at_10": 0.8867, "hit_rate_at_20": 1.0000, "ndcg_at_10": 0.8303},
            "published_mrr_at_10": 0.7835,
            "delta_mrr_at_10": 0.0388,
        },
        {
            "pipeline_id": "voyage4_nano_2048_float32__qwen_local",
            "metrics": {"mrr_at_10": 0.8220, "hit_rate_at_1": 0.7867, "hit_rate_at_10": 0.8867, "hit_rate_at_20": 0.9933, "ndcg_at_10": 0.8301},
            "published_mrr_at_10": 0.7837,
            "delta_mrr_at_10": 0.0383,
        },
        {
            "pipeline_id": "voyage4_nano_2048_int8__qwen_local",
            "metrics": {"mrr_at_10": 0.7834, "hit_rate_at_1": 0.7533, "hit_rate_at_10": 0.8600, "hit_rate_at_20": 0.9467, "ndcg_at_10": 0.7953},
            "published_mrr_at_10": 0.7835,
            "delta_mrr_at_10": -0.0001,
        },
        {
            "pipeline_id": "voyage_4_large_1024_float32__qwen_local",
            "metrics": {"mrr_at_10": 0.8201, "hit_rate_at_1": 0.7867, "hit_rate_at_10": 0.8867, "hit_rate_at_20": 0.9800, "ndcg_at_10": 0.8284},
            "published_mrr_at_10": 0.7903,
            "delta_mrr_at_10": 0.0298,
        },
    ]


def main() -> None:
    parse_errors: list[dict[str, str]] = []
    pipelines: list[dict[str, Any]] = []
    for path in sorted(PIPELINES_DIR.glob("*/*.json")):
        try:
            pipelines.append(pipeline_record(path))
        except Exception as exc:  # diagnostic collection; validation reports failure
            parse_errors.append({"source_path": str(path.relative_to(ROOT)), "error": f"{type(exc).__name__}: {exc}"})

    counts = Counter(item["reranker"] for item in pipelines)
    embeddings = sorted({item["embedding"] for item in pipelines})
    missing_metrics = [
        {"pipeline_id": item["pipeline_id"], "source_path": item["source_path"], "missing": item["missing_required_metrics"]}
        for item in pipelines
        if item["missing_required_metrics"]
    ]

    pipelines.sort(key=rank_key)
    for rank, item in enumerate(pipelines, start=1):
        item["rank_by_mrr_at_10"] = rank

    grouped_embeddings: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_rerankers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in pipelines:
        grouped_embeddings[item["embedding"]].append(item)
        grouped_rerankers[item["reranker"]].append(item)

    embedding_index = []
    for embedding, items in sorted(grouped_embeddings.items()):
        ranked = sorted(items, key=rank_key)
        embedding_index.append({
            "embedding": embedding,
            "pipeline_count": len(ranked),
            "rerankers": sorted(item["reranker"] for item in ranked),
            "best_published_pipeline": {
                "pipeline_id": ranked[0]["pipeline_id"],
                "rank_by_mrr_at_10": ranked[0]["rank_by_mrr_at_10"],
                "metrics": ranked[0]["metrics"],
            },
        })

    reranker_index = []
    for reranker, items in sorted(grouped_rerankers.items()):
        ranked = sorted(items, key=rank_key)
        reranker_index.append({
            "reranker": reranker,
            "pipeline_count": len(ranked),
            "best_published_pipeline": {
                "pipeline_id": ranked[0]["pipeline_id"],
                "rank_by_mrr_at_10": ranked[0]["rank_by_mrr_at_10"],
                "metrics": ranked[0]["metrics"],
            },
        })

    validation_checks = {
        "pipeline_count_89": len(pipelines) == EXPECTED_PIPELINES,
        "embedding_count_32": len(embeddings) == EXPECTED_EMBEDDINGS,
        "reranker_counts_match": dict(sorted(counts.items())) == dict(sorted(EXPECTED_BY_RERANKER.items())),
        "parse_errors_zero": not parse_errors,
        "missing_required_metrics_zero": not missing_metrics,
    }

    document = {
        "schema_version": "1.0.0",
        "title": "Holo — Complete Consolidated Embedding and Reranker Benchmark Results",
        "repository": "Weltall-IA/holo-models",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": os.environ.get("GITHUB_SHA"),
        "validation": {
            "status": "PASS" if all(validation_checks.values()) else "INCOMPLETE",
            "checks": validation_checks,
            "parse_errors": parse_errors,
            "missing_required_metrics": missing_metrics,
            "expected_reranker_counts": EXPECTED_BY_RERANKER,
            "actual_reranker_counts": dict(sorted(counts.items())),
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
        },
        "source_of_truth_policy": {
            "published_pipeline_metrics": "individual JSON artifacts under benchmark/embedding-v3/results/reranker/pipelines",
            "raw_artifacts_remain_authoritative": True,
            "published_and_stash_results_are_not_merged": True,
            "missing_values_are_never_estimated": True,
            "ranking_primary_metric": "MRR@10",
            "ranking_tie_breakers": ["nDCG@10", "HitRate@1", "HitRate@10", "pipeline_id"],
        },
        "inventory": {
            "published_pipeline_count": len(pipelines),
            "unique_embedding_count": len(embeddings),
            "published_pipeline_count_by_reranker": dict(sorted(counts.items())),
            "score_artifacts_reported": 3,
            "candidate_files_reported_approx": 20,
            "unmerged_remote_branches_reported": [
                "origin/agent/record-embedding-benchmark-results",
                "origin/agent/record-top5-reranker-results",
            ],
            "active_stash_reported": "stash@{0}:preserve-unstaged-pre-voyage",
        },
        "leaders_published": {
            "best_by_mrr_at_10": pipelines[0] if pipelines else None,
            "best_fully_local_recorded_reference": {"pipeline_id": "qwen3_embedding_4b_q8_0__qwen_local", "mrr_at_10": 0.8243, "hit_rate_at_10": 0.8867},
            "selected_operational_pipeline": {"pipeline_id": "nomic_embed_text_v2_moe_q4__qwen_local", "reason": "quality-equivalent, 10.7x faster indexing, zero observed errors"},
        },
        "published_pipelines_ranked_by_mrr_at_10": pipelines,
        "embedding_index": embedding_index,
        "reranker_index": reranker_index,
        "local_only_alternative_artifacts": {
            "source": "operator-supplied verified read-only inventory",
            "status": "excluded_from_published_ranking_until_provenance_and_protocol_are_reconciled",
            "stash": "stash@{0}:preserve-unstaged-pre-voyage",
            "pipelines": stash_alternatives(),
            "updated_candidate_files": [
                "embeddinggemma_768_float32.json",
                "voyage4_nano_1024_float32.json",
                "voyage4_nano_2048_float32.json",
                "voyage4_nano_2048_int8.json",
                "voyage_4_large_1024_float32.json",
            ],
            "updated_score_artifact": "results/reranker/scores/qwen_local.json",
        },
        "operational_smoke_test_user_verified": {
            "pipeline": "nomic_embed_text_v2_moe_q4__qwen_local",
            "retrieval_top_k": 50,
            "rerank_top_k": 20,
            "queries_completed": 150,
            "errors": 0,
            "latency_p50_ms": 4584.16,
            "latency_p95_ms": 4825.65,
            "latency_max_ms": 4915.86,
            "qps": 0.218,
            "peak_vram_gb": 13.06,
            "peak_ram_gb": 4.74,
            "status": "PASS",
            "provenance": "verified result supplied by the repository operator after PR #12",
        },
        "operational_comparison_artifact": optional_json(BENCH / "results" / "operational" / "operational_comparison.json"),
        "legacy_consolidated_document": optional_json(BENCH / "BENCHMARK_RESULTS.json"),
        "historical_append_only_registry": optional_json(BENCH / "BENCHMARK_RESULTS_REGISTRY.json"),
        "notes": [
            "Single consolidated lookup requested by the repository operator.",
            "No benchmark was rerun and no raw artifact was deleted or overwritten.",
            "All published pipeline summaries are read directly from individual source JSON files.",
            "The five stash alternatives remain separate from the published ranking.",
        ],
    }

    OUTPUT.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT.relative_to(ROOT)),
        "pipelines": len(pipelines),
        "embeddings": len(embeddings),
        "rerankers": dict(sorted(counts.items())),
        "parse_errors": len(parse_errors),
        "missing_required_metrics": len(missing_metrics),
        "validation": document["validation"]["status"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
