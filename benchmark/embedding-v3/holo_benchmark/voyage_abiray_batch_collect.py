"""Collect a completed Voyage rerank batch whose top_k is smaller than the union.

Voyage returns only the requested top_k rows. This collector validates the returned
subset, preserves Voyage ordering for candidates present in each embedding variant,
and appends unreturned candidates in their original embedding order. It never
invents relevance scores for unreturned candidates.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import voyage_abiray_batch as base
from .artifact_portability import assert_portable_payload
from .reranker_metrics import candidate_ids, evaluate_reranker_effect
from .reranker_runtime import CORPUS_SHA256, DEFAULT_RERANK_INSTRUCTION, atomic_json


def _response_scores(
    response_body: Mapping[str, Any],
    ids: Sequence[str],
    *,
    expected_top_k: int = base.RERANK_TOP_K,
) -> dict[str, float]:
    """Return the scored subset from a Voyage rerank response.

    The response is valid when it contains exactly min(top_k, union_size) unique,
    in-range indices. Candidates outside the returned top-k are intentionally
    unscored and must not receive synthetic values.
    """
    data = response_body.get("data")
    if not isinstance(data, list):
        raise ValueError("batch rerank response has no data list")
    expected_count = min(expected_top_k, len(ids))
    if len(data) != expected_count:
        raise ValueError(
            f"batch rerank response returned {len(data)} rows; "
            f"expected {expected_count}"
        )

    result: dict[str, float] = {}
    seen_indices: set[int] = set()
    for item in data:
        if not isinstance(item, Mapping):
            raise ValueError("batch rerank response data row is not an object")
        index = int(item["index"])
        if index < 0 or index >= len(ids):
            raise ValueError(f"rerank index out of range: {index}")
        if index in seen_indices:
            raise ValueError(f"duplicate rerank index: {index}")
        seen_indices.add(index)
        result[str(ids[index])] = float(item["relevance_score"])
    return result


def _parse_output(
    content: bytes,
    query_ids: Sequence[str],
    union_ids: Sequence[Sequence[str]],
) -> list[dict[str, float]]:
    by_query: dict[str, dict[str, float]] = {}
    query_index = {query_id: index for index, query_id in enumerate(query_ids)}
    for raw_line in content.decode("utf-8").splitlines():
        if not raw_line.strip():
            continue
        row = json.loads(raw_line)
        custom_id = str(row.get("custom_id") or "")
        if custom_id in by_query:
            raise ValueError(f"duplicate batch custom_id: {custom_id}")
        if row.get("error"):
            raise RuntimeError(f"batch request failed for {custom_id}: {row['error']}")
        response = row.get("response")
        if not isinstance(response, Mapping):
            raise ValueError(f"missing response object for {custom_id}")
        status_code = int(response.get("status_code") or 0)
        if status_code != 200:
            raise RuntimeError(f"batch response HTTP {status_code} for {custom_id}")
        body = response.get("body")
        if not isinstance(body, Mapping):
            raise ValueError(f"missing response body for {custom_id}")
        if custom_id not in query_index:
            raise ValueError(f"unexpected batch custom_id: {custom_id}")
        by_query[custom_id] = _response_scores(
            body,
            union_ids[query_index[custom_id]],
        )
    if set(by_query) != set(query_ids):
        missing = sorted(set(query_ids) - set(by_query))
        raise ValueError(f"batch output missing requests: {missing[:10]}")
    return [by_query[query_id] for query_id in query_ids]


def _partial_rankings(
    candidate_rows: Sequence[Sequence[Mapping[str, Any]]],
    score_rows: Sequence[Mapping[str, float]],
) -> list[list[str]]:
    """Rank each variant's top-20 using Voyage's scored subset.

    Returned/scored candidates come first by descending Voyage score. Candidates
    omitted because the union exceeded top_k are appended in stable base order.
    """
    if len(candidate_rows) != len(score_rows):
        raise ValueError("candidate and score query counts diverge")
    rankings: list[list[str]] = []
    for candidates, score_map in zip(candidate_rows, score_rows, strict=True):
        ids = [str(item["chunk_id"]) for item in candidates]
        original_rank = {chunk_id: rank for rank, chunk_id in enumerate(ids, 1)}
        scored = [chunk_id for chunk_id in ids if chunk_id in score_map]
        scored.sort(
            key=lambda chunk_id: (
                -float(score_map[chunk_id]),
                original_rank[chunk_id],
                chunk_id,
            )
        )
        unscored = [chunk_id for chunk_id in ids if chunk_id not in score_map]
        ranking = scored + unscored
        if len(ranking) != len(ids) or set(ranking) != set(ids):
            raise ValueError("partial rerank did not preserve the candidate set")
        rankings.append(ranking)
    return rankings


def collect(args: argparse.Namespace) -> dict[str, Any]:
    state = base.status(args)
    current = str(state.get("status") or "")
    if current not in base.TERMINAL_STATUSES:
        return {"status": "PENDING", "batch_status": current, "state": str(base.STATE)}
    if current != "completed":
        raise RuntimeError(f"Voyage batch ended with non-complete status: {current}")
    output_file_id = str(state.get("output_file_id") or "")
    if not output_file_id:
        raise ValueError("completed batch has no output_file_id")

    payloads, queries, union_ids, _ = base._load_context()
    query_ids = [str(row["query_id"]) for row in queries]
    score_rows = _parse_output(
        base._download_file(output_file_id, base._api_key(args.api_key_path)),
        query_ids,
        union_ids,
    )

    score_path = base.SCORES / "voyage_rerank_2_5_nemotron_8b_abiray.json"
    score = base._portable(
        {
            "schema_version": "1.1",
            "reranker_id": "voyage_rerank_2_5",
            "model": {"id": base.MODEL, "provider": "Voyage AI", "api_model": True},
            "corpus_sha256": CORPUS_SHA256,
            "instruction": DEFAULT_RERANK_INSTRUCTION,
            "runtime": {
                "backend": "voyage_batch_api",
                "batch_id": state["batch_id"],
                "input_file_id": state.get("input_file_id"),
                "output_file_id": output_file_id,
                "request_counts": state.get("request_counts"),
                "completion_window": "12h",
                "top_k": base.RERANK_TOP_K,
                "partial_union_scoring": True,
            },
            "variants": list(base.VARIANTS),
            "queries": [
                {
                    "query_id": query_id,
                    "candidate_ids": list(ids),
                    "scored_candidate_ids": [
                        chunk_id for chunk_id in ids if chunk_id in scores
                    ],
                    "unscored_candidate_ids": [
                        chunk_id for chunk_id in ids if chunk_id not in scores
                    ],
                    "scores": scores,
                }
                for query_id, ids, scores in zip(
                    query_ids, union_ids, score_rows, strict=True
                )
            ],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    atomic_json(score_path, score)

    written = [str(score_path.relative_to(base.PROJECT_ROOT))]
    for variant in base.VARIANTS:
        rows = [list(row["candidates"]) for row in payloads[variant]["queries"]]
        top_rows = [row[: base.RERANK_TOP_K] for row in rows]
        evaluation = evaluate_reranker_effect(
            queries,
            candidate_ids(top_rows),
            _partial_rankings(top_rows, score_rows),
            base.RERANK_TOP_K,
        )
        pipeline = base._portable(
            {
                "schema_version": "1.1",
                "pipeline_id": f"{variant}__voyage_rerank_2_5",
                "embedding_variant": variant,
                "reranker_id": "voyage_rerank_2_5",
                "candidate_top_k": 50,
                "rerank_top_k": base.RERANK_TOP_K,
                "score_artifact": str(score_path.relative_to(base.PROJECT_ROOT)),
                "partial_union_scoring": True,
                "unscored_policy": "append in stable base-embedding order",
                "evaluation": evaluation,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        path = base.PIPELINES / f"{variant}.json"
        atomic_json(path, pipeline)
        written.append(str(path.relative_to(base.PROJECT_ROOT)))

    if base.BLOCKED.exists():
        base.BLOCKED.unlink()
    state["status"] = "COLLECTED"
    state["collected_at"] = datetime.now(timezone.utc).isoformat()
    state["written"] = written
    state["partial_union_scoring"] = True
    atomic_json(base.STATE, base._portable(state))
    return {"status": "PASS", "written": written, "batch_id": state["batch_id"]}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key-path", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    result = collect(parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
