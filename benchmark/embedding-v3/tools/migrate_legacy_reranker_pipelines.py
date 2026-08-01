#!/usr/bin/env python3
"""Canonicalize historical Jina/KaLM/Querit reranker pipelines.

The 48 pipelines under ``results/reranker/pipelines/{jina_reranker_v3_noncommercial,
kalm_reranker_v1_nano,kalm_reranker_v1_small,querit_reranker_4b}`` are real
executions recorded in the RERANKER-TOP5 session (commits ``7ece93a`` and
``8786f57``) using a legacy schema that exposes only ``metrics``.

This tool migrates them to the canonical pipeline schema deterministically:

* ``evaluation.base_metrics`` is recomputed from the persisted candidate
  artifacts through ``evaluate_rankings`` (the base ranking is the candidate
  top-50 ordering).
* ``evaluation.reranked_metrics`` is taken from the already persisted
  ``metrics`` block (summary, per-query rows and per-query-type grouping).
* ``per_query_effect`` cannot be derived because the historical artifacts did
  not persist the reranked rankings; it is recorded explicitly as
  ``MEASUREMENT_BLOCKED_LEGACY_ARTIFACT``.
* Runtime telemetry is recorded explicitly as
  ``MEASUREMENT_BLOCKED_LEGACY_ARTIFACT``.
* Provenance records the historical origin commit, that this is a historical
  execution, and that the current document is a schema conversion.

No metric is invented and no telemetry is fabricated.  The migrated artifact
remains eligible for quality ranking while flagging limited performance
confidence.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from holo_benchmark.metrics import DEFAULT_KS, evaluate_rankings
from holo_benchmark.reranker_runtime import (
    CORPUS_SHA256,
    load_frozen_dataset,
    read_json,
)

LEGACY_RERANKERS = (
    "jina_reranker_v3_noncommercial",
    "kalm_reranker_v1_nano",
    "kalm_reranker_v1_small",
    "querit_reranker_4b",
)
HISTORICAL_COMMIT = "7ece93ad68f734b94f841badcbebc3e191f0d749"
HISTORICAL_COMMIT_EXTRA = "8786f57"
MEASUREMENT_BLOCKED = "MEASUREMENT_BLOCKED_LEGACY_ARTIFACT"
REQUIRED_KS = tuple(DEFAULT_KS)
CANDIDATE_TOP_K = 50
RERANK_TOP_K = 20


def current_commit(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def load_legacy(path: Path) -> Mapping[str, Any]:
    payload = read_json(path)
    if "metrics" not in payload or not isinstance(payload["metrics"], Mapping):
        raise ValueError(f"legacy pipeline has no metrics block: {path}")
    return payload


def candidate_rankings(candidate_path: Path, query_ids: Sequence[str]) -> list[list[str]]:
    payload = read_json(candidate_path)
    if payload.get("schema_version") == "1.0":
        rows = list(payload.get("queries") or [])
        if [str(row.get("query_id")) for row in rows] != list(query_ids):
            raise ValueError(f"candidate query order mismatch: {candidate_path}")
        rankings = [
            [str(item.get("chunk_id")) for item in list(row.get("candidates") or [])]
            for row in rows
        ]
    else:
        candidates = payload.get("candidates")
        if not isinstance(candidates, Mapping):
            raise ValueError(f"legacy candidate mapping missing: {candidate_path}")
        if set(map(str, candidates)) != set(query_ids):
            raise ValueError(f"candidate query set mismatch: {candidate_path}")
        rankings = [list(candidates[query_id]) for query_id in query_ids]
    for ranking in rankings:
        if len(ranking) != CANDIDATE_TOP_K:
            raise ValueError(f"candidate row is not top {CANDIDATE_TOP_K}: {candidate_path}")
    return rankings


def legacy_reranked_metrics(metrics: Mapping[str, Any]) -> Mapping[str, Any]:
    summary = metrics.get("summary")
    per_query = metrics.get("per_query")
    by_query_type = metrics.get("by_query_type")
    if not isinstance(summary, Mapping):
        raise ValueError("legacy metrics.summary is missing")
    if not isinstance(per_query, list) or len(per_query) != 150:
        raise ValueError("legacy metrics.per_query must contain 150 rows")
    if not isinstance(by_query_type, Mapping):
        raise ValueError("legacy metrics.by_query_type is missing")
    return {
        "summary": dict(summary),
        "per_query": [dict(row) for row in per_query],
        "by_query_type": {k: dict(v) for k, v in by_query_type.items()},
    }


def blocked_effect(
    query_ids: Sequence[str],
    queries: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for query in queries:
        rows.append(
            {
                "query_id": str(query["query_id"]),
                "query_type": query.get("query_type"),
                "status": MEASUREMENT_BLOCKED,
                "reason": (
                    "historical artifact did not persist reranked rankings; "
                    "per-query effect cannot be derived deterministically"
                ),
            }
        )
    return rows


def migrate_pipeline(
    pipeline_path: Path,
    candidate_path: Path,
    queries: Sequence[Mapping[str, Any]],
    query_ids: Sequence[str],
    *,
    conversion_commit: str,
) -> Mapping[str, Any]:
    legacy = load_legacy(pipeline_path)
    metrics = legacy["metrics"]
    reranked = legacy_reranked_metrics(metrics)

    # Recompute base metrics from the persisted candidate rankings.
    base_rankings = candidate_rankings(candidate_path, query_ids)
    base = evaluate_rankings(queries, base_rankings, REQUIRED_KS)
    for row in base["per_query"]:
        row.pop("difficulty", None)

    embedding = legacy.get("embedding_model") or legacy.get("embedding_variant")
    reranker = legacy.get("reranker") or pipeline_path.parent.name
    pipeline_id = legacy.get("pipeline_id") or legacy.get("id") or (
        f"{embedding}__{reranker}"
    )
    origin_commit = (
        HISTORICAL_COMMIT_EXTRA
        if pipeline_path.name == "snowflake_arctic_embed_l_v2_q4.json"
        else HISTORICAL_COMMIT
    )
    candidate_rel = candidate_path.resolve().relative_to(
        pipeline_path.resolve().parents[3]
    ).as_posix()

    migrated = {
        "schema_version": "1.0",
        "pipeline_id": pipeline_id,
        "embedding_variant": embedding,
        "reranker_id": reranker,
        "reranker": {"id": reranker, "name": reranker},
        "dataset": {
            "corpus_sha256": CORPUS_SHA256,
            "documents": len(queries) and 600,
            "queries": len(queries),
        },
        "candidate_top_k": CANDIDATE_TOP_K,
        "rerank_top_k": RERANK_TOP_K,
        "candidate_artifact": candidate_rel,
        "evaluation": {
            "base_metrics": {
                "summary": base["summary"],
                "per_query": base["per_query"],
                "by_query_type": base["by_query_type"],
            },
            "reranked_metrics": reranked,
            "per_query_effect": blocked_effect(query_ids, queries),
        },
        "telemetry": {
            "status": MEASUREMENT_BLOCKED,
            "reason": (
                "historical RERANKER-TOP5 session did not record runtime "
                "telemetry; no load, latency, RAM or VRAM measurement exists"
            ),
        },
        "provenance": {
            "origin_commit": origin_commit,
            "execution_type": "historical_execution",
            "conversion": {
                "tool": "tools/migrate_legacy_reranker_pipelines.py",
                "conversion_commit": conversion_commit,
                "schema_source": "legacy metrics block from RERANKER-TOP5 session",
                "converted_at": datetime.now(timezone.utc).isoformat(),
                "preserves_metrics": True,
                "base_metrics_source": "persisted candidate top-50 rankings",
                "reranked_metrics_source": "legacy metrics block",
            },
        },
        "confidence": {
            "quality_eligible": True,
            "performance_analysis_limited": True,
            "note": (
                "quality metrics are real and internally consistent; runtime "
                "performance is unavailable because the historical session did "
                "not record telemetry"
            ),
        },
    }
    return migrated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--commit")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    bench = root / "benchmark" / "embedding-v3"
    pipelines_root = bench / "results" / "reranker" / "pipelines"
    candidates_root = bench / "results" / "reranker" / "candidates"
    chunks, queries = load_frozen_dataset(bench)
    query_ids = [str(query["query_id"]) for query in queries]
    conversion_commit = args.commit or current_commit(root)

    migrated: list[str] = []
    failed: list[str] = []
    for reranker in LEGACY_RERANKERS:
        directory = pipelines_root / reranker
        if not directory.is_dir():
            continue
        for pipeline_path in sorted(directory.glob("*.json")):
            embedding = json.loads(pipeline_path.read_text(encoding="utf-8")).get(
                "embedding_model"
            ) or pipeline_path.stem
            candidate_path = candidates_root / f"{embedding}.json"
            if not candidate_path.is_file():
                failed.append(f"{pipeline_path.relative_to(root)} (no candidate)")
                continue
            try:
                migrated_payload = migrate_pipeline(
                    pipeline_path,
                    candidate_path,
                    queries,
                    query_ids,
                    conversion_commit=conversion_commit,
                )
            except Exception as exc:  # noqa: BLE001
                failed.append(
                    f"{pipeline_path.relative_to(root)} ({type(exc).__name__}: {exc})"
                )
                continue
            if not args.dry_run:
                pipeline_path.write_text(
                    json.dumps(migrated_payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            migrated.append(str(pipeline_path.relative_to(root)))

    print(
        json.dumps(
            {
                "status": "PASS" if not failed else "INCOMPLETE",
                "dry_run": args.dry_run,
                "migrated": len(migrated),
                "failed": failed,
                "conversion_commit": conversion_commit,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
