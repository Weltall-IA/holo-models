#!/usr/bin/env python3
"""Operational comparison of two embedding + reranker pipelines.

Measures: load time, indexing throughput, query latency p50/p95/max, qps,
peak VRAM/RAM, stability, errors. Quality taken from existing artifacts.

Pipelines compared:
  A) qwen3_embedding_4b_q8_0 + qwen_local (Qwen3-Reranker-0.6B)
  B) nomic_embed_text_v2_moe_q4 + qwen_local (Qwen3-Reranker-0.6B)
"""
from __future__ import annotations

import gc
import json
import os
import signal
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_ROOT.parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from holo_benchmark.gate2_worker import _wait_server
from holo_benchmark.reranker_runtime import (
    DEFAULT_RERANK_INSTRUCTION,
    ResourceSampler,
    _free_port,
    llama_cpp_encode,
    load_frozen_dataset,
    read_json,
)
from holo_benchmark.reranker_backends import rerank_query_text

os.environ["LLAMA_SERVER"] = "/home/alpha/llama.cpp/build/bin/llama-server"
RESULTS_DIR = PROJECT_ROOT / "results" / "operational"
CANDIDATE_DIR = PROJECT_ROOT / "results" / "reranker" / "candidates"
PIPELINE_DIR = PROJECT_ROOT / "results" / "reranker" / "pipelines" / "qwen_local"

RERANKER_SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub/models--Qwen--Qwen3-Reranker-0.6B/snapshots"
    / "e61197ed45024b0ed8a2d74b80b4d909f1255473"
)

VARIANTS = [
    {
        "id": "qwen3_embedding_4b_q8_0",
        "label": "Qwen3-Embedding-4B-Q8_0 + Qwen3-Reranker-0.6B",
        "gguf": "embed/qwen3_embedding_4b_q8_0/Qwen3-Embedding-4B-Q8_0.gguf",
    },
    {
        "id": "nomic_embed_text_v2_moe_q4",
        "label": "nomic-embed-text-v2-moe-Q4_K_M + Qwen3-Reranker-0.6B",
        "gguf": "embed/nomic-embed-text-v2-moe-Q4_K_M/nomic-embed-text-v2-moe.Q4_K_M.gguf",
    },
]

EMBED_BATCH = 64
RERANK_BATCH = 32
SAMPLE_INTERVAL = 0.3


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int((len(ordered) - 1) * p))
    return ordered[idx]


def load_candidates(variant_id: str, expected_query_ids: list[str]) -> dict[str, list[str]]:
    path = CANDIDATE_DIR / f"{variant_id}.json"
    raw = read_json(path)
    cand = raw.get("candidates") or {}
    return {qid: [str(cid) for cid in cand[qid]] for qid in expected_query_ids}


def load_reranker_candidate_texts(
    query_ids: list[str],
    candidates_per_query: dict[str, list[str]],
    chunk_text_by_id: dict[str, str],
) -> dict[str, list[tuple[str, str]]]:
    pairs: dict[str, list[tuple[str, str]]] = {}
    for qid in query_ids:
        pairs[qid] = [
            ("", chunk_text_by_id[cid])
            for cid in candidates_per_query[qid]
            if cid in chunk_text_by_id
        ]
    return pairs


