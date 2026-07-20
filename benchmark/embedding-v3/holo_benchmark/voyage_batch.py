from __future__ import annotations

import hashlib
import json
import os
import stat
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

API_BASE = "https://api.voyageai.com"
TERMINAL_BATCH_STATUSES = {
    "completed",
    "partially_completed",
    "failed",
    "cancelled",
    "canceled",
}


class VoyageBatchHTTPError(RuntimeError):
    def __init__(
        self,
        status_code: int,
        message: str,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    _atomic_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )


def _validated_key_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file() or resolved.stat().st_size == 0:
        raise RuntimeError(f"Voyage key is missing or empty: {resolved}")
    mode = stat.S_IMODE(resolved.stat().st_mode)
    if mode & 0o077:
        raise PermissionError(f"unsafe permissions on {resolved}; use chmod 600")
    return resolved


def _read_api_key(path: Path) -> str:
    key = _validated_key_path(path).read_text(encoding="utf-8").strip()
    if not key:
        raise RuntimeError("Voyage key file is empty")
    return key


def _sanitized_error(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return "empty response body"
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text[:1000]
    if isinstance(payload, Mapping):
        error = payload.get("error")
        if isinstance(error, Mapping):
            message = error.get("message") or error.get("detail") or error
            return str(message)[:1000]
        message = payload.get("message") or payload.get("detail")
        if message is not None:
            return str(message)[:1000]
    return json.dumps(payload, ensure_ascii=False)[:1000]


def _retry_after(headers: Mapping[str, str]) -> float | None:
    raw = headers.get("Retry-After") or headers.get("retry-after")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _open(request: urllib.request.Request, timeout: float = 180.0) -> bytes:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        message = _sanitized_error(raw)
        retry_after = _retry_after(dict(exc.headers.items()))
        raise VoyageBatchHTTPError(
            int(exc.code),
            f"Voyage Batch API HTTP {exc.code}: {message}",
            retry_after,
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Voyage Batch API network error: {exc.reason}") from exc


def _json_request(
    method: str,
    path: str,
    api_key: str,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    data = None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        API_BASE + path,
        data=data,
        headers=headers,
        method=method,
    )
    raw = _open(request)
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Voyage Batch API returned invalid JSON") from exc
    if not isinstance(decoded, dict):
        raise RuntimeError("Voyage Batch API returned a non-object JSON response")
    return decoded


def _text_request(path: str, api_key: str) -> str:
    request = urllib.request.Request(
        API_BASE + path,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "text/plain",
        },
        method="GET",
    )
    return _open(request).decode("utf-8")


def _upload_jsonl(path: Path, api_key: str) -> dict[str, Any]:
    boundary = f"----holo-voyage-{uuid.uuid4().hex}"
    file_bytes = path.read_bytes()
    chunks = [
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="purpose"\r\n\r\n',
        b"batch\r\n",
        f"--{boundary}\r\n".encode(),
        (
            'Content-Disposition: form-data; name="file"; '
            f'filename="{path.name}"\r\n'
        ).encode(),
        b"Content-Type: application/jsonl\r\n\r\n",
        file_bytes,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    request = urllib.request.Request(
        API_BASE + "/v1/files",
        data=b"".join(chunks),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
        method="POST",
    )
    raw = _open(request)
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict) or not payload.get("id"):
        raise RuntimeError("Voyage file upload did not return a file id")
    return payload


def _call_with_429_retry(
    operation: Any,
    retry_seconds: float,
) -> tuple[Any, int]:
    retries = 0
    while True:
        try:
            return operation(), retries
        except VoyageBatchHTTPError as exc:
            if exc.status_code != 429 or retries >= 1:
                raise
            retries += 1
            time.sleep(max(retry_seconds, exc.retry_after or 0.0))


def build_batch_jsonl(
    queries: Sequence[Mapping[str, Any]],
    union_ids: Sequence[Sequence[str]],
    chunk_text_by_id: Mapping[str, str],
    instruction: str,
    output_path: Path,
    query_text_builder: Any,
) -> dict[str, Any]:
    if len(queries) != len(union_ids):
        raise ValueError("query and candidate counts diverge")
    lines: list[str] = []
    query_ids: list[str] = []
    pair_count = 0
    for query, chunk_ids in zip(queries, union_ids, strict=True):
        query_id = str(query.get("query_id") or "")
        if not query_id:
            raise ValueError("query without query_id")
        if query_id in query_ids:
            raise ValueError(f"duplicate query_id: {query_id}")
        ids = [str(chunk_id) for chunk_id in chunk_ids]
        if not ids:
            raise ValueError(f"query without candidates: {query_id}")
        missing = [chunk_id for chunk_id in ids if chunk_id not in chunk_text_by_id]
        if missing:
            raise ValueError(f"unknown candidate ids for {query_id}: {missing[:3]}")
        request = {
            "custom_id": query_id,
            "body": {
                "query": query_text_builder(query, instruction),
                "documents": [chunk_text_by_id[chunk_id] for chunk_id in ids],
            },
        }
        lines.append(json.dumps(request, ensure_ascii=False, separators=(",", ":")))
        query_ids.append(query_id)
        pair_count += len(ids)
    content = "\n".join(lines) + "\n"
    _atomic_text(output_path, content)
    encoded = content.encode("utf-8")
    return {
        "requests": len(lines),
        "pairs": pair_count,
        "bytes": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "query_ids": query_ids,
    }


def parse_batch_output(
    content: str,
    queries: Sequence[Mapping[str, Any]],
    union_ids: Sequence[Sequence[str]],
) -> tuple[list[dict[str, float]], dict[str, int], list[dict[str, Any]]]:
    expected = {
        str(query["query_id"]): [str(chunk_id) for chunk_id in chunk_ids]
        for query, chunk_ids in zip(queries, union_ids, strict=True)
    }
    rows: dict[str, dict[str, float]] = {}
    total_tokens = 0
    errors: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append({"line": line_number, "error": f"invalid JSON: {exc}"})
            continue
        custom_id = str(payload.get("custom_id") or "")
        if custom_id not in expected:
            errors.append({"line": line_number, "custom_id": custom_id, "error": "unexpected custom_id"})
            continue
        if payload.get("error"):
            errors.append({"custom_id": custom_id, "error": payload.get("error")})
            continue
        response = payload.get("response") or {}
        status_code = int(response.get("status_code") or 0)
        if status_code != 200:
            errors.append({"custom_id": custom_id, "status_code": status_code, "error": response.get("body")})
            continue
        body = response.get("body") or {}
        results = body.get("data")
        if results is None:
            results = body.get("results")
        if not isinstance(results, list):
            errors.append({"custom_id": custom_id, "error": "missing rerank results"})
            continue
        chunk_ids = expected[custom_id]
        score_map: dict[str, float] = {}
        for item in results:
            try:
                index = int(item["index"])
                score = float(item["relevance_score"])
            except (KeyError, TypeError, ValueError) as exc:
                errors.append({"custom_id": custom_id, "error": f"invalid result item: {exc}"})
                score_map = {}
                break
            if index < 0 or index >= len(chunk_ids):
                errors.append({"custom_id": custom_id, "error": f"result index out of range: {index}"})
                score_map = {}
                break
            chunk_id = chunk_ids[index]
            if chunk_id in score_map:
                errors.append({"custom_id": custom_id, "error": f"duplicate result index: {index}"})
                score_map = {}
                break
            score_map[chunk_id] = score
        if len(score_map) != len(chunk_ids):
            if score_map:
                errors.append({"custom_id": custom_id, "error": "result count diverged"})
            continue
        rows[custom_id] = score_map
        usage = body.get("usage") or {}
        total_tokens += int(usage.get("total_tokens") or body.get("total_tokens") or 0)

    missing = [query_id for query_id in expected if query_id not in rows]
    errors.extend({"custom_id": query_id, "error": "missing batch output"} for query_id in missing)
    ordered = [rows[str(query["query_id"])] for query in queries if str(query["query_id"]) in rows]
    return ordered, {"tokens": total_tokens, "requests": len(rows)}, errors


def execute_batch(
    *,
    key_path: Path,
    input_path: Path,
    state_path: Path,
    output_path: Path,
    error_path: Path,
    input_sha256: str,
    request_count: int,
    model: str,
    resume: bool,
    poll_interval_seconds: float,
    submit_retry_seconds: float,
    metadata: Mapping[str, str],
) -> dict[str, Any]:
    if poll_interval_seconds <= 0:
        raise ValueError("poll_interval_seconds must be positive")
    api_key = _read_api_key(key_path)
    state: dict[str, Any] = {}
    if resume and state_path.is_file():
        loaded = json.loads(state_path.read_text(encoding="utf-8"))
        if loaded.get("model") != model or loaded.get("input_sha256") != input_sha256:
            raise RuntimeError("incompatible Voyage batch checkpoint")
        state = dict(loaded)

    submit_retries = int(state.get("submit_retries") or 0)
    if not state.get("input_file_id"):
        uploaded, retries = _call_with_429_retry(
            lambda: _upload_jsonl(input_path, api_key),
            submit_retry_seconds,
        )
        submit_retries += retries
        state.update(
            {
                "schema_version": "1.0",
                "model": model,
                "input_sha256": input_sha256,
                "request_count": request_count,
                "input_file_id": uploaded["id"],
                "submit_retries": submit_retries,
                "updated_at": time.time(),
            }
        )
        _atomic_json(state_path, state)

    if not state.get("batch_id"):
        created, retries = _call_with_429_retry(
            lambda: _json_request(
                "POST",
                "/v1/batches",
                api_key,
                {
                    "endpoint": "/v1/rerank",
                    "input_file_id": state["input_file_id"],
                    "completion_window": "12h",
                    "request_params": {
                        "model": model,
                        "truncation": False,
                        "return_documents": False,
                    },
                    "metadata": dict(metadata),
                },
            ),
            submit_retry_seconds,
        )
        submit_retries += retries
        state.update(
            {
                "batch_id": created["id"],
                "status": created.get("status"),
                "submit_retries": submit_retries,
                "created_at": created.get("created_at"),
                "updated_at": time.time(),
            }
        )
        _atomic_json(state_path, state)

    started = time.monotonic()
    batch: dict[str, Any] = {}
    while True:
        try:
            batch = _json_request("GET", f"/v1/batches/{state['batch_id']}", api_key)
        except VoyageBatchHTTPError as exc:
            if exc.status_code != 429:
                raise
            time.sleep(max(poll_interval_seconds, exc.retry_after or 0.0))
            continue
        state.update(
            {
                "status": batch.get("status"),
                "request_counts": batch.get("request_counts"),
                "output_file_id": batch.get("output_file_id"),
                "error_file_id": batch.get("error_file_id"),
                "updated_at": time.time(),
            }
        )
        _atomic_json(state_path, state)
        if str(batch.get("status")) in TERMINAL_BATCH_STATUSES:
            break
        time.sleep(poll_interval_seconds)

    status = str(batch.get("status"))
    if batch.get("error_file_id"):
        _atomic_text(error_path, _text_request(f"/v1/files/{batch['error_file_id']}/content", api_key))
    if not batch.get("output_file_id"):
        raise RuntimeError(f"Voyage batch ended without output: status={status}")
    _atomic_text(output_path, _text_request(f"/v1/files/{batch['output_file_id']}/content", api_key))
    return {
        "status": status,
        "request_counts": batch.get("request_counts") or {},
        "created_at": batch.get("created_at"),
        "in_progress_at": batch.get("in_progress_at"),
        "finalizing_at": batch.get("finalizing_at"),
        "completed_at": batch.get("completed_at"),
        "partially_completed_at": batch.get("partially_completed_at"),
        "wall_seconds": round(time.monotonic() - started, 4),
        "submit_retries": submit_retries,
        "error_file_present": bool(batch.get("error_file_id")),
    }
