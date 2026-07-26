#!/usr/bin/env python3
"""Execute Voyage rerank-2.5 for the 4 AUTHORIZED embeddings via the Voyage Batch API.

This mirrors the historical batch execution recorded in
results/reranker/scores/voyage_rerank_2_5.json (backend: Voyage Batch API,
transport: batch, endpoint /v1/rerank, model rerank-2.5, completion_window 12h),
but restricted to the 4 authorized variants and writing to distinct
`-authorized4` artifacts so the historical run is never overwritten.

Protocol guarantees:
- 150 requests, one per query.
- each request carries the FULL union of top-20 candidates (no split, no merge).
- only the 4 authorized variants (no fifth combination).
- free tier only; no payment method; charged_cost_usd = null (free tokens).
- checkpoint of batch_id via the `-authorized4` state file (resume/reuse).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
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
    candidate_ids,
    evaluate_reranker_effect,
    scores_to_rankings,
)
from holo_benchmark.voyage_batch import (  # noqa: E402
    VoyageBatchHTTPError,
    build_batch_jsonl,
    execute_batch,
    parse_batch_output,
)
from reranker_execution import (  # noqa: E402
    DEFAULT_KEY_PATH,
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
            "queries": [
                {
                    "query_id": qid,
                    "candidates": [{"chunk_id": cid} for cid in cand[qid]],
                }
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


def estimate_tokens_from_jsonl(input_path: Path) -> int:
    total = 0
    for line in input_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        body = obj.get("body") or {}
        q = body.get("query") or ""
        docs = body.get("documents") or []
        total += max(1, (sum(len(d) for d in docs) + len(q)) // 4)
    return total


def run_comparison(input_path: Path, union_ids, query_ids, measured_tokens_path):
    lines = [ln for ln in input_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    n_requests = len(lines)

    # 1) 150 requisições
    assert n_requests == 150, f"expected 150 requests, got {n_requests}"

    # 2) candidatos completos por consulta (no truncation) + 3) nenhuma consulta dividida
    custom_ids = []
    per_query_counts = []
    for ln in lines:
        obj = json.loads(ln)
        custom_ids.append(obj["custom_id"])
        docs = obj["body"]["documents"]
        per_query_counts.append(len(docs))
    assert custom_ids == query_ids, "custom_id order diverges from frozen queries"
    assert len(set(custom_ids)) == 150, "duplicate custom_id (query split detected)"
    for i, (cnt, ids) in enumerate(zip(per_query_counts, union_ids, strict=True)):
        assert cnt == len(ids), (
            f"query {custom_ids[i]} documents({cnt}) != union({len(ids)}) -> split/truncated"
        )

    # 4) nenhuma quinta combinação: apenas as 4 variantes autorizadas
    used_variants = set(AUTHORIZED_VARIANTS)
    assert len(used_variants) == 4, "expected exactly 4 authorized variants"

    est_chars = estimate_tokens_from_jsonl(input_path)
    measured = None
    if measured_tokens_path and Path(measured_tokens_path).is_file():
        raw = read_json(Path(measured_tokens_path))
        vals = [r[2] for r in raw if isinstance(r, list) and len(r) >= 3 and r[2] > 0]
        measured = sum(vals)
    report = {
        "schema_version": "1.0",
        "stage": "pre-execution-comparison",
        "reranker_id": "voyage_rerank_2_5",
        "transport": "batch",
        "requests": n_requests,
        "distinct_queries": len(set(custom_ids)),
        "variants_used": sorted(used_variants),
        "variant_count": len(used_variants),
        "union_total_slots": sum(len(ids) for ids in union_ids),
        "min_candidates_per_query": min(len(ids) for ids in union_ids),
        "max_candidates_per_query": max(len(ids) for ids in union_ids),
        "full_candidates_per_query": True,
        "query_split": False,
        "fifth_combination": False,
        "estimated_tokens_chars_div4": est_chars,
        "estimated_tokens_voyage_count": measured,
        "historical_reference_tokens": 2275458,
        "historical_reference_requests": 150,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    out = RAW_DIR / "authorized4_comparison.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def run(args: argparse.Namespace) -> dict[str, Any]:
    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    unauthorized = set(variants) - set(AUTHORIZED_VARIANTS)
    if unauthorized:
        raise SystemExit(f"UNAUTHORIZED variants rejected: {sorted(unauthorized)}")

    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    chunk_text_by_id = {str(c["chunk_id"]): str(c["text"]) for c in chunks}
    payloads = load_authorized_candidates(variants)
    manifests = build_manifests(payloads)
    union_ids = build_union_candidates(manifests, RERANK_TOP_K)
    query_ids = [str(q["query_id"]) for q in queries]

    input_path = RAW_DIR / "rerank-2.5-input-authorized4.jsonl"
    state_path = RAW_DIR / "rerank-2.5-state-authorized4.json"
    output_path = RAW_DIR / "rerank-2.5-output-authorized4.jsonl"
    error_path = RAW_DIR / "rerank-2.5-errors-authorized4.jsonl"

    manifest = build_batch_jsonl(
        queries,
        union_ids,
        chunk_text_by_id,
        args.instruction,
        input_path,
        rerank_query_text,
    )
    print(f"[comparison] building JSONL: requests={manifest['requests']} "
          f"pairs={manifest['pairs']} bytes={manifest['bytes']} "
          f"sha256={manifest['sha256']}", flush=True)

    report = run_comparison(input_path, union_ids, query_ids, args.measured_tokens)
    print("[comparison] PASS:", json.dumps({
        "requests": report["requests"],
        "distinct_queries": report["distinct_queries"],
        "variants_used": report["variants_used"],
        "full_candidates_per_query": report["full_candidates_per_query"],
        "query_split": report["query_split"],
        "fifth_combination": report["fifth_combination"],
        "estimated_tokens_chars_div4": report["estimated_tokens_chars_div4"],
        "estimated_tokens_voyage_count": report["estimated_tokens_voyage_count"],
    }, ensure_ascii=False), flush=True)

    if args.dry_run:
        print("[dry-run] skipping Batch API submission as requested.", flush=True)
        return {"status": "DRY_RUN", "comparison": report}

    # ---- Batch API submission (free tier, no payment) ----
    print("[batch] submitting via Voyage Batch API (endpoint /v1/rerank, "
          f"model rerank-2.5, completion_window 12h)...", flush=True)
    try:
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
                "task": "RERANK-BENCH-V1-1.6-AUTH4",
                "corpus_sha256": CORPUS_SHA256,
                "candidate_strategy": "union-top20",
                "variants": ",".join(variants),
            },
        )
    except VoyageBatchHTTPError as exc:
        # Determine the exact failing step from checkpoint state.
        step = "unknown"
        if state_path.is_file():
            st = read_json(state_path)
            if not st.get("input_file_id"):
                step = "upload-input-file (/v1/files)"
            elif not st.get("batch_id"):
                step = "create-batch (/v1/batches)"
            else:
                step = "poll-or-retrieve-output (/v1/batches/<id>)"
        print(f"Voyage Batch API REJECTED the free account.\n"
              f"  HTTP status : {exc.status_code}\n"
              f"  step        : {step}\n"
              f"  full message: {exc.message}", flush=True)
        raise SystemExit(2)

    if batch["status"] != "completed":
        print(f"Voyage batch did not complete: status={batch['status']} "
              f"request_counts={batch['request_counts']}", flush=True)
        raise SystemExit(2)

    score_rows, usage, errors = parse_batch_output(
        output_path.read_text(encoding="utf-8"),
        queries,
        union_ids,
    )
    if errors:
        print(f"Voyage batch output had errors: {json.dumps(errors[:10], ensure_ascii=False)}",
              flush=True)
        raise SystemExit(2)
    if len(score_rows) != len(queries):
        print(f"Voyage batch output count diverged: {len(score_rows)} != {len(queries)}",
              flush=True)
        raise SystemExit(2)

    usage.update({
        "retries": int(batch["submit_retries"]),
        "seconds": float(batch["wall_seconds"]),
        "estimated_standard_price_usd": round(
            int(usage["tokens"]) * 0.05 / 1_000_000, 8),
        "charged_cost_usd": None,
        "tier": "free (no payment method; 200M free tokens, no charge)",
    })
    runtime = {
        "backend": "Voyage Batch API",
        "transport": "batch",
        "model": "rerank-2.5",
        "usage": usage,
        "batch": batch,
        "input_manifest": {
            k: v for k, v in manifest.items() if k != "query_ids"
        },
        "latency_p50_seconds": None,
        "latency_p95_seconds": None,
        "latency_max_seconds": None,
    }
    reranker_id = "voyage_rerank_2_5"
    score_path = SCORE_DIR / "voyage_rerank_2_5_authorized4.json"
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
    score_path.parent.mkdir(parents=True, exist_ok=True)
    score_path.write_text(
        json.dumps(score_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[batch] wrote score artifact: {score_path}", flush=True)

    pipelines = _evaluate_and_write_pipelines(
        reranker_id,
        variants,
        payloads,
        queries,
        score_rows,
        RERANK_TOP_K,
        score_path,
    )
    print(f"[batch] wrote {len(pipelines)} pipelines to "
          f"{PIPELINE_DIR / reranker_id}/", flush=True)
    return {
        "schema_version": "1.0",
        "status": "PASS",
        "reranker_id": reranker_id,
        "transport": "batch",
        "runtime": runtime,
        "pipelines": [row["pipeline_id"] for row in pipelines],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default=",".join(AUTHORIZED_VARIANTS))
    ap.add_argument("--instruction", default=DEFAULT_RERANK_INSTRUCTION)
    ap.add_argument("--api-key-path", type=Path, default=DEFAULT_KEY_PATH)
    ap.add_argument("--dry-run", action="store_true",
                    help="build + compare JSONL only; do NOT submit to Batch API")
    ap.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--poll-interval", type=float, default=60.0)
    ap.add_argument("--submit-retry-seconds", type=float, default=1800.0)
    ap.add_argument("--measured-tokens", default="/tmp/voyage_real_tokens.json")
    args = ap.parse_args()
    try:
        result = run(args)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"Voyage batch authorized4 blocked: {type(exc).__name__}: {exc}", flush=True)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
