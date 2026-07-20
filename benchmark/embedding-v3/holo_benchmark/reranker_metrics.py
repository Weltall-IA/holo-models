from __future__ import annotations

import statistics
from collections import Counter
from typing import Any, Mapping, Sequence

from .metrics import DEFAULT_KS, evaluate_rankings


DEFAULT_RERANKER_IDS = ("qwen_local", "voyage_rerank_2_5")


def stable_top_k(
    score_rows: Any,
    chunk_ids: Sequence[str],
    top_k: int,
) -> list[list[dict[str, Any]]]:
    """Return deterministic top-k candidate rows from a 2-D score matrix."""
    import numpy as np

    scores = np.asarray(score_rows)
    if scores.ndim != 2:
        raise ValueError(f"score matrix must be 2-D, got shape={scores.shape}")
    if scores.shape[1] != len(chunk_ids):
        raise ValueError("score columns and chunk ids diverge")
    if top_k <= 0 or top_k > len(chunk_ids):
        raise ValueError(f"invalid top_k={top_k}")

    order = np.argsort(-scores, axis=1, kind="stable")[:, :top_k]
    output: list[list[dict[str, Any]]] = []
    for row_index, indices in enumerate(order):
        output.append(
            [
                {
                    "chunk_id": str(chunk_ids[int(index)]),
                    "score": float(scores[row_index, int(index)]),
                    "rank": rank,
                }
                for rank, index in enumerate(indices, start=1)
            ]
        )
    return output


def candidate_ids(candidate_rows: Sequence[Sequence[Mapping[str, Any]]]) -> list[list[str]]:
    return [
        [str(item["chunk_id"]) for item in row]
        for row in candidate_rows
    ]


def build_union_candidates(
    manifests: Mapping[str, Sequence[Sequence[Mapping[str, Any]]]],
    top_n: int,
) -> list[list[str]]:
    """Build a stable per-query union, preserving variant and original rank order."""
    if not manifests:
        raise ValueError("no candidate manifests")
    lengths = {len(rows) for rows in manifests.values()}
    if len(lengths) != 1:
        raise ValueError("candidate manifests have divergent query counts")
    if top_n <= 0:
        raise ValueError("top_n must be positive")

    query_count = lengths.pop()
    output: list[list[str]] = []
    for query_index in range(query_count):
        seen: set[str] = set()
        union: list[str] = []
        for rows in manifests.values():
            for item in rows[query_index][:top_n]:
                chunk_id = str(item["chunk_id"])
                if chunk_id not in seen:
                    seen.add(chunk_id)
                    union.append(chunk_id)
        output.append(union)
    return output


def scores_to_rankings(
    candidate_rows: Sequence[Sequence[Mapping[str, Any]]],
    score_rows: Sequence[Mapping[str, float]],
) -> list[list[str]]:
    if len(candidate_rows) != len(score_rows):
        raise ValueError("candidate and score query counts diverge")
    rankings: list[list[str]] = []
    for candidates, score_map in zip(candidate_rows, score_rows, strict=True):
        original_rank = {
            str(item["chunk_id"]): int(item.get("rank") or index)
            for index, item in enumerate(candidates, start=1)
        }
        ids = [str(item["chunk_id"]) for item in candidates]
        missing = [chunk_id for chunk_id in ids if chunk_id not in score_map]
        if missing:
            raise ValueError(f"reranker scores missing candidates: {missing[:3]}")
        rankings.append(
            sorted(
                ids,
                key=lambda chunk_id: (
                    -float(score_map[chunk_id]),
                    original_rank[chunk_id],
                    chunk_id,
                ),
            )
        )
    return rankings


def pipeline_completion(
    variants: Sequence[str],
    records: Sequence[Mapping[str, Any]],
    reranker_ids: Sequence[str] = DEFAULT_RERANKER_IDS,
) -> dict[str, Any]:
    """Describe whether the complete embedding × reranker matrix exists."""
    if not variants:
        raise ValueError("no embedding variants")
    if len(variants) != len(set(variants)):
        raise ValueError("duplicate embedding variants")
    if len(reranker_ids) != len(set(reranker_ids)):
        raise ValueError("duplicate reranker ids")

    expected: list[str] = []
    for variant in variants:
        expected.append(f"{variant}__none")
        expected.extend(f"{variant}__{reranker_id}" for reranker_id in reranker_ids)

    completed = [str(record.get("pipeline_id") or "") for record in records]
    if any(not pipeline_id for pipeline_id in completed):
        raise ValueError("pipeline record without pipeline_id")

    counts = Counter(completed)
    completed_set = set(completed)
    expected_set = set(expected)
    missing = [pipeline_id for pipeline_id in expected if pipeline_id not in completed_set]
    unexpected = sorted(completed_set - expected_set)
    duplicates = sorted(
        pipeline_id for pipeline_id, count in counts.items() if count > 1
    )

    complete = not missing and not unexpected and not duplicates
    status = "PASS" if complete else ("PARTIAL" if completed_set else "BLOCKED")
    return {
        "status": status,
        "expected_pipeline_count": len(expected),
        "completed_pipeline_count": len(completed_set),
        "pipeline_record_count": len(completed),
        "expected_pipelines": expected,
        "completed_pipelines": sorted(completed_set),
        "missing_pipelines": missing,
        "unexpected_pipelines": unexpected,
        "duplicate_pipelines": duplicates,
    }


