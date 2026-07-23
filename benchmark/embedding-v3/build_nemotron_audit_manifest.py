#!/usr/bin/env python3
"""Build the versioned manifest for the Nemotron audit 1.0.5."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT_FILES = (
    ".ai/tasks/NEMOTRON-AUDIT-1.0.5/STATUS.yml",
    "benchmark/embedding-v3/NEMOTRON_AUDIT_1_0_5_REPORT.md",
    "benchmark/embedding-v3/README.md",
    "benchmark/embedding-v3/build_nemotron_audit_manifest.py",
    "benchmark/embedding-v3/config/nemotron_1b_profiles.json",
    "benchmark/embedding-v3/run_nemotron_1b_admission.py",
    "benchmark/embedding-v3/run_nemotron_1b_gguf_preflight.py",
    "benchmark/embedding-v3/run_nemotron_gguf_startups.py",
    "benchmark/embedding-v3/run_nemotron_nvfp4_preflight.py",
    "benchmark/embedding-v3/summarize_nemotron_8b_ggufs.py",
)

EXCLUDED_RESULTS = {"manifest.json", "full_diff.patch"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _entry(repo: Path, relative: Path) -> dict[str, Any]:
    path = repo / relative
    return {
        "path": relative.as_posix(),
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("benchmark/embedding-v3/results/nemotron_audit_1_0_5"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    results = (repo / args.results).resolve()

    relative_files = [Path(item) for item in ROOT_FILES]
    relative_files.extend(
        path.relative_to(repo)
        for path in sorted(results.rglob("*"))
        if path.is_file() and path.name not in EXCLUDED_RESULTS
    )
    missing = [str(path) for path in relative_files if not (repo / path).is_file()]
    if missing:
        raise FileNotFoundError("arquivos do escopo ausentes: " + ", ".join(missing))

    payload = {
        "schema_version": "1.0",
        "state": "COMPLETED",
        "task": "NEMOTRON-AUDIT-1.0.5",
        "git": {
            "branch": _git(repo, "branch", "--show-current"),
            "head": _git(repo, "rev-parse", "HEAD"),
            "origin_branch": "ai/reranker-benchmark-v1.5",
            "local_head_at_inventory": "493ccd2432d550deb6daa84956ea1056bf028c1c",
            "remote_head_at_inventory": "4dab19f",
            "explanation": (
                "A execução foi herdada com artefatos não versionados na branch de "
                "reranker; eles foram preservados e a publicação será feita em branch "
                "dedicada."
            ),
        },
        "models_not_versioned": [
            {
                "path": "embed/Nemotron-3-Embed-8B-Abiray-Q4_K_M/Nemotron-3-Embed-8B-Q4_K_M.gguf",
                "bytes": 4896390039,
                "sha256": "a2aa29c618da6eed10d9474e72e33188c61e5fd700aed2fe9a1d98abdc90c6fc",
            },
            {
                "path": "embed/Nemotron-3-Embed-8B-Aqua00-Q4_K_M/Nemotron-3-Embed-8B-Q4_K_M.gguf",
                "bytes": 4896389984,
                "sha256": "1352d929879c61fccf76ff855c6250c7fdc924479932918febcc6fe384cb70a7",
            },
            {
                "path": "embed/Nemotron-3-Embed-1B-NVFP4/model.safetensors",
                "bytes": 1027789672,
                "sha256": "f2753954c89055eb679a45b7dfea27a3e05c04ecbdb1f4e6c086180fe8c32bc7",
            },
            {
                "path": "embed/Nemotron-3-Embed-1B-Q4_K_M/nemotron-3-embed-1b-q4_k_m.gguf",
                "bytes": 749352096,
                "sha256": "9a74166f51dbc280073748fa199bea49283bd21f7f9280f2dec2b4d975ddfd1d",
            },
        ],
        "runtime_not_versioned": {
            "vllm_environment": "/tmp/vllm-env",
            "vllm": "0.25.0",
            "python": "3.12.13",
            "torch": "2.11.0+cu130",
            "llama_cpp": "9972 (c92e806d1)",
            "gpu": "NVIDIA GeForce RTX 5060 Ti",
            "driver": "610.43.03",
            "vram_mib": 16311,
        },
        "preserved_preexisting_untracked": [
            "benchmark/embedding-v3/run_voyage.py",
            "comandos.md",
            "runtime/vane-native-ops/",
        ],
        "files": [_entry(repo, path) for path in sorted(set(relative_files))],
        "self_hash_note": (
            "manifest.json não lista o próprio hash; full_diff.patch é gerado depois "
            "do manifesto e documenta o diff completo exceto a si próprio."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
