from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from holo_benchmark.metrics import DEFAULT_KS, evaluate_rankings
from holo_benchmark.reranker_metrics import candidate_ids, pipeline_completion
from holo_benchmark.reranker_runtime import (
    CORPUS_SHA256,
    atomic_json,
    load_frozen_dataset,
    read_json,
)
from reranker_execution import (
    PIPELINE_DIR,
    PROJECT_ROOT,
    RESULTS_DIR,
    _candidate_rows,
    load_candidate_payloads,
    parse_csv,
)


REPORT_TITLE = "# Reranker Pipeline Benchmark"


def _baseline_record(
    variant: str,
    payload: Mapping[str, Any],
    queries: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    rankings = candidate_ids(_candidate_rows(payload))
    metrics = evaluate_rankings(queries, rankings, DEFAULT_KS)
    return {
        "pipeline_id": f"{variant}__none",
        "embedding_variant": variant,
        "reranker_id": "none",
        "metrics": metrics,
        "runtime": payload.get("runtime"),
        "model": payload.get("model"),
    }


def _pipeline_record(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    score_path = PROJECT_ROOT / str(payload["score_artifact"])
    score_payload = read_json(score_path)
    return {
        "pipeline_id": payload["pipeline_id"],
        "embedding_variant": payload["embedding_variant"],
        "reranker_id": payload["reranker_id"],
        "metrics": payload["evaluation"]["reranked_metrics"],
        "base_metrics": payload["evaluation"]["base_metrics"],
        "effect": payload["evaluation"]["effect"],
        "reranker_model": score_payload.get("model"),
        "reranker_runtime": score_payload.get("runtime"),
    }


def render_report(summary: Mapping[str, Any]) -> str:
    rows = list(summary["pipelines"])
    rows.sort(
        key=lambda row: (
            -float(row["metrics"]["summary"]["MRR@10"]),
            -float(row["metrics"]["summary"]["nDCG@10"]),
            str(row["pipeline_id"]),
        )
    )
    lines = [
        REPORT_TITLE,
        "",
        f"- Frozen corpus SHA-256: `{CORPUS_SHA256}`",
        f"- Benchmark status: `{summary['status']}`",
        "- Pipelines completed: "
        f"{summary['completed_pipeline_count']} / {summary['expected_pipeline_count']}",
    ]
    missing = list(summary.get("missing_pipelines") or [])
    if missing:
        lines.append("- Missing pipelines: " + ", ".join(f"`{item}`" for item in missing))
    lines.extend(
        [
            "",
            "| Rank | Pipeline | HitRate@1 | HitRate@10 | MRR@10 | nDCG@10 | Rescue | Damage |",
            "|---:|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for rank, row in enumerate(rows, start=1):
        metrics = row["metrics"]["summary"]
        effect = row.get("effect") or {}
        rescue = effect.get("rescue_rate")
        damage = effect.get("damage_rate")
        lines.append(
            "| {rank} | {pipeline} | {hit1:.6f} | {hit10:.6f} | {mrr:.6f} | {ndcg:.6f} | {rescue} | {damage} |".format(
                rank=rank,
                pipeline=row["pipeline_id"],
                hit1=float(metrics["HitRate@1"]),
                hit10=float(metrics["HitRate@10"]),
                mrr=float(metrics["MRR@10"]),
                ndcg=float(metrics["nDCG@10"]),
                rescue="—" if rescue is None else f"{float(rescue):.6f}",
                damage="—" if damage is None else f"{float(damage):.6f}",
            )
        )
    lines.extend(["", "## Embedding resources", ""])
    lines.extend(
        [
            "| Variant | Dimension | Dtype | Vector bytes | Model bytes | Peak VRAM | Total seconds |",
            "|---|---:|---|---:|---:|---:|---:|",
        ]
    )
    for row in rows:
        if row.get("reranker_id") != "none":
            continue
        model = row.get("model") or {}
        runtime = row.get("runtime") or {}
        lines.append(
            "| {variant} | {dimension} | {dtype} | {vector_bytes} | {model_bytes} | {vram} | {seconds} |".format(
                variant=row["embedding_variant"],
                dimension=model.get("dimension", "—"),
                dtype=model.get("vector_dtype", "—"),
                vector_bytes=model.get("bytes_per_vector", "—"),
                model_bytes=model.get(
                    "file_bytes",
                    model.get("snapshot_bytes", "—"),
                ),
                vram=runtime.get(
                    "peak_vram_bytes",
                    runtime.get("peak_gpu_memory_bytes", "—"),
                ),
                seconds=runtime.get(
                    "total_seconds",
                    runtime.get("total_seconds_shared", "—"),
                ),
            )
        )

    lines.extend(["", "## Reranker runtime", ""])
    seen_rerankers: set[str] = set()
    for row in rows:
        reranker_id = str(row.get("reranker_id") or "none")
        if reranker_id == "none" or reranker_id in seen_rerankers:
            continue
        seen_rerankers.add(reranker_id)
        runtime = row.get("reranker_runtime") or {}
        model = row.get("reranker_model") or {}
        total_seconds = runtime.get(
            "total_seconds",
            (runtime.get("usage") or {}).get("seconds"),
        )
        peak_vram = runtime.get(
            "peak_vram_bytes",
            runtime.get("peak_gpu_memory_bytes"),
        )
        lines.extend(
            [
                f"### `{reranker_id}`",
                "",
                f"- Model: `{model.get('name') or model.get('id') or 'unknown'}`",
                f"- Backend: `{runtime.get('backend') or 'unknown'}`",
                f"- Total seconds: `{total_seconds}`",
                "- Latency p50/p95/max: "
                f"`{runtime.get('latency_p50_seconds')}` / "
                f"`{runtime.get('latency_p95_seconds')}` / "
                f"`{runtime.get('latency_max_seconds')}` seconds",
                f"- Peak VRAM: `{peak_vram}` bytes",
                "- Peak process-tree RSS: "
                f"`{runtime.get('peak_process_tree_rss_bytes')}` bytes",
                f"- API usage: `{runtime.get('usage')}`",
                "",
            ]
        )
    lines.extend(
        [
            "The ranking covers only completed pipelines and does not establish statistical significance between near-tied results.",
            "The 2048 int8 variant uses corpus-calibrated scalar quantization with dequantized cosine scoring; native vector-database latency was not measured.",
            "No merge or production choice is implicit.",
            "",
        ]
    )
    return "\n".join(lines)


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    _, queries = load_frozen_dataset(PROJECT_ROOT)
    variants = parse_csv(args.variants)
    candidates = load_candidate_payloads(variants, args.rerank_top_k)
    records = [
        _baseline_record(variant, candidates[variant], queries)
        for variant in variants
    ]
    for reranker_id in ("qwen_local", "voyage_rerank_2_5"):
        directory = PIPELINE_DIR / reranker_id
        if not directory.is_dir():
            continue
        for variant in variants:
            path = directory / f"{variant}.json"
            if path.is_file():
                records.append(_pipeline_record(path))

    completion = pipeline_completion(variants, records)
    summary = {
        "schema_version": "1.0",
        **completion,
        "corpus_sha256": CORPUS_SHA256,
        "candidate_top_k": args.candidate_top_k,
        "rerank_top_k": args.rerank_top_k,
        "pipelines": records,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(RESULTS_DIR / "summary.json", summary)
    report_path = PROJECT_ROOT / "RERANKER_PIPELINE_REPORT.md"
    temporary = report_path.with_suffix(report_path.suffix + ".tmp")
    temporary.write_text(render_report(summary), encoding="utf-8")
    temporary.replace(report_path)
    return summary