def _first_relevant_rank(query: Mapping[str, Any], ranking: Sequence[str]) -> int | None:
    relevant = set(map(str, query.get("relevant_chunk_ids") or []))
    for rank, chunk_id in enumerate(ranking, start=1):
        if str(chunk_id) in relevant:
            return rank
    return None


def evaluate_reranker_effect(
    queries: Sequence[dict[str, Any]],
    base_rankings: Sequence[Sequence[str]],
    reranked_rankings: Sequence[Sequence[str]],
    candidate_cutoff: int,
) -> dict[str, Any]:
    if not (len(queries) == len(base_rankings) == len(reranked_rankings)):
        raise ValueError("query and ranking counts diverge")
    if candidate_cutoff <= 0:
        raise ValueError("candidate_cutoff must be positive")

    base_metrics = evaluate_rankings(queries, base_rankings, DEFAULT_KS)
    reranked_metrics = evaluate_rankings(queries, reranked_rankings, DEFAULT_KS)

    rescue_eligible = 0
    rescue_count = 0
    damage_eligible = 0
    damage_count = 0
    candidate_eligible = 0
    candidate_top1_correct = 0
    rank_deltas: list[int] = []
    per_query: list[dict[str, Any]] = []

    for query, base, reranked in zip(
        queries, base_rankings, reranked_rankings, strict=True
    ):
        relevant = set(map(str, query.get("relevant_chunk_ids") or []))
        base_first = _first_relevant_rank(query, base)
        reranked_first = _first_relevant_rank(query, reranked)
        base_top1 = bool(base and str(base[0]) in relevant)
        reranked_top1 = bool(reranked and str(reranked[0]) in relevant)
        present = any(str(chunk_id) in relevant for chunk_id in base[:candidate_cutoff])

        if present:
            candidate_eligible += 1
            if reranked_top1:
                candidate_top1_correct += 1
        if not base_top1 and present:
            rescue_eligible += 1
            if reranked_top1:
                rescue_count += 1
        if base_top1:
            damage_eligible += 1
            if not reranked_top1:
                damage_count += 1
        if base_first is not None and reranked_first is not None:
            rank_deltas.append(base_first - reranked_first)

        per_query.append(
            {
                "query_id": query.get("query_id"),
                "query_type": query.get("query_type"),
                "candidate_contains_relevant": present,
                "base_first_relevant_rank": base_first,
                "reranked_first_relevant_rank": reranked_first,
                "base_top1_correct": base_top1,
                "reranked_top1_correct": reranked_top1,
                "rescued": bool(not base_top1 and present and reranked_top1),
                "damaged": bool(base_top1 and not reranked_top1),
            }
        )

    def ratio(numerator: int, denominator: int) -> float | None:
        return float(numerator / denominator) if denominator else None

    return {
        "base_metrics": base_metrics,
        "reranked_metrics": reranked_metrics,
        "effect": {
            "candidate_cutoff": candidate_cutoff,
            "candidate_coverage": ratio(candidate_eligible, len(queries)),
            "conditional_HitRate@1": ratio(candidate_top1_correct, candidate_eligible),
            "rescue_count": rescue_count,
            "rescue_eligible": rescue_eligible,
            "rescue_rate": ratio(rescue_count, rescue_eligible),
            "damage_count": damage_count,
            "damage_eligible": damage_eligible,
            "damage_rate": ratio(damage_count, damage_eligible),
            "mean_rank_improvement": (
                float(statistics.mean(rank_deltas)) if rank_deltas else None
            ),
            "median_rank_improvement": (
                float(statistics.median(rank_deltas)) if rank_deltas else None
            ),
        },
        "per_query_effect": per_query,
    }
