from __future__ import annotations

import importlib.metadata
import os
import stat
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .gate2_worker import _find_llama_server, _wait_server
from .reranker_runtime import (
    CORPUS_SHA256,
    DEFAULT_RERANK_INSTRUCTION,
    ResourceSampler,
    _free_port,
    _parse_llama_rerank,
    atomic_json,
    post_json,
    read_json,
    rerank_query_text,
)


def score_qwen_cross_encoder(
    model_path: Path,
    queries: Sequence[dict[str, Any]],
    union_ids: Sequence[Sequence[str]],
    chunk_text_by_id: Mapping[str, str],
    device: str,
    batch_size: int,
    instruction: str = DEFAULT_RERANK_INSTRUCTION,
) -> tuple[list[dict[str, float]], dict[str, Any]]:
    try:
        import torch
        from sentence_transformers import CrossEncoder
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers and torch are required for Qwen reranking"
        ) from exc

    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
    score_rows: list[dict[str, float]] = []
    latencies: list[float] = []
    pair_count = 0
    with ResourceSampler() as resources:
        load_started = time.monotonic()
        try:
            model = CrossEncoder(
                str(model_path),
                device=device,
                trust_remote_code=True,
            )
        except TypeError:
            model = CrossEncoder(
                str(model_path),
                device=device,
                model_kwargs={"trust_remote_code": True},
            )
        load_seconds = time.monotonic() - load_started
        for query, chunk_ids in zip(queries, union_ids, strict=True):
            query_text = rerank_query_text(query, instruction)
            pairs = [
                (query_text, chunk_text_by_id[chunk_id])
                for chunk_id in chunk_ids
            ]
            request_started = time.monotonic()
            raw_scores = model.predict(
                pairs,
                batch_size=batch_size,
                show_progress_bar=False,
            )
            latencies.append(time.monotonic() - request_started)
            pair_count += len(pairs)
            scores: dict[str, float] = {}
            for chunk_id, score in zip(chunk_ids, raw_scores, strict=True):
                array = score
                try:
                    import numpy as np

                    values = np.asarray(array).reshape(-1)
                    if values.size != 1:
                        raise RuntimeError(
                            f"Qwen reranker returned {values.size} logits per pair"
                        )
                    scalar = float(values[0])
                except ImportError:
                    scalar = float(array)
                scores[chunk_id] = scalar
            score_rows.append(scores)
        peak_vram = (
            int(torch.cuda.max_memory_allocated())
            if device == "cuda"
            else None
        )

    ordered = sorted(latencies)

    def percentile(fraction: float) -> float | None:
        if not ordered:
            return None
        index = min(len(ordered) - 1, int((len(ordered) - 1) * fraction))
        return ordered[index]

    return score_rows, {
        "backend": "sentence-transformers.CrossEncoder",
        "device": device,
        "load_seconds": round(load_seconds, 4),
        "score_seconds": round(sum(latencies), 4),
        "total_seconds": round(time.monotonic() - started, 4),
        "queries": len(latencies),
        "pairs": pair_count,
        "latency_p50_seconds": (
            round(percentile(0.50), 4) if latencies else None
        ),
        "latency_p95_seconds": (
            round(percentile(0.95), 4) if latencies else None
        ),
        "latency_max_seconds": round(max(latencies), 4) if latencies else None,
        "peak_vram_bytes": peak_vram,
        **resources.as_dict(),
    }


def score_qwen_llama_cpp(
    model_file: Path,
    queries: Sequence[dict[str, Any]],
    union_ids: Sequence[Sequence[str]],
    chunk_text_by_id: Mapping[str, str],
    device: str,
    instruction: str = DEFAULT_RERANK_INSTRUCTION,
) -> tuple[list[dict[str, float]], dict[str, Any]]:
    llama_server = _find_llama_server()
    port = _free_port()
    command = [
        llama_server,
        "-m",
        str(model_file),
        "--reranking",
        "--pooling",
        "rank",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "-np",
        "1",
        "-ngl",
        "99" if device == "cuda" else "0",
        "-c",
        "32768",
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    latencies: list[float] = []
    score_rows: list[dict[str, float]] = []
    started = time.monotonic()
    with ResourceSampler() as resources:
        try:
            load_started = time.monotonic()
            _wait_server(port, process)
            load_seconds = time.monotonic() - load_started
            for query, chunk_ids in zip(queries, union_ids, strict=True):
                documents = [chunk_text_by_id[chunk_id] for chunk_id in chunk_ids]
                request_started = time.monotonic()
                payload = post_json(
                    f"http://127.0.0.1:{port}/v1/rerank",
                    {
                        "model": model_file.name,
                        "query": rerank_query_text(query, instruction),
                        "documents": documents,
                        "top_n": len(documents),
                    },
                )
                latencies.append(time.monotonic() - request_started)
                scores = _parse_llama_rerank(payload, documents)
                score_rows.append(dict(zip(chunk_ids, scores, strict=True)))
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=15)

    ordered = sorted(latencies)

    def percentile(fraction: float) -> float | None:
        if not ordered:
            return None
        index = min(len(ordered) - 1, int((len(ordered) - 1) * fraction))
        return ordered[index]

    return score_rows, {
        "backend": "llama.cpp /v1/rerank",
        "device": device,
        "llama_server": llama_server,
        "command": command,
        "load_seconds": round(load_seconds, 4),
        "total_seconds": round(time.monotonic() - started, 4),
        "requests": len(latencies),
        "latency_p50_seconds": (
            round(percentile(0.50), 4) if latencies else None
        ),
        "latency_p95_seconds": (
            round(percentile(0.95), 4) if latencies else None
        ),
        "latency_max_seconds": round(max(latencies), 4) if latencies else None,
        **resources.as_dict(),
    }


