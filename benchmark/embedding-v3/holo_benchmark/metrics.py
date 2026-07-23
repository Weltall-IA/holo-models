from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Any, Iterable, Sequence


DEFAULT_KS = (1, 3, 5, 10, 20, 50)


def _mean(values: Iterable[float]) -> float:
    materialized = list(values)
    return float(sum(materialized) / len(materialized)) if materialized else 0.0


def _dcg(binary_relevance: Sequence[int], k: int) -> float:
    score = 0.0
    for rank, relevant in enumerate(binary_relevance[:k], start=1):
        if relevant:
            score += 1.0 / math.log2(rank + 1)
    return score


def _evaluate_one(
    query: dict[str, Any],
    ranked_chunk_ids: Sequence[str],
    ks: Sequence[int],
) -> dict[str, Any]:
    relevant = set(query.get("relevant_chunk_ids") or [])
    hard_negatives = set(query.get("hard_negative_chunk_ids") or [])
    if not relevant:
        raise ValueError(f"consulta sem relevantes: {query.get('query_id')}")

    ranks = {
        chunk_id: rank
        for rank, chunk_id in enumerate(ranked_chunk_ids, start=1)
    }
    relevant_ranks = sorted(
        ranks[chunk_id] for chunk_id in relevant if chunk_id in ranks
    )
    first_relevant_rank = relevant_ranks[0] if relevant_ranks else None

    result: dict[str, Any] = {
        "query_id": query.get("query_id"),
        "query_type": query.get("query_type"),
        "difficulty": query.get("difficulty"),
        "first_relevant_rank": first_relevant_rank,
        "relevant_ranks": relevant_ranks,
    }

    for k in ks:
        retrieved = sum(1 for rank in relevant_ranks if rank <= k)
        result[f"HitRate@{k}"] = 1.0 if retrieved else 0.0
        result[f"Recall@{k}"] = retrieved / len(relevant)

    result["MRR@10"] = (
        1.0 / first_relevant_rank
        if first_relevant_rank is not None and first_relevant_rank <= 10
        else 0.0
    )

    binary = [1 if chunk_id in relevant else 0 for chunk_id in ranked_chunk_ids]
    ideal = [1] * min(len(relevant), 10)
    ideal_dcg = _dcg(ideal, 10)
    result["nDCG@10"] = _dcg(binary, 10) / ideal_dcg if ideal_dcg else 0.0

    hard_negative_ranks = [
        ranks[chunk_id] for chunk_id in hard_negatives if chunk_id in ranks
    ]
    best_hard_negative = min(hard_negative_ranks) if hard_negative_ranks else None
    result["best_hard_negative_rank"] = best_hard_negative
    result["hard_negative_error"] = (
        1.0
        if (
            first_relevant_rank is not None
            and best_hard_negative is not None
            and best_hard_negative < first_relevant_rank
        )
        else 0.0
    )
    return result


def evaluate_rankings(
    queries: Sequence[dict[str, Any]],
    rankings: Sequence[Sequence[str]],
    ks: Sequence[int] = DEFAULT_KS,
) -> dict[str, Any]:
    if len(queries) != len(rankings):
        raise ValueError("quantidade de consultas e rankings divergente")
    if not queries:
        raise ValueError("nenhuma consulta para avaliar")

    per_query = [
        _evaluate_one(query, ranked, ks)
        for query, ranked in zip(queries, rankings, strict=True)
    ]

    summary: dict[str, Any] = {}
    for k in ks:
        summary[f"HitRate@{k}"] = _mean(row[f"HitRate@{k}"] for row in per_query)
        summary[f"Recall@{k}"] = _mean(row[f"Recall@{k}"] for row in per_query)
    summary["MRR@10"] = _mean(row["MRR@10"] for row in per_query)
    summary["nDCG@10"] = _mean(row["nDCG@10"] for row in per_query)

    finite_ranks = [
        int(row["first_relevant_rank"])
        for row in per_query
        if row["first_relevant_rank"] is not None
    ]
    summary["mean_first_relevant_rank"] = (
        _mean(finite_ranks) if finite_ranks else None
    )
    summary["median_first_relevant_rank"] = (
        float(statistics.median(finite_ranks)) if finite_ranks else None
    )
    summary["queries_without_relevant"] = len(per_query) - len(finite_ranks)
    summary["hard_negative_error_rate"] = _mean(
        row["hard_negative_error"] for row in per_query
    )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in per_query:
        grouped[str(row.get("query_type") or "unknown")].append(row)

    by_query_type: dict[str, Any] = {}
    for query_type, rows in sorted(grouped.items()):
        by_query_type[query_type] = {
            "count": len(rows),
            "HitRate@10": _mean(row["HitRate@10"] for row in rows),
            "MRR@10": _mean(row["MRR@10"] for row in rows),
            "nDCG@10": _mean(row["nDCG@10"] for row in rows),
            "hard_negative_error_rate": _mean(
                row["hard_negative_error"] for row in rows
            ),
        }

    return {
        "summary": summary,
        "by_query_type": by_query_type,
        "per_query": per_query,
    }
