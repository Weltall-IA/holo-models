from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from holo_benchmark.reranker_runtime import (
    CORPUS_SHA256,
    atomic_json,
    discover_qwen_rerankers,
    load_frozen_dataset,
    select_qwen_reranker,
)

PROJECT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_ROOT.parents[1]
RESULTS_DIR = PROJECT_ROOT / "results" / "reranker"


def preflight(args: argparse.Namespace) -> dict[str, Any]:
    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    blockers: list[str] = []

    if args.qwen_model_path == "auto":
        qwen_candidates = discover_qwen_rerankers(REPO_ROOT)
        if not qwen_candidates:
            blockers.append("no Qwen reranker discovered")
    else:
        try:
            qwen_candidates = [
                select_qwen_reranker(REPO_ROOT, args.qwen_model_path)
            ]
        except Exception as exc:
            qwen_candidates = []
            blockers.append(
                f"invalid explicit Qwen reranker: {type(exc).__name__}: {exc}"
            )

    paths = {
        "embeddinggemma": (
            REPO_ROOT
            / "embed"
            / "embeddinggemma_gguf"
            / "embeddinggemma-300M-Q8_0.gguf"
        ),
        "voyage4_nano": REPO_ROOT / "embed" / "voyage4_nano",
        "voyage_large_documents_checkpoint": (
            PROJECT_ROOT
            / "results"
            / "raw"
            / "voyage"
            / "voyage-4-large"
            / "documents.json"
        ),
        "voyage_large_queries_checkpoint": (
            PROJECT_ROOT
            / "results"
            / "raw"
            / "voyage"
            / "voyage-4-large"
            / "queries.json"
        ),
    }
    blockers.extend(
        f"missing path: {name}"
        for name, path in paths.items()
        if not path.exists()
    )

    payload = {
        "schema_version": "1.0",
        "stage": "1.5.0",
        "status": "READY" if not blockers else "BLOCKED",
        "blockers": blockers,
        "corpus_sha256": CORPUS_SHA256,
        "documents": len(chunks),
        "queries": len(queries),
        "candidate_top_k": args.candidate_top_k,
        "rerank_top_k": args.rerank_top_k,
        "rerank_instruction": args.instruction,
        "paths": {
            name: {"path": str(path), "exists": path.exists()}
            for name, path in paths.items()
        },
        "qwen_candidates": qwen_candidates,
        "qwen_model_path_requested": args.qwen_model_path,
        "voyage_rerank_api_enabled": bool(args.allow_voyage_rerank_api),
        "voyage_key_path_configured": args.api_key_path.expanduser().exists(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(RESULTS_DIR / "preflight.json", payload)
    return payload