def configure_voyage_key(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file() or resolved.stat().st_size == 0:
        raise RuntimeError(f"Voyage key is missing or empty: {resolved}")
    mode = stat.S_IMODE(resolved.stat().st_mode)
    if mode & 0o077:
        raise PermissionError(f"unsafe permissions on {resolved}; use chmod 600")
    os.environ["VOYAGE_API_KEY_PATH"] = str(resolved)
    return resolved


def _status_code(exc: BaseException) -> int | None:
    direct = getattr(exc, "status_code", None)
    response = getattr(exc, "response", None)
    nested = getattr(response, "status_code", None)
    if isinstance(direct, int):
        return direct
    if isinstance(nested, int):
        return nested
    message = str(exc).lower()
    return 429 if "429" in message or "rate limit" in message else None


def score_voyage_reranker(
    key_path: Path,
    queries: Sequence[dict[str, Any]],
    union_ids: Sequence[Sequence[str]],
    chunk_text_by_id: Mapping[str, str],
    checkpoint_path: Path,
    resume: bool,
    model: str = "rerank-2.5",
    request_interval_seconds: float = 1.0,
    instruction: str = DEFAULT_RERANK_INSTRUCTION,
) -> tuple[list[dict[str, float]], dict[str, Any]]:
    configure_voyage_key(key_path)
    try:
        import voyageai
    except ImportError as exc:
        raise RuntimeError("voyageai SDK is required") from exc

    client = voyageai.Client(max_retries=0)
    checkpoint: dict[str, Any] = {}
    if resume and checkpoint_path.is_file():
        checkpoint = read_json(checkpoint_path)
        if (
            checkpoint.get("model") != model
            or checkpoint.get("corpus_sha256") != CORPUS_SHA256
        ):
            raise RuntimeError("incompatible Voyage rerank checkpoint")
    rows = dict(checkpoint.get("rows") or {})
    usage = {
        "tokens": 0,
        "requests": 0,
        "retries": 0,
        "seconds": 0.0,
    }
    usage.update(dict(checkpoint.get("usage") or {}))
    last_request_at: float | None = None
    latencies: list[float] = list(checkpoint.get("latencies_seconds") or [])

    for query, chunk_ids in zip(queries, union_ids, strict=True):
        query_id = str(query["query_id"])
        if query_id in rows:
            continue
        documents = [chunk_text_by_id[chunk_id] for chunk_id in chunk_ids]
        if last_request_at is not None:
            wait = request_interval_seconds - (time.monotonic() - last_request_at)
            if wait > 0:
                time.sleep(wait)
        retries = 0
        while True:
            started = time.monotonic()
            last_request_at = started
            try:
                kwargs = {
                    "query": rerank_query_text(query, instruction),
                    "documents": documents,
                    "model": model,
                    "truncation": False,
                }
                try:
                    response = client.rerank(
                        **kwargs,
                        top_k=len(documents),
                    )
                except TypeError:
                    response = client.rerank(
                        **kwargs,
                        top_n=len(documents),
                    )
                break
            except Exception as exc:
                if _status_code(exc) != 429 or retries >= 1:
                    raise
                retries += 1
                time.sleep(max(95.0, request_interval_seconds))

        elapsed = time.monotonic() - started
        latencies.append(elapsed)
        results = sorted(response.results, key=lambda item: int(item.index))
        if len(results) != len(chunk_ids):
            raise RuntimeError("Voyage rerank response count diverged")
        rows[query_id] = {
            chunk_id: float(item.relevance_score)
            for chunk_id, item in zip(chunk_ids, results, strict=True)
        }
        total_tokens = getattr(response, "total_tokens", None)
        if total_tokens is None:
            total_tokens = getattr(
                getattr(response, "usage", None),
                "total_tokens",
                0,
            )
        usage["tokens"] += int(total_tokens or 0)
        usage["requests"] += 1
        usage["retries"] += retries
        usage["seconds"] += elapsed
        atomic_json(
            checkpoint_path,
            {
                "schema_version": "1.0",
                "model": model,
                "corpus_sha256": CORPUS_SHA256,
                "rows": rows,
                "usage": usage,
                "latencies_seconds": latencies,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    missing = [
        str(query["query_id"])
        for query in queries
        if str(query["query_id"]) not in rows
    ]
    if missing:
        raise RuntimeError(f"Voyage rerank checkpoint incomplete: {missing[:3]}")

    ordered = sorted(latencies)

    def percentile(fraction: float) -> float | None:
        if not ordered:
            return None
        index = min(len(ordered) - 1, int((len(ordered) - 1) * fraction))
        return ordered[index]

    return [
        {
            str(chunk_id): float(score)
            for chunk_id, score in rows[str(query["query_id"])].items()
        }
        for query in queries
    ], {
        "backend": "Voyage API",
        "model": model,
        "sdk_version": importlib.metadata.version("voyageai"),
        "usage": usage,
        "latency_p50_seconds": (
            round(percentile(0.50), 4) if latencies else None
        ),
        "latency_p95_seconds": (
            round(percentile(0.95), 4) if latencies else None
        ),
        "latency_max_seconds": round(max(latencies), 4) if latencies else None,
    }
