from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from holo_benchmark.reranker_runtime import (
    CANDIDATE_VARIANTS,
    DEFAULT_RERANK_INSTRUCTION,
)
from reranker_execution import (
    DEFAULT_KEY_PATH,
    generate_candidates,
    preflight,
    run_qwen,
    run_voyage,
)
from reranker_report import build_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark decisório de embeddings e rerankers para busca de cenas"
    )
    parser.add_argument(
        "--phase",
        choices=("preflight", "candidates", "qwen", "voyage", "report", "all"),
        default="preflight",
    )
    parser.add_argument("--variants", default=",".join(CANDIDATE_VARIANTS))
    parser.add_argument("--candidate-top-k", type=int, default=50)
    parser.add_argument("--rerank-top-k", type=int, default=20)
    parser.add_argument("--embedding-batch-size", type=int, default=16)
    parser.add_argument("--reranker-batch-size", type=int, default=4)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--qwen-model-path", default="auto")
    parser.add_argument("--instruction", default=DEFAULT_RERANK_INSTRUCTION)
    parser.add_argument("--api-key-path", type=Path, default=DEFAULT_KEY_PATH)
    parser.add_argument("--allow-voyage-rerank-api", action="store_true")
    parser.add_argument("--voyage-request-interval", type=float, default=1.0)
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.candidate_top_k < 50:
            raise ValueError("candidate-top-k must be at least 50")
        if not 1 <= args.rerank_top_k <= args.candidate_top_k:
            raise ValueError(
                "rerank-top-k must be between 1 and candidate-top-k"
            )
        outputs: list[dict[str, object]] = []
        if args.phase in {"preflight", "all"}:
            outputs.append(preflight(args))
        if args.phase in {"candidates", "all"}:
            outputs.append(generate_candidates(args))
        if args.phase in {"qwen", "all"}:
            outputs.append(run_qwen(args))
        if args.phase == "voyage" or (
            args.phase == "all" and args.allow_voyage_rerank_api
        ):
            outputs.append(run_voyage(args))
        if args.phase in {"report", "all"}:
            outputs.append(build_report(args))
        print(
            json.dumps(
                outputs[-1] if len(outputs) == 1 else outputs,
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        print(
            f"Reranker benchmark blocked: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
