"""Canonical NVIDIA Llama Nemotron reranking for the fixed six-profile panel."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .artifact_portability import assert_portable_payload, sanitize_host_payload
from .mxbai_panel_benchmark import PANEL_PROFILES, PROJECT_ROOT, load_candidate
from .reranker_metrics import candidate_ids as extract_candidate_ids
from .reranker_metrics import evaluate_reranker_effect, scores_to_rankings
from .reranker_runtime import CORPUS_SHA256, atomic_json, load_frozen_dataset, read_json

MODEL_ID = "llama_nemotron_rerank_1b_v2"
MODEL_REPOSITORY = "nvidia/llama-nemotron-rerank-1b-v2"
MODEL_REVISION = "d896ceda696c5c6fe0abf65f63a77c691bbf4548"
MODEL_WEIGHT_FILE = "model.safetensors"
MODEL_WEIGHT_SIZE_BYTES = 2471649792
MODEL_WEIGHT_SHA256 = "7d60ff24db62fe6a639c4c6f4aeac3a3b32ed20939ab72a0be4b019c2219e5e0"
MODEL_LICENSE = "NVIDIA Open Model License"
CANDIDATE_TOP_K = 50
RERANK_TOP_K = 20
REQUIRED_MODEL_FILES = (
    "model.safetensors",
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "llama_bidirectional_model.py",
)
SCORE_TEMPLATE = (
    'question:{{ (messages | selectattr("role", "eq", "query") | first).content }}'
    " \n \n "
    'passage:{{ (messages | selectattr("role", "eq", "document") | first).content }}'
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def metadata_path(model_path: Path, relative: str) -> Path:
    return model_path / ".cache" / "huggingface" / "download" / f"{relative}.metadata"


def metadata_revision(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Hugging Face metadata is missing: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError(f"Hugging Face metadata is empty: {path}")
    return lines[0].strip()


def validate_complete_model(
    path: Path,
    revision: str = MODEL_REVISION,
    *,
    expected_weight_size: int = MODEL_WEIGHT_SIZE_BYTES,
    expected_weight_sha256: str = MODEL_WEIGHT_SHA256,
) -> tuple[Path, dict[str, Any]]:
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        raise FileNotFoundError(f"Nemotron model directory is missing: {resolved}")

    critical: list[dict[str, Any]] = []
    for relative in REQUIRED_MODEL_FILES:
        item = resolved / relative
        if not item.is_file():
            raise FileNotFoundError(f"Nemotron snapshot file is missing: {relative}")
        file_revision = metadata_revision(metadata_path(resolved, relative))
        if file_revision != revision:
            raise ValueError(
                f"Nemotron revision mismatch for {relative}: "
                f"expected {revision}, found {file_revision}"
            )
        critical.append(
            {
                "file": relative,
                "bytes": item.stat().st_size,
                "sha256": sha256_file(item),
                "revision": file_revision,
            }
        )

    weight = next(item for item in critical if item["file"] == MODEL_WEIGHT_FILE)
    if int(weight["bytes"]) != expected_weight_size:
        raise ValueError("Nemotron weight size mismatch")
    if str(weight["sha256"]) != expected_weight_sha256:
        raise ValueError("Nemotron weight SHA-256 mismatch")

    config = json.loads((resolved / "config.json").read_text(encoding="utf-8"))
    auto_map = config.get("auto_map") or {}
    if not any("llama_bidirectional_model" in str(value) for value in auto_map.values()):
        raise ValueError("Nemotron config does not reference llama_bidirectional_model")

    return resolved, {
        "id": MODEL_ID,
        "repository": MODEL_REPOSITORY,
        "revision": revision,
        "backend": "vllm",
        "license": MODEL_LICENSE,
        "weight_files": [weight],
        "critical_snapshot_files": critical,
        "snapshot_validation": "all critical files share one immutable revision",
    }


def validate_score_template(path: Path) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Nemotron score template is missing: {resolved}")
    content = resolved.read_text(encoding="utf-8")
    if content.rstrip("\n") != SCORE_TEMPLATE:
        raise ValueError("Nemotron score template diverged from the official format")
    try:
        relative = resolved.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        relative = f"<external>/{resolved.name}"
    return {
        "format": "question_passage_score_template",
        "path": relative,
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }


def post_json(url: str, payload: Mapping[str, Any], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(dict(payload), ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    if not isinstance(parsed, dict):
        raise RuntimeError("vLLM rerank response is not an object")
    return parsed


def wait_for_server(base_url: str, timeout_seconds: float = 180.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        for endpoint in ("/health", "/v1/models"):
            try:
                with urllib.request.urlopen(
                    f"{base_url.rstrip('/')}{endpoint}", timeout=5
                ) as response:
                    if 200 <= int(response.status) < 300:
                        return
            except Exception as exc:
                last_error = exc
        time.sleep(1)
    raise RuntimeError(f"vLLM server did not become ready: {last_error}")


def parse_rerank_response(
    payload: Mapping[str, Any], document_count: int
) -> list[float]:
    rows = payload.get("results")
    if not isinstance(rows, list) or len(rows) != document_count:
        raise RuntimeError(f"vLLM response must contain {document_count} results")
    scores: list[float | None] = [None] * document_count
    for item in rows:
        if not isinstance(item, Mapping):
            raise RuntimeError("vLLM rerank result is not an object")
        index = int(item.get("index", -1))
        if not 0 <= index < document_count:
            raise RuntimeError(f"vLLM rerank index is invalid: {index}")
        if scores[index] is not None:
            raise RuntimeError(f"vLLM rerank index is duplicated: {index}")
        score = float(item.get("relevance_score"))
        if not math.isfinite(score):
            raise RuntimeError("vLLM returned a non-finite relevance score")
        scores[index] = score
    if any(score is None for score in scores):
        raise RuntimeError("vLLM rerank response is incomplete")
    return [float(score) for score in scores if score is not None]


def score_documents(
    base_url: str,
    query: str,
    documents: Sequence[str],
    timeout_seconds: float,
) -> tuple[list[float], float]:
    started = time.monotonic()
    payload = post_json(
        f"{base_url.rstrip('/')}/rerank",
        {
            "model": MODEL_ID,
            "query": query,
            "documents": list(documents),
            "top_n": len(documents),
        },
        timeout_seconds,
    )
    return parse_rerank_response(payload, len(documents)), time.monotonic() - started


def official_semantic_smoke(
    base_url: str, timeout_seconds: float = 60.0
) -> dict[str, Any]:
    query = "What is machine learning?"
    documents = [
        "Bananas are a good source of potassium.",
        "Machine learning is a branch of AI that learns patterns from data.",
    ]
    scores, latency = score_documents(base_url, query, documents, timeout_seconds)
    top_index = max(range(len(scores)), key=scores.__getitem__)
    margin = scores[1] - scores[0]
    if top_index != 1 or not margin > 0:
        raise RuntimeError("Nemotron semantic smoke failed")
    return {
        "status": "PASS",
        "query": query,
        "documents": documents,
        "scores": scores,
        "top_index": top_index,
        "margin": margin,
        "latency_seconds": round(latency, 4),
    }


def process_tree_pids(root_pid: int) -> set[int]:
    pids = {int(root_pid)}
    try:
        import psutil

        root = psutil.Process(int(root_pid))
        pids.update(int(process.pid) for process in root.children(recursive=True))
    except Exception:
        pass
    return pids


def gpu_memory_bytes_for_process_tree(root_pid: int) -> int:
    pids = process_tree_pids(root_pid)
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-compute-apps=pid,used_memory",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return 0
    if completed.returncode != 0:
        return 0
    total_mib = 0
    for line in completed.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 2:
            continue
        try:
            pid, used_mib = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        if pid in pids and used_mib > 0:
            total_mib += used_mib
    return total_mib * 1024 * 1024


def percentile(values: Sequence[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    index = min(len(ordered) - 1, int((len(ordered) - 1) * fraction))
    return ordered[index]


def score_panel_profile(
    base_url: str,
    server_pid: int,
    queries: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Sequence[str]],
    chunk_text_by_id: Mapping[str, str],
    timeout_seconds: float,
) -> tuple[list[dict[str, float]], dict[str, Any]]:
    score_rows: list[dict[str, float]] = []
    latencies: list[float] = []
    peak_vram = gpu_memory_bytes_for_process_tree(server_pid)
    started = time.monotonic()
    for query, ids in zip(queries, candidate_rows, strict=True):
        documents = [chunk_text_by_id[chunk_id] for chunk_id in ids]
        values, latency = score_documents(
            base_url, str(query["query"]), documents, timeout_seconds
        )
        score_rows.append(
            {chunk_id: score for chunk_id, score in zip(ids, values, strict=True)}
        )
        latencies.append(latency)
        peak_vram = max(peak_vram, gpu_memory_bytes_for_process_tree(server_pid))
    if peak_vram <= 0:
        raise RuntimeError("Nemotron has no positive CUDA VRAM evidence")
    return score_rows, {
        "backend": "vllm",
        "device": "cuda",
        "runner": "pooling",
        "endpoint": "/rerank",
        "query_format": "question_passage_score_template",
        "queries": len(queries),
        "pairs": sum(len(ids) for ids in candidate_rows),
        "score_seconds": round(sum(latencies), 4),
        "total_seconds": round(time.monotonic() - started, 4),
        "latency_p50_seconds": round(percentile(latencies, 0.50) or 0.0, 4),
        "latency_p95_seconds": round(percentile(latencies, 0.95) or 0.0, 4),
        "latency_max_seconds": round(max(latencies), 4) if latencies else None,
        "peak_vram_bytes": peak_vram,
    }


def benchmark_profile(args: argparse.Namespace) -> dict[str, Any]:
    if args.profile_id not in PANEL_PROFILES:
        raise ValueError(
            f"profile is not in the fixed Nemotron panel: {args.profile_id}"
        )
    if int(args.server_pid) <= 0:
        raise ValueError("server_pid must be positive")

    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    query_ids = [str(query["query_id"]) for query in queries]
    chunk_text_by_id = {
        str(chunk["chunk_id"]): str(chunk["text"]) for chunk in chunks
    }
    canonical = read_json(args.canonical)
    rows, candidate_provenance, embedding_identity = load_candidate(
        args.candidate,
        args.profile_id,
        query_ids,
        set(chunk_text_by_id),
        canonical,
    )
    ids = extract_candidate_ids(rows)
    _, model_identity = validate_complete_model(args.model_path, args.model_revision)
    template_identity = validate_score_template(args.score_template)

    wait_for_server(args.base_url, args.startup_timeout)
    smoke = official_semantic_smoke(args.base_url, args.request_timeout)
    score_rows, runtime = score_panel_profile(
        args.base_url,
        args.server_pid,
        queries,
        ids,
        chunk_text_by_id,
        args.request_timeout,
    )
    runtime["backend_version"] = args.vllm_version
    runtime["score_template"] = template_identity
    runtime["semantic_smoke"] = smoke
    if len(score_rows) != len(queries) or any(
        set(row) != set(ids[index]) for index, row in enumerate(score_rows)
    ):
        raise RuntimeError("Nemotron score candidate set mismatch")
    if int(runtime["pairs"]) != 7500:
        raise RuntimeError("Nemotron runtime pair count mismatch")

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
        "instruction": None,
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
    evaluation = evaluate_reranker_effect(
        queries, ids, reranked_top, CANDIDATE_TOP_K
    )
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
        "embedding": sanitize_host_payload(embedding_identity),
        "candidate_ranking_sha256": candidate_provenance["ranking_sha256"],
        "reranker_id": MODEL_ID,
        "reranker": model_identity,
        "dataset": dataset,
        "candidate_top_k": CANDIDATE_TOP_K,
        "rerank_top_k": RERANK_TOP_K,
        "score_artifact": score_artifact,
        "evaluation": evaluation,
        "runtime": runtime,
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
        "reranked_MRR@10": evaluation["reranked_metrics"]["summary"]["MRR@10"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-id", choices=PANEL_PROFILES, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--model-revision", default=MODEL_REVISION)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument(
        "--canonical",
        type=Path,
        default=PROJECT_ROOT / "ALL_BENCHMARK_RESULTS.json",
    )
    parser.add_argument("--score-template", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8099")
    parser.add_argument("--server-pid", type=int, required=True)
    parser.add_argument("--vllm-version", required=True)
    parser.add_argument("--startup-timeout", type=float, default=180.0)
    parser.add_argument("--request-timeout", type=float, default=180.0)
    parser.add_argument("--score-output", type=Path, required=True)
    parser.add_argument("--pipeline-output", type=Path, required=True)
    return parser


def main() -> int:
    print(benchmark_profile(build_parser().parse_args()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
