"""Finalize completed BitNet result artifacts without repeating inference."""
from __future__ import annotations

import argparse
import copy
from pathlib import Path
from typing import Any, Mapping

from .artifact_portability import (
    assert_portable_payload,
    host_specific_strings,
    sanitize_host_payload,
)
from .reranker_runtime import atomic_json, read_json

PROFILE_IDS = ("bitnet_06b_current", "bitnet_270m_current")


def _validate(payload: Mapping[str, Any], profile_id: str) -> None:
    if payload.get("schema_version") != "1.0":
        raise ValueError("BitNet schema mismatch")
    if payload.get("id") != profile_id:
        raise ValueError("BitNet profile mismatch")
    if payload.get("status") != "COMPLETED":
        raise ValueError("BitNet result is not completed")
    if payload.get("gate_result") not in {"PASS", "FAIL"}:
        raise ValueError("BitNet gate result is invalid")
    dataset = payload.get("dataset") or {}
    if int(dataset.get("documents") or 0) != 600 or int(dataset.get("queries") or 0) != 150:
        raise ValueError("BitNet corpus counts mismatch")
    metrics = payload.get("metrics") or {}
    summary = metrics.get("summary") or {}
    required = ("HitRate@50", "MRR@10", "nDCG@10", "queries_without_relevant")
    if any(summary.get(key) is None for key in required):
        raise ValueError("BitNet summary is incomplete")
    if len(metrics.get("per_query") or []) != 150:
        raise ValueError("BitNet per-query evidence is incomplete")
    if not metrics.get("by_query_type"):
        raise ValueError("BitNet query-type evidence is missing")


def finalize_result(path: Path, profile_id: str) -> dict[str, Any]:
    payload = read_json(path)
    _validate(payload, profile_id)
    protected = {
        key: copy.deepcopy(payload.get(key))
        for key in (
            "schema_version",
            "id",
            "gate",
            "status",
            "gate_result",
            "model",
            "dataset",
            "metrics",
            "completed_at",
        )
    }
    findings = host_specific_strings(payload)
    sanitized = sanitize_host_payload(payload)
    for key, expected in protected.items():
        actual = sanitized.get(key)
        if actual != expected:
            raise RuntimeError(f"BitNet protected field changed: {key}")
    assert_portable_payload(sanitized)
    atomic_json(path, sanitized)
    return {
        "status": "PASS",
        "profile_id": profile_id,
        "sanitized_strings": len(findings),
        "gate_result": sanitized["gate_result"],
        "HitRate@50": sanitized["metrics"]["summary"]["HitRate@50"],
        "MRR@10": sanitized["metrics"]["summary"]["MRR@10"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-id", choices=PROFILE_IDS, required=True)
    parser.add_argument("--result", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    print(finalize_result(args.result, args.profile_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
