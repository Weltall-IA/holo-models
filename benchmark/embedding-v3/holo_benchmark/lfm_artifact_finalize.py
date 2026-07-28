"""Validate and finalize the existing canonical LFM2.5 result without rerunning it."""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

from .artifact_portability import (
    assert_portable_payload,
    host_specific_strings,
    sanitize_host_payload,
)
from .lfm_benchmark import (
    EXPECTED_GGUF_BYTES,
    EXPECTED_GGUF_SHA256,
    PROFILE_ID,
    REVISION,
)
from .reranker_runtime import CORPUS_SHA256, atomic_json, read_json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULT = PROJECT_ROOT / "results" / "gate3" / f"{PROFILE_ID}.json"


def _assert_finite(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _assert_finite(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _assert_finite(item, f"{path}[{index}]")
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"non-finite number at {path}")


def validate_lfm_result(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != "1.0":
        raise ValueError("unexpected result schema version")
    if payload.get("id") != PROFILE_ID or payload.get("status") != "COMPLETED":
        raise ValueError("result identity or status mismatch")
    if payload.get("gate_result") not in {"PASS", "FAIL"}:
        raise ValueError("invalid gate result")

    model = payload.get("model") or {}
    if model.get("id") != PROFILE_ID:
        raise ValueError("model profile mismatch")
    if model.get("revision") != REVISION:
        raise ValueError("model revision mismatch")
    if int(model.get("bytes") or 0) != EXPECTED_GGUF_BYTES:
        raise ValueError("model byte count mismatch")
    if model.get("sha256") != EXPECTED_GGUF_SHA256:
        raise ValueError("model SHA-256 mismatch")

    dataset = payload.get("dataset") or {}
    if dataset.get("combined_sha256") != CORPUS_SHA256:
        raise ValueError("corpus SHA-256 mismatch")
    if int(dataset.get("documents") or 0) != 600:
        raise ValueError("document count mismatch")
    if int(dataset.get("queries") or 0) != 150:
        raise ValueError("query count mismatch")

    runtime = payload.get("runtime") or {}
    if runtime.get("device") != "cuda":
        raise ValueError("LFM result was not produced on CUDA")
    if int(runtime.get("peak_vram_bytes") or 0) <= 0:
        raise ValueError("LFM result has no positive VRAM evidence")
    if runtime.get("gguf_sha256") != EXPECTED_GGUF_SHA256:
        raise ValueError("runtime GGUF identity mismatch")

    metrics = payload.get("metrics") or {}
    if len(metrics.get("per_query") or []) != 150:
        raise ValueError("per-query metric count mismatch")
    if not metrics.get("by_query_type"):
        raise ValueError("query-type metrics are missing")
    _assert_finite(payload)


def finalize_result(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    validate_lfm_result(payload)
    before = host_specific_strings(payload)
    payload["hardware"] = sanitize_host_payload(payload.get("hardware") or {})
    assert_portable_payload(payload)
    atomic_json(path, payload)
    return {
        "status": "PASS",
        "result": str(path),
        "sanitized_string_count": len(before),
        "gate_result": payload["gate_result"],
        "hit_rate_at_50": payload["metrics"]["summary"]["HitRate@50"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    print(finalize_result(args.result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
