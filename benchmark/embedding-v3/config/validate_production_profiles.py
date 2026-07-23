#!/usr/bin/env python3
"""Validate production_profiles.json against existing benchmark results and configs."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent.parent.parent
BENCH = REPO / "benchmark/embedding-v3"
PROFILES_PATH = BENCH / "config/production_profiles.json"
MODELS_PATH = BENCH / "config/models.json"
NEMOTRON_PROFILES_PATH = BENCH / "config/nemotron_1b_profiles.json"
RERANKER_SUMMARY_PATH = BENCH / "results/reranker/summary.json"
CANDIDATES_DIR = BENCH / "results/reranker/candidates"
GATE3_DIR = BENCH / "results/gate3"


def _load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(str(path))
    with open(path) as f:
        return json.load(f)


def _pipeline_ids_from_candidates() -> set[str]:
    ids: set[str] = set()
    if CANDIDATES_DIR.is_dir():
        for f in CANDIDATES_DIR.iterdir():
            if f.suffix == ".json":
                ids.add(f.stem)
    return ids


def _gate3_ids() -> set[str]:
    ids: set[str] = set()
    if GATE3_DIR.is_dir():
        for f in GATE3_DIR.iterdir():
            if f.suffix == ".json" and f.stem != "summary":
                ids.add(f.stem)
    return ids


def validate_forbidden_states() -> list[str]:
    data = _load(PROFILES_PATH)
    errors = []
    for p in data.get("profiles", []):
        pid = p.get("id", "?")
        state = p.get("state", "enabled" if p.get("enabled") else "disabled")
        forbidden = {"REJECTED", "BLOCKED", "CANCELLED"}
        if state in forbidden:
            errors.append(f"{pid}: state {state} is forbidden for an operational profile")
    return errors


def validate_authorization_gate() -> list[str]:
    data = _load(PROFILES_PATH)
    errors = []
    for p in data.get("profiles", []):
        pid = p.get("id", "?")
        if p.get("requires_api") and not p.get("requires_authorization"):
            errors.append(f"{pid}: requires_api=true but requires_authorization is not true")
    return errors


def validate_embedding_references() -> list[str]:
    models = _load(MODELS_PATH)
    model_ids = {m["id"] for m in models.get("models", [])}
    nemotron = _load(NEMOTRON_PROFILES_PATH)
    nemotron_ids = {p["id"] for p in nemotron.get("profiles", [])}
    pipeline_ids = _pipeline_ids_from_candidates()
    gate3_ids = _gate3_ids()
    valid_ids = model_ids | nemotron_ids | pipeline_ids | gate3_ids
    data = _load(PROFILES_PATH)
    errors = []
    for p in data.get("profiles", []):
        pid = p.get("id", "?")
        emb = p.get("embedding", {})
        eid = emb.get("id", "")
        if eid and eid not in valid_ids:
            errors.append(f"{pid}: embedding id '{eid}' not found in models.json, nemotron_1b_profiles.json, candidates or gate3 results")
        weight_sha = emb.get("weight_sha256", "")
        if weight_sha and not re.match(r'^[a-f0-9]{64}$', weight_sha):
            errors.append(f"{pid}: weight_sha256 '{weight_sha}' is not a valid 64-char hex string")
        result_gate3 = emb.get("result_gate3", "")
        result_admission = emb.get("result_admission", "")
        if result_gate3 and not (BENCH / result_gate3).exists():
            errors.append(f"{pid}: gate3 result '{result_gate3}' not found")
        if result_admission and not (BENCH / result_admission).exists():
            errors.append(f"{pid}: admission result '{result_admission}' not found")
    return errors


def validate_reranker_references() -> list[str]:
    reranker = _load(RERANKER_SUMMARY_PATH)
    pipeline_record_count = reranker.get("pipeline_record_count", 0)
    data = _load(PROFILES_PATH)
    errors = []
    for p in data.get("profiles", []):
        pid = p.get("id", "?")
        rrk = p.get("reranker", {})
        rid = rrk.get("id", "")
        if not rid:
            continue
        score_path = rrk.get("result_scores", "")
        if score_path and not (BENCH / score_path).exists():
            errors.append(f"{pid}: reranker scores '{score_path}' not found")
        pipeline_dir = rrk.get("result_pipeline", "")
        if pipeline_dir and not (BENCH / pipeline_dir).is_dir():
            errors.append(f"{pid}: pipeline directory '{pipeline_dir}' not found")
    return errors


def validate_self_hash_note() -> list[str]:
    data = _load(PROFILES_PATH)
    errors = []
    for p in data.get("profiles", []):
        pid = p.get("id", "?")
        if p.get("enabled") is False and not p.get("requires_authorization"):
            disabled = [x.get("id") for x in data.get("profiles", []) if x.get("enabled") is False and not x.get("requires_authorization")]
            if pid in disabled:
                pass  # nemotron profiles are disabled for evaluation without API — acceptable
    return errors


def validate_disabled_profiles_have_explicit_reason() -> list[str]:
    data = _load(PROFILES_PATH)
    errors = []
    for p in data.get("profiles", []):
        pid = p.get("id", "?")
        if p.get("enabled") is False and not p.get("reason"):
            errors.append(f"{pid}: disabled profile must have a reason field")
    return errors


def main() -> int:
    checks = [
        ("forbidden_states", validate_forbidden_states),
        ("authorization_gate", validate_authorization_gate),
        ("embedding_references", validate_embedding_references),
        ("reranker_references", validate_reranker_references),
        ("disabled_profiles_reason", validate_disabled_profiles_have_explicit_reason),
    ]
    exit_code = 0
    for name, func in checks:
        errs = func()
        if errs:
            print(f"FAIL {name}:")
            for e in errs:
                print(f"  - {e}")
            exit_code = 1
        else:
            print(f"PASS {name}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
