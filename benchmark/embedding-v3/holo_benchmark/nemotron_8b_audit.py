"""Independent audit runner for the two previously ambiguous Nemotron 8B GGUFs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .artifact_portability import assert_portable_payload, sanitize_host_payload
from .gate3_worker import (
    _VramSampler,
    _encode,
    _find_llama_server,
    _free_port,
    _server_version,
    _truncate_and_normalize,
    _wait_server,
)
from .metrics import DEFAULT_KS, evaluate_rankings
from .reranker_backends import (
    score_qwen_cross_encoder,
    score_qwen_llama_cpp,
    score_voyage_reranker,
)
from .reranker_metrics import (
    build_union_candidates,
    candidate_ids,
    evaluate_reranker_effect,
    scores_to_rankings,
)
from .reranker_runtime import (
    CORPUS_SHA256,
    DEFAULT_RERANK_INSTRUCTION,
    _candidate_payload,
    atomic_json,
    directory_weight_files,
    load_frozen_dataset,
    path_size_bytes,
    select_qwen_reranker,
    sha256_file,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parents[1]
RESULTS_ROOT = PROJECT_ROOT / "results"
RAW_DIR = RESULTS_ROOT / "gate3"
CANDIDATE_DIR = RESULTS_ROOT / "reranker" / "candidates"
SCORE_DIR = RESULTS_ROOT / "reranker" / "scores"
PIPELINE_DIR = RESULTS_ROOT / "reranker" / "pipelines"
VOYAGE_CHECKPOINT = (
    RESULTS_ROOT
    / "raw"
    / "reranker"
    / "voyage_rerank_2_5_nemotron_8b_audit.json"
)

AUDIT_MODEL_OWNERS = {
    "nemotron_8b_abiray_q4_audit": "Abiray",
    "nemotron_8b_aqua00_q4_audit": "Aqua00",
}
AUDIT_DIMENSIONS = (4096, 1024)
AUDIT_VARIANTS = tuple(
    f"{model_id}_{dimension}"
    for model_id in AUDIT_MODEL_OWNERS
    for dimension in AUDIT_DIMENSIONS
)
CANDIDATE_TOP_K = 50
RERANK_TOP_K = 20
EMBEDDING_BATCH_SIZE = 8
RERANK_BATCH_SIZE = 8
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ModelIdentity:
    model_id: str
    repo: str
    revision: str
    model_file: Path
    expected_bytes: int
    expected_sha256: str

    def validate(self) -> dict[str, Any]:
        owner = AUDIT_MODEL_OWNERS.get(self.model_id)
        if owner is None:
            raise ValueError(f"unsupported audit model id: {self.model_id}")
        if not self.repo.lower().startswith(owner.lower() + "/"):
            raise ValueError(
                f"repository owner mismatch for {self.model_id}: expected {owner}/"
            )
        revision = self.revision.lower()
        if not REVISION_RE.fullmatch(revision):
            raise ValueError("revision must be an immutable 40-character SHA")
        expected_sha = self.expected_sha256.lower()
        if not SHA256_RE.fullmatch(expected_sha):
            raise ValueError("expected SHA-256 must contain 64 hexadecimal characters")
        if self.expected_bytes <= 0:
            raise ValueError("expected model byte size must be positive")

        resolved = self.model_file.expanduser().resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"GGUF model file is missing: {resolved}")
        if resolved.suffix.lower() != ".gguf":
            raise ValueError(f"model file is not GGUF: {resolved.name}")
        if "Q4_K_M" not in resolved.name.upper():
            raise ValueError(
                f"canonical audit requires the Q4_K_M file: {resolved.name}"
            )

        actual_bytes = resolved.stat().st_size
        actual_sha = sha256_file(resolved)
        if actual_bytes != self.expected_bytes:
            raise ValueError(
                f"model byte size mismatch: expected {self.expected_bytes}, "
                f"found {actual_bytes}"
            )
        if actual_sha != expected_sha:
            raise ValueError(
                f"model SHA-256 mismatch: expected {expected_sha}, found {actual_sha}"
            )

        return {
            "id": self.model_id,
            "repository": self.repo,
            "revision": revision,
            "file": resolved.name,
            "bytes": actual_bytes,
            "sha256": actual_sha,
            "quantization": "Q4_K_M",
            "pooling": "mean",
            "native_dimension": 4096,
            "document_prefix": "passage: ",
            "query_prefix": "query: ",
            "normalization": "l2-after-truncation",
            "identity_validation": "local bytes and SHA-256 matched explicit immutable identity",
        }


def ensure_distinct_models(identities: Sequence[Mapping[str, Any]]) -> None:
    if len(identities) != 2:
        raise ValueError("exactly two model identities are required")
    ids = [str(item.get("id") or "") for item in identities]
    if set(ids) != set(AUDIT_MODEL_OWNERS):
        raise ValueError(f"audit identities diverged: {ids}")
    hashes = [str(item.get("sha256") or "") for item in identities]
    if len(set(hashes)) != 2:
        raise ValueError(
            "Abiray and Aqua00 resolved to the same weight SHA-256; "
            "do not publish duplicate-model results"
        )
    files = [str(item.get("file") or "") for item in identities]
    repos = [str(item.get("repository") or "") for item in identities]
    if len(set(repos)) != 2:
        raise ValueError("Abiray and Aqua00 repository identities are not distinct")
    if any(not name for name in files):
        raise ValueError("model identity is missing the GGUF filename")


def variant_id(model_id: str, dimension: int) -> str:
    if model_id not in AUDIT_MODEL_OWNERS:
        raise ValueError(f"unsupported audit model id: {model_id}")
    if dimension not in AUDIT_DIMENSIONS:
        raise ValueError(f"unsupported audit dimension: {dimension}")
    return f"{model_id}_{dimension}"


def _portable(payload: Mapping[str, Any]) -> dict[str, Any]:
    sanitized = sanitize_host_payload(dict(payload))
    assert_portable_payload(sanitized)
    return sanitized


def _command(
    server: str,
    model_file: Path,
    port: int,
    device: str,
) -> list[str]:
    return [
        server,
        "-m",
        str(model_file),
        "--embedding",
        "--pooling",
        "mean",
        "--embd-normalize",
        "2",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "-np",
        "1",
        "-ngl",
        "99" if device == "cuda" else "0",
        "-c",
        "4096",
        "-b",
        "512",
        "-ub",
        "512",
    ]


def encode_model(
    identity: ModelIdentity,
    chunks: Sequence[dict[str, Any]],
    queries: Sequence[dict[str, Any]],
    *,
    device: str,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any], dict[str, Any]]:
    if device != "cuda":
        raise ValueError("the canonical Nemotron 8B audit requires CUDA")
    if batch_size != EMBEDDING_BATCH_SIZE:
        raise ValueError(
            f"the canonical Nemotron 8B audit requires batch size "
            f"{EMBEDDING_BATCH_SIZE}"
        )

    model = identity.validate()
    model_file = identity.model_file.expanduser().resolve()
    documents = [f"passage: {str(row['text'])}" for row in chunks]
    query_texts = [f"query: {str(row['query'])}" for row in queries]

    server = _find_llama_server()
    port = _free_port()
    command = _command(server, model_file, port, device)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix=f"{identity.model_id}-audit-") as temporary:
        log_path = Path(temporary) / "llama-server.log"
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                command,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
            )
            failure: BaseException | None = None
            with _VramSampler(process.pid) as vram:
                try:
                    load_started = time.monotonic()
                    _wait_server(port, process, timeout=300)
                    load_seconds = time.monotonic() - load_started

                    document_started = time.monotonic()
                    document_embeddings = _encode(port, documents, batch_size)
                    document_seconds = time.monotonic() - document_started

                    query_started = time.monotonic()
                    query_embeddings = _encode(port, query_texts, batch_size)
                    query_seconds = time.monotonic() - query_started
                except BaseException as exc:
                    failure = exc
                finally:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=15)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=15)
                    log.flush()
        if failure is not None:
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-12000:]
            raise RuntimeError(
                f"{failure}\nllama-server log tail:\n{tail}"
            ) from failure

    documents_array = np.asarray(document_embeddings, dtype=np.float32)
    queries_array = np.asarray(query_embeddings, dtype=np.float32)
    if documents_array.ndim != 2 or queries_array.ndim != 2:
        raise RuntimeError("llama.cpp returned a non-matrix embedding payload")
    if documents_array.shape[1] < 4096 or queries_array.shape[1] < 4096:
        raise RuntimeError(
            "Nemotron 8B audit requires native vectors with at least 4096 dimensions"
        )

    runtime = {
        "backend": "llama.cpp",
        "backend_version": _server_version(server),
        "device": device,
        "dtype": "gguf",
        "pooling": "mean",
        "normalization": "l2-client-after-truncation",
        "embedding_batch_size": batch_size,
        "context_size": 4096,
        "server_batch_size": 512,
        "server_ubatch_size": 512,
        "gpu_layers": 99,
        "load_seconds": round(load_seconds, 6),
        "document_encode_seconds": round(document_seconds, 6),
        "query_encode_seconds": round(query_seconds, 6),
        "documents_per_second": round(len(chunks) / document_seconds, 6),
        "queries_per_second": round(len(queries) / query_seconds, 6),
        "total_seconds": round(time.monotonic() - started, 6),
        "peak_vram_bytes": (
            vram.peak_mib * 1024 * 1024 if vram.peak_mib is not None else None
        ),
        "command": command,
    }
    return documents_array, queries_array, model, runtime


def build_embedding_outputs(
    identity: Mapping[str, Any],
    document_embeddings: Any,
    query_embeddings: Any,
    runtime: Mapping[str, Any],
    chunks: Sequence[dict[str, Any]],
    queries: Sequence[dict[str, Any]],
    *,
    candidate_top_k: int = CANDIDATE_TOP_K,
) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    if candidate_top_k != CANDIDATE_TOP_K:
        raise ValueError(f"candidate_top_k must be {CANDIDATE_TOP_K}")
    model_id = str(identity["id"])
    outputs: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for dimension in AUDIT_DIMENSIONS:
        variant = variant_id(model_id, dimension)
        documents = _truncate_and_normalize(document_embeddings, dimension)
        query_rows = _truncate_and_normalize(query_embeddings, dimension)
        scores = query_rows @ documents.T

        model = {
            **dict(identity),
            "configured_dimension": dimension,
            "actual_dimension": int(documents.shape[1]),
            "vector_dtype": "float32",
            "bytes_per_vector": dimension * 4,
        }
        candidate = _candidate_payload(
            variant,
            model,
            scores,
            chunks,
            queries,
            candidate_top_k,
            {
                **dict(runtime),
                "configured_dimension": dimension,
                "shared_native_encoding": True,
            },
        )
        rankings = candidate_ids(
            [list(row["candidates"]) for row in candidate["queries"]]
        )
        metrics = evaluate_rankings(queries, rankings, DEFAULT_KS)
        raw = {
            "schema_version": "1.0",
            "id": variant,
            "gate": 3,
            "status": "COMPLETED",
            "model": model,
            "dataset": {
                "corpus_version": "holo_fake_scenes_v3",
                "combined_sha256": CORPUS_SHA256,
                "documents": len(chunks),
                "queries": len(queries),
            },
            "runtime": {
                **dict(runtime),
                "configured_dimension": dimension,
                "shared_native_encoding": True,
            },
            "metrics": metrics,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        outputs[variant] = (_portable(raw), _portable(candidate))
    return outputs


def write_embedding_outputs(
    outputs: Mapping[str, tuple[Mapping[str, Any], Mapping[str, Any]]],
) -> list[str]:
    if set(outputs) - set(AUDIT_VARIANTS):
        raise ValueError("unexpected Nemotron 8B audit variant")
    written: list[str] = []
    for variant, (raw, candidate) in outputs.items():
        raw_path = RAW_DIR / f"{variant}.json"
        candidate_path = CANDIDATE_DIR / f"{variant}.json"
        atomic_json(raw_path, dict(raw))
        atomic_json(candidate_path, dict(candidate))
        written.extend(
            [
                str(raw_path.relative_to(PROJECT_ROOT)),
                str(candidate_path.relative_to(PROJECT_ROOT)),
            ]
        )
    return written


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_audit_candidates() -> dict[str, dict[str, Any]]:
    chunks, expected_queries = load_frozen_dataset(PROJECT_ROOT)
    del chunks
    query_ids = [str(row["query_id"]) for row in expected_queries]
    payloads: dict[str, dict[str, Any]] = {}
    for variant in AUDIT_VARIANTS:
        path = CANDIDATE_DIR / f"{variant}.json"
        if not path.is_file():
            raise FileNotFoundError(f"audit candidate is missing: {path}")
        payload = _read_json(path)
        if payload.get("variant") != variant:
            raise ValueError(f"candidate variant mismatch: {path}")
        dataset = payload.get("dataset") or {}
        if dataset.get("corpus_sha256") != CORPUS_SHA256:
            raise ValueError(f"candidate corpus hash mismatch: {path}")
        if int(payload.get("candidate_top_k") or 0) != CANDIDATE_TOP_K:
            raise ValueError(f"candidate top-k mismatch: {path}")
        rows = list(payload.get("queries") or [])
        if [str(row.get("query_id")) for row in rows] != query_ids:
            raise ValueError(f"candidate query order mismatch: {path}")
        if any(len(list(row.get("candidates") or [])) != CANDIDATE_TOP_K for row in rows):
            raise ValueError(f"candidate row length mismatch: {path}")
        assert_portable_payload(payload)
        payloads[variant] = payload

    identities: dict[str, dict[str, Any]] = {}
    for model_id in AUDIT_MODEL_OWNERS:
        pair = [
            payloads[variant_id(model_id, dimension)]["model"]
            for dimension in AUDIT_DIMENSIONS
        ]
        hashes = {str(item.get("sha256") or "") for item in pair}
        revisions = {str(item.get("revision") or "") for item in pair}
        repos = {str(item.get("repository") or "") for item in pair}
        if len(hashes) != 1 or len(revisions) != 1 or len(repos) != 1:
            raise ValueError(f"identity drift between dimensions for {model_id}")
        identities[model_id] = dict(pair[0])
    ensure_distinct_models(list(identities.values()))
    return payloads


def _candidate_rows(payload: Mapping[str, Any]) -> list[list[dict[str, Any]]]:
    return [list(row["candidates"]) for row in payload["queries"]]


def _model_hash_payload(selection: Mapping[str, Any]) -> dict[str, Any]:
    path = Path(str(selection["path"])).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"reranker model is missing: {path}")
    weights = [path] if path.is_file() else directory_weight_files(path)
    if not weights:
        raise RuntimeError(f"reranker has no weight files: {path}")
    return {
        "id": str(selection.get("name") or path.name),
        "backend": str(selection["backend"]),
        "bytes": path_size_bytes(path),
        "weight_files": [
            {
                "file": item.name if path.is_file() else str(item.relative_to(path)),
                "bytes": item.stat().st_size,
                "sha256": sha256_file(item),
            }
            for item in weights
        ],
    }


def _score_payload(
    reranker_id: str,
    model: Mapping[str, Any],
    runtime: Mapping[str, Any],
    queries: Sequence[dict[str, Any]],
    union_ids: Sequence[Sequence[str]],
    score_rows: Sequence[Mapping[str, float]],
    instruction: str,
) -> dict[str, Any]:
    return _portable(
        {
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
                        chunk_id: float(scores[chunk_id]) for chunk_id in ids
                    },
                }
                for query, ids, scores in zip(
                    queries, union_ids, score_rows, strict=True
                )
            ],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def _write_pipelines(
    reranker_id: str,
    score_path: Path,
    payloads: Mapping[str, Mapping[str, Any]],
    queries: Sequence[dict[str, Any]],
    score_rows: Sequence[Mapping[str, float]],
    rerank_top_k: int,
) -> list[str]:
    written: list[str] = []
    for variant in AUDIT_VARIANTS:
        candidate_rows = [
            row[:rerank_top_k] for row in _candidate_rows(payloads[variant])
        ]
        base = candidate_ids(candidate_rows)
        reranked = scores_to_rankings(candidate_rows, score_rows)
        evaluation = evaluate_reranker_effect(
            queries,
            base,
            reranked,
            rerank_top_k,
        )
        pipeline = _portable(
            {
                "schema_version": "1.0",
                "pipeline_id": f"{variant}__{reranker_id}",
                "embedding_variant": variant,
                "reranker_id": reranker_id,
                "candidate_top_k": CANDIDATE_TOP_K,
                "rerank_top_k": rerank_top_k,
                "score_artifact": str(score_path.relative_to(PROJECT_ROOT)),
                "evaluation": evaluation,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        path = PIPELINE_DIR / reranker_id / f"{variant}.json"
        atomic_json(path, pipeline)
        written.append(str(path.relative_to(PROJECT_ROOT)))
    return written


def _union_context(
    payloads: Mapping[str, Mapping[str, Any]],
    rerank_top_k: int,
) -> tuple[list[dict[str, Any]], list[list[str]], dict[str, str]]:
    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    union_ids = build_union_candidates(
        {variant: _candidate_rows(payloads[variant]) for variant in AUDIT_VARIANTS},
        rerank_top_k,
    )
    text_by_id = {str(row["chunk_id"]): str(row["text"]) for row in chunks}
    return queries, union_ids, text_by_id


def run_qwen(
    qwen_model_path: str,
    *,
    device: str,
    reranker_batch_size: int,
    rerank_top_k: int,
    instruction: str,
) -> dict[str, Any]:
    if rerank_top_k != RERANK_TOP_K:
        raise ValueError(f"rerank_top_k must be {RERANK_TOP_K}")
    if reranker_batch_size != RERANK_BATCH_SIZE:
        raise ValueError(f"reranker batch size must be {RERANK_BATCH_SIZE}")
    payloads = load_audit_candidates()
    queries, union_ids, text_by_id = _union_context(payloads, rerank_top_k)
    selection = select_qwen_reranker(REPO_ROOT, qwen_model_path)
    path = Path(str(selection["path"]))
    if selection["backend"] == "llama.cpp":
        score_rows, runtime = score_qwen_llama_cpp(
            path,
            queries,
            union_ids,
            text_by_id,
            device,
            instruction,
        )
    else:
        score_rows, runtime = score_qwen_cross_encoder(
            path,
            queries,
            union_ids,
            text_by_id,
            device,
            reranker_batch_size,
            instruction,
        )
    model = _model_hash_payload(selection)
    score_path = SCORE_DIR / "qwen_local_nemotron_8b_audit.json"
    score = _score_payload(
        "qwen_local",
        model,
        runtime,
        queries,
        union_ids,
        score_rows,
        instruction,
    )
    atomic_json(score_path, score)
    pipelines = _write_pipelines(
        "qwen_local",
        score_path,
        payloads,
        queries,
        score_rows,
        rerank_top_k,
    )
    return {
        "status": "PASS",
        "reranker_id": "qwen_local",
        "score_artifact": str(score_path.relative_to(PROJECT_ROOT)),
        "pipelines": pipelines,
    }


def run_voyage(
    key_path: Path,
    *,
    resume: bool,
    rerank_top_k: int,
    instruction: str,
    request_interval_seconds: float,
    confirm_no_charge: bool,
) -> dict[str, Any]:
    if not confirm_no_charge or os.environ.get("VOYAGE_NO_CHARGE_CONFIRMED") != "1":
        raise RuntimeError(
            "Voyage execution requires --confirm-no-charge and "
            "VOYAGE_NO_CHARGE_CONFIRMED=1 after billing preflight"
        )
    if rerank_top_k != RERANK_TOP_K:
        raise ValueError(f"rerank_top_k must be {RERANK_TOP_K}")
    payloads = load_audit_candidates()
    queries, union_ids, text_by_id = _union_context(payloads, rerank_top_k)
    score_rows, runtime = score_voyage_reranker(
        key_path,
        queries,
        union_ids,
        text_by_id,
        VOYAGE_CHECKPOINT,
        resume,
        "rerank-2.5",
        request_interval_seconds,
        instruction,
    )
    runtime = {
        **dict(runtime),
        "billing_preflight": "operator-confirmed no-charge execution",
        "charged_cost_usd": None,
    }
    score_path = SCORE_DIR / "voyage_rerank_2_5_nemotron_8b_audit.json"
    score = _score_payload(
        "voyage_rerank_2_5",
        {
            "id": "rerank-2.5",
            "provider": "Voyage AI",
            "api_model": True,
        },
        runtime,
        queries,
        union_ids,
        score_rows,
        instruction,
    )
    atomic_json(score_path, score)
    pipelines = _write_pipelines(
        "voyage_rerank_2_5",
        score_path,
        payloads,
        queries,
        score_rows,
        rerank_top_k,
    )
    return {
        "status": "PASS",
        "reranker_id": "voyage_rerank_2_5",
        "score_artifact": str(score_path.relative_to(PROJECT_ROOT)),
        "pipelines": pipelines,
        "usage": runtime.get("usage"),
    }


def validate_audit(*, require_voyage: bool) -> dict[str, Any]:
    payloads = load_audit_candidates()
    raw_paths = [RAW_DIR / f"{variant}.json" for variant in AUDIT_VARIANTS]
    qwen_paths = [
        PIPELINE_DIR / "qwen_local" / f"{variant}.json"
        for variant in AUDIT_VARIANTS
    ]
    voyage_paths = [
        PIPELINE_DIR / "voyage_rerank_2_5" / f"{variant}.json"
        for variant in AUDIT_VARIANTS
    ]
    required = raw_paths + qwen_paths
    if require_voyage:
        required += voyage_paths
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"audit outputs are missing: {missing}")

    checked: list[str] = []
    for path in required:
        payload = _read_json(path)
        assert_portable_payload(payload)
        checked.append(str(path.relative_to(PROJECT_ROOT)))
    for payload in payloads.values():
        assert_portable_payload(payload)

    return {
        "status": "PASS",
        "models": list(AUDIT_MODEL_OWNERS),
        "variants": list(AUDIT_VARIANTS),
        "raw_results": len(raw_paths),
        "candidate_artifacts": len(payloads),
        "qwen_pipelines": len(qwen_paths),
        "voyage_pipelines": len(voyage_paths) if require_voyage else 0,
        "checked": checked,
    }


def _print(payload: Mapping[str, Any]) -> None:
    print(json.dumps(dict(payload), ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the independent two-model Nemotron 8B audit."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    embed = subparsers.add_parser("embed")
    embed.add_argument("--model-id", choices=tuple(AUDIT_MODEL_OWNERS), required=True)
    embed.add_argument("--repo", required=True)
    embed.add_argument("--revision", required=True)
    embed.add_argument("--model-file", type=Path, required=True)
    embed.add_argument("--expected-bytes", type=int, required=True)
    embed.add_argument("--expected-sha256", required=True)
    embed.add_argument("--device", default="cuda", choices=("cuda",))
    embed.add_argument("--batch-size", type=int, default=EMBEDDING_BATCH_SIZE)
    embed.add_argument("--candidate-top-k", type=int, default=CANDIDATE_TOP_K)

    qwen = subparsers.add_parser("qwen")
    qwen.add_argument("--qwen-model-path", required=True)
    qwen.add_argument("--device", default="cuda", choices=("cuda", "cpu"))
    qwen.add_argument("--reranker-batch-size", type=int, default=RERANK_BATCH_SIZE)
    qwen.add_argument("--rerank-top-k", type=int, default=RERANK_TOP_K)
    qwen.add_argument("--instruction", default=DEFAULT_RERANK_INSTRUCTION)

    voyage = subparsers.add_parser("voyage")
    voyage.add_argument("--api-key-path", type=Path, required=True)
    voyage.add_argument("--resume", action="store_true")
    voyage.add_argument("--rerank-top-k", type=int, default=RERANK_TOP_K)
    voyage.add_argument("--instruction", default=DEFAULT_RERANK_INSTRUCTION)
    voyage.add_argument("--request-interval-seconds", type=float, default=1.0)
    voyage.add_argument("--confirm-no-charge", action="store_true")

    validate = subparsers.add_parser("validate")
    validate.add_argument("--require-voyage", action="store_true")

    args = parser.parse_args()
    if args.command == "embed":
        identity = ModelIdentity(
            model_id=args.model_id,
            repo=args.repo,
            revision=args.revision,
            model_file=args.model_file,
            expected_bytes=args.expected_bytes,
            expected_sha256=args.expected_sha256,
        )
        chunks, queries = load_frozen_dataset(PROJECT_ROOT)
        docs, qrys, model, runtime = encode_model(
            identity,
            chunks,
            queries,
            device=args.device,
            batch_size=args.batch_size,
        )
        outputs = build_embedding_outputs(
            model,
            docs,
            qrys,
            runtime,
            chunks,
            queries,
            candidate_top_k=args.candidate_top_k,
        )
        _print(
            {
                "status": "PASS",
                "model": model,
                "written": write_embedding_outputs(outputs),
            }
        )
        return 0
    if args.command == "qwen":
        _print(
            run_qwen(
                args.qwen_model_path,
                device=args.device,
                reranker_batch_size=args.reranker_batch_size,
                rerank_top_k=args.rerank_top_k,
                instruction=args.instruction,
            )
        )
        return 0
    if args.command == "voyage":
        _print(
            run_voyage(
                args.api_key_path,
                resume=args.resume,
                rerank_top_k=args.rerank_top_k,
                instruction=args.instruction,
                request_interval_seconds=args.request_interval_seconds,
                confirm_no_charge=args.confirm_no_charge,
            )
        )
        return 0
    if args.command == "validate":
        _print(validate_audit(require_voyage=args.require_voyage))
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
