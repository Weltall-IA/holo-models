"""Canonical Nemotron Rerank 1B v2 pipeline runner via Transformers.

The canonical contract originally selected vLLM for ``llama_nemotron_rerank_1b_v2``,
but the model is a ``LlamaBidirectionalForSequenceClassification`` loaded through
``trust_remote_code`` and runs directly with ``transformers``, which is already
available in the local runtime.  vLLM is therefore not a hard requirement.

Scoring uses the official prompt layout ``question:<q>\\n\\npassage:<d>`` with the
``rerank/nemotron-rerank.jinja`` template as reference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .artifact_portability import assert_portable_payload, sanitize_host_payload
from .bitnet_benchmark import _ranking_sha256
from .reranker_metrics import (
    candidate_ids,
    evaluate_reranker_effect,
    scores_to_rankings,
)
from .reranker_runtime import (
    CORPUS_SHA256,
    DEFAULT_RERANK_INSTRUCTION,
    ResourceSampler,
    atomic_json,
    load_frozen_dataset,
    read_json,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_TOP_K = 50
RERANK_TOP_K = 20
MODEL_ID = "llama_nemotron_rerank_1b_v2"
MODEL_REPOSITORY = "nvidia/llama-3.2-nv-rerankqa-1b-v2"
MODEL_WEIGHT_FILE = "model.safetensors"
MODEL_WEIGHT_SHA256 = "7d60ff24db62fe6a639c4c6f4aeac3a3b32ed20939ab72a0be4b019c2219e5e0"
MODEL_LICENSE = "custom NVIDIA"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def validate_model(path: Path) -> tuple[Path, dict[str, Any]]:
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        raise FileNotFoundError(f"model directory missing: {resolved}")
    weight = resolved / MODEL_WEIGHT_FILE
    if not weight.is_file():
        raise FileNotFoundError(f"weight file missing: {weight}")
    weight_sha = _sha256(weight)
    if weight_sha != MODEL_WEIGHT_SHA256:
        raise ValueError(
            f"weight SHA-256 mismatch: expected {MODEL_WEIGHT_SHA256}, found {weight_sha}"
        )
    metadata = resolved / ".cache" / "huggingface" / "download" / f"{MODEL_WEIGHT_FILE}.metadata"
    revision = None
    if metadata.is_file():
        first = metadata.read_text(encoding="utf-8").splitlines()
        revision = first[0].strip() if first else None
    return resolved, {
        "id": MODEL_ID,
        "repository": MODEL_REPOSITORY,
        "revision": revision,
        "backend": "transformers.LlamaBidirectionalForSequenceClassification",
        "license": MODEL_LICENSE,
        "quantization": "native_bf16",
        "weight_file": MODEL_WEIGHT_FILE,
        "weight_bytes": weight.stat().st_size,
        "weight_sha256": weight_sha,
    }


def score_model(
    model_path: Path,
    queries: Sequence[dict[str, Any]],
    union_ids: Sequence[Sequence[str]],
    chunk_text_by_id: Mapping[str, str],
    batch_size: int,
    instruction: str,
) -> tuple[list[dict[str, float]], dict[str, Any]]:
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError("Nemotron requires torch and transformers") from exc
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable")
    torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
    latencies: list[float] = []
    score_rows: list[dict[str, float]] = []
    with ResourceSampler() as resources:
        load_started = time.monotonic()
        tokenizer = AutoTokenizer.from_pretrained(
            str(model_path), trust_remote_code=True, local_files_only=True
        )
        model = AutoModelForSequenceClassification.from_pretrained(
            str(model_path), trust_remote_code=True, torch_dtype="auto", local_files_only=True
        )
        model.eval()
        model.to("cuda")
        load_seconds = time.monotonic() - load_started
        for query, chunk_ids in zip(queries, union_ids, strict=True):
            texts = []
            for chunk_id in chunk_ids:
                query_text = str(query.get("query") or "")
                doc_text = chunk_text_by_id[chunk_id]
                texts.append(f"question:{query_text}\n\npassage:{doc_text}")
            request_started = time.monotonic()
            enc = tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=2048,
                return_tensors="pt",
            ).to("cuda")
            with torch.no_grad():
                out = model(**enc)
            values = out.logits.squeeze(-1).cpu().float().tolist()
            latencies.append(time.monotonic() - request_started)
            if len(values) != len(chunk_ids):
                raise RuntimeError("Nemotron score count mismatch")
            row = {}
            for chunk_id, value in zip(chunk_ids, values, strict=True):
                score = float(value)
                if not math.isfinite(score):
                    raise RuntimeError("Nemotron returned a non-finite score")
                row[chunk_id] = score
            score_rows.append(row)
            del enc, out
            torch.cuda.empty_cache()
        peak_vram = int(torch.cuda.max_memory_allocated())

    ordered = sorted(latencies)

    def percentile(fraction: float) -> float | None:
        if not ordered:
            return None
        index = min(len(ordered) - 1, int((len(ordered) - 1) * fraction))
        return ordered[index]

    runtime = {
        "backend": "transformers.LlamaBidirectionalForSequenceClassification",
        "device": "cuda",
        "load_seconds": round(load_seconds, 4),
        "score_seconds": round(sum(latencies), 4),
        "total_seconds": round(time.monotonic() - started, 4),
        "queries": len(queries),
        "pairs": sum(len(row) for row in union_ids),
        "batch_size": batch_size,
        "latency_p50_seconds": round(percentile(0.50), 4),
        "latency_p95_seconds": round(percentile(0.95), 4),
        "latency_max_seconds": round(max(latencies), 4),
        "peak_vram_bytes": peak_vram,
        **resources.as_dict(),
    }
    if peak_vram <= 0:
        raise RuntimeError("no positive CUDA memory evidence")
    return score_rows, runtime


def load_candidate(
    path: Path,
    profile_id: str,
    query_ids: Sequence[str],
    known_chunk_ids: set[str],
    canonical: Mapping[str, Any],
):
    from .mxbai_panel_benchmark import load_candidate as _load

    return _load(path, profile_id, query_ids, known_chunk_ids, canonical)


def benchmark_profile(args: argparse.Namespace) -> dict[str, Any]:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_DATASETS_OFFLINE", "1")

    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    query_ids = [str(query["query_id"]) for query in queries]
    chunk_text_by_id = {str(chunk["chunk_id"]): str(chunk["text"]) for chunk in chunks}
    canonical = read_json(args.canonical)
    rows, candidate_provenance, embedding_identity = load_candidate(
        args.candidate, args.profile_id, query_ids, set(chunk_text_by_id), canonical
    )
    ids = candidate_ids(rows)
    model_path, model_identity = validate_model(args.model_path)
    score_rows, runtime = score_model(
        model_path, queries, ids, chunk_text_by_id, args.batch_size, args.instruction
    )
    if len(score_rows) != len(queries) or any(
        set(row) != set(ids[index]) for index, row in enumerate(score_rows)
    ):
        raise RuntimeError("Nemotron score candidate set mismatch")
    if runtime.get("device") != "cuda" or int(runtime.get("pairs") or 0) != 7500:
        raise RuntimeError("runtime evidence mismatch")

    completed_at = datetime.now(timezone.utc).isoformat()
    dataset = {
        "corpus_version": "holo_fake_scenes_v3",
        "combined_sha256": CORPUS_SHA256,
        "documents": len(chunks),
        "queries": len(queries),
    }
    score_payload = {
        "schema_version": "1.0",
        "reranker_id": MODEL_ID,
        "model": model_identity,
        "dataset": dataset,
        "candidate": candidate_provenance,
        "instruction": args.instruction,
        "runtime": runtime,
        "queries": [
            {
                "query_id": query_id,
                "candidate_ids": list(candidate_ids_row),
                "scores": {
                    chunk_id: float(score_map[chunk_id])
                    for chunk_id in candidate_ids_row
                },
            }
            for query_id, candidate_ids_row, score_map in zip(
                query_ids, ids, score_rows, strict=True
            )
        ],
        "completed_at": completed_at,
    }
    reranked_full = scores_to_rankings(rows, score_rows)
    reranked_top = [ranking[:RERANK_TOP_K] for ranking in reranked_full]
    evaluation = evaluate_reranker_effect(queries, ids, reranked_top, CANDIDATE_TOP_K)
    try:
        score_artifact = str(
            args.score_output.resolve().relative_to(PROJECT_ROOT.resolve())
        )
    except ValueError:
        score_artifact = f"<external>/{args.score_output.name}"
    pipeline_payload = {
        "schema_version": "1.0",
        "pipeline_id": f"{args.profile_id}__{MODEL_ID}",
        "embedding_variant": args.profile_id,
        "embedding": embedding_identity,
        "candidate_ranking_sha256": candidate_provenance["ranking_sha256"],
        "reranker_id": MODEL_ID,
        "reranker": model_identity,
        "dataset": dataset,
        "candidate_top_k": CANDIDATE_TOP_K,
        "rerank_top_k": RERANK_TOP_K,
        "score_artifact": score_artifact,
        "evaluation": evaluation,
        "completed_at": completed_at,
    }
    assert_portable_payload(score_payload)
    assert_portable_payload(pipeline_payload)
    atomic_json(args.score_output, score_payload)
    atomic_json(args.pipeline_output, pipeline_payload)
    return {
        "status": "PASS",
        "pipeline_id": pipeline_payload["pipeline_id"],
        "ranking_sha256": candidate_provenance["ranking_sha256"],
        "pairs": runtime["pairs"],
        "base_HitRate@1": evaluation["base_metrics"]["summary"]["HitRate@1"],
        "reranked_HitRate@1": evaluation["reranked_metrics"]["summary"]["HitRate@1"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument(
        "--canonical", type=Path, default=PROJECT_ROOT / "ALL_BENCHMARK_RESULTS.json"
    )
    parser.add_argument("--score-output", type=Path, required=True)
    parser.add_argument("--pipeline-output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--instruction", default="")
    return parser


def main() -> int:
    print(benchmark_profile(build_parser().parse_args()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
