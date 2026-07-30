"""Finalize canonical Abiray selection even when Voyage is unavailable."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import nemotron_8b_abiray_finalize as base
from .reranker_runtime import atomic_json

BLOCKED_PATH = (
    base.RESULTS
    / "reranker"
    / "voyage_rerank_2_5_nemotron_8b_abiray_blocked.json"
)


def voyage_complete() -> bool:
    """Return true only when both authorized Voyage pipelines exist."""
    return all(
        (
            base.PIPELINES
            / "voyage_rerank_2_5"
            / f"{variant}.json"
        ).is_file()
        for variant in base.VARIANTS
    )


def expected_counts(has_voyage: bool) -> tuple[int, int]:
    """Return expected total pipelines and Voyage pipeline count."""
    return (107, 11) if has_voyage else (105, 9)


def write_voyage_blocker() -> None:
    payload = {
        "schema_version": "1.0",
        "status": "BLOCKED_RATE_LIMIT",
        "provider": "Voyage AI",
        "model": "rerank-2.5",
        "variants": list(base.VARIANTS),
        "reason": (
            "Free-tier rate limit remained active after two attempts and a "
            "five-minute cooldown; no Voyage pipeline was published."
        ),
        "observed_limits": {"requests_per_minute": 3, "tokens_per_minute": 10000},
        "billing": "free tier without automatic paid fallback",
        "retry_policy": "deferred; canonical deduplication is not blocked",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(BLOCKED_PATH, payload)


def finalize(args: argparse.Namespace) -> dict[str, Any]:
    audit = base._read(
        base.RESULTS
        / "reranker"
        / "nemotron_8b_abiray_aqua00_identity_audit.json"
    )
    expected_status = (
        "IDENTICAL_ALL_TENSOR_CONTENT_METADATA_ONLY_CONTAINER_DIFFERENCE"
    )
    if audit.get("status") != expected_status:
        raise ValueError("full tensor identity audit is not accepted")

    has_voyage = voyage_complete()
    if not has_voyage:
        write_voyage_blocker()

    removed: list[str] = []
    for relative in base.DELETE_PATHS:
        path = base.PROJECT_ROOT / relative
        if path.exists():
            path.unlink()
            removed.append(relative)

    consolidate = base._load_tool(
        "consolidate_all_benchmark_results",
        base.PROJECT_ROOT / "tools" / "consolidate_all_benchmark_results.py",
    )
    pipeline_count, voyage_count = expected_counts(has_voyage)
    reranker_counts = dict(consolidate.EXPECTED_RERANKER_COUNTS)
    reranker_counts["voyage_rerank_2_5"] = voyage_count

    canonical_path = base.PROJECT_ROOT / "ALL_BENCHMARK_RESULTS.json"
    baseline = consolidate.load_json(canonical_path)
    document = consolidate.build_document(
        base.REPO_ROOT,
        base.PROJECT_ROOT,
        baseline,
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_commit=args.source_commit,
        expected_pipeline_count=pipeline_count,
        expected_pipeline_embeddings=36,
        expected_raw_profile_count=39,
        expected_reranker_counts=reranker_counts,
        expected_raw_source_counts=consolidate.EXPECTED_RAW_SOURCE_COUNTS,
        required_raw_profile_ids=consolidate.REQUIRED_RAW_PROFILE_IDS,
    )
    document["nemotron_8b_mirror_selection"] = {
        "selected": "Abiray/Nemotron-3-Embed-8B-GGUF",
        "removed_equivalent_mirror": "Aqua00/Nemotron-3-Embed-8B-GGUF",
        "identity_audit": (
            "results/reranker/"
            "nemotron_8b_abiray_aqua00_identity_audit.json"
        ),
        "reason": "tensor-identical mirrors; Abiray retained by higher HF adoption",
    }
    document["voyage_nemotron_8b_status"] = (
        {
            "status": "COMPLETED",
            "pipelines": [
                f"{variant}__voyage_rerank_2_5" for variant in base.VARIANTS
            ],
        }
        if has_voyage
        else {
            "status": "BLOCKED_RATE_LIMIT",
            "artifact": str(BLOCKED_PATH.relative_to(base.PROJECT_ROOT)),
            "published_pipeline_count": 0,
        }
    )
    consolidate.write_json(canonical_path, document)

    updater = base._load_tool(
        "update_canonical_readme_tables",
        base.PROJECT_ROOT / "tools" / "update_canonical_readme_tables.py",
    )
    retained_table1 = tuple(
        row
        for row in updater.TABLE1_SPECS
        if row[0]
        not in {"nemotron_8b_abiray_q4", "nemotron_8b_aqua00_q4"}
    )
    voyage_note = (
        "Voyage 2.5 publicado."
        if has_voyage
        else "Voyage 2.5 bloqueado por rate limit da conta gratuita; raw e Qwen permanecem válidos."
    )
    updater.TABLE1_SPECS = (
        (
            "nemotron_8b_abiray_q4_audit_4096",
            "A",
            "alta",
            "Nemotron 8B Q4_K_M canônico; Abiray selecionado; melhor configuração raw. "
            + voyage_note,
        ),
        (
            "nemotron_8b_abiray_q4_audit_1024",
            "A",
            "alta",
            "Variante 1024; Qwen recupera parte da perda dimensional. "
            + voyage_note,
        ),
    ) + retained_table1
    updater.TABLE2_SPECS = tuple(
        row
        for row in updater.TABLE2_SPECS
        if row[0]
        not in {"nemotron_8b_abiray_q4", "nemotron_8b_aqua00_q4"}
    )
    readme_path = base.PROJECT_ROOT / "README.md"
    updated = updater.update_readme(
        readme_path.read_text(encoding="utf-8"),
        document,
        args.revision,
    )
    readme_path.write_text(updated, encoding="utf-8")

    return {
        "status": "PASS_WITH_EXTERNAL_BLOCKER" if not has_voyage else "PASS",
        "selected_mirror": "Abiray/Nemotron-3-Embed-8B-GGUF",
        "removed": removed,
        "voyage_status": "COMPLETED" if has_voyage else "BLOCKED_RATE_LIMIT",
        "pipelines": document["canonical_scope"]["published_pipeline_artifacts"],
        "embeddings": document["canonical_scope"]["unique_embeddings"],
        "raw_profiles": document["canonical_scope"]["raw_embedding_profiles"],
        "voyage_count": document["inventory"][
            "published_pipeline_count_by_reranker"
        ]["voyage_rerank_2_5"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--revision", required=True)
    return parser.parse_args()


def main() -> int:
    result = finalize(parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
