from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import random
import time
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

import numpy as np
import psutil

from metrics import aggregate, bootstrap_ci, per_query_metrics

BENCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parents[1]
SEED = 20260904

MODEL_SPECS = {
    "nemotron_1b_v2": {
        "hf_id": "nvidia/llama-nemotron-rerank-1b-v2",
        "adapter": "nemotron_native",
        "local_candidates": [REPO_ROOT / "rerank" / "llama_nemotron_rerank_1b_v2"],
    },
    "jina_v35": {
        "hf_id": "jinaai/jina-reranker-v3.5",
        "adapter": "jina_listwise",
        # rerank/jina_reranker_v3_5 contains legacy reports, not model weights.
        "local_candidates": [],
    },
    "qwen3_06b": {
        "hf_id": "Qwen/Qwen3-Reranker-0.6B",
        "adapter": "cross_encoder",
        "local_candidates": [REPO_ROOT / "rerank" / "qwen3_reranker_06"],
    },
    "ettin_400m": {
        "hf_id": "cross-encoder/ettin-reranker-400m-v1",
        "adapter": "cross_encoder",
        "local_candidates": [REPO_ROOT / "rerank" / "ettin_reranker_400m_v1"],
    },
}


def load_jsonl(path: Path) -> List[dict]:
    rows: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON") from exc
    return rows


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_frozen_data(data_dir: Path) -> dict:
    manifest_path = data_dir / "freeze_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Missing {manifest_path}; candidate pools must be frozen before a run"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for filename, expected in manifest.get("files", {}).items():
        path = data_dir / filename
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(
                f"Frozen-data hash mismatch for {path}: expected {expected}, got {actual}. "
                "Refusing to benchmark mutable candidate pools."
            )
    return manifest


def validate_rows(corpus_rows: Sequence[dict], query_rows: Sequence[dict]) -> None:
    doc_ids = [str(row["doc_id"]) for row in corpus_rows]
    if len(doc_ids) != len(set(doc_ids)):
        raise ValueError("Duplicate doc_id in corpus")
    corpus_set = set(doc_ids)

    qids = [str(row["query_id"]) for row in query_rows]
    if len(qids) != len(set(qids)):
        raise ValueError("Duplicate query_id")

    for row in query_rows:
        qid = str(row["query_id"])
        relevant = [str(x) for x in row.get("relevant_doc_ids", [])]
        candidates = [str(x) for x in row.get("candidate_ids", [])]
        if not relevant:
            raise ValueError(f"{qid}: no relevant_doc_ids")
        if len(candidates) < 20:
            raise ValueError(f"{qid}: fewer than 20 candidates")
        if len(candidates) != len(set(candidates)):
            raise ValueError(f"{qid}: duplicate candidates")
        unknown = (set(relevant) | set(candidates)) - corpus_set
        if unknown:
            raise ValueError(f"{qid}: unknown doc IDs {sorted(unknown)[:5]}")
        if not set(relevant).issubset(candidates):
            raise ValueError(f"{qid}: pure-reranker candidate pool is not positive-complete")


def parse_overrides(values: Sequence[str]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"--model-path requires MODEL_KEY=PATH_OR_HF_ID, got {item!r}")
        key, value = item.split("=", 1)
        if key not in MODEL_SPECS:
            raise ValueError(f"Unknown model key in override: {key}")
        result[key] = value
    return result


def _looks_like_model_dir(path: Path) -> bool:
    return path.is_dir() and (path / "config.json").is_file()


def resolve_source(model_key: str, overrides: Mapping[str, str]) -> str:
    if model_key in overrides:
        return overrides[model_key]
    for candidate in MODEL_SPECS[model_key]["local_candidates"]:
        if _looks_like_model_dir(candidate):
            return str(candidate)
    return str(MODEL_SPECS[model_key]["hf_id"])


class BaseAdapter:
    def __init__(self, source: str, device: str) -> None:
        self.source = source
        self.device = device

    def rank(self, query: str, documents: Sequence[str]) -> List[int]:
        raise NotImplementedError

    def metadata(self) -> dict:
        return {"source": self.source, "adapter": type(self).__name__}

    def close(self) -> None:
        pass


