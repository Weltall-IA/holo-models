from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from holo_benchmark.reranker_backends import (
    score_qwen_cross_encoder,
    score_qwen_llama_cpp,
    score_voyage_reranker,
)
from holo_benchmark.reranker_candidates import (
    generate_embeddinggemma_candidates,
    generate_nano_candidates,
    generate_voyage_large_candidates_from_checkpoint,
)
from holo_benchmark.reranker_metrics import (
    build_union_candidates,
    candidate_ids,
    evaluate_reranker_effect,
    scores_to_rankings,
)
from holo_benchmark.reranker_runtime import (
    CANDIDATE_VARIANTS,
    CORPUS_SHA256,
    atomic_json,
    directory_weight_files,
    discover_qwen_rerankers,
    load_frozen_dataset,
    path_size_bytes,
    read_json,
    select_qwen_reranker,
    sha256_file,
)

PROJECT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_ROOT.parents[1]
RESULTS_DIR = PROJECT_ROOT / "results" / "reranker"
CANDIDATE_DIR = RESULTS_DIR / "candidates"
SCORE_DIR = RESULTS_DIR / "scores"
PIPELINE_DIR = RESULTS_DIR / "pipelines"
DEFAULT_KEY_PATH = REPO_ROOT / ".voyage4_token"


def parse_csv(raw: str) -> list[str]:
    values = [value.strip() for value in raw.split(",") if value.strip()]
    if not values:
        raise ValueError("at least one value is required")
    if len(values) != len(set(values)):
        raise ValueError("duplicate values are not allowed")
    return values


def candidate_path(variant: str) -> Path:
    return CANDIDATE_DIR / f"{variant}.json"


def _candidate_rows(
    payload: Mapping[str, Any],
    top_n: int | None = None,
) -> list[list[dict[str, Any]]]:
    rows = [list(item["candidates"]) for item in payload["queries"]]
    return [row[:top_n] if top_n else row for row in rows]


def load_candidate_payloads(
    variants: Sequence[str],
    expected_top_k: int,
) -> dict[str, dict[str, Any]]:
    _, expected_queries = load_frozen_dataset(PROJECT_ROOT)
    expected_query_ids = [str(query["query_id"]) for query in expected_queries]
    payloads: dict[str, dict[str, Any]] = {}
    for variant in variants:
        path = candidate_path(variant)
        if not path.is_file():
            raise RuntimeError(f"candidate artifact missing: {path}")
        payload = read_json(path)
        if payload.get("variant") != variant:
            raise RuntimeError(f"candidate variant mismatch: {path}")
        dataset = payload.get("dataset") or {}
        if dataset.get("corpus_sha256") != CORPUS_SHA256:
            raise RuntimeError(f"candidate corpus hash mismatch: {path}")
        if int(payload.get("candidate_top_k") or 0) < expected_top_k:
            raise RuntimeError(f"candidate artifact has insufficient top-k: {path}")
        query_rows = list(payload.get("queries") or [])
        if len(query_rows) != 150:
            raise RuntimeError(f"candidate query count mismatch: {path}")
        query_ids = [str(row.get("query_id")) for row in query_rows]
        if query_ids != expected_query_ids:
            raise RuntimeError(f"candidate query order mismatch: {path}")
        payloads[variant] = payload
    return payloads


def write_candidate(payload: dict[str, Any]) -> None:
    atomic_json(candidate_path(str(payload["variant"])), payload)


