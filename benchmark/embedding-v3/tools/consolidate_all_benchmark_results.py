#!/usr/bin/env python3
"""Generate one canonical summary file from every published benchmark artifact.

The raw pipeline files remain authoritative. This generator collects their complete
summary metrics, ranks all published pipelines, indexes every embedding/reranker,
and records verified local-only alternatives without mixing them into the published
leaderboard.
"""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

OMIT_KEYS = {
    "per_query",
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


def metric(summary: dict[str, Any], canonical: str) -> Any:
    for alias in METRIC_ALIASES[canonical]:
        if alias in summary:
            return summary[alias]
    return None


def compact(value: Any, *, depth: int = 0) -> Any:
    """Keep useful metadata while replacing large raw arrays with counts."""
    if depth > 6:
        return "<depth-limit>"
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, child in value.items():
            if key in OMIT_KEYS:
                if isinstance(child, (list, dict)):
                    out[f"{key}_omitted"] = len(child)
                continue
            out[key] = compact(child, depth=depth + 1)
        return out
    if isinstance(value, list):
        if len(value) > 50:
            return {"items_omitted": len(value)}
        return [compact(item, depth=depth + 1) for item in value]
    return value


def pipeline_record(path: Path) -> dict[str, Any]:
    data = load_json(path)
    reranker_dir = path.parent.name
    summary = data.get("metrics", {}).get("summary", {})
    if not summary:
        summary = data.get("summary", {})

    pipeline_id = data.get("id") or data.get("pipeline_id") or path.stem
    embedding = data.get("embedding_model") or data.get("embedding") or path.stem

    required = {
        "mrr_at_10": metric(summary, "mrr_at_10"),
        "hit_rate_at_1": metric(summary, "hit_rate_at_1"),
        "hit_rate_at_10": metric(summary, "hit_rate_at_10"),
        "ndcg_at_10": metric(summary, "ndcg_at_10"),
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise RuntimeError(f"{path}: missing required metrics: {', '.join(missing)}")

    normalized = {
        name: metric(summary, name)
        for name in METRIC_ALIASES
    }

    metadata = {
        key: compact(value)
        for key, value in data.items()
        if key not in {"metrics"}
    }

    return {
        "pipeline_id": pipeline_id,
        "embedding": embedding,
        "reranker": reranker_dir,
        "source_path": str(path.relative_to(ROOT)),
        "metrics": normalized,
        "metrics_summary_original": compact(summary),
        "metrics_by_query_type": compact(data.get("metrics", {}).get("by_query_type", {})),
        "metadata": metadata,
    }


def rank_key(item: dict[str, Any]) -> tuple[float, float, float, float, str]:
    m = item["metrics"]
    return (
        -(m.get("mrr_at_10") or -1.0),
        -(m.get("ndcg_at_10") or -1.0),
        -(m.get("hit_rate_at_1") or -1.0),
        -(m.get("hit_rate_at_10") or -1.0),
        item["pipeline_id"],
    )


def optional_json(path: Path) -> Any:
    return load_json(path) if path.exists() else None


def main() -> None:
    paths = sorted(PIPELINES_DIR.glob("*/*.json"))
    pipelines = [pipeline_record(path) for path in paths]

    counts = Counter(item["reranker"] for item in pipelines)
    embeddings = sorted({item["embedding"] for item in pipelines})

    if len(pipelines) != EXPECTED_PIPELINES:
        raise RuntimeError(
            f"expected {EXPECTED_PIPELINES} published pipelines, found {len(pipelines)}"
        )
    if len(embeddings) != EXPECTED_EMBEDDINGS:
        raise RuntimeError(
            f"expected {EXPECTED_EMBEDDINGS} unique embeddings, found {len(embeddings)}"
        )
    if dict(sorted(counts.items())) != dict(sorted(EXPECTED_BY_RERANKER.items())):
        raise RuntimeError(
            f"reranker counts differ: expected {EXPECTED_BY_RERANKER}, found {dict(counts)}"
        )

    pipelines.sort(key=rank_key)
    for index, item in enumerate(pipelines, start=1):
        item["rank_by_mrr_at_10"] = index

    by_embedding: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_reranker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in pipelines:
        by_embedding[item["embedding"]].append(item)
        by_reranker[item["reranker"]].append(item)

    embedding_index = []
    for embedding in sorted(by_embedding):
        items = sorted(by_embedding[embedding], key=rank_key)
        embedding_index.append(
            {
                "embedding": embedding,
                "pipeline_count": len(items),
                "rerankers": sorted(item["reranker"] for item in items),
                "best_published_pipeline": {
                    "pipeline_id": items[0]["pipeline_id"],
                    "reranker": items[0]["reranker"],
                    "rank_by_mrr_at_10": items[0]["rank_by_mrr_at_10"],
                    "metrics": items[0]["metrics"],
                },
            }
        )

    reranker_index = []
    for reranker in sorted(by_reranker):
        items = sorted(by_reranker[reranker], key=rank_key)
        reranker_index.append(
            {
                "reranker": reranker,
                "pipeline_count": len(items),
                "best_published_pipeline": {
                    "pipeline_id": items[0]["pipeline_id"],
                    "embedding": items[0]["embedding"],
                    "rank_by_mrr_at_10": items[0]["rank_by_mrr_at_10"],
                    "metrics": items[0]["metrics"],
                },
            }
        )

    stash_alternatives = [
        {
            "pipeline_id": "embeddinggemma_768_float32__qwen_local",
            "source": "stash@{0}:preserve-unstaged-pre-voyage",
            "published_source_path": "benchmark/embedding-v3/results/reranker/pipelines/qwen_local/embeddinggemma_768_float32.json",
            "status": "local_alternative_not_published",
            "metrics": {
                "mrr_at_10": 0.8172,
                "hit_rate_at_1": 0.7800,
                "hit_rate_at_10": 0.8933,
                "hit_rate_at_20": 1.0000,
                "ndcg_at_10": 0.8276,
            },
            "published_mrr_at_10": 0.7911,
            "delta_mrr_at_10": 0.0261,
        },
        {
            "pipeline_id": "voyage4_nano_1024_float32__qwen_local",
            "source": "stash@{0}:preserve-unstaged-pre-voyage",
            "published_source_path": "benchmark/embedding-v3/results/reranker/pipelines/qwen_local/voyage4_nano_1024_float32.json",
            "status": "local_alternative_not_published",
            "metrics": {
                "mrr_at_10": 0.8223,
                "hit_rate_at_1": 0.7867,
                "hit_rate_at_10": 0.8867,
                "hit_rate_at_20": 1.0000,
                "ndcg_at_10": 0.8303,
            },
            "published_mrr_at_10": 0.7835,
            "delta_mrr_at_10": 0.0388,
        },
        {
            "pipeline_id": "voyage4_nano_2048_float32__qwen_local",
            "source": "stash@{0}:preserve-unstaged-pre-voyage",
            "published_source_path": "benchmark/embedding-v3/results/reranker/pipelines/qwen_local/voyage4_nano_2048_float32.json",
            "status": "local_alternative_not_published",
            "metrics": {
                "mrr_at_10": 0.8220,
                "hit_rate_at_1": 0.7867,
                "hit_rate_at_10": 0.8867,
                "hit_rate_at_20": 0.9933,
                "ndcg_at_10": 0.8301,
            },
            "published_mrr_at_10": 0.7837,
            "delta_mrr_at_10": 0.0383,
        },
        {
            "pipeline_id": "voyage4_nano_2048_int8__qwen_local",
            "source": "stash@{0}:preserve-unstaged-pre-voyage",
            "published_source_path": "benchmark/embedding-v3/results/reranker/pipelines/qwen_local/voyage4_nano_2048_int8.json",
            "status": "local_alternative_not_published",
            "metrics": {
                "mrr_at_10": 0.7834,
                "hit_rate_at_1": 0.7533,
                "hit_rate_at_10": 0.8600,
                "hit_rate_at_20": 0.9467,
                "ndcg_at_10": 0.7953,
            },
            "published_mrr_at_10": 0.7835,
            "delta_mrr_at_10": -0.0001,
        },
        {
            "pipeline_id": "voyage_4_large_1024_float32__qwen_local",
            "source": "stash@{0}:preserve-unstaged-pre-voyage",
            "published_source_path": "benchmark/embedding-v3/results/reranker/pipelines/qwen_local/voyage_4_large_1024_float32.json",
            "status": "local_alternative_not_published",
            "metrics": {
                "mrr_at_10": 0.8201,
                "hit_rate_at_1": 0.7867,
                "hit_rate_at_10": 0.8867,
                "hit_rate_at_20": 0.9800,
                "ndcg_at_10": 0.8284,
            },
            "published_mrr_at_10": 0.7903,
            "delta_mrr_at_10": 0.0298,
        },
    ]

    document = {
        "schema_version": "1.0.0",
        "title": "Holo — Complete Consolidated Embedding and Reranker Benchmark Results",
        "repository": "Weltall-IA/holo-models",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": os.environ.get("GITHUB_SHA"),
        "canonical_scope": {
            "published_pipeline_artifacts": EXPECTED_PIPELINES,
            "unique_embeddings": EXPECTED_EMBEDDINGS,
            "rerankers": len(EXPECTED_BY_RERANKER),
            "corpus_documents": 600,
            "corpus_queries": 150,
            "corpus_sha256": "8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b",
            "candidate_top_k": 50,
            "rerank_top_k": 20,
        },
        "source_of_truth_policy": {
            "published_pipeline_metrics": "individual JSON artifacts under results/reranker/pipelines",
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
            "best_by_mrr_at_10": pipelines[0],
            "best_fully_local_recorded_reference": {
                "pipeline_id": "qwen3_embedding_4b_q8_0__qwen_local",
                "mrr_at_10": 0.8243,
                "hit_rate_at_10": 0.8867,
            },
            "selected_operational_pipeline": {
                "pipeline_id": "nomic_embed_text_v2_moe_q4__qwen_local",
                "reason": "quality-equivalent, 10.7x faster indexing, zero observed errors",
            },
        },
        "published_pipelines_ranked_by_mrr_at_10": pipelines,
        "embedding_index": embedding_index,
        "reranker_index": reranker_index,
        "local_only_alternative_artifacts": {
            "provenance": "verified read-only inventory supplied by the repository operator; stash content is not available through GitHub",
            "ranking_status": "excluded_from_published_ranking_until_provenance_and_protocol_are reconciled",
            "pipelines": stash_alternatives,
            "other_modified_artifacts": {
                "candidate_files": [
                    "embeddinggemma_768_float32.json",
                    "voyage4_nano_1024_float32.json",
                    "voyage4_nano_2048_float32.json",
                    "voyage4_nano_2048_int8.json",
                    "voyage_4_large_1024_float32.json",
                ],
                "score_artifact": "results/reranker/scores/qwen_local.json",
                "config_and_diagnostics": [
                    "config/models.json",
                    "gate2/diagnostics/selected_models_manifest.json",
                    "gate2/diagnostics/selected_models_summary.json",
                    "results/gate2/gte_multilingual_base.json",
                    "candidate_summary.json",
                ],
            },
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
        "operational_comparison_artifact": optional_json(
            BENCH / "results" / "operational" / "operational_comparison.json"
        ),
        "legacy_consolidated_document": optional_json(BENCH / "BENCHMARK_RESULTS.json"),
        "historical_append_only_registry": optional_json(
            BENCH / "BENCHMARK_RESULTS_REGISTRY.json"
        ),
        "notes": [
            "This file is the single consolidated lookup requested by the repository operator.",
            "It does not delete or replace raw artifacts.",
            "The five stash alternatives are preserved separately and are not silently promoted over published results.",
            "All 89 published pipeline summaries are read directly from their source JSON files during generation.",
        ],
    }

    OUTPUT.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {OUTPUT.relative_to(ROOT)}: {len(pipelines)} pipelines, "
        f"{len(embeddings)} embeddings, {len(counts)} rerankers"
    )


if __name__ == "__main__":
    main()
