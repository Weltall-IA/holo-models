"""Strict model-native protocol for the Mixedbread reranker panel.

The upstream snapshot added Sentence Transformers CrossEncoder integration through
``modules.json`` and ``1_LogitScore``. Loading only the causal-LM weights through
a generic sequence-classification fallback produces meaningless scores. This
module validates the complete local snapshot, requires the LogitScore module,
uses raw query-document pairs, and runs a deterministic semantic smoke test
before any Holo scoring.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import math
import re
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from .reranker_runtime import ResourceSampler

MODEL_ID = "mxbai_rerank_base_v2"
MODEL_REPOSITORY = "mixedbread-ai/mxbai-rerank-base-v2"
MODEL_WEIGHT_FILE = "model.safetensors"
MODEL_WEIGHT_SHA256 = "c01649fe56b3fe32e52da43c69e084dff7c2252cf231a38c56d5a291a674338f"
MODEL_LICENSE = "Apache-2.0"
_REVISION = re.compile(r"^[0-9a-f]{40}$")

CRITICAL_MODEL_FILES = (
    "model.safetensors",
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "modules.json",
    "sentence_bert_config.json",
    "config_sentence_transformers.json",
    "chat_template.jinja",
    "1_LogitScore/config.json",
)

_OFFICIAL_SMOKE_QUERY = "Which planet is known as the Red Planet?"
_OFFICIAL_SMOKE_DOCUMENTS = (
    "Venus is often called Earth's twin because of its similar size and proximity.",
    "Mars, known for its reddish appearance, is often referred to as the Red Planet.",
    "Jupiter, the largest planet in our solar system, has a prominent red spot.",
    "Saturn, famous for its rings, is sometimes mistaken for the Red Planet.",
)
_OFFICIAL_RELEVANT_INDEX = 1


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _metadata_path(model_path: Path, relative_path: str) -> Path:
    return model_path / ".cache" / "huggingface" / "download" / f"{relative_path}.metadata"


def read_local_revision(model_path: Path, relative_path: str) -> str:
    metadata = _metadata_path(model_path, relative_path)
    if not metadata.is_file():
        raise FileNotFoundError(
            f"Mixedbread download metadata is missing for {relative_path}: {metadata}"
        )
    lines = metadata.read_text(encoding="utf-8").splitlines()
    revision = lines[0].strip().lower() if lines else ""
    if not _REVISION.fullmatch(revision):
        raise ValueError(f"invalid Mixedbread revision metadata for {relative_path}")
    return revision


def validate_complete_model(
    model_path: Path,
    expected_revision: str,
) -> tuple[Path, dict[str, Any]]:
    revision = str(expected_revision).strip().lower()
    if not _REVISION.fullmatch(revision):
        raise ValueError("Mixedbread revision must be an immutable 40-character SHA")

    resolved = model_path.expanduser().resolve()
    if not resolved.is_dir():
        raise FileNotFoundError(f"Mixedbread model directory is missing: {resolved}")

    missing = [name for name in CRITICAL_MODEL_FILES if not (resolved / name).is_file()]
    if missing:
        raise FileNotFoundError(
            "Mixedbread repository is incomplete; missing model-native files: "
            f"{missing}"
        )

    file_records: list[dict[str, Any]] = []
    for relative_path in CRITICAL_MODEL_FILES:
        path = resolved / relative_path
        local_revision = read_local_revision(resolved, relative_path)
        if local_revision != revision:
            raise ValueError(
                "Mixedbread snapshot contains divergent revisions: "
                f"{relative_path}={local_revision}, expected={revision}"
            )
        file_records.append(
            {
                "file": relative_path,
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "revision": local_revision,
            }
        )

    weight_record = next(
        record for record in file_records if record["file"] == MODEL_WEIGHT_FILE
    )
    if weight_record["sha256"] != MODEL_WEIGHT_SHA256:
        raise ValueError(
            "Mixedbread weight SHA-256 mismatch: "
            f"expected {MODEL_WEIGHT_SHA256}, found {weight_record['sha256']}"
        )

    return resolved, {
        "id": MODEL_ID,
        "repository": MODEL_REPOSITORY,
        "revision": revision,
        "backend": "sentence-transformers.CrossEncoder",
        "license": MODEL_LICENSE,
        "weight_files": [weight_record],
        "critical_snapshot_files": file_records,
        "snapshot_validation": "all critical files share one immutable revision",
    }


def native_query_text(query: Mapping[str, Any], instruction: str = "") -> str:
    if str(instruction).strip():
        raise ValueError(
            "mxbai-rerank-base-v2 requires the upstream raw query-document pair; "
            "a generic rerank instruction is not permitted"
        )
    text = str(query.get("query") or "").strip()
    if not text:
        raise ValueError("Mixedbread query text is empty")
    return text


def model_module_names(model: Any) -> list[str]:
    names: list[str] = []
    named_modules = getattr(model, "named_modules", None)
    if callable(named_modules):
        for name, module in named_modules():
            names.append(f"{name}:{module.__class__.__module__}.{module.__class__.__name__}")
    else:
        for name, module in dict(getattr(model, "_modules", {}) or {}).items():
            names.append(f"{name}:{module.__class__.__module__}.{module.__class__.__name__}")
    return names


def require_logit_score_module(model: Any) -> list[str]:
    names = model_module_names(model)
    if not any(name.endswith(".LogitScore") or ".LogitScore" in name for name in names):
        raise RuntimeError(
            "Mixedbread did not load the upstream Sentence Transformers LogitScore "
            "module; refusing a generic or randomly initialized classifier fallback"
        )
    return names


def official_semantic_smoke(model: Any, identity_activation: Any) -> dict[str, Any]:
    import numpy as np

    pairs = [
        (_OFFICIAL_SMOKE_QUERY, document)
        for document in _OFFICIAL_SMOKE_DOCUMENTS
    ]
    values = np.asarray(
        model.predict(
            pairs,
            batch_size=4,
            show_progress_bar=False,
            activation_fn=identity_activation,
        ),
        dtype=np.float64,
    ).reshape(-1)
    if values.shape != (4,) or not np.isfinite(values).all():
        raise RuntimeError("Mixedbread official semantic smoke returned invalid scores")
    order = np.argsort(-values, kind="stable")
    if int(order[0]) != _OFFICIAL_RELEVANT_INDEX:
        raise RuntimeError(
            "Mixedbread official semantic smoke failed: the Mars passage was not top-1"
        )
    sorted_scores = np.sort(values)[::-1]
    margin = float(sorted_scores[0] - sorted_scores[1])
    if not math.isfinite(margin) or margin <= 0.0:
        raise RuntimeError("Mixedbread official semantic smoke has no positive top-1 margin")
    return {
        "query": _OFFICIAL_SMOKE_QUERY,
        "relevant_document_index": _OFFICIAL_RELEVANT_INDEX,
        "scores": [float(value) for value in values],
        "top_index": int(order[0]),
        "top1_margin": margin,
        "status": "PASS",
    }


def score_cross_encoder_native(
    model_path: Path,
    queries: Sequence[dict[str, Any]],
    union_ids: Sequence[Sequence[str]],
    chunk_text_by_id: Mapping[str, str],
    batch_size: int,
    instruction: str,
) -> tuple[list[dict[str, float]], dict[str, Any]]:
    try:
        import numpy as np
        import torch
        from sentence_transformers import CrossEncoder
    except ImportError as exc:
        raise RuntimeError(
            "Mixedbread requires numpy, torch and sentence-transformers"
        ) from exc

    if str(instruction).strip():
        native_query_text({"query": "validation"}, instruction)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable for Mixedbread")

    torch.cuda.reset_peak_memory_stats()
    identity_activation = torch.nn.Identity()
    started = time.monotonic()
    latencies: list[float] = []
    score_rows: list[dict[str, float]] = []

    with ResourceSampler() as resources:
        load_started = time.monotonic()
        try:
            model = CrossEncoder(
                str(model_path),
                device="cuda",
                trust_remote_code=True,
                local_files_only=True,
            )
        except TypeError:
            model = CrossEncoder(
                str(model_path),
                device="cuda",
                model_kwargs={
                    "trust_remote_code": True,
                    "local_files_only": True,
                },
            )
        load_seconds = time.monotonic() - load_started

        modules = require_logit_score_module(model)
        semantic_smoke = official_semantic_smoke(model, identity_activation)
        tokenizer = getattr(model, "tokenizer", None)
        effective_max_length = getattr(model, "max_length", None)
        tokenizer_max_length = getattr(tokenizer, "model_max_length", None)

        for query, chunk_ids in zip(queries, union_ids, strict=True):
            query_text = native_query_text(query, instruction)
            pairs = [
                (query_text, chunk_text_by_id[chunk_id])
                for chunk_id in chunk_ids
            ]
            request_started = time.monotonic()
            raw_scores = model.predict(
                pairs,
                batch_size=batch_size,
                show_progress_bar=False,
                activation_fn=identity_activation,
            )
            latencies.append(time.monotonic() - request_started)
            values = np.asarray(raw_scores)
            if values.shape[0] != len(chunk_ids):
                raise RuntimeError("Mixedbread score count mismatch")
            row: dict[str, float] = {}
            for chunk_id, value in zip(chunk_ids, values, strict=True):
                flattened = np.asarray(value).reshape(-1)
                if flattened.size != 1:
                    raise RuntimeError("Mixedbread returned multiple logits per pair")
                score = float(flattened[0])
                if not math.isfinite(score):
                    raise RuntimeError("Mixedbread returned a non-finite score")
                row[chunk_id] = score
            score_rows.append(row)

        peak_vram = int(torch.cuda.max_memory_allocated())

    ordered = sorted(latencies)

    def percentile(fraction: float) -> float | None:
        if not ordered:
            return None
        index = min(len(ordered) - 1, int((len(ordered) - 1) * fraction))
        return ordered[index]

    runtime = {
        "backend": "sentence-transformers.CrossEncoder",
        "backend_version": importlib.metadata.version("sentence-transformers"),
        "device": "cuda",
        "query_format": "raw_query_document_pair",
        "activation_fn": "torch.nn.Identity",
        "model_modules": modules,
        "official_semantic_smoke": semantic_smoke,
        "load_seconds": round(load_seconds, 4),
        "score_seconds": round(sum(latencies), 4),
        "total_seconds": round(time.monotonic() - started, 4),
        "queries": len(queries),
        "pairs": sum(len(row) for row in union_ids),
        "batch_size": batch_size,
        "tokenizer_class": type(tokenizer).__name__ if tokenizer is not None else None,
        "tokenizer_model_max_length": tokenizer_max_length,
        "effective_max_length": effective_max_length,
        "truncation": "CrossEncoder tokenizer truncation enabled",
        "latency_p50_seconds": round(percentile(0.50), 4),
        "latency_p95_seconds": round(percentile(0.95), 4),
        "latency_max_seconds": round(max(latencies), 4),
        "peak_vram_bytes": peak_vram,
        **resources.as_dict(),
    }
    if peak_vram <= 0:
        raise RuntimeError("Mixedbread has no positive CUDA memory evidence")
    return score_rows, runtime


def install_protocol(benchmark_module: Any, expected_revision: str) -> None:
    """Install the strict protocol into the canonical serializer/evaluator module."""

    def validate(path: Path) -> tuple[Path, dict[str, Any]]:
        return validate_complete_model(path, expected_revision)

    benchmark_module.validate_model = validate
    benchmark_module.score_cross_encoder = score_cross_encoder_native