class CrossEncoderAdapter(BaseAdapter):
    def __init__(self, source: str, device: str) -> None:
        super().__init__(source, device)
        from sentence_transformers import CrossEncoder

        kwargs = {"device": device, "trust_remote_code": True}
        try:
            self.model = CrossEncoder(source, model_kwargs={"dtype": "auto"}, **kwargs)
        except TypeError:
            self.model = CrossEncoder(source, **kwargs)

    def rank(self, query: str, documents: Sequence[str]) -> List[int]:
        raw_scores = self.model.predict(
            [(query, doc) for doc in documents],
            show_progress_bar=False,
        )
        values = np.asarray(raw_scores, dtype=np.float64).reshape(-1)
        if len(values) != len(documents):
            raise RuntimeError(
                f"CrossEncoder returned {len(values)} scores for {len(documents)} documents"
            )
        return sorted(range(len(values)), key=lambda i: (-float(values[i]), i))

    def metadata(self) -> dict:
        meta = super().metadata()
        try:
            config = self.model.model.config
            meta["parameter_dtype"] = str(next(self.model.model.parameters()).dtype)
            meta["resolved_revision"] = getattr(config, "_commit_hash", None)
        except Exception:
            meta["parameter_dtype"] = "unknown"
            meta["resolved_revision"] = None
        meta["max_length"] = getattr(self.model, "max_length", None)
        return meta

    def close(self) -> None:
        del self.model


class JinaListwiseAdapter(BaseAdapter):
    def __init__(self, source: str, device: str) -> None:
        super().__init__(source, device)
        import torch
        from transformers import AutoModel

        self.torch = torch
        self.model = (
            AutoModel.from_pretrained(
                source,
                dtype="auto",
                trust_remote_code=True,
            )
            .eval()
            .to(device)
        )

    def rank(self, query: str, documents: Sequence[str]) -> List[int]:
        with self.torch.inference_mode():
            results = self.model.rerank(query, list(documents), top_n=None)
        indices = [int(item["index"]) for item in results]
        if sorted(indices) != list(range(len(documents))):
            raise RuntimeError("Jina listwise output did not return a full permutation")
        return indices

    def metadata(self) -> dict:
        meta = super().metadata()
        meta["inference_api"] = "model.rerank(query, documents, top_n=None)"
        try:
            meta["parameter_dtype"] = str(next(self.model.parameters()).dtype)
            meta["resolved_revision"] = getattr(self.model.config, "_commit_hash", None)
        except Exception:
            meta["parameter_dtype"] = "unknown"
            meta["resolved_revision"] = None
        return meta

    def close(self) -> None:
        del self.model


class NemotronAdapter(BaseAdapter):
    def __init__(self, source: str, device: str, batch_size: int = 16) -> None:
        super().__init__(source, device)
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.batch_size = batch_size
        self.tokenizer = AutoTokenizer.from_pretrained(
            source,
            trust_remote_code=True,
            padding_side="left",
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        self.model = (
            AutoModelForSequenceClassification.from_pretrained(
                source,
                trust_remote_code=True,
                dtype="auto",
            )
            .eval()
            .to(device)
        )
        if self.model.config.pad_token_id is None:
            self.model.config.pad_token_id = self.tokenizer.eos_token_id

        tokenizer_max = getattr(self.tokenizer, "model_max_length", 8192)
        if tokenizer_max is None or tokenizer_max > 1_000_000:
            tokenizer_max = 8192
        self.max_length = min(int(tokenizer_max), 8192)

    @staticmethod
    def prompt(query: str, passage: str) -> str:
        return f"question:{query} \n \n passage:{passage}"

    def rank(self, query: str, documents: Sequence[str]) -> List[int]:
        import torch

        scores: List[float] = []
        with torch.inference_mode():
            for start in range(0, len(documents), self.batch_size):
                batch = documents[start : start + self.batch_size]
                texts = [self.prompt(query, doc) for doc in batch]
                enc = self.tokenizer(
                    texts,
                    padding=True,
                    truncation=True,
                    max_length=self.max_length,
                    return_tensors="pt",
                ).to(self.device)
                values = (
                    self.model(**enc)
                    .logits.squeeze(-1)
                    .detach()
                    .float()
                    .cpu()
                    .reshape(-1)
                    .tolist()
                )
                scores.extend(float(x) for x in values)

        if len(scores) != len(documents):
            raise RuntimeError(
                f"Nemotron returned {len(scores)} scores for {len(documents)} documents"
            )
        return sorted(range(len(scores)), key=lambda i: (-scores[i], i))

    def metadata(self) -> dict:
        meta = super().metadata()
        meta.update(
            {
                "parameter_dtype": str(next(self.model.parameters()).dtype),
                "resolved_revision": getattr(self.model.config, "_commit_hash", None),
                "max_length": self.max_length,
                "batch_size": self.batch_size,
                "prompt_template": "question:{q} \\n \\n passage:{p}",
            }
        )
        return meta

    def close(self) -> None:
        del self.model
        del self.tokenizer


def build_adapter(
    model_key: str,
    source: str,
    device: str,
    nemotron_batch_size: int,
) -> BaseAdapter:
    adapter = str(MODEL_SPECS[model_key]["adapter"])
    if adapter == "jina_listwise":
        return JinaListwiseAdapter(source, device)
    if adapter == "nemotron_native":
        return NemotronAdapter(source, device, batch_size=nemotron_batch_size)
    if adapter == "cross_encoder":
        return CrossEncoderAdapter(source, device)
    raise KeyError(adapter)


def runtime_metadata() -> dict:
    import sentence_transformers
    import torch
    import transformers

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "sentence_transformers": sentence_transformers.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "seed": SEED,
    }


