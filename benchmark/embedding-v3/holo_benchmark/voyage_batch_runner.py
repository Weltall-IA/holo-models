from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from holo_benchmark.reranker_metrics import build_union_candidates
from holo_benchmark.reranker_runtime import (
    CANDIDATE_VARIANTS,
    CORPUS_SHA256,
    DEFAULT_RERANK_INSTRUCTION,
    atomic_json,
    load_frozen_dataset,
    rerank_query_text,
)
from holo_benchmark.voyage_batch import (
    build_batch_jsonl,
    execute_batch,
    parse_batch_output,
)
from reranker_execution import (
    DEFAULT_KEY_PATH,
    PROJECT_ROOT,
    SCORE_DIR,
    _candidate_rows,
    _evaluate_and_write_pipelines,
    _score_payload,
    load_candidate_payloads,
    parse_csv,
)

RAW_DIR = PROJECT_ROOT / "results" / "raw" / "reranker" / "voyage_batch"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Executa Voyage rerank-2.5 pela Batch API sem repetir embeddings ou Qwen"
    )
    parser.add_argument("--variants", default=",".join(CANDIDATE_VARIANTS))
    parser.add_argument("--rerank-top-k", type=int, default=20)
    parser.add_argument("--instruction", default=DEFAULT_RERANK_INSTRUCTION)
    parser.add_argument("--api-key-path", type=Path, default=DEFAULT_KEY_PATH)
    parser.add_argument("--allow-voyage-rerank-api", action="store_true")
    parser.add_argument("--poll-interval", type=float, default=60.0)
    parser.add_argument("--submit-retry-seconds", type=float, default=1800.0)
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not args.allow_voyage_rerank_api:
        raise RuntimeError(
            "Voyage rerank API is disabled; pass --allow-voyage-rerank-api"
        )
    if args.rerank_top_k != 20:
        raise ValueError("the frozen decision benchmark requires rerank-top-k=20")

    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    variants = parse_csv(args.variants)
    candidates = load_candidate_payloads(variants, args.rerank_top_k)
    union_ids = build_union_candidates(
        {
            variant: _candidate_rows(candidates[variant])
            for variant in variants
        },
        args.rerank_top_k,
    )
    chunk_text_by_id = {
        str(row["chunk_id"]): str(row["text"])
        for row in chunks
    }

    input_path = RAW_DIR / "rerank-2.5-input.jsonl"
    state_path = RAW_DIR / "rerank-2.5-state.json"
    output_path = RAW_DIR / "rerank-2.5-output.jsonl"
    error_path = RAW_DIR / "rerank-2.5-errors.jsonl"
    manifest = build_batch_jsonl(
        queries,
        union_ids,
        chunk_text_by_id,
        args.instruction,
        input_path,
        rerank_query_text,
    )
    batch = execute_batch(
        key_path=args.api_key_path,
        input_path=input_path,
        state_path=state_path,
        output_path=output_path,
        error_path=error_path,
        input_sha256=str(manifest["sha256"]),
        request_count=int(manifest["requests"]),
        model="rerank-2.5",
        resume=args.resume,
        poll_interval_seconds=args.poll_interval,
        submit_retry_seconds=args.submit_retry_seconds,
        metadata={
            "task": "RERANK-BENCH-V1-1.6",
            "corpus_sha256": CORPUS_SHA256,
            "candidate_strategy": "union-top20",
        },
    )
    if batch["status"] != "completed":
        raise RuntimeError(
            "Voyage batch did not complete fully: "
            f"status={batch['status']}, request_counts={batch['request_counts']}"
        )
    score_rows, usage, errors = parse_batch_output(
        output_path.read_text(encoding="utf-8"),
        queries,
        union_ids,
    )
    if errors:
        sanitized = errors[:10]
        raise RuntimeError(
            f"Voyage batch output incomplete: errors={json.dumps(sanitized, ensure_ascii=False)}"
        )
    if len(score_rows) != len(queries):
        raise RuntimeError(
            f"Voyage batch output count diverged: {len(score_rows)} != {len(queries)}"
        )

    usage.update(
        {
            "retries": int(batch["submit_retries"]),
            "seconds": float(batch["wall_seconds"]),
            "estimated_standard_price_usd": round(
                int(usage["tokens"]) * 0.05 / 1_000_000,
                8,
            ),
            "charged_cost_usd": None,
        }
    )
    runtime = {
        "backend": "Voyage Batch API",
        "transport": "batch",
        "model": "rerank-2.5",
        "usage": usage,
        "batch": batch,
        "input_manifest": {
            key: value
            for key, value in manifest.items()
            if key != "query_ids"
        },
        "latency_p50_seconds": None,
        "latency_p95_seconds": None,
        "latency_max_seconds": None,
    }
    reranker_id = "voyage_rerank_2_5"
    score_path = SCORE_DIR / "voyage_rerank_2_5.json"
    score_payload = _score_payload(
        reranker_id,
        {
            "id": "rerank-2.5",
            "provider": "Voyage AI",
            "api_model": True,
            "transport": "batch",
        },
        runtime,
        queries,
        score_rows,
        union_ids,
        args.instruction,
    )
    atomic_json(score_path, score_payload)
    pipelines = _evaluate_and_write_pipelines(
        reranker_id,
        variants,
        candidates,
        queries,
        score_rows,
        args.rerank_top_k,
        score_path,
    )
    return {
        "schema_version": "1.0",
        "status": "PASS",
        "reranker_id": reranker_id,
        "transport": "batch",
        "runtime": runtime,
        "pipelines": [row["pipeline_id"] for row in pipelines],
    }


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = run(args)
    except Exception as exc:
        print(
            f"Voyage batch reranker blocked: {type(exc).__name__}: {exc}",
            flush=True,
        )
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
