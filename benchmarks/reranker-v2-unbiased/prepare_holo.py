from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from holo_gold import generate_gold_rows

BENCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parents[1]

INCLUDE_ROOT_FILES = ("AGENTS.md", "ARCHITECTURE.md", "README.md")
INCLUDE_DIRS = ("library", "capabilities", "core", "harnesses")
INCLUDE_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".toml"}
TOKEN_RE = re.compile(r"[\w.-]+", re.UNICODE)


def dump_jsonl(path: Path, rows: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_output(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def tokenize(text: str) -> List[str]:
    return [token.casefold() for token in TOKEN_RE.findall(text)]


class BM25:
    def __init__(self, docs: Sequence[str], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.doc_tokens = [tokenize(doc) for doc in docs]
        self.doc_tf = [Counter(tokens) for tokens in self.doc_tokens]
        self.doc_len = [len(tokens) for tokens in self.doc_tokens]
        self.avgdl = sum(self.doc_len) / len(self.doc_len) if self.doc_len else 0.0

        df: Counter[str] = Counter()
        for tf in self.doc_tf:
            df.update(tf.keys())

        n = len(self.doc_tf)
        self.idf = {
            term: math.log(1.0 + (n - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }

    def score(self, query: str, doc_idx: int) -> float:
        if self.avgdl <= 0:
            return 0.0
        score = 0.0
        tf = self.doc_tf[doc_idx]
        dl = self.doc_len[doc_idx]
        for term in tokenize(query):
            freq = tf.get(term, 0)
            if not freq:
                continue
            idf = self.idf.get(term, 0.0)
            denom = freq + self.k1 * (1.0 - self.b + self.b * dl / self.avgdl)
            score += idf * (freq * (self.k1 + 1.0)) / denom
        return score

    def rank(self, query: str) -> List[int]:
        scored = [(self.score(query, idx), idx) for idx in range(len(self.doc_tf))]
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [idx for _, idx in scored]


def positive_complete_pool(
    ranked_ids: Sequence[str],
    positive_ids: Sequence[str],
    top_k: int,
) -> List[str]:
    pool = list(dict.fromkeys(ranked_ids[:top_k]))
    positives = list(dict.fromkeys(positive_ids))
    for positive in positives:
        if positive in pool:
            continue
        if len(pool) >= top_k:
            drop_idx = next(
                (idx for idx in range(len(pool) - 1, -1, -1) if pool[idx] not in positives),
                None,
            )
            if drop_idx is not None:
                pool.pop(drop_idx)
        pool.append(positive)

    if not set(positives).issubset(pool):
        raise AssertionError("Positive-complete policy failed")
    if len(pool) != len(set(pool)):
        raise AssertionError("Candidate pool contains duplicates")
    return pool


def collect_corpus(tooling_root: Path) -> List[dict]:
    paths: List[Path] = []
    for name in INCLUDE_ROOT_FILES:
        path = tooling_root / name
        if path.is_file():
            paths.append(path)

    for dirname in INCLUDE_DIRS:
        root = tooling_root / dirname
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in INCLUDE_SUFFIXES:
                paths.append(path)

    rows: List[dict] = []
    seen = set()
    for path in sorted(set(paths)):
        rel = path.relative_to(tooling_root).as_posix()
        if rel in seen:
            continue
        seen.add(rel)
        text = path.read_text(encoding="utf-8", errors="replace")
        rows.append(
            {
                "doc_id": rel,
                "source_path": rel,
                "text": f"PATH: {rel}\n\n{text}",
                "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )

    if len(rows) < 50:
        raise RuntimeError(
            f"HOLO corpus has only {len(rows)} documents; need >= 50 for a fixed top-50 pool"
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Freeze the Holo-specific held-out candidate pool for reranker-v2-unbiased."
    )
    parser.add_argument(
        "--tooling-root",
        type=Path,
        default=REPO_ROOT.parent / "holo-agent-tooling",
        help="Checkout of Weltall-IA/holo-agent-tooling",
    )
    parser.add_argument("--out", type=Path, default=BENCH_DIR / "data" / "holo-v1")
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow a dirty tooling checkout; file hashes still freeze the exact corpus.",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    tooling_root = args.tooling_root.resolve()
    if not (tooling_root / ".git").exists():
        raise SystemExit(f"{tooling_root} is not a git checkout")
    if args.top_k != 50:
        raise SystemExit("HOLO v1 fixes top_k=50; create a new benchmark version to change it")

    source_head = git_output(tooling_root, "rev-parse", "HEAD")
    source_status = git_output(tooling_root, "status", "--porcelain")
    if source_status and not args.allow_dirty:
        raise SystemExit(
            "holo-agent-tooling checkout is dirty. Commit/stash it or pass --allow-dirty; "
            "the benchmark must not silently change under a fixed version."
        )

    out: Path = args.out
    if out.exists():
        if not args.force:
            raise SystemExit(f"{out} already exists; refusing to mutate frozen data without --force")
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=False)

    corpus_rows = collect_corpus(tooling_root)
    corpus_by_id = {row["doc_id"]: row for row in corpus_rows}
    gold_rows = generate_gold_rows()

    missing_targets = sorted(
        {
            doc_id
            for row in gold_rows
            for doc_id in row["relevant_doc_ids"]
            if doc_id not in corpus_by_id
        }
    )
    if missing_targets:
        raise RuntimeError(f"Gold targets are missing from corpus: {missing_targets}")

    doc_ids = [row["doc_id"] for row in corpus_rows]
    bm25 = BM25([row["text"] for row in corpus_rows])

    query_rows: List[dict] = []
    for gold in gold_rows:
        ranked_ids = [doc_ids[idx] for idx in bm25.rank(str(gold["query"]))]
        pipeline_ids = ranked_ids[: args.top_k]
        relevant = list(gold["relevant_doc_ids"])
        pure_ids = positive_complete_pool(ranked_ids, relevant, args.top_k)
        pipeline_recall = len(set(pipeline_ids) & set(relevant)) / len(set(relevant))

        query_rows.append(
            {
                **gold,
                "track": "HOLO",
                "dataset": "holo-agent-tooling",
                "candidate_ids": pure_ids,
                "pipeline_candidate_ids": pipeline_ids,
                "pipeline_candidate_recall@50": pipeline_recall,
                "candidate_policy": "lexical_bm25_top50_positive_complete_for_pure_reranking",
            }
        )

    corpus_path = out / "corpus.jsonl"
    queries_path = out / "queries.jsonl"
    dump_jsonl(corpus_path, corpus_rows)
    dump_jsonl(queries_path, query_rows)

    languages = Counter(str(row["language"]) for row in query_rows)
    categories = Counter(str(row["category"]) for row in query_rows)
    groups = {str(row["group_id"]) for row in query_rows}
    intents = {str(row["intent_id"]) for row in query_rows}

    manifest = {
        "benchmark_id": "reranker-v2-unbiased",
        "track": "HOLO",
        "candidate_top_k": args.top_k,
        "candidate_policy": "lexical_bm25_top50_then_positive_complete_for_pure_reranker_comparison",
        "retriever": {
            "type": "local_bm25",
            "k1": bm25.k1,
            "b": bm25.b,
            "tokenizer": r"unicode regex [\w.-]+ + casefold",
        },
        "source": {
            "repo": "Weltall-IA/holo-agent-tooling",
            "git_head": source_head,
            "dirty": bool(source_status),
            "included_roots": list(INCLUDE_ROOT_FILES) + list(INCLUDE_DIRS),
        },
        "counts": {
            "documents": len(corpus_rows),
            "queries": len(query_rows),
            "semantic_families": len(groups),
            "intents": len(intents),
            "languages": dict(sorted(languages.items())),
            "categories": dict(sorted(categories.items())),
        },
        "files": {
            "corpus.jsonl": sha256_file(corpus_path),
            "queries.jsonl": sha256_file(queries_path),
        },
    }
    manifest_path = out / "freeze_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                **manifest,
                "freeze_manifest_sha256": sha256_file(manifest_path),
                "output_dir": str(out),
            },
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