def baseline_metrics(query_rows: Sequence[dict]) -> dict:
    pure: Dict[str, dict] = {}
    pipeline: Dict[str, dict] = {}
    for row in query_rows:
        qid = str(row["query_id"])
        relevant = row["relevant_doc_ids"]
        pure[qid] = per_query_metrics(row["candidate_ids"], relevant)
        pipeline_ids = row.get("pipeline_candidate_ids", row["candidate_ids"])
        pipeline[qid] = per_query_metrics(pipeline_ids, relevant)
    return {
        "pure_candidate_order": {"aggregate": aggregate(pure), "per_query": pure},
        "pipeline_first_stage": {"aggregate": aggregate(pipeline), "per_query": pipeline},
    }


def _nearest_percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * q)))
    return ordered[idx]


def run_model(
    model_key: str,
    adapter: BaseAdapter,
    corpus: Mapping[str, str],
    query_rows: Sequence[dict],
    *,
    warmup: bool,
) -> dict:
    import torch

    if warmup and query_rows:
        row = query_rows[0]
        docs = [corpus[doc_id] for doc_id in row["candidate_ids"]]
        adapter.rank(str(row["query"]), docs)
        if torch.cuda.is_available():
            torch.cuda.synchronize()

    process = psutil.Process(os.getpid())
    rss_peak = process.memory_info().rss
    latencies: List[float] = []
    per_query: Dict[str, dict] = {}
    rankings: Dict[str, List[str]] = {}

    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()

    started = time.perf_counter()
    for row in query_rows:
        qid = str(row["query_id"])
        candidate_ids = [str(x) for x in row["candidate_ids"]]
        docs = [corpus[doc_id] for doc_id in candidate_ids]

        if torch.cuda.is_available():
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        order = adapter.rank(str(row["query"]), docs)
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        latencies.append(time.perf_counter() - t0)

        if sorted(order) != list(range(len(candidate_ids))):
            raise RuntimeError(f"{model_key}/{qid}: adapter returned an invalid permutation")

        ranked_ids = [candidate_ids[i] for i in order]
        rankings[qid] = ranked_ids
        per_query[qid] = per_query_metrics(ranked_ids, row["relevant_doc_ids"])
        rss_peak = max(rss_peak, process.memory_info().rss)

    total_time = time.perf_counter() - started

    if torch.cuda.is_available():
        peak_alloc = torch.cuda.max_memory_allocated() / (1024**2)
        peak_reserved = torch.cuda.max_memory_reserved() / (1024**2)
    else:
        peak_alloc = 0.0
        peak_reserved = 0.0

    group_ids = {
        str(row["query_id"]): str(row.get("group_id", row["query_id"]))
        for row in query_rows
    }
    ci = {}
    for metric in ("ndcg@10", "mrr@10"):
        low, high = bootstrap_ci(per_query, metric, group_ids=group_ids)
        ci[metric] = {"low": low, "high": high}

    by_dataset: Dict[str, dict] = {}
    datasets = sorted({str(row.get("dataset", "HOLO")) for row in query_rows})
    for dataset in datasets:
        ids = [
            str(row["query_id"])
            for row in query_rows
            if str(row.get("dataset", "HOLO")) == dataset
        ]
        subset = {qid: per_query[qid] for qid in ids}
        subset_groups = {qid: group_ids[qid] for qid in ids}
        subset_ci = {}
        for metric in ("ndcg@10", "mrr@10"):
            low, high = bootstrap_ci(subset, metric, group_ids=subset_groups)
            subset_ci[metric] = {"low": low, "high": high}
        by_dataset[dataset] = {
            "query_count": len(ids),
            "aggregate": aggregate(subset),
            "ci95": subset_ci,
        }

    return {
        "model_key": model_key,
        "model": MODEL_SPECS[model_key],
        "adapter_metadata": adapter.metadata(),
        "query_count": len(query_rows),
        "aggregate": aggregate(per_query),
        "ci95": ci,
        "by_dataset": by_dataset,
        "efficiency": {
            "peak_gpu_allocated_mib": peak_alloc,
            "peak_gpu_reserved_mib": peak_reserved,
            "peak_process_rss_mib": rss_peak / (1024**2),
            "latency_p50_s": _nearest_percentile(latencies, 0.50),
            "latency_p95_s": _nearest_percentile(latencies, 0.95),
            "queries_per_second": len(query_rows) / total_time if total_time else 0.0,
            "total_time_s": total_time,
        },
        "per_query": per_query,
        "rankings": rankings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the frozen reranker-v2-unbiased benchmark."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=BENCH_DIR / "data" / "general-v1",
        help="Frozen data directory with corpus.jsonl, queries.jsonl and freeze_manifest.json",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=list(MODEL_SPECS),
        choices=list(MODEL_SPECS),
    )
    parser.add_argument(
        "--model-path",
        action="append",
        default=[],
        metavar="MODEL_KEY=PATH_OR_HF_ID",
        help="Override a model source without changing the benchmark manifest",
    )
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--nemotron-batch-size", type=int, default=16)
    parser.add_argument("--no-warmup", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    random.seed(SEED)
    try:
        import torch

        torch.manual_seed(SEED)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(SEED)
    except Exception:
        pass

    manifest = verify_frozen_data(args.data_dir)
    corpus_rows = load_jsonl(args.data_dir / "corpus.jsonl")
    query_rows = load_jsonl(args.data_dir / "queries.jsonl")
    validate_rows(corpus_rows, query_rows)

    corpus = {str(row["doc_id"]): str(row["text"]) for row in corpus_rows}
    overrides = parse_overrides(args.model_path)

    result_dir = BENCH_DIR / "results" / args.data_dir.name
    result_dir.mkdir(parents=True, exist_ok=True)

    base_path = result_dir / "baseline.json"
    baseline_payload = {
        "benchmark_id": "reranker-v2-unbiased",
        "track": manifest.get("track"),
        "data_dir": str(args.data_dir),
        "candidate_files": manifest.get("files"),
        "baseline": baseline_metrics(query_rows),
    }
    if base_path.exists() and not args.force:
        existing = json.loads(base_path.read_text(encoding="utf-8"))
        if existing.get("candidate_files") != baseline_payload.get("candidate_files"):
            raise RuntimeError("Existing baseline belongs to different candidate files")
    else:
        base_path.write_text(
            json.dumps(baseline_payload, indent=2, ensure_ascii=False, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )

    runtime = runtime_metadata()

    for model_key in args.models:
        out_path = result_dir / f"{model_key}.json"
        if out_path.exists() and not args.force:
            print(f"SKIP {model_key}: {out_path} already exists (use --force to rerun)")
            continue

        source = resolve_source(model_key, overrides)
        print(f"RUN {model_key} source={source}")
        adapter = build_adapter(model_key, source, args.device, args.nemotron_batch_size)
        try:
            payload = run_model(
                model_key,
                adapter,
                corpus,
                query_rows,
                warmup=not args.no_warmup,
            )
            payload.update(
                {
                    "benchmark_id": "reranker-v2-unbiased",
                    "track": manifest.get("track"),
                    "data_dir": str(args.data_dir),
                    "candidate_files": manifest.get("files"),
                    "runtime": runtime,
                    "measured": True,
                    "projected": False,
                }
            )
            out_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print(
                f"DONE {model_key}: "
                f"NDCG@10={payload['aggregate']['ndcg@10']:.4f} "
                f"MRR@10={payload['aggregate']['mrr@10']:.4f} "
                f"p50={payload['efficiency']['latency_p50_s']:.3f}s"
            )
        finally:
            adapter.close()
            del adapter
            gc.collect()
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass


if __name__ == "__main__":
    main()
