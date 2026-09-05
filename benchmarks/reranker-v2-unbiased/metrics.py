from __future__ import annotations

import math
import random
import statistics
from collections import defaultdict
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

METRIC_KEYS = ("ndcg@10", "mrr@10", "map", "hit@1", "recall@10", "recall@20")


def _dcg(rels: Sequence[int], k: int) -> float:
    total = 0.0
    for i, rel in enumerate(rels[:k], start=1):
        if rel:
            total += 1.0 / math.log2(i + 1)
    return total


def per_query_metrics(ranked_ids: Sequence[str], relevant_ids: Iterable[str]) -> Dict[str, float]:
    relevant = set(relevant_ids)
    if not relevant:
        raise ValueError("Each query must have at least one relevant document")

    binary = [1 if doc_id in relevant else 0 for doc_id in ranked_ids]

    ideal_hits = min(len(relevant), 10)
    idcg = _dcg([1] * ideal_hits, 10)
    ndcg10 = _dcg(binary, 10) / idcg if idcg else 0.0

    rr = 0.0
    for rank, hit in enumerate(binary[:10], start=1):
        if hit:
            rr = 1.0 / rank
            break

    hit1 = float(bool(binary and binary[0]))

    hits_seen = 0
    precisions = []
    for rank, hit in enumerate(binary, start=1):
        if hit:
            hits_seen += 1
            precisions.append(hits_seen / rank)
    ap = sum(precisions) / len(relevant)

    def recall_at(k: int) -> float:
        return sum(binary[:k]) / len(relevant)

    return {
        "ndcg@10": ndcg10,
        "mrr@10": rr,
        "map": ap,
        "hit@1": hit1,
        "recall@10": recall_at(10),
        "recall@20": recall_at(20),
    }


def aggregate(per_query: Mapping[str, Mapping[str, float]]) -> Dict[str, float]:
    if not per_query:
        raise ValueError("No query metrics to aggregate")
    return {
        metric: statistics.fmean(values[metric] for values in per_query.values())
        for metric in METRIC_KEYS
    }


def _percentile(sorted_values: Sequence[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("Cannot take percentile of empty sequence")
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = (len(sorted_values) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return sorted_values[lo]
    weight = pos - lo
    return sorted_values[lo] * (1.0 - weight) + sorted_values[hi] * weight


def _grouped_query_ids(query_ids: Sequence[str], group_ids: Mapping[str, str] | None) -> List[List[str]]:
    if not group_ids:
        return [[qid] for qid in query_ids]
    groups: Dict[str, List[str]] = defaultdict(list)
    for qid in query_ids:
        groups[group_ids.get(qid, qid)].append(qid)
    return list(groups.values())


def bootstrap_ci(
    per_query: Mapping[str, Mapping[str, float]],
    metric: str,
    *,
    seed: int = 20260904,
    resamples: int = 10_000,
    confidence: float = 0.95,
    group_ids: Mapping[str, str] | None = None,
) -> Tuple[float, float]:
    if metric not in METRIC_KEYS:
        raise KeyError(metric)
    query_ids = list(per_query)
    groups = _grouped_query_ids(query_ids, group_ids)
    rng = random.Random(seed)
    means: List[float] = []

    for _ in range(resamples):
        sampled_groups = [groups[rng.randrange(len(groups))] for _ in groups]
        sampled_ids = [qid for group in sampled_groups for qid in group]
        means.append(statistics.fmean(per_query[qid][metric] for qid in sampled_ids))

    means.sort()
    alpha = (1.0 - confidence) / 2.0
    return _percentile(means, alpha), _percentile(means, 1.0 - alpha)


def paired_bootstrap_delta(
    a: Mapping[str, Mapping[str, float]],
    b: Mapping[str, Mapping[str, float]],
    metric: str,
    *,
    seed: int = 20260904,
    resamples: int = 10_000,
    confidence: float = 0.95,
    group_ids: Mapping[str, str] | None = None,
) -> Dict[str, float | str]:
    if set(a) != set(b):
        missing_a = sorted(set(b) - set(a))
        missing_b = sorted(set(a) - set(b))
        raise ValueError(
            f"Paired comparison requires identical query IDs; "
            f"missing_from_a={missing_a[:5]} missing_from_b={missing_b[:5]}"
        )

    query_ids = list(a)
    groups = _grouped_query_ids(query_ids, group_ids)
    rng = random.Random(seed)
    deltas: List[float] = []

    for _ in range(resamples):
        sampled_groups = [groups[rng.randrange(len(groups))] for _ in groups]
        sampled_ids = [qid for group in sampled_groups for qid in group]
        deltas.append(
            statistics.fmean(a[qid][metric] - b[qid][metric] for qid in sampled_ids)
        )

    deltas.sort()
    alpha = (1.0 - confidence) / 2.0
    lo = _percentile(deltas, alpha)
    hi = _percentile(deltas, 1.0 - alpha)
    mean = statistics.fmean(a[qid][metric] - b[qid][metric] for qid in query_ids)

    if lo > 0:
        verdict = "a_wins"
    elif hi < 0:
        verdict = "b_wins"
    else:
        verdict = "inconclusive"

    return {"mean_delta": mean, "ci_low": lo, "ci_high": hi, "verdict": verdict}
