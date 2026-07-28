from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any, Mapping

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


def _path_basename(path: Path | str) -> str:
    raw = str(path)
    if "\\" in raw:
        return PureWindowsPath(raw).name
    return Path(raw).name


def _portable_path(path: Path | str) -> str:
    raw = str(path)
    if "\\" in raw and PureWindowsPath(raw).is_absolute():
        basename = _path_basename(path)
        return f"<external>/{basename}" if basename else "<external>"
    candidate = Path(path).expanduser()
    try:
        relative = candidate.resolve().relative_to(REPO_ROOT.resolve())
    except (OSError, RuntimeError, ValueError):
        basename = _path_basename(path)
        return f"<external>/{basename}" if basename else "<external>"
    return relative.as_posix() or "."


def _portable_requested_model(value: str) -> str:
    if value == "auto":
        return value
    if Path(value).is_absolute() or "/" in value or "\\" in value:
        return _portable_path(value)
    return value


def _portable_qwen_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    portable = dict(candidate)
    if portable.get("path"):
        portable["path"] = _portable_path(str(portable["path"]))
    return portable


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
        "stage": "1.5.1",
        "status": "READY" if not blockers else "BLOCKED",
        "blockers": blockers,
        "corpus_sha256": CORPUS_SHA256,
        "documents": len(chunks),
        "queries": len(queries),
        "candidate_top_k": args.candidate_top_k,
        "rerank_top_k": args.rerank_top_k,
        "rerank_instruction": args.instruction,
        "paths": {
            name: {"path": _portable_path(path), "exists": path.exists()}
            for name, path in paths.items()
        },
        "qwen_candidates": [
            _portable_qwen_candidate(candidate) for candidate in qwen_candidates
        ],
        "qwen_model_path_requested": _portable_requested_model(
            args.qwen_model_path
        ),
        "voyage_rerank_api_enabled": bool(args.allow_voyage_rerank_api),
        "voyage_key_path_configured": args.api_key_path.expanduser().exists(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(RESULTS_DIR / "preflight.json", payload)
    return payload
