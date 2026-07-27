#!/usr/bin/env python3
"""Correct the consolidated leaderboard using each pipeline's reranked metrics.

Some historical artifacts contain both evaluation.base_metrics and
 evaluation.reranked_metrics. The original consolidator selected the first
 summary recursively, which incorrectly ranked those pipelines by their raw
 embedding metrics. This tool always prefers reranked_metrics.summary.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
CANONICAL = ROOT / "benchmark/embedding-v3/ALL_BENCHMARK_RESULTS.json"

EXPECTED_RERANKERS = {
    "qwen_local": 32,
    "jina_reranker_v3_noncommercial": 12,
    "kalm_reranker_v1_small": 12,
    "kalm_reranker_v1_nano": 12,
    "querit_reranker_4b": 12,
    "voyage_rerank_2_5": 9,
}


def select_metrics(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
    evaluation = raw.get("evaluation")
    if isinstance(evaluation, dict):
        reranked = evaluation.get("reranked_metrics")
        if isinstance(reranked, dict) and isinstance(reranked.get("summary"), dict):
            return (
                reranked["summary"],
                reranked.get("by_query_type", {}),
                "$.evaluation.reranked_metrics.summary",
            )

    metrics = raw.get("metrics")
    if isinstance(metrics, dict) and isinstance(metrics.get("summary"), dict):
        return metrics["summary"], metrics.get("by_query_type", {}), "$.metrics.summary"

    reranked = raw.get("reranked_metrics")
    if isinstance(reranked, dict) and isinstance(reranked.get("summary"), dict):
        return reranked["summary"], reranked.get("by_query_type", {}), "$.reranked_metrics.summary"

    raise ValueError("no reranked/summary metric block found")


def normalized(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "hit_rate_at_1": summary.get("HitRate@1"),
        "hit_rate_at_3": summary.get("HitRate@3"),
        "hit_rate_at_5": summary.get("HitRate@5"),
        "hit_rate_at_10": summary.get("HitRate@10"),
        "hit_rate_at_20": summary.get("HitRate@20"),
        "mrr_at_10": summary.get("MRR@10"),
        "ndcg_at_10": summary.get("nDCG@10"),
        "hard_negative_error_rate": summary.get("hard_negative_error_rate"),
    }


def sort_key(entry: dict[str, Any]) -> tuple[Any, ...]:
    metrics = entry["metrics"]
    return (
        -float(metrics["mrr_at_10"]),
        -float(metrics["ndcg_at_10"]),
        -float(metrics["hit_rate_at_1"]),
        -float(metrics["hit_rate_at_10"]),
        entry["pipeline_id"],
    )


def index_best(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "pipeline_id": entry["pipeline_id"],
        "rank_by_mrr_at_10": entry["rank_by_mrr_at_10"],
        "metrics": entry["metrics"],
    }


def update_index(index: Any, field: str, grouped: dict[str, list[dict[str, Any]]]) -> None:
    if isinstance(index, list):
        for item in index:
            if not isinstance(item, dict):
                continue
            key = item.get(field) or item.get(f"{field}_id")
            if key not in grouped:
                continue
            best = grouped[key][0]
            replacement = index_best(best)
            replaced = False
            for best_key in ("best_published_pipeline", "best_pipeline"):
                if best_key in item:
                    item[best_key] = replacement
                    replaced = True
            if not replaced:
                item["best_published_pipeline"] = replacement
    elif isinstance(index, dict):
        for key, item in index.items():
            if key not in grouped or not isinstance(item, dict):
                continue
            best = grouped[key][0]
            replacement = index_best(best)
            replaced = False
            for best_key in ("best_published_pipeline", "best_pipeline"):
                if best_key in item:
                    item[best_key] = replacement
                    replaced = True
            if not replaced:
                item["best_published_pipeline"] = replacement


def main() -> None:
    data = json.loads(CANONICAL.read_text(encoding="utf-8"))
    entries = data["published_pipelines_ranked_by_mrr_at_10"]
    errors: list[str] = []
    reranked_metric_paths = 0

    for entry in entries:
        source = ROOT / entry["source_path"]
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
            summary, by_query, metric_path = select_metrics(raw)
            values = normalized(summary)
            missing = [
                name
                for name in ("hit_rate_at_1", "hit_rate_at_10", "mrr_at_10", "ndcg_at_10")
                if values.get(name) is None
            ]
            if missing:
                raise ValueError(f"missing required metrics: {missing}")
            entry["metrics"] = values
            entry["metrics_summary_original"] = summary
            entry["metrics_by_query_type"] = by_query
            entry["metric_summary_path"] = metric_path
            entry["missing_required_metrics"] = []
            if "reranked_metrics.summary" in metric_path:
                reranked_metric_paths += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{entry.get('pipeline_id')}: {type(exc).__name__}: {exc}")

    if errors:
        raise SystemExit("\n".join(errors))

    entries.sort(key=sort_key)
    for rank, entry in enumerate(entries, start=1):
        entry["rank_by_mrr_at_10"] = rank

    leader = entries[0]
    data["leaders_published"]["best_by_mrr_at_10"] = leader

    by_embedding: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_reranker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        by_embedding[entry["embedding"]].append(entry)
        by_reranker[entry["reranker"]].append(entry)

    update_index(data.get("embedding_index"), "embedding", by_embedding)
    update_index(data.get("reranker_index"), "reranker", by_reranker)

    actual_counts = Counter(entry["reranker"] for entry in entries)
    assert len(entries) == 89, len(entries)
    assert len(by_embedding) == 32, len(by_embedding)
    assert dict(actual_counts) == EXPECTED_RERANKERS, actual_counts
    assert reranked_metric_paths >= 14, reranked_metric_paths
    assert leader["pipeline_id"] == "embeddinggemma_768_float32__voyage_rerank_2_5", leader["pipeline_id"]
    assert abs(leader["metrics"]["mrr_at_10"] - 0.8264444444444444) < 1e-12

    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    data["validation"]["status"] = "PASS"
    data["validation"]["checks"]["reranked_metric_selection_corrected"] = True
    data["validation"]["reranked_metric_paths"] = reranked_metric_paths
    data["correction"] = {
        "reason": "Historical pipeline artifacts contain both base_metrics and reranked_metrics; ranking must use reranked_metrics.",
        "affected_scope": "published ranking and best-pipeline indices",
        "raw_artifacts_changed": False,
    }

    CANONICAL.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "pipelines": len(entries),
                "embeddings": len(by_embedding),
                "reranked_metric_paths": reranked_metric_paths,
                "leader": leader["pipeline_id"],
                "leader_mrr_at_10": leader["metrics"]["mrr_at_10"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
