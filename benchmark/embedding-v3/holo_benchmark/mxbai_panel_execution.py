"""Execution wrapper requiring a locally proven Mixedbread repository revision."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from . import mxbai_panel_benchmark as benchmark
from .reranker_runtime import DEFAULT_RERANK_INSTRUCTION

_REVISION = re.compile(r"^[0-9a-f]{40}$")


def validate_revision(value: str) -> str:
    revision = str(value).strip().lower()
    if not _REVISION.fullmatch(revision):
        raise ValueError("Mixedbread revision must be an immutable 40-character SHA")
    return revision


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-id", choices=benchmark.PANEL_PROFILES, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument(
        "--canonical",
        type=Path,
        default=benchmark.PROJECT_ROOT / "ALL_BENCHMARK_RESULTS.json",
    )
    parser.add_argument("--score-output", type=Path, required=True)
    parser.add_argument("--pipeline-output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--instruction", default=DEFAULT_RERANK_INSTRUCTION)
    return parser


def execute(args: argparse.Namespace):
    benchmark.MODEL_REVISION = validate_revision(args.model_revision)
    return benchmark.benchmark_profile(args)


def main() -> int:
    print(execute(build_parser().parse_args()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