def preflight(args: argparse.Namespace) -> dict[str, Any]:
    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    qwen_candidates = discover_qwen_rerankers(REPO_ROOT)
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
    missing_paths = [name for name, path in paths.items() if not path.exists()]
    blockers = [f"missing path: {name}" for name in missing_paths]
    if not qwen_candidates:
        blockers.append("no Qwen reranker discovered")
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
        "voyage_rerank_api_enabled": bool(args.allow_voyage_rerank_api),
        "voyage_key_path_configured": args.api_key_path.expanduser().exists(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(RESULTS_DIR / "preflight.json", payload)
    return payload


def generate_candidates(args: argparse.Namespace) -> dict[str, Any]:
    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    selected = set(parse_csv(args.variants))
    unknown = selected - set(CANDIDATE_VARIANTS)
    if unknown:
        raise ValueError(f"unknown variants: {', '.join(sorted(unknown))}")
    generated: list[str] = []
    reused: list[str] = []

    def needs(variant: str) -> bool:
        path = candidate_path(variant)
        if args.force or not path.is_file():
            return True
        try:
            load_candidate_payloads([variant], args.candidate_top_k)
            reused.append(variant)
            return False
        except Exception:
            return True

    gemma_variant = "embeddinggemma_768_float32"
    if gemma_variant in selected and needs(gemma_variant):
        write_candidate(
            generate_embeddinggemma_candidates(
                PROJECT_ROOT,
                REPO_ROOT,
                chunks,
                queries,
                args.candidate_top_k,
                args.embedding_batch_size,
                args.device,
            )
        )
        generated.append(gemma_variant)

    nano_variants = {
        "voyage4_nano_1024_float32",
        "voyage4_nano_2048_float32",
        "voyage4_nano_2048_int8",
    }
    pending_nano = {
        variant for variant in selected & nano_variants if needs(variant)
    }
    if pending_nano:
        payloads = generate_nano_candidates(
            PROJECT_ROOT,
            REPO_ROOT,
            chunks,
            queries,
            args.candidate_top_k,
            args.embedding_batch_size,
            args.device,
        )
        for variant in sorted(pending_nano):
            write_candidate(payloads[variant])
            generated.append(variant)

    large_variant = "voyage_4_large_1024_float32"
    if large_variant in selected and needs(large_variant):
        write_candidate(
            generate_voyage_large_candidates_from_checkpoint(
                PROJECT_ROOT,
                chunks,
                queries,
                args.candidate_top_k,
            )
        )
        generated.append(large_variant)

    payload = {
        "schema_version": "1.0",
        "status": "PASS",
        "generated": generated,
        "reused": sorted(set(reused) - set(generated)),
        "variants": sorted(selected),
        "candidate_top_k": args.candidate_top_k,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(RESULTS_DIR / "candidate_summary.json", payload)
    return payload


def _score_payload(
    reranker_id: str,
    model: Mapping[str, Any],
    runtime: Mapping[str, Any],
    queries: Sequence[dict[str, Any]],
    score_rows: Sequence[Mapping[str, float]],
    union_ids: Sequence[Sequence[str]],
    instruction: str,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "reranker_id": reranker_id,
        "model": dict(model),
        "corpus_sha256": CORPUS_SHA256,
        "instruction": instruction,
        "runtime": dict(runtime),
        "queries": [
            {
                "query_id": str(query["query_id"]),
                "candidate_ids": list(ids),
                "scores": {
                    chunk_id: float(score_map[chunk_id]) for chunk_id in ids
                },
            }
            for query, ids, score_map in zip(
                queries,
                union_ids,
                score_rows,
                strict=True,
            )
        ],
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


def _hash_qwen_model(selection: Mapping[str, Any]) -> dict[str, Any]:
    path = Path(str(selection["path"]))
    if path.is_file():
        weights = [
            {
                "file": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        ]
    else:
        weights = [
            {
                "file": str(item.relative_to(path)),
                "bytes": item.stat().st_size,
                "sha256": sha256_file(item),
            }
            for item in directory_weight_files(path)
        ]
    return {
        **dict(selection),
        "path": str(path),
        "bytes": path_size_bytes(path),
        "weight_files": weights,
    }


def _evaluate_and_write_pipelines(
    reranker_id: str,
    variants: Sequence[str],
    candidates: Mapping[str, Mapping[str, Any]],
    queries: Sequence[dict[str, Any]],
    score_rows: Sequence[Mapping[str, float]],
    rerank_top_k: int,
    score_artifact: Path,
) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for variant in variants:
        rows = _candidate_rows(candidates[variant], rerank_top_k)
        base = candidate_ids(rows)
        reranked = scores_to_rankings(rows, score_rows)
        evaluation = evaluate_reranker_effect(
            queries,
            base,
            reranked,
            rerank_top_k,
        )
        payload = {
            "schema_version": "1.0",
            "pipeline_id": f"{variant}__{reranker_id}",
            "embedding_variant": variant,
            "reranker_id": reranker_id,
            "candidate_top_k": int(candidates[variant]["candidate_top_k"]),
            "rerank_top_k": rerank_top_k,
            "score_artifact": str(score_artifact.relative_to(PROJECT_ROOT)),
            "evaluation": evaluation,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        path = PIPELINE_DIR / reranker_id / f"{variant}.json"
        atomic_json(path, payload)
        outputs.append(payload)
    return outputs


def run_qwen(args: argparse.Namespace) -> dict[str, Any]:
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
        str(row["chunk_id"]): str(row["text"]) for row in chunks
    }

    if args.qwen_model_path == "auto":
        selections = discover_qwen_rerankers(REPO_ROOT)
        if not selections:
            raise RuntimeError("no Qwen reranker was discovered")
    else:
        selections = [select_qwen_reranker(REPO_ROOT, args.qwen_model_path)]

    failures: list[dict[str, str]] = []
    score_rows: list[dict[str, float]] | None = None
    runtime: dict[str, Any] | None = None
    selection: dict[str, Any] | None = None
    for candidate in selections:
        path = Path(str(candidate["path"]))
        try:
            if candidate["backend"] == "llama.cpp":
                score_rows, runtime = score_qwen_llama_cpp(
                    path,
                    queries,
                    union_ids,
                    chunk_text_by_id,
                    args.device,
                    args.instruction,
                )
            else:
                score_rows, runtime = score_qwen_cross_encoder(
                    path,
                    queries,
                    union_ids,
                    chunk_text_by_id,
                    args.device,
                    args.reranker_batch_size,
                    args.instruction,
                )
            selection = dict(candidate)
            break
        except Exception as exc:
            failures.append(
                {
                    "path": str(path),
                    "backend": str(candidate["backend"]),
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )
            try:
                import gc
                import torch

                gc.collect()
                if args.device == "cuda":
                    torch.cuda.empty_cache()
            except ImportError:
                pass
            if args.qwen_model_path != "auto":
                raise

    if selection is None or score_rows is None or runtime is None:
        raise RuntimeError(
            f"all discovered Qwen rerankers failed preflight: {failures}"
        )

    model = _hash_qwen_model(selection)
    model["failed_stronger_candidates"] = failures
    reranker_id = "qwen_local"
    score_path = SCORE_DIR / "qwen_local.json"
    score_payload = _score_payload(
        reranker_id,
        model,
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
        "model": model,
        "runtime": runtime,
        "pipelines": [row["pipeline_id"] for row in pipelines],
    }


def run_voyage(args: argparse.Namespace) -> dict[str, Any]:
    if not args.allow_voyage_rerank_api:
        raise RuntimeError(
            "Voyage rerank API is disabled; pass --allow-voyage-rerank-api"
        )
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
        str(row["chunk_id"]): str(row["text"]) for row in chunks
    }
    checkpoint_path = (
        PROJECT_ROOT
        / "results"
        / "raw"
        / "reranker"
        / "voyage_rerank_2_5.json"
    )
    score_rows, runtime = score_voyage_reranker(
        args.api_key_path,
        queries,
        union_ids,
        chunk_text_by_id,
        checkpoint_path,
        args.resume,
        "rerank-2.5",
        args.voyage_request_interval,
        args.instruction,
    )
    reranker_id = "voyage_rerank_2_5"
    score_path = SCORE_DIR / "voyage_rerank_2_5.json"
    score_payload = _score_payload(
        reranker_id,
        {
            "id": "rerank-2.5",
            "provider": "Voyage AI",
            "api_model": True,
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
        "runtime": runtime,
        "pipelines": [row["pipeline_id"] for row in pipelines],
    }