def measure_one_pipeline(
    variant: dict[str, Any],
    chunks: list[dict],
    queries: list[dict],
    chunk_text_by_id: dict[str, str],
    reranker_pairs: dict[str, list[tuple[str, str]]],
) -> dict[str, Any]:
    variant_id = variant["id"]
    gguf_path = REPO_ROOT / variant["gguf"]
    query_ids = [str(q["query_id"]) for q in queries]
    n_queries = len(queries)
    n_docs = len(chunks)

    print(f"\n{'='*60}", flush=True)
    print(f"Pipeline: {variant['label']}", flush=True)
    print(f"GGUF: {gguf_path.name} ({gguf_path.stat().st_size / 1e9:.2f} GB)", flush=True)
    print(f"Documents: {n_docs}  Queries: {n_queries}", flush=True)
    print(f"{'='*60}", flush=True)

    port = _free_port()
    server_proc = None
    result: dict[str, Any] = {"variant": variant_id}

    try:
        with ResourceSampler(interval_seconds=SAMPLE_INTERVAL) as sampler:
            # --- Phase 1: Embedding server load ---
            print("  [1/5] Starting embedding server...", flush=True)
            cmd = [
                os.environ["LLAMA_SERVER"],
                "-m", str(gguf_path),
                "--embedding", "--pooling", "mean", "--embd-normalize", "2",
                "--host", "127.0.0.1", "--port", str(port),
                "-np", "1", "-ngl", "99", "-c", "2048",
            ]
            t_server_start = time.monotonic()
            server_proc = subprocess.Popen(cmd)
            _wait_server(port, server_proc, timeout=300)
            server_load_time = time.monotonic() - t_server_start
            print(f"         Server ready in {server_load_time:.1f}s", flush=True)

            # --- Phase 2: Index all documents ---
            print("  [2/5] Indexing documents...", flush=True)
            doc_texts = [str(c["text"]) for c in chunks]
            t_idx_start = time.monotonic()
            llama_cpp_encode(port, doc_texts, EMBED_BATCH)
            indexing_time = time.monotonic() - t_idx_start
            docs_per_sec = n_docs / indexing_time if indexing_time > 0 else 0
            print(f"         {n_docs} docs in {indexing_time:.1f}s "
                  f"({docs_per_sec:.1f} docs/s)", flush=True)

            # --- Phase 3: Load reranker ---
            print("  [3/5] Loading reranker...", flush=True)
            t_ce_start = time.monotonic()
            try:
                import torch
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise RuntimeError("sentence-transformers/torch required") from exc

            torch.cuda.reset_peak_memory_stats()
            try:
                reranker = CrossEncoder(
                    str(RERANKER_SNAPSHOT),
                    device="cuda",
                    trust_remote_code=True,
                )
            except TypeError:
                reranker = CrossEncoder(
                    str(RERANKER_SNAPSHOT),
                    device="cuda",
                    model_kwargs={"trust_remote_code": True},
                )
            reranker_load_time = time.monotonic() - t_ce_start
            print(f"         Reranker ready in {reranker_load_time:.1f}s", flush=True)

            # --- Phase 4a: Embed all queries ---
            print("  [4/5] Embedding queries + reranking...", flush=True)
            query_texts = [rerank_query_text(q, DEFAULT_RERANK_INSTRUCTION) for q in queries]
            query_embed_times: list[float] = []
            t_qembed_start = time.monotonic()
            for qt in query_texts:
                t0 = time.monotonic()
                llama_cpp_encode(port, [qt], 1)
                query_embed_times.append(time.monotonic() - t0)
            query_embed_total = time.monotonic() - t_qembed_start

            # --- Phase 4b: Rerank all queries ---
            rerank_times: list[float] = []
            errors = 0
            t_rerank_start = time.monotonic()
            for q in queries:
                qid = str(q["query_id"])
                pairs = reranker_pairs.get(qid, [])
                if not pairs:
                    rerank_times.append(0.0)
                    errors += 1
                    continue
                qt = rerank_query_text(q, DEFAULT_RERANK_INSTRUCTION)
                full_pairs = [(qt, doc_text) for _, doc_text in pairs]
                t0 = time.monotonic()
                try:
                    reranker.predict(full_pairs, batch_size=RERANK_BATCH, show_progress_bar=False)
                except Exception:
                    errors += 1
                rerank_times.append(time.monotonic() - t0)
            rerank_total = time.monotonic() - t_rerank_start

            combined_times = [e + r for e, r in zip(query_embed_times, rerank_times, strict=True)]
            print(f"         Query embed: {query_embed_total:.2f}s total, "
                  f"{query_embed_total/n_queries*1000:.1f}ms avg", flush=True)
            print(f"         Rerank: {rerank_total:.2f}s total, "
                  f"{rerank_total/n_queries*1000:.1f}ms avg", flush=True)
            print(f"         Combined: {sum(combined_times):.2f}s total, "
                  f"{sum(combined_times)/n_queries*1000:.1f}ms avg", flush=True)

            # --- Phase 5: Cleanup ---
            print("  [5/5] Stopping server...", flush=True)

        # ResourceSampler context exited; peaks captured.
        peak_rss = sampler.peak_rss_bytes
        peak_gpu = sampler.peak_gpu_memory_bytes

    finally:
        if server_proc is not None:
            server_proc.send_signal(signal.SIGTERM)
            try:
                server_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server_proc.kill()
            server_proc = None
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    combined_sorted = sorted(combined_times)
    qps = n_queries / sum(combined_times) if combined_times else 0

    result.update({
        "embedding_model": variant_id,
        "reranker": "qwen3_reranker_0.6B",
        "n_documents": n_docs,
        "n_queries": n_queries,
        "embedding_server_load_time_s": round(server_load_time, 2),
        "indexing_time_s": round(indexing_time, 2),
        "docs_per_second": round(docs_per_sec, 1),
        "reranker_load_time_s": round(reranker_load_time, 2),
        "query_embed_total_s": round(query_embed_total, 2),
        "query_embed_avg_ms": round(query_embed_total / n_queries * 1000, 2),
        "rerank_total_s": round(rerank_total, 2),
        "rerank_avg_ms": round(rerank_total / n_queries * 1000, 2),
        "combined_total_s": round(sum(combined_times), 2),
        "combined_avg_ms": round(sum(combined_times) / n_queries * 1000, 2),
        "qps": round(qps, 2),
        "latency_p50_ms": round(percentile(combined_times, 0.50) * 1000, 2),
        "latency_p95_ms": round(percentile(combined_times, 0.95) * 1000, 2),
        "latency_max_ms": round(max(combined_times) * 1000, 2),
        "latency_stdev_ms": round(statistics.stdev(combined_times) * 1000, 2) if len(combined_times) > 1 else 0,
        "peak_rss_bytes": peak_rss,
        "peak_rss_gb": round(peak_rss / 1e9, 2),
        "peak_gpu_bytes": peak_gpu,
        "peak_gpu_gb": round(peak_gpu / 1e9, 2),
        "errors": errors,
        "stable": errors == 0 and statistics.stdev(combined_times) < statistics.mean(combined_times) if len(combined_times) > 1 else True,
        "per_query_embed_ms": [round(t * 1000, 2) for t in query_embed_times],
        "per_query_rerank_ms": [round(t * 1000, 2) for t in rerank_times],
        "per_query_combined_ms": [round(t * 1000, 2) for t in combined_times],
    })

    print(f"\n  Results: qps={qps:.2f}  p50={result['latency_p50_ms']}ms  "
          f"p95={result['latency_p95_ms']}ms  max={result['latency_max_ms']}ms  "
          f"peak_gpu={result['peak_gpu_gb']}GB  peak_rss={result['peak_rss_gb']}GB  "
          f"errors={errors}", flush=True)
    return result


