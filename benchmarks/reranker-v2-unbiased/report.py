from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

from metrics import aggregate, bootstrap_ci, paired_bootstrap_delta

BENCH_DIR = Path(__file__).resolve().parent
MODEL_ORDER = ("nemotron_1b_v2", "jina_v35", "qwen3_06b", "ettin_400m")
DISPLAY = {
    "nemotron_1b_v2": "Nemotron 1B v2",
    "jina_v35": "Jina v3.5",
    "qwen3_06b": "Qwen3-Reranker-0.6B",
    "ettin_400m": "Ettin 400M",
}


def load_jsonl(path: Path) -> List[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def percentile(sorted_values: Sequence[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("empty percentile")
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = (len(sorted_values) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return sorted_values[lo]
    w = pos - lo
    return sorted_values[lo] * (1 - w) + sorted_values[hi] * w


def dataset_query_ids(query_rows: Sequence[dict]) -> Dict[str, List[str]]:
    by_dataset: Dict[str, List[str]] = {}
    for row in query_rows:
        by_dataset.setdefault(str(row.get("dataset", "unknown")), []).append(str(row["query_id"]))
    return by_dataset


def dimension_query_ids(
    query_rows: Sequence[dict], field: str
) -> Dict[str, List[str]]:
    by_dimension: Dict[str, List[str]] = {}
    for row in query_rows:
        value = str(row.get(field, "unknown"))
        by_dimension.setdefault(value, []).append(str(row["query_id"]))
    return by_dimension


def macro_metric(
    per_query: Mapping[str, Mapping[str, float]],
    by_dataset: Mapping[str, Sequence[str]],
    metric: str,
) -> float:
    dataset_means = [
        statistics.fmean(per_query[qid][metric] for qid in qids)
        for qids in by_dataset.values()
    ]
    return statistics.fmean(dataset_means)


def stratified_macro_ci(
    per_query: Mapping[str, Mapping[str, float]],
    by_dataset: Mapping[str, Sequence[str]],
    metric: str,
    *,
    seed: int = 20260904,
    resamples: int = 10_000,
    confidence: float = 0.95,
) -> Tuple[float, float]:
    rng = random.Random(seed)
    reps: List[float] = []
    datasets = list(by_dataset.values())
    for _ in range(resamples):
        ds_means = []
        for qids in datasets:
            sampled = [qids[rng.randrange(len(qids))] for _ in qids]
            ds_means.append(statistics.fmean(per_query[qid][metric] for qid in sampled))
        reps.append(statistics.fmean(ds_means))
    reps.sort()
    alpha = (1.0 - confidence) / 2.0
    return percentile(reps, alpha), percentile(reps, 1.0 - alpha)


def stratified_macro_delta(
    a: Mapping[str, Mapping[str, float]],
    b: Mapping[str, Mapping[str, float]],
    by_dataset: Mapping[str, Sequence[str]],
    metric: str,
    *,
    seed: int = 20260904,
    resamples: int = 10_000,
    confidence: float = 0.95,
) -> dict:
    if set(a) != set(b):
        raise ValueError("Paired GENERAL comparison requires identical query IDs")
    rng = random.Random(seed)
    reps: List[float] = []
    datasets = list(by_dataset.values())

    for _ in range(resamples):
        ds_deltas = []
        for qids in datasets:
            sampled = [qids[rng.randrange(len(qids))] for _ in qids]
            ds_deltas.append(
                statistics.fmean(a[qid][metric] - b[qid][metric] for qid in sampled)
            )
        reps.append(statistics.fmean(ds_deltas))

    reps.sort()
    alpha = (1.0 - confidence) / 2.0
    lo = percentile(reps, alpha)
    hi = percentile(reps, 1.0 - alpha)
    mean = statistics.fmean(
        statistics.fmean(a[qid][metric] - b[qid][metric] for qid in qids)
        for qids in datasets
    )
    if lo > 0:
        verdict = "a_wins"
    elif hi < 0:
        verdict = "b_wins"
    else:
        verdict = "inconclusive"
    return {"mean_delta": mean, "ci_low": lo, "ci_high": hi, "verdict": verdict}


def fmt_ci(value: float, ci: Tuple[float, float]) -> str:
    return f"{value:.4f} [{ci[0]:.4f}, {ci[1]:.4f}]"


def verify_results(results: Mapping[str, dict], query_rows: Sequence[dict]) -> None:
    expected_qids = {str(row["query_id"]) for row in query_rows}
    candidate_fingerprints = None
    for key, payload in results.items():
        if not payload.get("measured") or payload.get("projected"):
            raise RuntimeError(f"{key}: V2 accepts measured, non-projected results only")
        actual_qids = set(payload.get("per_query", {}))
        if actual_qids != expected_qids:
            raise RuntimeError(
                f"{key}: query IDs differ from frozen data "
                f"(expected={len(expected_qids)} actual={len(actual_qids)})"
            )
        fingerprint = payload.get("candidate_files")
        if candidate_fingerprints is None:
            candidate_fingerprints = fingerprint
        elif fingerprint != candidate_fingerprints:
            raise RuntimeError(f"{key}: candidate fingerprint differs from other models")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a statistically paired reranker-v2 report.")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--resamples", type=int, default=10_000)
    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    manifest = json.loads((data_dir / "freeze_manifest.json").read_text(encoding="utf-8"))
    query_rows = load_jsonl(data_dir / "queries.jsonl")
    track = str(manifest["track"]).upper()

    result_dir = BENCH_DIR / "results" / data_dir.name
    results: Dict[str, dict] = {}
    for key in MODEL_ORDER:
        path = result_dir / f"{key}.json"
        if path.exists():
            results[key] = json.loads(path.read_text(encoding="utf-8"))

    missing = [key for key in MODEL_ORDER if key not in results]
    if missing and not args.allow_partial:
        raise SystemExit(
            "Missing measured results: "
            + ", ".join(missing)
            + ". Use --allow-partial only for an explicitly partial report."
        )
    if len(results) < 2:
        raise SystemExit("Need at least two model results for a comparison")

    verify_results(results, query_rows)

    group_ids = {str(row["query_id"]): str(row.get("group_id", row["query_id"])) for row in query_rows}
    by_dataset = dataset_query_ids(query_rows)

    model_summary: Dict[str, dict] = {}
    for key, payload in results.items():
        per_query = payload["per_query"]
        if track == "GENERAL":
            ndcg = macro_metric(per_query, by_dataset, "ndcg@10")
            mrr = macro_metric(per_query, by_dataset, "mrr@10")
            ndcg_ci = stratified_macro_ci(
                per_query, by_dataset, "ndcg@10", resamples=args.resamples
            )
            mrr_ci = stratified_macro_ci(
                per_query, by_dataset, "mrr@10", resamples=args.resamples
            )
        else:
            agg = aggregate(per_query)
            ndcg = agg["ndcg@10"]
            mrr = agg["mrr@10"]
            ndcg_ci = bootstrap_ci(
                per_query,
                "ndcg@10",
                group_ids=group_ids,
                resamples=args.resamples,
            )
            mrr_ci = bootstrap_ci(
                per_query,
                "mrr@10",
                group_ids=group_ids,
                resamples=args.resamples,
            )

        model_summary[key] = {
            "ndcg@10": ndcg,
            "ndcg@10_ci95": {"low": ndcg_ci[0], "high": ndcg_ci[1]},
            "mrr@10": mrr,
            "mrr@10_ci95": {"low": mrr_ci[0], "high": mrr_ci[1]},
            "aggregate_query_weighted": aggregate(per_query),
            "efficiency": payload["efficiency"],
        }

    pairwise: Dict[str, dict] = {}
    for a, b in combinations(results, 2):
        pair_key = f"{a}__vs__{b}"
        pairwise[pair_key] = {}
        for metric in ("ndcg@10", "mrr@10"):
            if track == "GENERAL":
                delta = stratified_macro_delta(
                    results[a]["per_query"],
                    results[b]["per_query"],
                    by_dataset,
                    metric,
                    resamples=args.resamples,
                )
            else:
                delta = paired_bootstrap_delta(
                    results[a]["per_query"],
                    results[b]["per_query"],
                    metric,
                    group_ids=group_ids,
                    resamples=args.resamples,
                )
            pairwise[pair_key][metric] = delta

    ranking = sorted(results, key=lambda key: model_summary[key]["ndcg@10"], reverse=True)
    top = ranking[0]
    runner_up = ranking[1]
    if track == "GENERAL":
        top_delta = stratified_macro_delta(
            results[top]["per_query"],
            results[runner_up]["per_query"],
            by_dataset,
            "ndcg@10",
            resamples=args.resamples,
        )
    else:
        top_delta = paired_bootstrap_delta(
            results[top]["per_query"],
            results[runner_up]["per_query"],
            "ndcg@10",
            group_ids=group_ids,
            resamples=args.resamples,
        )

    top_verdict = str(top_delta["verdict"])
    winner = DISPLAY[top] if top_verdict == "a_wins" else "INCONCLUSIVE"

    dataset_decisions: Dict[str, dict] = {}
    if track == "GENERAL":
        for dataset, qids in by_dataset.items():
            dataset_ranking = sorted(
                results,
                key=lambda key: statistics.fmean(
                    results[key]["per_query"][qid]["ndcg@10"] for qid in qids
                ),
                reverse=True,
            )
            dataset_top, dataset_runner_up = dataset_ranking[:2]
            dataset_delta = paired_bootstrap_delta(
                {qid: results[dataset_top]["per_query"][qid] for qid in qids},
                {qid: results[dataset_runner_up]["per_query"][qid] for qid in qids},
                "ndcg@10",
                resamples=args.resamples,
            )
            dataset_verdict = str(dataset_delta["verdict"])
            dataset_decisions[dataset] = {
                "point_estimate_leader": dataset_top,
                "runner_up": dataset_runner_up,
                "quality_winner": dataset_top if dataset_verdict == "a_wins" else None,
                "winner_label": (
                    DISPLAY[dataset_top]
                    if dataset_verdict == "a_wins"
                    else "INCONCLUSIVE"
                ),
                "top_vs_runner_ndcg@10": dataset_delta,
            }

    dimension_groups: Dict[str, Dict[str, List[str]]] = {}
    if track == "HOLO":
        for field in ("category", "language"):
            dimension_groups[field] = dimension_query_ids(query_rows, field)
        for key in results:
            model_summary[key]["by_dimension"] = {
                field: {
                    value: aggregate(
                        {
                            qid: results[key]["per_query"][qid]
                            for qid in qids
                        }
                    )
                    for value, qids in groups.items()
                }
                for field, groups in dimension_groups.items()
            }

    efficiency_summary: Dict[str, dict] = {}
    for key in ranking:
        efficiency = model_summary[key]["efficiency"]
        vram_gib = efficiency["peak_gpu_allocated_mib"] / 1024.0
        ndcg = model_summary[key]["ndcg@10"]
        efficiency_summary[key] = {
            "ndcg_per_peak_gpu_gib": ndcg / vram_gib if vram_gib else 0.0,
            "ndcg_per_latency_p50_s": (
                ndcg / efficiency["latency_p50_s"]
                if efficiency["latency_p50_s"]
                else 0.0
            ),
        }
    best_quality_vram = max(
        ranking, key=lambda key: efficiency_summary[key]["ndcg_per_peak_gpu_gib"]
    )
    best_quality_latency = max(
        ranking, key=lambda key: efficiency_summary[key]["ndcg_per_latency_p50_s"]
    )

    # Keep machine-readable verdicts explicit for consumers of the report.
    for pair_metrics in pairwise.values():
        for delta in pair_metrics.values():
            delta["verdict"] = str(delta["verdict"]).upper()
    top_delta["verdict"] = top_verdict.upper()

    decision = {
        "track": track,
        "point_estimate_leader": top,
        "runner_up": runner_up,
        "quality_winner": top if winner != "INCONCLUSIVE" else None,
        "winner_label": winner,
        "top_vs_runner_ndcg@10": top_delta,
        "dataset_decisions": dataset_decisions,
        "best_quality_per_vram": best_quality_vram,
        "best_quality_per_latency": best_quality_latency,
    }

    lines: List[str] = [
        f"# Reranker V2 — {track}",
        "",
        "All quality numbers below are measured on the same frozen candidate pools. No projected scores are admitted.",
        "",
        "## Quality",
        "",
        "| Model | NDCG@10 (95% CI) | MRR@10 (95% CI) | MAP | Hit@1 | Recall@10 | Recall@20 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key in ranking:
        s = model_summary[key]
        agg = s["aggregate_query_weighted"]
        lines.append(
            f"| {DISPLAY[key]} | "
            f"{fmt_ci(s['ndcg@10'], (s['ndcg@10_ci95']['low'], s['ndcg@10_ci95']['high']))} | "
            f"{fmt_ci(s['mrr@10'], (s['mrr@10_ci95']['low'], s['mrr@10_ci95']['high']))} | "
            f"{agg['map']:.4f} | {agg['hit@1']:.4f} | {agg['recall@10']:.4f} | {agg['recall@20']:.4f} |"
        )

    if track == "GENERAL":
        lines.extend(["", "## Per dataset", ""])
        for dataset, qids in by_dataset.items():
            lines.append(f"### {dataset}")
            lines.append("")
            lines.append("| Model | NDCG@10 | MRR@10 |")
            lines.append("|---|---:|---:|")
            for key in ranking:
                pq = results[key]["per_query"]
                lines.append(
                    f"| {DISPLAY[key]} | "
                    f"{statistics.fmean(pq[qid]['ndcg@10'] for qid in qids):.4f} | "
                    f"{statistics.fmean(pq[qid]['mrr@10'] for qid in qids):.4f} |"
                )
            lines.append("")

        lines.extend(["## Dataset decisions", ""])
        lines.append(
            "| Dataset | Point-estimate leader | NDCG@10 decision vs runner-up | 95% CI |"
        )
        lines.append("|---|---|---|---:|")
        for dataset, dataset_decision in dataset_decisions.items():
            delta = dataset_decision["top_vs_runner_ndcg@10"]
            lines.append(
                f"| {dataset} | {DISPLAY[dataset_decision['point_estimate_leader']]} | "
                f"{dataset_decision['winner_label']} | "
                f"[{delta['ci_low']:+.4f}, {delta['ci_high']:+.4f}] |"
            )

    if track == "HOLO":
        for field, groups in dimension_groups.items():
            lines.extend(["", f"## By {field}", ""])
            lines.append(
                "| Group | Model | NDCG@10 | MRR@10 | MAP | Hit@1 | Recall@10 | Recall@20 |"
            )
            lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
            for value, qids in groups.items():
                for key in ranking:
                    metrics = model_summary[key]["by_dimension"][field][value]
                    lines.append(
                        f"| {value} | {DISPLAY[key]} | {metrics['ndcg@10']:.4f} | "
                        f"{metrics['mrr@10']:.4f} | {metrics['map']:.4f} | "
                        f"{metrics['hit@1']:.4f} | {metrics['recall@10']:.4f} | "
                        f"{metrics['recall@20']:.4f} |"
                    )

    lines.extend(
        [
            "## Paired significance",
            "",
            "| Comparison | Metric | Mean delta | 95% CI | Verdict |",
            "|---|---|---:|---:|---|",
        ]
    )
    for pair_key, metrics in pairwise.items():
        a, b = pair_key.split("__vs__")
        for metric, d in metrics.items():
            lines.append(
                f"| {DISPLAY[a]} − {DISPLAY[b]} | {metric} | "
                f"{d['mean_delta']:+.4f} | [{d['ci_low']:+.4f}, {d['ci_high']:+.4f}] | "
                f"{str(d['verdict']).upper()} |"
            )

    lines.extend(
        [
            "",
            "## Efficiency",
            "",
            "| Model | GPU alloc peak MiB | GPU reserved peak MiB | RSS peak MiB | p50 s | p95 s | queries/s | total s |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for key in ranking:
        e = model_summary[key]["efficiency"]
        lines.append(
            f"| {DISPLAY[key]} | {e['peak_gpu_allocated_mib']:.1f} | "
            f"{e['peak_gpu_reserved_mib']:.1f} | {e['peak_process_rss_mib']:.1f} | "
            f"{e['latency_p50_s']:.3f} | {e['latency_p95_s']:.3f} | "
            f"{e['queries_per_second']:.3f} | {e['total_time_s']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Efficiency trade-offs",
            "",
            "| Model | NDCG@10 | Peak VRAM GiB | p50 s | NDCG/GiB | NDCG/p50 s |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for key in ranking:
        e = model_summary[key]["efficiency"]
        ratios = efficiency_summary[key]
        lines.append(
            f"| {DISPLAY[key]} | {model_summary[key]['ndcg@10']:.4f} | "
            f"{e['peak_gpu_allocated_mib'] / 1024.0:.3f} | {e['latency_p50_s']:.3f} | "
            f"{ratios['ndcg_per_peak_gpu_gib']:.4f} | "
            f"{ratios['ndcg_per_latency_p50_s']:.4f} |"
        )

    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- Point-estimate leader: **{DISPLAY[top]}**.",
            (
                f"- Statistically supported NDCG@10 winner: **{DISPLAY[top]}** "
                f"(paired 95% CI vs {DISPLAY[runner_up]} excludes zero)."
                if winner != "INCONCLUSIVE"
                else f"- **No statistically supported winner** between {DISPLAY[top]} and "
                     f"{DISPLAY[runner_up]} at 95% confidence."
            ),
            f"- Best quality/VRAM: **{DISPLAY[best_quality_vram]}** (NDCG per peak GiB).",
            f"- Best quality/latency: **{DISPLAY[best_quality_latency]}** (NDCG per p50 second).",
            "- GENERAL and HOLO are separate decisions; this report does not combine them into one score.",
            "",
        ]
    )

    output = {
        "benchmark_id": "reranker-v2-unbiased",
        "track": track,
        "data_dir": str(data_dir),
        "measured_only": True,
        "models": model_summary,
        "pairwise": pairwise,
        "decision": decision,
        "efficiency": efficiency_summary,
    }

    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "comparison.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (result_dir / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
