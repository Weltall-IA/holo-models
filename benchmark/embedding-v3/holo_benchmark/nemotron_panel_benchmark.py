from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import signal
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from holo_benchmark.artifact_portability import assert_portable_payload
from holo_benchmark.reranker_execution import (
    atomic_json,
    build_pipeline_payload,
    evaluate_rankings,
    load_candidate_payloads,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parents[1]
RESULTS_DIR = PROJECT_ROOT / "results" / "reranker"
MODEL_REPOSITORY = "nvidia/llama-nemotron-rerank-1b-v2"
MODEL_REVISION = "d896ceda696c5c6fe0abf65f63a77c691bbf4548"
MODEL_WEIGHT_FILE = "model.safetensors"
MODEL_WEIGHT_SIZE = 2471649792
MODEL_WEIGHT_SHA256 = "7d60ff24db62fe6a639c4c6f4aeac3a3b32ed20939ab72a0be4b019c2219e5e0"
REQUIRED_MODEL_FILES = (
    MODEL_WEIGHT_FILE,
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "llama_bidirectional_model.py",
)
SCORE_TEMPLATE = "question: {{ messages[0]['content'] }} passage: {{ messages[1]['content'] }}"
PANEL_PROFILES = (
    "nemotron_3_embed_1b_nvfp4",
    "nomic_embed_text_v2_moe_q4",
    "qwen3_embedding_4b_q8_0",
    "embeddinggemma",
    "colibri_ptbr",
    "granite_embedding_311m_r2",
)
RERANK_ENDPOINT = "/rerank"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def metadata_path(model_dir: Path, relative: str) -> Path:
    return model_dir / ".cache" / "huggingface" / "download" / f"{relative}.metadata"


def validate_complete_model(
    model_dir: Path,
    revision: str = MODEL_REVISION,
    expected_weight_size: int = MODEL_WEIGHT_SIZE,
    expected_weight_sha256: str = MODEL_WEIGHT_SHA256,
) -> tuple[Path, dict[str, Any]]:
    resolved = model_dir.expanduser().resolve()
    if not resolved.is_dir():
        raise FileNotFoundError(f"missing Nemotron model directory: {resolved}")
    files: list[dict[str, Any]] = []
    for relative in REQUIRED_MODEL_FILES:
        path = resolved / relative
        if not path.is_file():
            raise FileNotFoundError(f"missing Nemotron model file: {relative}")
        metadata = metadata_path(resolved, relative)
        if not metadata.is_file():
            raise FileNotFoundError(f"missing Nemotron metadata: {relative}")
        lines = metadata.read_text(encoding="utf-8").splitlines()
        if not lines or lines[0].strip() != revision:
            actual = lines[0].strip() if lines else "<empty>"
            raise ValueError(
                f"Nemotron revision mismatch for {relative}: {actual} != {revision}"
            )
        files.append(
            {
                "file": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "revision": revision,
            }
        )
    weight = resolved / MODEL_WEIGHT_FILE
    if weight.stat().st_size != expected_weight_size:
        raise ValueError("Nemotron weight size mismatch")
    if sha256_file(weight) != expected_weight_sha256:
        raise ValueError("Nemotron weight SHA-256 mismatch")
    config = json.loads((resolved / "config.json").read_text(encoding="utf-8"))
    auto_map = config.get("auto_map")
    if not isinstance(auto_map, Mapping) or not auto_map:
        raise ValueError("Nemotron config does not declare remote model code")
    identity = {
        "id": "llama_nemotron_rerank_1b_v2",
        "repository": MODEL_REPOSITORY,
        "revision": revision,
        "backend": "vllm",
        "license": "NVIDIA Open Model License",
        "precision": "BF16",
        "weight_files": [files[0]],
        "critical_snapshot_files": files,
        "snapshot_validation": "all critical files share one immutable revision",
    }
    return resolved, identity


def validate_score_template(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"missing Nemotron score template: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if text != SCORE_TEMPLATE:
        raise ValueError("Nemotron score template does not match official format")
    return {
        "file": path.name,
        "sha256": sha256_file(path),
        "format": "question_passage_score_template",
    }


def _json_request(
    url: str,
    payload: Mapping[str, Any] | None,
    timeout_seconds: float,
) -> Any:
    data = None
    headers: dict[str, str] = {}
    method = "GET"
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def wait_for_server(base_url: str, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = "server not contacted"
    while time.monotonic() < deadline:
        try:
            payload = _json_request(f"{base_url}/health", None, 5.0)
            if payload is not None:
                return
        except (OSError, ValueError, urllib.error.URLError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(2.0)
    raise TimeoutError(f"Nemotron server not ready: {last_error}")


def parse_rerank_response(payload: Any, expected_count: int) -> list[float]:
    if not isinstance(payload, Mapping):
        raise RuntimeError("Nemotron /rerank response is not an object")
    results = payload.get("results")
    if not isinstance(results, list) or len(results) != expected_count:
        raise RuntimeError("Nemotron /rerank response has wrong result count")
    ordered: list[float | None] = [None] * expected_count
    for item in results:
        if not isinstance(item, Mapping):
            raise RuntimeError("Nemotron /rerank result is not an object")
        index = item.get("index")
        score = item.get("relevance_score")
        if not isinstance(index, int) or index < 0 or index >= expected_count:
            raise RuntimeError("Nemotron /rerank result has invalid index")
        if ordered[index] is not None:
            raise RuntimeError("Nemotron /rerank response has duplicated index")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise RuntimeError("Nemotron /rerank result has invalid relevance_score")
        numeric = float(score)
        if not math.isfinite(numeric):
            raise RuntimeError("Nemotron /rerank result has non-finite score")
        ordered[index] = numeric
    if any(value is None for value in ordered):
        raise RuntimeError("Nemotron /rerank response is missing indices")
    return [float(value) for value in ordered]


def score_documents(
    base_url: str,
    query: str,
    documents: Sequence[str],
    timeout_seconds: float,
) -> tuple[list[float], float]:
    if not documents:
        raise ValueError("Nemotron documents must not be empty")
    started = time.monotonic()
    payload = _json_request(
        f"{base_url}{RERANK_ENDPOINT}",
        {
            "model": "llama_nemotron_rerank_1b_v2",
            "query": query,
            "documents": list(documents),
            "top_n": len(documents),
        },
        timeout_seconds,
    )
    elapsed = time.monotonic() - started
    return parse_rerank_response(payload, len(documents)), elapsed


def official_semantic_smoke(base_url: str, timeout_seconds: float = 120.0) -> dict[str, Any]:
    query = "Qual passagem identifica corretamente o planeta vermelho?"
    documents = [
        "Vênus é conhecido por sua atmosfera densa e quente.",
        "Marte é frequentemente chamado de planeta vermelho por causa do óxido de ferro.",
    ]
    scores, elapsed = score_documents(base_url, query, documents, timeout_seconds)
    top_index = max(range(len(scores)), key=lambda index: scores[index])
    margin = scores[top_index] - max(
        score for index, score in enumerate(scores) if index != top_index
    )
    if top_index != 1 or not math.isfinite(margin) or margin <= 0:
        raise RuntimeError(
            f"Nemotron semantic smoke failed: top_index={top_index}, margin={margin}"
        )
    return {
        "status": "PASS",
        "query": query,
        "documents": documents,
        "scores": scores,
        "top_index": top_index,
        "top_margin": margin,
        "seconds": elapsed,
        "endpoint": RERANK_ENDPOINT,
    }


def _descendant_pids(root_pid: int) -> set[int]:
    try:
        output = subprocess.check_output(
            ["ps", "-eo", "pid=,ppid="], text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return {root_pid}
    children: dict[int, list[int]] = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        pid, parent = map(int, parts)
        children.setdefault(parent, []).append(pid)
    pids = {root_pid}
    pending = [root_pid]
    while pending:
        current = pending.pop()
        for child in children.get(current, []):
            if child not in pids:
                pids.add(child)
                pending.append(child)
    return pids


def gpu_memory_bytes_for_process_tree(root_pid: int) -> int:
    pids = _descendant_pids(root_pid)
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-compute-apps=pid,used_memory",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return 0
    total_mib = 0
    for line in output.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 2:
            continue
        try:
            pid = int(parts[0])
            used_mib = int(parts[1])
        except ValueError:
            continue
        if pid in pids:
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
        "endpoint": RERANK_ENDPOINT,
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
    candidate_payload, candidate_rows = load_candidate_payloads(
        args.candidate,
        query_ids=query_ids,
        known_chunk_ids=set(chunk_text_by_id),
        expected_profile_id=args.profile_id,
        expected_candidate_top_k=args.candidate_top_k,
    )
    model_dir, model_identity = validate_complete_model(args.model_dir)
    template_identity = validate_score_template(args.score_template)
    score_rows, runtime = score_panel_profile(
        args.base_url,
        args.server_pid,
        queries,
        candidate_rows,
        chunk_text_by_id,
        args.timeout_seconds,
    )
    score_payload = {
        "schema_version": "1.0",
        "reranker_id": "llama_nemotron_rerank_1b_v2",
        "model": model_identity,
        "dataset": candidate_payload["dataset"],
        "candidate": {
            "variant": args.profile_id,
            "source_artifact": args.candidate.as_posix(),
            "source_artifact_sha256": sha256_file(args.candidate),
            "source_schema": candidate_payload["schema_version"],
            "ranking_sha256": candidate_payload["ranking_sha256"],
            "candidate_top_k": args.candidate_top_k,
        },
        "score_template": template_identity,
        "runtime": runtime,
        "scores": [
            {
                "query_id": query_id,
                "scores_by_chunk_id": scores,
            }
            for query_id, scores in zip(query_ids, score_rows, strict=True)
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    assert_portable_payload(score_payload)
    atomic_json(args.score_output, score_payload)

    base_rankings = [list(row) for row in candidate_rows]
    reranked_rankings: list[list[str]] = []
    for ids, scores in zip(candidate_rows, score_rows, strict=True):
        ordered = sorted(range(len(ids)), key=lambda index: (-scores[ids[index]], index))
        reranked_rankings.append([ids[index] for index in ordered[: args.rerank_top_k]])
    base_metrics = evaluate_rankings(queries, base_rankings)
    reranked_metrics = evaluate_rankings(queries, reranked_rankings)
    pipeline = build_pipeline_payload(
        candidate_payload=candidate_payload,
        candidate_path=args.candidate,
        score_path=args.score_output,
        reranker_id="llama_nemotron_rerank_1b_v2",
        reranker=model_identity,
        rerank_top_k=args.rerank_top_k,
        base_metrics=base_metrics,
        reranked_metrics=reranked_metrics,
        base_rankings=base_rankings,
        reranked_rankings=reranked_rankings,
        queries=queries,
        runtime=runtime,
    )
    assert_portable_payload(pipeline)
    atomic_json(args.pipeline_output, pipeline)
    return pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--score-template", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8099")
    parser.add_argument("--server-pid", type=int, required=True)
    parser.add_argument("--candidate-top-k", type=int, default=50)
    parser.add_argument("--rerank-top-k", type=int, default=20)
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    parser.add_argument("--score-output", type=Path, required=True)
    parser.add_argument("--pipeline-output", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    pipeline = benchmark_profile(args)
    print(json.dumps(pipeline["evaluation"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
