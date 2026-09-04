from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Dict, Iterable, List

from datasets import load_dataset
from huggingface_hub import HfApi

DATASETS = {
    "NanoMSMARCO": "sentence-transformers/NanoMSMARCO-bm25",
    "NanoNQ": "sentence-transformers/NanoNQ-bm25",
    "NanoNFCorpus": "sentence-transformers/NanoNFCorpus-bm25",
    "NanoFiQA2018": "sentence-transformers/NanoFiQA2018-bm25",
    "NanoSciFact": "sentence-transformers/NanoSciFact-bm25",
}


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


def prefix(dataset_name: str, raw_id: str) -> str:
    return f"{dataset_name}:{raw_id}"


def positive_complete_pool(
    ranked_ids: List[str],
    positive_ids: List[str],
    top_k: int,
) -> List[str]:
    pool = list(dict.fromkeys(ranked_ids[:top_k]))
    missing = [pid for pid in positive_ids if pid not in pool]

    # Pure reranker comparison: guarantee every judged positive is available to
    # every reranker, but inject missing positives at the tail so they remain hard.
    for positive in missing:
        if len(pool) >= top_k:
            drop_idx = None
            for idx in range(len(pool) - 1, -1, -1):
                if pool[idx] not in positive_ids:
                    drop_idx = idx
                    break
            if drop_idx is None:
                raise RuntimeError("Cannot inject a positive without dropping another positive")
            pool.pop(drop_idx)
        pool.append(positive)

    if len(pool) > top_k:
        pool = pool[:top_k]
    if len(pool) != len(set(pool)):
        raise AssertionError("Candidate pool contains duplicates")
    if not set(positive_ids).issubset(pool):
        raise AssertionError("Positive-complete candidate policy failed")
    return pool


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Freeze external NanoBEIR BM25 candidate pools for reranker-v2-unbiased."
    )
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "data" / "general-v1")
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.top_k < 20:
        raise SystemExit("--top-k must be >= 20 so Recall@20 remains meaningful")

    out: Path = args.out
    if out.exists():
        if not args.force:
            raise SystemExit(f"{out} already exists; refusing to mutate a frozen pool without --force")
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=False)

    api = HfApi()
    corpus_rows: List[dict] = []
    query_rows: List[dict] = []
    source_revisions: Dict[str, str] = {}

    for dataset_name, repo_id in DATASETS.items():
        info = api.dataset_info(repo_id)
        source_revisions[repo_id] = info.sha

        corpus = load_dataset(repo_id, "corpus", split="train")
        queries = load_dataset(repo_id, "queries", split="train")
        relevance = load_dataset(repo_id, "relevance", split="train")

        raw_corpus = {str(row["_id"]): str(row["text"]) for row in corpus}
        raw_queries = {str(row["_id"]): str(row["text"]) for row in queries}

        for raw_doc_id, text in raw_corpus.items():
            corpus_rows.append(
                {
                    "doc_id": prefix(dataset_name, raw_doc_id),
                    "dataset": dataset_name,
                    "text": text,
                }
            )

        seen_query_ids = set()
        for rel in relevance:
            raw_qid = str(rel["query-id"])
            if raw_qid in seen_query_ids:
                raise RuntimeError(f"Duplicate relevance row for {dataset_name}/{raw_qid}")
            seen_query_ids.add(raw_qid)

            positives_raw = [str(x) for x in rel["positive-corpus-ids"]]
            bm25_raw = [str(x) for x in rel["bm25-ranked-ids"]]
            if raw_qid not in raw_queries:
                raise KeyError(f"Query {raw_qid} missing from {repo_id}/queries")
            unknown_docs = (set(positives_raw) | set(bm25_raw[: args.top_k])) - set(raw_corpus)
            if unknown_docs:
                raise KeyError(f"{repo_id}: unknown document IDs: {sorted(unknown_docs)[:5]}")

            pipeline_raw = list(dict.fromkeys(bm25_raw[: args.top_k]))
            pure_raw = positive_complete_pool(bm25_raw, positives_raw, args.top_k)
            pipeline_recall = len(set(pipeline_raw) & set(positives_raw)) / len(set(positives_raw))

            query_rows.append(
                {
                    "query_id": prefix(dataset_name, raw_qid),
                    "group_id": prefix(dataset_name, raw_qid),
                    "track": "GENERAL",
                    "dataset": dataset_name,
                    "query": raw_queries[raw_qid],
                    "relevant_doc_ids": [prefix(dataset_name, x) for x in positives_raw],
                    "candidate_ids": [prefix(dataset_name, x) for x in pure_raw],
                    "pipeline_candidate_ids": [prefix(dataset_name, x) for x in pipeline_raw],
                    "pipeline_candidate_recall@50": pipeline_recall,
                    "candidate_policy": "bm25_top50_positive_complete_for_pure_reranking",
                }
            )

        if len(seen_query_ids) != len(queries):
            missing = set(raw_queries) - seen_query_ids
            raise RuntimeError(
                f"{repo_id}: relevance/query mismatch: "
                f"queries={len(queries)} relevance={len(seen_query_ids)} missing={sorted(missing)[:5]}"
            )

    corpus_rows.sort(key=lambda x: x["doc_id"])
    query_rows.sort(key=lambda x: x["query_id"])

    corpus_path = out / "corpus.jsonl"
    queries_path = out / "queries.jsonl"
    dump_jsonl(corpus_path, corpus_rows)
    dump_jsonl(queries_path, query_rows)

    freeze_manifest = {
        "benchmark_id": "reranker-v2-unbiased",
        "track": "GENERAL",
        "candidate_top_k": args.top_k,
        "candidate_policy": "published_bm25_top50_then_positive_complete_for_pure_reranker_comparison",
        "datasets": DATASETS,
        "source_revisions": source_revisions,
        "counts": {
            "documents": len(corpus_rows),
            "queries": len(query_rows),
            "datasets": len(DATASETS),
        },
        "files": {
            "corpus.jsonl": sha256_file(corpus_path),
            "queries.jsonl": sha256_file(queries_path),
        },
    }
    manifest_path = out / "freeze_manifest.json"
    manifest_path.write_text(
        json.dumps(freeze_manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        **freeze_manifest,
        "freeze_manifest_sha256": sha256_file(manifest_path),
        "output_dir": str(out),
    }, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
