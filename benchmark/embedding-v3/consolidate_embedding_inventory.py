from __future__ import annotations

import argparse
import difflib
import json
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
INVENTORY_PATH = PROJECT_ROOT / "local_model_inventory.json"
REPORT_PATH = PROJECT_ROOT / "LOCAL_MODEL_INVENTORY_REPORT.md"

MODEL_SPECS: tuple[dict[str, str], ...] = (
    {
        "id": "colibri_ptbr",
        "result": "results/gate2/colibri_ptbr.json",
        "backend": "sentence-transformers/CUDA",
        "source": "Gate 2",
    },
    {
        "id": "multilingual_e5_large_instruct",
        "result": "results/gate2/multilingual_e5_large_instruct.json",
        "backend": "sentence-transformers/CUDA",
        "source": "Gate 2",
    },
    {
        "id": "qwen3_embedding_06",
        "result": "results/gate2/qwen3_embedding_06.json",
        "backend": "sentence-transformers/CUDA",
        "source": "Gate 2",
    },
    {
        "id": "bge_m3_dense",
        "result": "results/gate2/bge_m3_dense.json",
        "backend": "sentence-transformers/CUDA",
        "source": "Gate 2",
    },
    {
        "id": "voyage4_nano",
        "result": "results/gate2/voyage4_nano.json",
        "backend": "sentence-transformers/CUDA",
        "source": "Gate 2",
    },
    {
        "id": "qwen3_embedding_8b_gguf",
        "result": "results/gate3/qwen3_embedding_8b_gguf.json",
        "backend": "llama.cpp/CUDA",
        "source": "Gate 3",
    },
    {
        "id": "embeddinggemma_gguf",
        "result": "results/gate3/embeddinggemma_gguf.json",
        "backend": "llama.cpp/CUDA",
        "source": "Gate 3",
    },
    {
        "id": "qwen3_embedding_06_gguf",
        "result": "results/gate3/qwen3_embedding_06_gguf.json",
        "backend": "llama.cpp/CUDA",
        "source": "Gate 3",
    },
    {
        "id": "gte_multilingual_base",
        "result": "results/gate2/gte_multilingual_base.json",
        "backend": "sentence-transformers/CUDA",
        "source": "Patch 1.4.3",
    },
    {
        "id": "voyage-4-large",
        "result": "results/voyage/voyage-4-large.json",
        "backend": "Voyage API",
        "source": "Patch 1.4.4",
    },
    {
        "id": "voyage-context-4",
        "result": "results/voyage/voyage-context-4.json",
        "backend": "Voyage API contextual",
        "source": "Patch 1.4.4",
    },
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _replace_with_diff(path: Path, content: str, *, check: bool) -> bool:
    previous = path.read_text(encoding="utf-8") if path.exists() else ""
    if previous == content:
        return False
    diff = "".join(
        difflib.unified_diff(
            previous.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=str(path),
            tofile=f"{path}.tmp",
        )
    )
    print(diff, end="")
    if check:
        raise RuntimeError(f"arquivo desatualizado: {path}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)
    return True


def _metrics(path: Path) -> tuple[dict[str, float], int | None]:
    payload = _read_json(path)
    summary = dict(payload["metrics"]["summary"])
    usage = payload.get("usage")
    tokens = int(usage["tokens"]) if isinstance(usage, dict) and "tokens" in usage else None
    return summary, tokens


def _correct_inventory(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    models = [dict(model) for model in payload.get("models", [])]
    by_id = {str(model.get("id")): model for model in models}

    for model_id in ("voyage-4-large", "voyage-context-4"):
        model = by_id.get(model_id)
        if model is None:
            raise RuntimeError(f"modelo ausente no inventário: {model_id}")
        if model.get("status") != "BENCHMARKED":
            raise RuntimeError(f"modelo não consolidado como BENCHMARKED: {model_id}")
        model.pop("revision", None)
        evidence = model.get("evidence")
        if not isinstance(evidence, dict) or not evidence.get("api_model"):
            raise RuntimeError(f"identidade de API incompleta: {model_id}")

    status_counts = Counter(str(model.get("status")) for model in models)
    category_counts = Counter(str(model.get("category")) for model in models)
    result["models"] = models
    result["total_models"] = len(models)
    result["by_status"] = {
        "BENCHMARKED": status_counts["BENCHMARKED"],
        "BLOCKED": status_counts["BLOCKED"],
        "HEALTHCHECK_PASSED": status_counts["HEALTHCHECK_PASSED"],
    }
    result["by_category"] = {
        "embedding": category_counts["embedding"],
        "text_llm": category_counts["text_llm"],
        "image": category_counts["image"],
        "audio": category_counts["audio"],
        "video": category_counts["video"],
    }

    if result["total_models"] != 53:
        raise RuntimeError(f"total de modelos divergente: {result['total_models']}")
    if result["by_status"] != {
        "BENCHMARKED": 12,
        "BLOCKED": 19,
        "HEALTHCHECK_PASSED": 22,
    }:
        raise RuntimeError(f"contagens por status divergentes: {result['by_status']}")
    if result["by_category"]["embedding"] != 14:
        raise RuntimeError("contagem de embeddings divergente")
    return result


def _render_report(inventory: dict[str, Any]) -> str:
    embeddings = [
        model for model in inventory["models"] if model.get("category") == "embedding"
    ]
    benchmarked_unique = [
        model
        for model in embeddings
        if model.get("status") == "BENCHMARKED" and not model.get("alias_of")
    ]
    aliases = [model for model in embeddings if model.get("alias_of")]
    blocked = [model for model in embeddings if model.get("status") == "BLOCKED"]

    if (len(benchmarked_unique), len(aliases), len(blocked)) != (11, 1, 2):
        raise RuntimeError(
            "composição de embeddings divergente: "
            f"únicos={len(benchmarked_unique)}, aliases={len(aliases)}, bloqueados={len(blocked)}"
        )

    rows: list[dict[str, Any]] = []
    expected_ids = {str(model["id"]) for model in benchmarked_unique}
    configured_ids = {spec["id"] for spec in MODEL_SPECS}
    if expected_ids != configured_ids:
        raise RuntimeError(
            f"modelos benchmarkados divergentes: inventário={sorted(expected_ids)}, "
            f"configuração={sorted(configured_ids)}"
        )

    for spec in MODEL_SPECS:
        summary, tokens = _metrics(PROJECT_ROOT / spec["result"])
        rows.append(
            {
                **spec,
                "MRR@10": float(summary["MRR@10"]),
                "nDCG@10": float(summary["nDCG@10"]),
                "HitRate@1": float(summary["HitRate@1"]),
                "tokens": tokens,
            }
        )
    ranking = sorted(rows, key=lambda row: row["MRR@10"], reverse=True)

    lines = [
        "# Local Model Inventory Report — v1.4.6",
        "",
        "Generated from canonical benchmark artifacts.",
        "",
        "## Coverage Validation",
        "",
        "```json",
        json.dumps(
            {
                "passed": bool(inventory.get("coverage_validation", {}).get("passed")),
                "finding_count": int(
                    inventory.get("coverage_validation", {}).get("finding_count", 0)
                ),
                "coverage_complete": bool(inventory.get("coverage_complete")),
            },
            ensure_ascii=False,
            indent=2,
        ),
        "```",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
    for status in ("BENCHMARKED", "BLOCKED", "HEALTHCHECK_PASSED"):
        lines.append(f"| {status} | {inventory['by_status'][status]} |")
    lines.extend(
        [
            f"| **Total** | **{inventory['total_models']}** |",
            "",
            "| Category | Count |",
            "|---|---:|",
        ]
    )
    for category in ("embedding", "text_llm", "image", "audio", "video"):
        lines.append(f"| {category} | {inventory['by_category'][category]} |")

    lines.extend(
        [
            "",
            "## Embedding Models (14)",
            "",
            "Composition: **11 benchmarked unique models + 1 verified alias + 2 blocked models = 14 entries**.",
            "",
            "### Canonical benchmark results",
            "",
            "| Rank | ID | Backend | MRR@10 | nDCG@10 | HitRate@1 | Tokens | Source |",
            "|---:|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for rank, row in enumerate(ranking, start=1):
        tokens = f"{row['tokens']:,}".replace(",", ".") if row["tokens"] is not None else "local"
        lines.append(
            f"| {rank} | {row['id']} | {row['backend']} | "
            f"{row['MRR@10']:.6f} | {row['nDCG@10']:.6f} | "
            f"{row['HitRate@1']:.6f} | {tokens} | {row['source']} |"
        )

    alias = aliases[0]
    lines.extend(
        [
            "",
            "### Verified alias",
            "",
            f"- `{alias['id']}` → `{alias['alias_of']}`. It is excluded from the unique-model ranking.",
            "",
            "### Blocked embeddings",
            "",
            "| ID | Reason |",
            "|---|---|",
        ]
    )
    for model in sorted(blocked, key=lambda item: str(item["id"])):
        lines.append(f"| {model['id']} | {model.get('reason') or 'documented block'} |")

    lines.extend(
        [
            "",
            "## Voyage API",
            "",
            "- `voyage-4-large`: 259.246 tokens, 31 requests, 0 retries, US$ 0.00 within the informed allowance.",
            "- `voyage-context-4`: 259.906 tokens, 31 requests, 0 retries, US$ 0.00 within the informed allowance.",
            "- SDK: `voyageai 0.5.0`.",
            "- Frozen corpus SHA-256: `8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b`.",
            "",
            "## Other categories",
            "",
            "The detailed status and structured evidence for text, image, audio and video models remain in `local_model_inventory.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consolidate the canonical embedding inventory and report"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when inventory or report would change",
    )
    args = parser.parse_args()

    inventory = _correct_inventory(_read_json(INVENTORY_PATH))
    report = _render_report(inventory)
    changed_inventory = _replace_with_diff(
        INVENTORY_PATH, _json_text(inventory), check=args.check
    )
    changed_report = _replace_with_diff(REPORT_PATH, report, check=args.check)
    print(
        json.dumps(
            {
                "inventory_changed": changed_inventory,
                "report_changed": changed_report,
                "status_counts": inventory["by_status"],
                "embedding_entries": inventory["by_category"]["embedding"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
