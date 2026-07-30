"""Run Voyage for the canonical Abiray Nemotron 8B variants and finalize deduplication."""
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .artifact_portability import assert_portable_payload, sanitize_host_payload
from .reranker_backends import score_voyage_reranker
from .reranker_metrics import (
    build_union_candidates,
    candidate_ids,
    evaluate_reranker_effect,
    scores_to_rankings,
)
from .reranker_runtime import (
    CORPUS_SHA256,
    DEFAULT_RERANK_INSTRUCTION,
    atomic_json,
    load_frozen_dataset,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parents[1]
RESULTS = PROJECT_ROOT / "results"
CANDIDATES = RESULTS / "reranker" / "candidates"
SCORES = RESULTS / "reranker" / "scores"
PIPELINES = RESULTS / "reranker" / "pipelines"
CHECKPOINT = RESULTS / "raw" / "reranker" / "voyage_rerank_2_5_nemotron_8b_abiray.json"
VARIANTS = (
    "nemotron_8b_abiray_q4_audit_4096",
    "nemotron_8b_abiray_q4_audit_1024",
)
RERANK_TOP_K = 20

DELETE_PATHS = (
    # Legacy ambiguous mirrors.
    "results/gate3/nemotron_8b_abiray_q4.json",
    "results/gate3/nemotron_8b_aqua00_q4.json",
    "results/reranker/candidates/nemotron_8b_abiray_q4.json",
    "results/reranker/candidates/nemotron_8b_aqua00_q4.json",
    "results/reranker/pipelines/qwen_local/nemotron_8b_abiray_q4.json",
    "results/reranker/pipelines/qwen_local/nemotron_8b_aqua00_q4.json",
    # Reexecuted Aqua00 mirror; tensor-identical to selected Abiray.
    "results/gate3/nemotron_8b_aqua00_q4_audit_4096.json",
    "results/gate3/nemotron_8b_aqua00_q4_audit_1024.json",
    "results/reranker/candidates/nemotron_8b_aqua00_q4_audit_4096.json",
    "results/reranker/candidates/nemotron_8b_aqua00_q4_audit_1024.json",
    "results/reranker/pipelines/qwen_local/nemotron_8b_aqua00_q4_audit_4096.json",
    "results/reranker/pipelines/qwen_local/nemotron_8b_aqua00_q4_audit_1024.json",
)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _portable(payload: Mapping[str, Any]) -> dict[str, Any]:
    value = sanitize_host_payload(dict(payload))
    assert_portable_payload(value)
    return value


def _load_candidates() -> dict[str, dict[str, Any]]:
    _, queries = load_frozen_dataset(PROJECT_ROOT)
    expected_ids = [str(row["query_id"]) for row in queries]
    result: dict[str, dict[str, Any]] = {}
    for variant in VARIANTS:
        path = CANDIDATES / f"{variant}.json"
        payload = _read(path)
        if payload.get("variant") != variant:
            raise ValueError(f"variant mismatch: {path}")
        if (payload.get("dataset") or {}).get("corpus_sha256") != CORPUS_SHA256:
            raise ValueError(f"corpus mismatch: {path}")
        rows = list(payload.get("queries") or [])
        if [str(row.get("query_id")) for row in rows] != expected_ids:
            raise ValueError(f"query order mismatch: {path}")
        if any(len(list(row.get("candidates") or [])) != 50 for row in rows):
            raise ValueError(f"candidate top-k mismatch: {path}")
        assert_portable_payload(payload)
        result[variant] = payload
    return result


def run_voyage(args: argparse.Namespace) -> dict[str, Any]:
    payloads = _load_candidates()
    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    rows = {
        variant: [list(item["candidates"]) for item in payloads[variant]["queries"]]
        for variant in VARIANTS
    }
    union_ids = build_union_candidates(rows, RERANK_TOP_K)
    text_by_id = {str(row["chunk_id"]): str(row["text"]) for row in chunks}
    score_rows, runtime = score_voyage_reranker(
        args.api_key_path,
        queries,
        union_ids,
        text_by_id,
        CHECKPOINT,
        args.resume,
        "rerank-2.5",
        args.request_interval,
        DEFAULT_RERANK_INSTRUCTION,
    )
    score_path = SCORES / "voyage_rerank_2_5_nemotron_8b_abiray.json"
    score_payload = _portable(
        {
            "schema_version": "1.0",
            "reranker_id": "voyage_rerank_2_5",
            "model": {"id": "rerank-2.5", "provider": "Voyage AI", "api_model": True},
            "corpus_sha256": CORPUS_SHA256,
            "instruction": DEFAULT_RERANK_INSTRUCTION,
            "runtime": runtime,
            "variants": list(VARIANTS),
            "queries": [
                {
                    "query_id": str(query["query_id"]),
                    "candidate_ids": list(ids),
                    "scores": {chunk_id: float(score_map[chunk_id]) for chunk_id in ids},
                }
                for query, ids, score_map in zip(queries, union_ids, score_rows, strict=True)
            ],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    atomic_json(score_path, score_payload)
    written: list[str] = [str(score_path.relative_to(PROJECT_ROOT))]
    for variant in VARIANTS:
        candidate_rows = [row[:RERANK_TOP_K] for row in rows[variant]]
        evaluation = evaluate_reranker_effect(
            queries,
            candidate_ids(candidate_rows),
            scores_to_rankings(candidate_rows, score_rows),
            RERANK_TOP_K,
        )
        pipeline = _portable(
            {
                "schema_version": "1.0",
                "pipeline_id": f"{variant}__voyage_rerank_2_5",
                "embedding_variant": variant,
                "reranker_id": "voyage_rerank_2_5",
                "candidate_top_k": 50,
                "rerank_top_k": RERANK_TOP_K,
                "score_artifact": str(score_path.relative_to(PROJECT_ROOT)),
                "evaluation": evaluation,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        path = PIPELINES / "voyage_rerank_2_5" / f"{variant}.json"
        atomic_json(path, pipeline)
        written.append(str(path.relative_to(PROJECT_ROOT)))
    return {"status": "PASS", "written": written, "runtime": runtime}


def _load_tool(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load tool: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def finalize(args: argparse.Namespace) -> dict[str, Any]:
    audit = _read(RESULTS / "reranker" / "nemotron_8b_abiray_aqua00_identity_audit.json")
    if audit.get("status") != "IDENTICAL_ALL_TENSOR_CONTENT_METADATA_ONLY_CONTAINER_DIFFERENCE":
        raise ValueError("full tensor identity audit is not accepted")
    for variant in VARIANTS:
        voyage = PIPELINES / "voyage_rerank_2_5" / f"{variant}.json"
        if not voyage.is_file():
            raise FileNotFoundError(f"Voyage pipeline missing: {voyage}")

    removed: list[str] = []
    for relative in DELETE_PATHS:
        path = PROJECT_ROOT / relative
        if path.exists():
            path.unlink()
            removed.append(relative)

    consolidate = _load_tool(
        "consolidate_all_benchmark_results",
        PROJECT_ROOT / "tools" / "consolidate_all_benchmark_results.py",
    )
    canonical_path = PROJECT_ROOT / "ALL_BENCHMARK_RESULTS.json"
    baseline = consolidate.load_json(canonical_path)
    reranker_counts = dict(consolidate.EXPECTED_RERANKER_COUNTS)
    reranker_counts["voyage_rerank_2_5"] = 11
    document = consolidate.build_document(
        REPO_ROOT,
        PROJECT_ROOT,
        baseline,
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_commit=args.source_commit,
        expected_pipeline_count=107,
        expected_pipeline_embeddings=36,
        expected_raw_profile_count=39,
        expected_reranker_counts=reranker_counts,
        expected_raw_source_counts=consolidate.EXPECTED_RAW_SOURCE_COUNTS,
        required_raw_profile_ids=consolidate.REQUIRED_RAW_PROFILE_IDS,
    )
    consolidate.write_json(canonical_path, document)

    updater = _load_tool(
        "update_canonical_readme_tables",
        PROJECT_ROOT / "tools" / "update_canonical_readme_tables.py",
    )
    retained_table1 = tuple(
        row for row in updater.TABLE1_SPECS
        if row[0] not in {"nemotron_8b_abiray_q4", "nemotron_8b_aqua00_q4"}
    )
    updater.TABLE1_SPECS = (
        (
            "nemotron_8b_abiray_q4_audit_4096",
            "A",
            "alta",
            "Nemotron 8B Q4_K_M canônico; Abiray escolhido por maior adoção no Hugging Face; melhor configuração raw usa 4096 dimensões.",
        ),
        (
            "nemotron_8b_abiray_q4_audit_1024",
            "A",
            "alta",
            "Variante truncada para 1024 dimensões; comparar Qwen e Voyage para decidir economia de armazenamento.",
        ),
    ) + retained_table1
    updater.TABLE2_SPECS = tuple(
        row for row in updater.TABLE2_SPECS
        if row[0] not in {"nemotron_8b_abiray_q4", "nemotron_8b_aqua00_q4"}
    )
    readme_path = PROJECT_ROOT / "README.md"
    updated = updater.update_readme(
        readme_path.read_text(encoding="utf-8"),
        document,
        args.revision,
    )
    readme_path.write_text(updated, encoding="utf-8")
    return {
        "status": "PASS",
        "selected_mirror": "Abiray/Nemotron-3-Embed-8B-GGUF",
        "removed": removed,
        "pipelines": document["canonical_scope"]["published_pipeline_artifacts"],
        "raw_profiles": document["canonical_scope"]["raw_embedding_profiles"],
        "voyage_count": document["inventory"]["published_pipeline_count_by_reranker"]["voyage_rerank_2_5"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    voyage = sub.add_parser("voyage")
    voyage.add_argument("--api-key-path", type=Path, required=True)
    voyage.add_argument("--request-interval", type=float, default=1.0)
    voyage.add_argument("--resume", action="store_true")
    final = sub.add_parser("finalize")
    final.add_argument("--source-commit", required=True)
    final.add_argument("--revision", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_voyage(args) if args.command == "voyage" else finalize(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
