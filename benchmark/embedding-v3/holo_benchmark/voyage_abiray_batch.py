"""Submit, inspect, and collect Voyage Batch reranking for canonical Abiray.

This module deliberately uses the REST Batch and Files APIs instead of the
synchronous rerank endpoint. Operations are idempotent and split into submit,
status, and collect so a 12-hour batch window never blocks repository work.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .artifact_portability import assert_portable_payload, sanitize_host_payload
from .reranker_metrics import (
    build_union_candidates,
    candidate_ids,
    evaluate_reranker_effect,
    scores_to_rankings,
)
from .reranker_runtime import (
    CORPUS_SHA256,
    DEFAULT_RERANK_INSTRUCTION,
    atomic_json,
    load_frozen_dataset,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS = PROJECT_ROOT / "results"
CANDIDATES = RESULTS / "reranker" / "candidates"
SCORES = RESULTS / "reranker" / "scores"
PIPELINES = RESULTS / "reranker" / "pipelines" / "voyage_rerank_2_5"
STATE = RESULTS / "raw" / "reranker" / "voyage_rerank_2_5_nemotron_8b_abiray_batch.json"
BLOCKED = RESULTS / "reranker" / "voyage_rerank_2_5_nemotron_8b_abiray_blocked.json"
VARIANTS = (
    "nemotron_8b_abiray_q4_audit_4096",
    "nemotron_8b_abiray_q4_audit_1024",
)
RERANK_TOP_K = 20
MODEL = "rerank-2.5"
API_ROOT = "https://api.voyageai.com/v1"
TERMINAL_STATUSES = {
    "completed",
    "partially_completed",
    "failed",
    "expired",
    "cancelled",
    "canceled",
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _portable(payload: Mapping[str, Any]) -> dict[str, Any]:
    value = sanitize_host_payload(dict(payload))
    assert_portable_payload(value)
    return value


def _api_key(path: Path) -> str:
    value = path.expanduser().read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError("Voyage API key file is empty")
    return value


def _json_request(
    method: str,
    path: str,
    api_key: str,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    body = None
    headers = {"Authorization": f"Bearer {api_key}"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{API_ROOT}{path}", data=body, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Voyage API HTTP {exc.code}: {detail}") from exc
    if not isinstance(result, dict):
        raise RuntimeError("Voyage API returned a non-object JSON response")
    return result


def _multipart_upload(path: Path, api_key: str) -> dict[str, Any]:
    boundary = "----holo-voyage-batch-boundary"
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
        f"{API_ROOT}/files",
        data=b"".join(chunks),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Voyage Files API HTTP {exc.code}: {detail}") from exc
    if not isinstance(result, dict) or not result.get("id"):
        raise RuntimeError("Voyage Files API did not return a file id")
    return result


def _download_file(file_id: str, api_key: str) -> bytes:
    request = urllib.request.Request(
        f"{API_ROOT}/files/{file_id}/content",
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Voyage file download HTTP {exc.code}: {detail}") from exc


def _load_context() -> tuple[
    dict[str, dict[str, Any]],
    list[dict[str, Any]],
    list[list[str]],
    dict[str, str],
]:
    chunks, queries = load_frozen_dataset(PROJECT_ROOT)
    expected_ids = [str(row["query_id"]) for row in queries]
    payloads: dict[str, dict[str, Any]] = {}
    candidate_rows: dict[str, list[list[dict[str, Any]]]] = {}
    for variant in VARIANTS:
        path = CANDIDATES / f"{variant}.json"
        payload = _read_json(path)
        if payload.get("variant") != variant:
            raise ValueError(f"candidate variant mismatch: {path}")
        if (payload.get("dataset") or {}).get("corpus_sha256") != CORPUS_SHA256:
            raise ValueError(f"candidate corpus mismatch: {path}")
        rows = list(payload.get("queries") or [])
        if [str(row.get("query_id")) for row in rows] != expected_ids:
            raise ValueError(f"candidate query order mismatch: {path}")
        if any(len(list(row.get("candidates") or [])) != 50 for row in rows):
            raise ValueError(f"candidate top-k mismatch: {path}")
        assert_portable_payload(payload)
        payloads[variant] = payload
        candidate_rows[variant] = [list(row["candidates"]) for row in rows]
    union_ids = build_union_candidates(candidate_rows, RERANK_TOP_K)
    text_by_id = {str(row["chunk_id"]): str(row["text"]) for row in chunks}
    return payloads, queries, union_ids, text_by_id


def build_jsonl_lines() -> list[str]:
    _, queries, union_ids, text_by_id = _load_context()
    lines: list[str] = []
    for query, ids in zip(queries, union_ids, strict=True):
        query_id = str(query["query_id"])
        body = {
            "query": str(query["query"]),
            "documents": [text_by_id[chunk_id] for chunk_id in ids],
        }
        lines.append(
            json.dumps(
                {"custom_id": query_id, "body": body},
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    if len(lines) != 150:
        raise ValueError(f"expected 150 batch requests, found {len(lines)}")
    return lines


def submit(args: argparse.Namespace) -> dict[str, Any]:
    if STATE.exists() and not args.force:
        state = _read_json(STATE)
        if state.get("batch_id"):
            raise RuntimeError(
                f"batch already submitted as {state['batch_id']}; use status/collect"
            )
    api_key = _api_key(args.api_key_path)
    lines = build_jsonl_lines()
    with tempfile.TemporaryDirectory(prefix="holo-voyage-batch-") as tmp:
        input_path = Path(tmp) / "nemotron_8b_abiray_rerank.jsonl"
        input_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        uploaded = _multipart_upload(input_path, api_key)
    batch = _json_request(
        "POST",
        "/batches",
        api_key,
        {
            "endpoint": "/v1/rerank",
            "input_file_id": uploaded["id"],
            "completion_window": "12h",
            "request_params": {
                "model": MODEL,
                "top_k": RERANK_TOP_K,
                "return_documents": False,
                "truncation": True,
            },
            "metadata": {
                "project": "holo-models",
                "benchmark": "embedding-v3",
                "profile": "nemotron-8b-abiray",
            },
        },
    )
    state = _portable(
        {
            "schema_version": "1.0",
            "status": str(batch.get("status") or "submitted"),
            "batch_id": batch.get("id"),
            "input_file_id": uploaded.get("id"),
            "output_file_id": batch.get("output_file_id"),
            "error_file_id": batch.get("error_file_id"),
            "request_count": 150,
            "variants": list(VARIANTS),
            "model": MODEL,
            "endpoint": "/v1/rerank",
            "completion_window": "12h",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "batch": batch,
        }
    )
    atomic_json(STATE, state)
    return state


def status(args: argparse.Namespace) -> dict[str, Any]:
    state = _read_json(STATE)
    batch_id = str(state.get("batch_id") or "")
    if not batch_id:
        raise ValueError("batch state does not contain batch_id")
    batch = _json_request("GET", f"/batches/{batch_id}", _api_key(args.api_key_path))
    state.update(
        {
            "status": batch.get("status"),
            "output_file_id": batch.get("output_file_id"),
            "error_file_id": batch.get("error_file_id"),
            "request_counts": batch.get("request_counts"),
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "batch": batch,
        }
    )
    atomic_json(STATE, _portable(state))
    return state


def _response_scores(response_body: Mapping[str, Any], ids: Sequence[str]) -> dict[str, float]:
    data = response_body.get("data")
    if not isinstance(data, list):
        raise ValueError("batch rerank response has no data list")
    result: dict[str, float] = {}
    for item in data:
        if not isinstance(item, Mapping):
            raise ValueError("batch rerank response data row is not an object")
        index = int(item["index"])
        if index < 0 or index >= len(ids):
            raise ValueError(f"rerank index out of range: {index}")
        result[ids[index]] = float(item["relevance_score"])
    if set(result) != set(ids):
        raise ValueError("batch rerank response did not score every union candidate")
    return result


def _parse_output(content: bytes, query_ids: Sequence[str], union_ids: Sequence[Sequence[str]]) -> list[dict[str, float]]:
    by_query: dict[str, dict[str, float]] = {}
    for raw_line in content.decode("utf-8").splitlines():
        if not raw_line.strip():
            continue
        row = json.loads(raw_line)
        custom_id = str(row.get("custom_id") or "")
        if custom_id in by_query:
            raise ValueError(f"duplicate batch custom_id: {custom_id}")
        if row.get("error"):
            raise RuntimeError(f"batch request failed for {custom_id}: {row['error']}")
        response = row.get("response")
        if not isinstance(response, Mapping):
            raise ValueError(f"missing response object for {custom_id}")
        status_code = int(response.get("status_code") or 0)
        if status_code != 200:
            raise RuntimeError(f"batch response HTTP {status_code} for {custom_id}")
        body = response.get("body")
        if not isinstance(body, Mapping):
            raise ValueError(f"missing response body for {custom_id}")
        try:
            index = query_ids.index(custom_id)
        except ValueError as exc:
            raise ValueError(f"unexpected batch custom_id: {custom_id}") from exc
        by_query[custom_id] = _response_scores(body, union_ids[index])
    if set(by_query) != set(query_ids):
        missing = sorted(set(query_ids) - set(by_query))
        raise ValueError(f"batch output missing requests: {missing[:10]}")
    return [by_query[query_id] for query_id in query_ids]


def collect(args: argparse.Namespace) -> dict[str, Any]:
    state = status(args)
    current = str(state.get("status") or "")
    if current not in TERMINAL_STATUSES:
        return {"status": "PENDING", "batch_status": current, "state": str(STATE)}
    if current != "completed":
        raise RuntimeError(f"Voyage batch ended with non-complete status: {current}")
    output_file_id = str(state.get("output_file_id") or "")
    if not output_file_id:
        raise ValueError("completed batch has no output_file_id")

    payloads, queries, union_ids, _ = _load_context()
    query_ids = [str(row["query_id"]) for row in queries]
    score_rows = _parse_output(
        _download_file(output_file_id, _api_key(args.api_key_path)),
        query_ids,
        union_ids,
    )
    score_path = SCORES / "voyage_rerank_2_5_nemotron_8b_abiray.json"
    score = _portable(
        {
            "schema_version": "1.0",
            "reranker_id": "voyage_rerank_2_5",
            "model": {"id": MODEL, "provider": "Voyage AI", "api_model": True},
            "corpus_sha256": CORPUS_SHA256,
            "instruction": DEFAULT_RERANK_INSTRUCTION,
            "runtime": {
                "backend": "voyage_batch_api",
                "batch_id": state["batch_id"],
                "input_file_id": state.get("input_file_id"),
                "output_file_id": output_file_id,
                "request_counts": state.get("request_counts"),
                "completion_window": "12h",
            },
            "variants": list(VARIANTS),
            "queries": [
                {
                    "query_id": query_id,
                    "candidate_ids": list(ids),
                    "scores": scores,
                }
                for query_id, ids, scores in zip(
                    query_ids, union_ids, score_rows, strict=True
                )
            ],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    atomic_json(score_path, score)

    written = [str(score_path.relative_to(PROJECT_ROOT))]
    for variant in VARIANTS:
        rows = [list(row["candidates"]) for row in payloads[variant]["queries"]]
        top_rows = [row[:RERANK_TOP_K] for row in rows]
        evaluation = evaluate_reranker_effect(
            queries,
            candidate_ids(top_rows),
            scores_to_rankings(top_rows, score_rows),
            RERANK_TOP_K,
        )
        pipeline = _portable(
            {
                "schema_version": "1.0",
                "pipeline_id": f"{variant}__voyage_rerank_2_5",
                "embedding_variant": variant,
                "reranker_id": "voyage_rerank_2_5",
                "candidate_top_k": 50,
                "rerank_top_k": RERANK_TOP_K,
                "score_artifact": str(score_path.relative_to(PROJECT_ROOT)),
                "evaluation": evaluation,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        path = PIPELINES / f"{variant}.json"
        atomic_json(path, pipeline)
        written.append(str(path.relative_to(PROJECT_ROOT)))

    if BLOCKED.exists():
        BLOCKED.unlink()
    state["status"] = "COLLECTED"
    state["collected_at"] = datetime.now(timezone.utc).isoformat()
    state["written"] = written
    atomic_json(STATE, _portable(state))
    return {"status": "PASS", "written": written, "batch_id": state["batch_id"]}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("submit", "status", "collect"):
        item = sub.add_parser(command)
        item.add_argument("--api-key-path", type=Path, required=True)
        if command == "submit":
            item.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    functions = {"submit": submit, "status": status, "collect": collect}
    result = functions[args.command](args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