def get_quality(variant_id: str) -> dict[str, Any]:
    path = PIPELINE_DIR / f"{variant_id}.json"
    if not path.is_file():
        return {"mrr_at_10": None, "hr_at_10": None, "ndcg_at_10": None}
    data = read_json(path)
    m = data.get("evaluation", {}).get("reranker_metrics", {}).get("summary", {})
    return {
        "mrr_at_10": m.get("MRR@10"),
        "hr_at_10": m.get("HitRate@10"),
        "ndcg_at_10": m.get("nDCG@10"),
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    chunk_text_by_id = {str(c["chunk_id"]): str(c["text"]) for c in chunks}
    query_ids = [str(q["query_id"]) for q in queries]

    all_results: list[dict[str, Any]] = []
    for variant in VARIANTS:
        cand = load_candidates(variant["id"], query_ids)
        pairs = load_reranker_candidate_texts(query_ids, cand, chunk_text_by_id)
        result = measure_one_pipeline(variant, chunks, queries, chunk_text_by_id, pairs)
        quality = get_quality(variant["id"])
        result["quality"] = quality
        all_results.append(result)

    # Build comparison
    a, b = all_results[0], all_results[1]
    comparison = {
        "schema_version": "1.0",
        "task": "operational-comparison",
        "compared_pipelines": [a["variant"], b["variant"]],
        "frozen_corpus": {
            "corpus_sha256": "8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b",
            "n_documents": a["n_documents"],
            "n_queries": a["n_queries"],
        },
        "reranker": {
            "model": "Qwen3-Reranker-0.6B",
            "device": "cuda",
            "shared_by_both_pipelines": True,
            "load_time_s": a["reranker_load_time_s"],
        },
        "quality": {
            a["variant"]: a["quality"],
            b["variant"]: b["quality"],
        },
        "performance": {
            a["variant"]: {k: v for k, v in a.items() if not k.startswith("per_query_")},
            b["variant"]: {k: v for k, v in b.items() if not k.startswith("per_query_")},
        },
        "per_query_detail": {
            a["variant"]: {
                "embed_ms": a["per_query_embed_ms"],
                "rerank_ms": a["per_query_rerank_ms"],
                "combined_ms": a["per_query_combined_ms"],
            },
            b["variant"]: {
                "embed_ms": b["per_query_embed_ms"],
                "rerank_ms": b["per_query_rerank_ms"],
                "combined_ms": b["per_query_combined_ms"],
            },
        },
        "recommendation": {
            "best_quality": max(
                [a, b], key=lambda x: x["quality"]["mrr_at_10"] or 0
            )["variant"],
            "best_performance": max(
                [a, b], key=lambda x: x["qps"]
            )["variant"],
            "best_balance": max(
                [a, b],
                key=lambda x: (x["quality"]["mrr_at_10"] or 0) * x["qps"],
            )["variant"],
        },
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    out_path = RESULTS_DIR / "operational_comparison.json"
    atomic = out_path.with_suffix(out_path.suffix + ".tmp")
    atomic.write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    atomic.replace(out_path)
    print(f"\nResults saved to {out_path}", flush=True)

    # Print summary table
    print("\n" + "=" * 72, flush=True)
    print("OPERATIONAL COMPARISON SUMMARY", flush=True)
    print("=" * 72, flush=True)
    fmt = "{:<35} {:>16} {:>16}"
    print(fmt.format("Metric", a["variant"], b["variant"]), flush=True)
    print("-" * 72, flush=True)
    print(fmt.format("Quality MRR@10", f'{a["quality"]["mrr_at_10"]:.4f}', f'{b["quality"]["mrr_at_10"]:.4f}'), flush=True)
    print(fmt.format("Load time (embed+rerank)", f'{a["embedding_server_load_time_s"]:.1f}s', f'{b["embedding_server_load_time_s"]:.1f}s'), flush=True)
    print(fmt.format("Indexing time", f'{a["indexing_time_s"]:.1f}s', f'{b["indexing_time_s"]:.1f}s'), flush=True)
    print(fmt.format("Docs/second", f'{a["docs_per_second"]:.0f}', f'{b["docs_per_second"]:.0f}'), flush=True)
    print(fmt.format("Query combined avg", f'{a["combined_avg_ms"]:.1f}ms', f'{b["combined_avg_ms"]:.1f}ms'), flush=True)
    print(fmt.format("Latency p50", f'{a["latency_p50_ms"]:.1f}ms', f'{b["latency_p50_ms"]:.1f}ms'), flush=True)
    print(fmt.format("Latency p95", f'{a["latency_p95_ms"]:.1f}ms', f'{b["latency_p95_ms"]:.1f}ms'), flush=True)
    print(fmt.format("Latency max", f'{a["latency_max_ms"]:.1f}ms', f'{b["latency_max_ms"]:.1f}ms'), flush=True)
    print(fmt.format("QPS", f'{a["qps"]:.2f}', f'{b["qps"]:.2f}'), flush=True)
    print(fmt.format("Peak GPU", f'{a["peak_gpu_gb"]:.2f} GB', f'{b["peak_gpu_gb"]:.2f} GB'), flush=True)
    print(fmt.format("Peak RAM (RSS)", f'{a["peak_rss_gb"]:.2f} GB', f'{b["peak_rss_gb"]:.2f} GB'), flush=True)
    print(fmt.format("Errors", str(a["errors"]), str(b["errors"])), flush=True)
    print(fmt.format("Stable", str(a["stable"]), str(b["stable"])), flush=True)
    print("=" * 72, flush=True)
    print(f"\nBest quality: {comparison['recommendation']['best_quality']}", flush=True)
    print(f"Best performance: {comparison['recommendation']['best_performance']}", flush=True)
    print(f"Best balance: {comparison['recommendation']['best_balance']}", flush=True)


if __name__ == "__main__":
    main()
