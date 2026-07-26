#!/usr/bin/env python3
"""Finalize the authorized4 Voyage Batch run: parse output, write score + pipelines.

The batch already COMPLETED (150/150, 0 failed). This reuses the downloaded
output file and the existing state checkpoint; it does NOT re-submit.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_ROOT.parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from holo_benchmark.reranker_runtime import (  # noqa: E402
    CORPUS_SHA256,
    DEFAULT_RERANK_INSTRUCTION,
    load_frozen_dataset,
    rerank_query_text,
)
from holo_benchmark.reranker_metrics import (  # noqa: E402
    build_union_candidates,
)
from holo_benchmark.voyage_batch import (  # noqa: E402
    build_batch_jsonl,
    parse_batch_output,
)
from reranker_execution import (  # noqa: E402
    PIPELINE_DIR,
    SCORE_DIR,
    _evaluate_and_write_pipelines,
    _score_payload,
)

RAW_DIR = PROJECT_ROOT / "results" / "raw" / "reranker" / "voyage_batch"
AUTHORIZED_VARIANTS = [
    "pplx_embed_v1_4b_q8_0",
    "nomic_embed_text_v2_moe_q4",
    "bge_m3_dense",
    "snowflake_arctic_embed_l_v2_q4",
]
RERANK_TOP_K = 20


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_authorized_candidates(variants):
    _, expected_queries = load_frozen_dataset(PROJECT_ROOT)
    expected_query_ids = [str(q["query_id"]) for q in expected_queries]
    payloads: dict[str, dict[str, Any]] = {}
    for variant in variants:
        path = PROJECT_ROOT / "results" / "reranker" / "candidates" / f"{variant}.json"
        if not path.is_file():
            raise RuntimeError(f"candidate artifact missing: {path}")
        payload = read_json(path)
        if payload.get("id") != variant:
            raise RuntimeError(f"candidate id mismatch: {path}")
        cand = payload.get("candidates") or {}
        query_ids = list(cand.keys())
        if query_ids != expected_query_ids:
            raise RuntimeError(f"candidate query order mismatch: {path}")
        payloads[variant] = {
            "variant": variant,
            "candidate_top_k": int(payload.get("candidate_top_k") or 50),
            "queries": [
                {"query_id": qid, "candidates": [{"chunk_id": cid} for cid in cand[qid]]}
                for qid in expected_query_ids
            ],
        }
    return payloads


def build_manifests(payloads):
    return {
        v: [
            [dict(item) for item in row["candidates"]]
            for row in payloads[v]["queries"]
        ]
        for v in payloads
    }


def parse_ts(s: str) -> float:
    return datetime.fromisoformat(s).timestamp()


def main() -> int:
    variants = list(AUTHORIZED_VARIANTS)
    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    chunk_text_by_id = {str(c["chunk_id"]): str(c["text"]) for c in chunks}
    payloads = load_authorized_candidates(variants)
    manifests = build_manifests(payloads)
    union_ids = build_union_candidates(manifests, RERANK_TOP_K)

    input_path = RAW_DIR / "rerank-2.5-input-authorized4.jsonl"
    output_path = RAW_DIR / "rerank-2.5-output-authorized4.jsonl"
    state_path = RAW_DIR / "rerank-2.5-state-authorized4.json"
    if not output_path.is_file():
        raise RuntimeError(f"output file missing: {output_path}")

    manifest = build_batch_jsonl(
        queries, union_ids, chunk_text_by_id, DEFAULT_RERANK_INSTRUCTION,
        input_path, rerank_query_text,
    )
    state = read_json(state_path)
    batch_obj = read_json(Path("/tmp/authorized4_batch.json")) if Path("/tmp/authorized4_batch.json").is_file() else {}

    score_rows, usage, errors = parse_batch_output(
        output_path.read_text(encoding="utf-8"), queries, union_ids)
    if errors:
        print("BATCH OUTPUT ERRORS:", json.dumps(errors[:10], ensure_ascii=False))
        return 2
    if len(score_rows) != len(queries):
        print(f"output count diverged: {len(score_rows)} != {len(queries)}")
        return 2

    created = batch_obj.get("created_at") or state.get("created_at")
    completed = batch_obj.get("completed_at")
    wall = None
    if created and completed:
        wall = round(parse_ts(completed) - parse_ts(created), 4)

    usage.update({
        "retries": int(state.get("submit_retries") or 0),
        "seconds": wall if wall is not None else float(state.get("updated_at", 0.0)),
        "estimated_standard_price_usd": round(int(usage["tokens"]) * 0.05 / 1_000_000, 8),
        "charged_cost_usd": None,
        "tier": "free (no payment method; 200M free tokens, no charge)",
    })
    runtime = {
        "backend": "Voyage Batch API",
        "transport": "batch",
        "model": "rerank-2.5",
        "usage": usage,
        "batch": {
            "status": batch_obj.get("status", state.get("status")),
            "request_counts": batch_obj.get("request_counts", state.get("request_counts")),
            "created_at": created,
            "in_progress_at": batch_obj.get("in_progress_at"),
            "finalizing_at": batch_obj.get("finalizing_at"),
            "completed_at": completed,
            "batch_id": state.get("batch_id"),
            "input_file_id": state.get("input_file_id"),
            "output_file_id": state.get("output_file_id"),
            "error_file_present": bool(batch_obj.get("error_file_id") or state.get("error_file_id")),
            "submit_retries": int(state.get("submit_retries") or 0),
        },
        "input_manifest": {k: v for k, v in manifest.items() if k != "query_ids"},
        "latency_p50_seconds": None,
        "latency_p95_seconds": None,
        "latency_max_seconds": None,
    }
    reranker_id = "voyage_rerank_2_5"
    score_path = SCORE_DIR / "voyage_rerank_2_5_authorized4.json"
    score_payload = _score_payload(
        reranker_id,
        {"id": "rerank-2.5", "provider": "Voyage AI", "api_model": True, "transport": "batch"},
        runtime, queries, score_rows, union_ids, DEFAULT_RERANK_INSTRUCTION,
    )
    score_path.parent.mkdir(parents=True, exist_ok=True)
    score_path.write_text(json.dumps(score_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[finalize] wrote score artifact: {score_path}")
    print(f"[finalize] tokens={usage['tokens']} requests={usage['requests']} "
          f"failed={runtime['batch']['request_counts'].get('failed')} "
          f"estimated_price_usd={usage['estimated_standard_price_usd']} "
          f"charged_cost_usd={usage['charged_cost_usd']}")

    pipelines = _evaluate_and_write_pipelines(
        reranker_id, variants, payloads, queries, score_rows, RERANK_TOP_K, score_path)
    print(f"[finalize] wrote {len(pipelines)} pipelines:")
    for row in pipelines:
        ev = row["evaluation"]["reranked_metrics"]["summary"]
        print(f"   {row['pipeline_id']}: MRR@10={ev['MRR@10']:.4f} "
              f"HR@10={ev['HitRate@10']:.4f} nDCG@10={ev['nDCG@10']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
