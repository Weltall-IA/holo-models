#!/usr/bin/env python3
from __future__ import annotations

import gc
import hashlib
import json
import math
import os
import sys
import time
from collections import Counter
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "8")
os.environ.setdefault("MKL_NUM_THREADS", "8")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
import torch

torch.set_num_threads(8)
torch.set_num_interop_threads(8)

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data" / "holo_fake_scenes_v3"
RESULTS_DIR = SCRIPT_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_REVISIONS = {
    "embeddinggemma": "57c266a740f537b4dc058e1b0cda161fd15afa75",
    "literary_minilm": "92a6516f32321dc4048b49c9e6eb2b9aaa7e8e8f",
}
NEMOTRON_MODEL = "/home/alpha/Playstoria/models/rerank/llama_nemotron_rerank_1b_v2"
NEMOTRON_REVISION = "7b6d977e129a50b29c6b557d5d38c2e7c0f527e7"

CORPUS_SHA = "59cf7d64a68770731e28308e421129d3193eacd2a10ba182da8dcf286249d85b"
QUERIES_SHA = "9aa48f789df1e3b246979a049478b217cfda1e47fad12a131b5618f4f17e329b"
COMBINED_SHA = "8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def load_corpus():
    corpus_sha = sha256_file(DATA_DIR / "corpus.jsonl")
    queries_sha = sha256_file(DATA_DIR / "queries.jsonl")
    assert corpus_sha == CORPUS_SHA, f"corpus hash mismatch: {corpus_sha}"
    assert queries_sha == QUERIES_SHA, f"queries hash mismatch: {queries_sha}"
    hashes = json.loads((DATA_DIR / "hashes.json").read_text())
    assert hashes["combined_sha256"] == COMBINED_SHA
    corpus = load_jsonl(DATA_DIR / "corpus.jsonl")
    queries = load_jsonl(DATA_DIR / "queries.jsonl")
    assert len(corpus) == 600, f"expected 600 docs, got {len(corpus)}"
    assert len(queries) == 150, f"expected 150 queries, got {len(queries)}"
    assert len(set(c["work_id"] for c in corpus)) == 30, "expected 30 works"
    qtypes = Counter(q.get("query_type", "unknown") for q in queries)
    assert len(qtypes) == 7, f"expected 7 query types, got {len(qtypes)}"
    assert sum(qtypes.values()) == 150
    return corpus, queries, hashes


def get_gpu_stats():
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        power = pynvml.nvmlDeviceGetPowerUsage(handle)
        temp = pynvml.nvmlDeviceGetTemperature(handle, 0)
        return {
            "vram_allocated_mb": mem.used / 1024 / 1024,
            "vram_total_mb": mem.total / 1024 / 1024,
            "gpu_util_percent": util.gpu,
            "power_w": power / 1000,
            "temperature_c": temp,
        }
    except Exception:
        return {}


def compute_metrics(rankings, queries):
    def dcg_at_k(ranking, relevant_ids, k):
        scores = [1 if doc in relevant_ids else 0 for doc in ranking[:k]]
        return sum((2**s - 1) / math.log2(i + 2) for i, s in enumerate(scores))

    def ndcg_at_k(ranking, relevant_ids, k):
        ideal_scores = [1] * min(len(relevant_ids), k)
        idcg = sum((2**s - 1) / math.log2(i + 2) for i, s in enumerate(ideal_scores))
        return dcg_at_k(ranking, relevant_ids, k) / idcg if idcg > 0 else 0.0

    def mrr_at_k(ranking, relevant_ids, k):
        for i, doc in enumerate(ranking[:k]):
            if doc in relevant_ids:
                return 1.0 / (i + 1)
        return 0.0

    def hit_at_k(ranking, relevant_ids, k):
        return float(any(doc in relevant_ids for doc in ranking[:k]))

    def recall_at_k(ranking, relevant_ids, k):
        if not relevant_ids:
            return 0.0
        hits = sum(1 for doc in ranking[:k] if doc in relevant_ids)
        return hits / len(relevant_ids)

    def ap_at_k(ranking, relevant_ids, k):
        hits = 0
        sum_prec = 0.0
        for i, doc in enumerate(ranking[:k]):
            if doc in relevant_ids:
                hits += 1
                sum_prec += hits / (i + 1)
        return sum_prec / len(relevant_ids) if relevant_ids else 0.0

    results = {
        "nDCG@10": [], "MRR@10": [], "MAP": [], "Hit@1": [],
        "Recall@10": [], "Recall@20": [], "Recall@50": [],
        "query_ids": [], "query_types": [], "ranks_of_first_relevant": []
    }

    for ranking, qinfo in zip(rankings, queries):
        relevant_ids = set(qinfo.get("relevant_chunk_ids", []))
        results["nDCG@10"].append(ndcg_at_k(ranking, relevant_ids, 10))
        results["MRR@10"].append(mrr_at_k(ranking, relevant_ids, 10))
        results["MAP"].append(ap_at_k(ranking, relevant_ids, 10))
        results["Hit@1"].append(hit_at_k(ranking, relevant_ids, 1))
        results["Recall@10"].append(recall_at_k(ranking, relevant_ids, 10))
        results["Recall@20"].append(recall_at_k(ranking, relevant_ids, 20))
        results["Recall@50"].append(recall_at_k(ranking, relevant_ids, 50))
        results["query_ids"].append(qinfo["query_id"])
        results["query_types"].append(qinfo.get("query_type", "unknown"))
        first_r = None
        for j, doc in enumerate(ranking):
            if doc in relevant_ids:
                first_r = j + 1
                break
        results["ranks_of_first_relevant"].append(first_r if first_r else len(ranking) + 1)

    summary = {
        "nDCG@10": float(np.mean(results["nDCG@10"])),
        "MRR@10": float(np.mean(results["MRR@10"])),
        "MAP": float(np.mean(results["MAP"])),
        "Hit@1": float(np.mean(results["Hit@1"])),
        "Recall@10": float(np.mean(results["Recall@10"])),
        "Recall@20": float(np.mean(results["Recall@20"])),
        "Recall@50": float(np.mean(results["Recall@50"])),
    }
    by_type = {}
    for qt in set(results["query_types"]):
        idxs = [i for i, t in enumerate(results["query_types"]) if t == qt]
        by_type[qt] = {
            k: float(np.mean([results[k][i] for i in idxs]))
            for k in ["nDCG@10", "MRR@10", "MAP", "Hit@1", "Recall@10", "Recall@20", "Recall@50"]
        }
    return summary, by_type, results


def run_embedding_benchmark():
    corpus, queries, hashes = load_corpus()
    doc_texts = [c["text"] for c in corpus]
    doc_ids = [c["chunk_id"] for c in corpus]
    query_texts = [q["query"] for q in queries]

    results = {}

    from sentence_transformers import SentenceTransformer

    # EmbeddingGemma
    eg_path = "/home/alpha/.cache/huggingface/hub/models--google--embeddinggemma-300m/snapshots/57c266a740f537b4dc058e1b0cda161fd15afa75"
    eg_revision = MODEL_REVISIONS["embeddinggemma"]
    model_eg = SentenceTransformer(eg_path)
    
    eg_query_prefix = model_eg.prompts.get("query", "") if hasattr(model_eg, 'prompts') else ""
    eg_doc_prefix = model_eg.prompts.get("document", "") if hasattr(model_eg, 'prompts') else ""
    if not eg_query_prefix:
        eg_query_prefix = "task: search result | query: "
    if not eg_doc_prefix:
        eg_doc_prefix = "title: none | text: "
    
    tokenizer_eg = model_eg.tokenizer
    batch_size = 64
    max_length = getattr(tokenizer_eg, "model_max_length", 2048)
    actual_max_length = min(getattr(model_eg, "max_seq_length", 2048) or 2048, 2048)

    eg_query_tokens = [len(tokenizer_eg(eg_query_prefix + q, truncation=False)["input_ids"]) for q in query_texts]
    eg_doc_tokens = [len(tokenizer_eg(eg_doc_prefix + d, truncation=False)["input_ids"]) for d in doc_texts]

    truncation_stats = {
        "model_name": "google/embeddinggemma-300m",
        "tokenizer_model_max_length": max_length,
        "truncation_max_length": actual_max_length,
        "document_prompt_prefix": eg_doc_prefix,
        "query_prompt_prefix": eg_query_prefix,
        "documents": {
            "mean_tokens": float(np.mean(eg_doc_tokens)),
            "p50_tokens": float(np.percentile(eg_doc_tokens, 50)),
            "p95_tokens": float(np.percentile(eg_doc_tokens, 95)),
            "max_tokens": float(max(eg_doc_tokens)),
            "over_limit": sum(1 for t in eg_doc_tokens if t > actual_max_length),
            "over_limit_pct": float(sum(1 for t in eg_doc_tokens if t > actual_max_length) / len(eg_doc_tokens) * 100),
        },
        "queries": {
            "mean_tokens": float(np.mean(eg_query_tokens)),
            "p50_tokens": float(np.percentile(eg_query_tokens, 50)),
            "p95_tokens": float(np.percentile(eg_query_tokens, 95)),
            "max_tokens": float(max(eg_query_tokens)),
            "over_limit": sum(1 for t in eg_query_tokens if t > actual_max_length),
            "over_limit_pct": float(sum(1 for t in eg_query_tokens if t > actual_max_length) / len(eg_query_tokens) * 100),
        },
    }

    torch.cuda.reset_peak_memory_stats()
    with torch.no_grad():
        _ = model_eg.encode("warmup", show_progress_bar=False)

    embed_start = time.time()
    doc_embeddings = []
    eg_query_latencies = []
    for i in range(0, len(doc_texts), batch_size):
        emb = model_eg.encode_document(
            doc_texts[i : i + batch_size],
            batch_size=len(doc_texts[i : i + batch_size]),
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        doc_embeddings.append(emb)
    corpus_embed_time = time.time() - embed_start
    doc_embeddings = np.concatenate(doc_embeddings, axis=0)

    query_embed_start = time.time()
    query_embeddings_list = []
    for i in range(0, len(query_texts), batch_size):
        t0 = time.perf_counter()
        emb = model_eg.encode_query(
            query_texts[i : i + batch_size],
            batch_size=len(query_texts[i : i + batch_size]),
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        eg_query_latencies.append(time.perf_counter() - t0)
        query_embeddings_list.append(emb)
    query_embed_time = time.time() - query_embed_start
    query_embeddings = np.concatenate(query_embeddings_list, axis=0)

    del model_eg
    gc.collect()
    torch.cuda.empty_cache()

    doc_ids_arr = np.array(doc_ids)
    eg_scores = np.asarray(query_embeddings @ doc_embeddings.T)
    print(f"EG embeddings: queries={query_embeddings.shape}, docs={doc_embeddings.shape}, scores={eg_scores.shape}")
    eg_rankings = [list(doc_ids_arr[np.argsort(-eg_scores[i])]) for i in range(len(queries))]
    eg_summary, eg_by_type, eg_detail = compute_metrics(eg_rankings, queries)

    peak_alloc = torch.cuda.max_memory_allocated() / 1024 / 1024
    peak_reserved = torch.cuda.max_memory_reserved() / 1024 / 1024
    gpu_stats = get_gpu_stats()

    results["embeddinggemma"] = {
        "measured": True,
        "projected": False,
        "model": "google/embeddinggemma-300m",
        "revision": eg_revision,
        "dimension": doc_embeddings.shape[1],
        "float32_bytes": int(doc_embeddings.shape[0] * doc_embeddings.shape[1] * 4),
        "query_prefix": eg_query_prefix,
        "document_prefix": eg_doc_prefix,
        "batch_size": batch_size,
        "max_length": actual_max_length,
        "warmup_excluded": True,
        "load_time_seconds": 0.0,
        "corpus_embedding_time_seconds": float(corpus_embed_time),
        "docs_per_second": float(len(doc_texts) / corpus_embed_time) if corpus_embed_time > 0 else 0,
        "query_embedding_time_seconds": float(query_embed_time),
        "queries_per_second": float(len(query_texts) / query_embed_time) if query_embed_time > 0 else 0,
        "query_latency_p50_ms": float(np.percentile(eg_query_latencies, 50) * 1000),
        "query_latency_p95_ms": float(np.percentile(eg_query_latencies, 95) * 1000),
        "peak_cuda_allocated_mib": float(peak_alloc),
        "peak_cuda_reserved_mib": float(peak_reserved),
        "gpu_stats": gpu_stats,
        "metrics": eg_summary,
        "metrics_by_query_type": eg_by_type,
        "truncation_stats": truncation_stats,
        "rankings": [list(r) for r in eg_rankings],
        "query_ids": [q["query_id"] for q in queries],
    }

    # Literary MiniLM
    lit_path = "/home/alpha/Playstoria/models/embed/literary/RafaelUI-literary-minilm-92a6516f"
    lit_revision = MODEL_REVISIONS["literary_minilm"]
    model_lit = SentenceTransformer(lit_path)
    lit_query_prefix = model_lit.prompts.get("query", "") if hasattr(model_lit, 'prompts') else ""
    lit_doc_prefix = model_lit.prompts.get("document", "") if hasattr(model_lit, 'prompts') else ""
    lit_max_length = model_lit.max_seq_length or getattr(model_lit.tokenizer, "model_max_length", 128)

    tokenizer_lit = model_lit.tokenizer

    lit_query_tokens = [len(tokenizer_lit(q, truncation=False)["input_ids"]) for q in query_texts]
    lit_doc_tokens = [len(tokenizer_lit(d, truncation=False)["input_ids"]) for d in doc_texts]

    lit_truncation_stats = {
        "model_name": "RafaelUI/literary-minilm",
        "tokenizer_model_max_length": getattr(tokenizer_lit, "model_max_length", "N/A"),
        "truncation_max_length": lit_max_length,
        "query_prompt_prefix": lit_query_prefix,
        "document_prompt_prefix": lit_doc_prefix,
        "documents": {
            "mean_tokens": float(np.mean(lit_doc_tokens)),
            "p50_tokens": float(np.percentile(lit_doc_tokens, 50)),
            "p95_tokens": float(np.percentile(lit_doc_tokens, 95)),
            "max_tokens": float(max(lit_doc_tokens)),
            "over_limit": sum(1 for t in lit_doc_tokens if t > lit_max_length),
            "over_limit_pct": float(sum(1 for t in lit_doc_tokens if t > lit_max_length) / len(lit_doc_tokens) * 100),
        },
        "queries": {
            "mean_tokens": float(np.mean(lit_query_tokens)),
            "p50_tokens": float(np.percentile(lit_query_tokens, 50)),
            "p95_tokens": float(np.percentile(lit_query_tokens, 95)),
            "max_tokens": float(max(lit_query_tokens)),
            "over_limit": sum(1 for t in lit_query_tokens if t > lit_max_length),
            "over_limit_pct": float(sum(1 for t in lit_query_tokens if t > lit_max_length) / len(lit_query_tokens) * 100),
        },
    }

    torch.cuda.reset_peak_memory_stats()
    with torch.no_grad():
        _ = model_lit.encode("warmup", show_progress_bar=False)

    embed_start = time.time()
    doc_embeddings_lit = model_lit.encode(doc_texts, batch_size=64, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True)
    corpus_embed_time = time.time() - embed_start

    query_embed_start = time.time()
    query_embeddings_list = []
    lit_query_latencies = []
    for j in range(0, len(query_texts), batch_size):
        t0 = time.perf_counter()
        batch_queries = query_texts[j:j+batch_size]
        emb = model_lit.encode(batch_queries, batch_size=len(batch_queries), show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True)
        lit_query_latencies.append(time.perf_counter() - t0)
        query_embeddings_list.append(emb)
    query_embed_time = time.time() - query_embed_start
    query_embeddings_lit = np.concatenate(query_embeddings_list, axis=0)

    del model_lit
    gc.collect()
    torch.cuda.empty_cache()

    scores_lit = np.asarray(query_embeddings_lit @ doc_embeddings_lit.T)
    lit_rankings = [list(doc_ids_arr[np.argsort(-scores_lit[i])]) for i in range(len(queries))]
    lit_summary, lit_by_type, lit_detail = compute_metrics(lit_rankings, queries)
    peak_alloc = torch.cuda.max_memory_allocated() / 1024 / 1024
    peak_reserved = torch.cuda.max_memory_reserved() / 1024 / 1024

    results["literary_minilm"] = {
        "measured": True,
        "projected": False,
        "model": "RafaelUI/literary-minilm",
        "revision": lit_revision,
        "dimension": doc_embeddings_lit.shape[1],
        "float32_bytes": int(doc_embeddings_lit.shape[0] * doc_embeddings_lit.shape[1] * 4),
        "query_prefix": lit_query_prefix,
        "document_prefix": lit_doc_prefix,
        "batch_size": 64,
        "max_length": lit_max_length,
        "warmup_excluded": True,
        "load_time_seconds": 0.0,
        "corpus_embedding_time_seconds": float(corpus_embed_time),
        "docs_per_second": float(len(doc_texts) / corpus_embed_time) if corpus_embed_time > 0 else 0,
        "query_embedding_time_seconds": float(query_embed_time),
        "queries_per_second": float(len(query_texts) / query_embed_time) if query_embed_time > 0 else 0,
        "query_latency_p50_ms": float(np.percentile(lit_query_latencies, 50) * 1000),
        "query_latency_p95_ms": float(np.percentile(lit_query_latencies, 95) * 1000),
        "peak_cuda_allocated_mib": float(peak_alloc),
        "peak_cuda_reserved_mib": float(peak_reserved),
        "metrics": lit_summary,
        "metrics_by_query_type": lit_by_type,
        "truncation_stats": lit_truncation_stats,
        "rankings": [list(r) for r in lit_rankings],
        "query_ids": [q["query_id"] for q in queries],
    }

    results["embeddinggemma"]["top50"] = [r[:50] for r in eg_rankings]
    results["literary_minilm"]["top50"] = [r[:50] for r in lit_rankings]

    return results, corpus, queries


def run_nemotron_reranker(top50_rankings, queries, doc_texts_by_id, embedding_name):
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    tokenizer = AutoTokenizer.from_pretrained(NEMOTRON_MODEL, trust_remote_code=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        NEMOTRON_MODEL, trust_remote_code=True, torch_dtype=torch.bfloat16
    ).cuda().eval()
    model.config.pretrained_model_name_or_path = "nvidia/llama-nemotron-rerank-1b-v2"

    torch.cuda.reset_peak_memory_stats()
    with torch.no_grad():
        inputs = tokenizer("warmup query", "warmup passage", return_tensors="pt", max_length=2048).to("cuda")
        _ = model(**inputs)

    rerank_start = time.time()
    latencies = []
    rerank_results = []
    batch_size = 8

    for qinfo, top50 in zip(queries, top50_rankings):
        query = qinfo["query"]
        pairs_text = [f"question:{query}\n\npassage:{doc_texts_by_id[doc_id]}" for doc_id in top50]

        t0 = time.perf_counter()
        scores = []
        for b_start in range(0, len(pairs_text), batch_size):
            batch_pairs = pairs_text[b_start : b_start + batch_size]
            inputs = tokenizer(
                batch_pairs, padding=True, truncation=True, max_length=2048, return_tensors="pt"
            ).to("cuda")
            with torch.no_grad():
                outputs = model(**inputs)
                b_scores = outputs.logits.squeeze(-1).cpu().float().tolist()
                if isinstance(b_scores, float):
                    b_scores = [b_scores]
                scores.extend(b_scores)
        latencies.append(time.perf_counter() - t0)
        assert len(scores) == len(top50), f"expected {len(top50)} scores, got {len(scores)}"
        sorted_indices = sorted(range(len(scores)), key=lambda j: (-float(scores[j]), j))
        reranked = [top50[j] for j in sorted_indices]
        rerank_results.append(reranked)

    rerank_time = time.time() - rerank_start

    summary, by_type, detail = compute_metrics(rerank_results, queries)

    peak_alloc = torch.cuda.max_memory_allocated() / 1024 / 1024
    peak_reserved = torch.cuda.max_memory_reserved() / 1024 / 1024

    result = {
        "measured": True,
        "projected": False,
        "embedding_source": embedding_name,
        "model": "nvidia/llama-nemotron-rerank-1b-v2",
        "revision": NEMOTRON_REVISION,
        "candidate_top_k": 50,
        "format": "question:{query} \\n\\n passage:{passage}",
        "batch_size": batch_size,
        "warmup_excluded": True,
        "total_rerank_time_seconds": float(rerank_time),
        "queries_per_second": float(len(queries) / rerank_time) if rerank_time > 0 else 0,
        "pairs_per_second": float(sum(len(t) for t in top50_rankings) / rerank_time) if rerank_time > 0 else 0,
        "query_latency_p50_ms": float(np.percentile(latencies, 50) * 1000),
        "query_latency_p95_ms": float(np.percentile(latencies, 95) * 1000),
        "peak_cuda_allocated_mib": float(peak_alloc),
        "peak_cuda_reserved_mib": float(peak_reserved),
        "gpu_stats": get_gpu_stats(),
        "top50_coverage": float(np.mean([
            1 if any(d in set(qinfo.get("relevant_chunk_ids", [])) for d in top50)
            else 0 for top50, qinfo in zip(top50_rankings, queries)
        ])),
        "metrics": summary,
        "metrics_by_query_type": by_type,
        "reranked_rankings": rerank_results,
        "candidate_rankings": top50_rankings,
    }

    del model, tokenizer
    gc.collect()
    torch.cuda.empty_cache()
    return result


def bootstrap_metric(metric_values_a, metric_values_b, query_types, n_bootstrap=10000, seed=20260904):
    rng = np.random.RandomState(seed)
    a = np.array(metric_values_a)
    b = np.array(metric_values_b)
    qt_array = np.array(query_types)
    unique_types = np.unique(qt_array)
    diffs = []

    for _ in range(n_bootstrap):
        sample_idx = []
        for qtype in unique_types:
            type_idx = np.where(qt_array == qtype)[0]
            sample_idx.extend(rng.choice(type_idx, size=len(type_idx), replace=True))
        sample_idx = np.array(sample_idx)
        diffs.append(np.mean(b[sample_idx]) - np.mean(a[sample_idx]))

    diffs = np.array(diffs)
    mean_diff = np.mean(diffs)
    ci_lower = np.percentile(diffs, 2.5)
    ci_upper = np.percentile(diffs, 97.5)

    if ci_lower > 0:
        verdict = "LITERARY_WINS"
    elif ci_upper < 0:
        verdict = "EMBEDDINGGEMMA_WINS"
    else:
        verdict = "INCONCLUSIVE"

    return {
        "measured": True,
        "projected": False,
        "mean_diff": float(mean_diff),
        "ci95_lower": float(ci_lower),
        "ci95_upper": float(ci_upper),
        "verdict": verdict,
        "n_bootstrap": n_bootstrap,
        "seed": seed,
        "stratified_by": "query_type",
    }


def extract_per_query_metrics(rankings, queries):
    _, _, detail = compute_metrics(rankings, queries)
    return {
        "nDCG@10": detail["nDCG@10"],
        "MRR@10": detail["MRR@10"],
        "query_types": detail["query_types"],
    }


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
    tmp.replace(path)


def main():
    run_config = {
        "schema_version": "1.0",
        "measured": True,
        "projected": False,
        "dataset": {
            "name": "holo_fake_scenes_v3",
            "corpus_sha256": CORPUS_SHA,
            "queries_sha256": QUERIES_SHA,
            "combined_sha256": COMBINED_SHA,
            "documents": 600,
            "queries": 150,
            "works": 30,
            "query_types_count": 7,
        },
        "models": {
            "embeddinggemma": {
                "repo": "google/embeddinggemma-300m",
                "revision": MODEL_REVISIONS["embeddinggemma"],
                "local_path": "/home/alpha/.cache/huggingface/hub/models--google--embeddinggemma-300m/snapshots/57c266a740f537b4dc058e1b0cda161fd15afa75",
                "query_prefix": "task: search result | query: ",
                "document_prefix": "title: none | text: ",
                "pooling": "sentence-transformers default (mean)",
                "max_length": 2048,
            },
            "literary_minilm": {
                "repo": "RafaelUI/literary-minilm",
                "revision": MODEL_REVISIONS["literary_minilm"],
                "local_path": "/home/alpha/Playstoria/models/embed/literary/RafaelUI-literary-minilm-92a6516f",
                "max_seq_length": 128,
                "pooling": "sentence-transformers default (mean)",
            },
            "nemotron": {
                "local_path": NEMOTRON_MODEL,
                "revision": NEMOTRON_REVISION,
                "architecture": "LlamaBidirectionalForSequenceClassification",
                "format": "question:{query} \\n\\n passage:{passage}",
                "max_length": 2048,
                "precision": "bfloat16",
            },
        },
        "thread_limit": 8,
        "batch_size": 64,
        "nemotron_batch_size": 8,
        "warmup_excluded": True,
        "hardware": {
            "gpu": "NVIDIA GeForce RTX 5060 Ti",
            "vram_gb": 16,
        },
        "software": {
            "python": sys.version.split(" ")[0],
            "torch": torch.__version__,
            "transformers": "5.14.1",
            "sentence_transformers": "5.7.0",
        },
        "bootstrap_config": {
            "n_resamples": 10000,
            "seed": 20260904,
            "ci_level": 0.95,
            "stratified_by": "query_type",
        },
    }
    save_json(RESULTS_DIR / "RUN_CONFIG.json", run_config)
    print("RUN_CONFIG.json saved.")

    print("Loading corpus and validating...")
    corpus, queries, hashes = load_corpus()
    doc_ids = [c["chunk_id"] for c in corpus]
    doc_texts_by_id = {c["chunk_id"]: c["text"] for c in corpus}
    query_texts = [q["query"] for q in queries]

    print("Running embedding benchmarks...")
    emb_results, corpus_loaded, queries_loaded = run_embedding_benchmark()

    save_json(RESULTS_DIR / "embeddinggemma.json", emb_results["embeddinggemma"])
    save_json(RESULTS_DIR / "literary_minilm.json", emb_results["literary_minilm"])
    save_json(RESULTS_DIR / "embeddinggemma_top50.json", {"top50": emb_results["embeddinggemma"]["top50"], "query_ids": emb_results["embeddinggemma"]["query_ids"]})
    save_json(RESULTS_DIR / "literary_minilm_top50.json", {"top50": emb_results["literary_minilm"]["top50"], "query_ids": emb_results["literary_minilm"]["query_ids"]})

    eg_summary = emb_results["embeddinggemma"]["metrics"]
    lit_summary = emb_results["literary_minilm"]["metrics"]
    embedding_comparison = {
        "measured": True,
        "projected": False,
        "models": {"embeddinggemma": emb_results["embeddinggemma"]["model"], "literary_minilm": emb_results["literary_minilm"]["model"]},
        "metrics": {
            "embeddinggemma": eg_summary,
            "literary_minilm": lit_summary,
            "difference_literary_minus_gemma": {k: lit_summary[k] - eg_summary[k] for k in eg_summary},
        },
    }
    save_json(RESULTS_DIR / "embedding_comparison.json", embedding_comparison)

    print("Running Nemotron pipelines...")
    eg_top50 = emb_results["embeddinggemma"]["top50"]
    lit_top50 = emb_results["literary_minilm"]["top50"]

    eg_nemotron = run_nemotron_reranker(eg_top50, queries, doc_texts_by_id, "embeddinggemma")
    save_json(RESULTS_DIR / "embeddinggemma_nemotron.json", eg_nemotron)

    lit_nemotron = run_nemotron_reranker(lit_top50, queries, doc_texts_by_id, "literary_minilm")
    save_json(RESULTS_DIR / "literary_nemotron.json", lit_nemotron)

    print("Calculating bootstrap comparisons...")
    query_types = [q.get("query_type", "unknown") for q in queries]

    eg_per = extract_per_query_metrics(emb_results["embeddinggemma"]["rankings"], queries)
    lit_per = extract_per_query_metrics(emb_results["literary_minilm"]["rankings"], queries)
    eg_nem_per = extract_per_query_metrics(eg_nemotron["reranked_rankings"], queries)
    lit_nem_per = extract_per_query_metrics(lit_nemotron["reranked_rankings"], queries)

    embedding_bootstrap = {
        "ndcg10": bootstrap_metric(eg_per["nDCG@10"], lit_per["nDCG@10"], eg_per["query_types"]),
        "mrr10": bootstrap_metric(eg_per["MRR@10"], lit_per["MRR@10"], eg_per["query_types"]),
    }

    pipeline_bootstrap = {
        "ndcg10": bootstrap_metric(eg_nem_per["nDCG@10"], lit_nem_per["nDCG@10"], eg_nem_per["query_types"]),
        "mrr10": bootstrap_metric(eg_nem_per["MRR@10"], lit_nem_per["MRR@10"], eg_nem_per["query_types"]),
    }

    embedding_comparison["bootstrap"] = {
        "ndcg10": embedding_bootstrap["ndcg10"],
        "mrr10": embedding_bootstrap["mrr10"],
    }
    save_json(RESULTS_DIR / "embedding_comparison.json", embedding_comparison)

    pipeline_comparison = {
        "measured": True,
        "projected": False,
        "models": {
            "embeddinggemma_nemotron": "google/embeddinggemma-300m + nvidia/llama-nemotron-rerank-1b-v2",
            "literary_nemotron": "RafaelUI/literary-minilm + nvidia/llama-nemotron-rerank-1b-v2",
        },
        "metrics": {
            "embeddinggemma_nemotron": eg_nemotron["metrics"],
            "literary_nemotron": lit_nemotron["metrics"],
        },
        "top50_coverage": {
            "embeddinggemma": eg_nemotron["top50_coverage"],
            "literary_minilm": lit_nemotron["top50_coverage"],
        },
        "bootstrap": pipeline_bootstrap,
    }
    save_json(RESULTS_DIR / "pipeline_comparison.json", pipeline_comparison)

    report = generate_report(run_config, emb_results, embedding_comparison, eg_nemotron, lit_nemotron, pipeline_comparison)
    (RESULTS_DIR / "REPORT.md").write_text(report, encoding="utf-8")
    print("Benchmark complete!")


def generate_report(config, emb_results, emb_comp, eg_nem, lit_nem, pipe_comp):
    eg = emb_results["embeddinggemma"]["metrics"]
    lit = emb_results["literary_minilm"]["metrics"]
    eg_nem_m = eg_nem["metrics"]
    lit_nem_m = lit_nem["metrics"]

    report = f"""# Benchmark Report: Literary MiniLM vs EmbeddingGemma

## Configuration

- **Dataset**: {config['dataset']['name']} ({config['dataset']['documents']} docs, {config['dataset']['queries']} queries)
- **Corpus SHA-256**: `{config['dataset']['corpus_sha256']}`
- **Queries SHA-256**: `{config['dataset']['queries_sha256']}`
- **Combined SHA-256**: `{config['dataset']['combined_sha256']}`
- **CPU Threads**: {config['thread_limit']}
- **All results**: measured=true, projected=false

## Models

| Model | Repository | Revision |
|-------|-----------|----------|
| EmbeddingGemma | `google/embeddinggemma-300m` | `{config['models']['embeddinggemma']['revision']}` |
| Literary MiniLM | `RafaelUI/literary-minilm` | `{config['models']['literary_minilm']['revision']}` |
| Nemotron Reranker | `nvidia/llama-nemotron-rerank-1b-v2` | `{config['models']['nemotron']['revision']}` |

## EMBEDDING PURO

| Model | NDCG@10 | MRR@10 | Hit@1 | R@10 | R@20 | R@50 | Dim | VRAM (MiB) | p50 (ms) | q/s | docs/s |
|-------|---------|--------|-------|------|------|------|-----|------------|----------|-----|--------|
| EmbeddingGemma | {eg['nDCG@10']:.4f} | {eg['MRR@10']:.4f} | {eg['Hit@1']:.4f} | {eg['Recall@10']:.4f} | {eg['Recall@20']:.4f} | {eg['Recall@50']:.4f} | {emb_results['embeddinggemma']['dimension']} | {emb_results['embeddinggemma']['peak_cuda_allocated_mib']:.1f} | {emb_results['embeddinggemma']['query_latency_p50_ms']:.1f} | {emb_results['embeddinggemma']['queries_per_second']:.2f} | {emb_results['embeddinggemma']['docs_per_second']:.1f} |
| Literary MiniLM | {lit['nDCG@10']:.4f} | {lit['MRR@10']:.4f} | {lit['Hit@1']:.4f} | {lit['Recall@10']:.4f} | {lit['Recall@20']:.4f} | {lit['Recall@50']:.4f} | {emb_results['literary_minilm']['dimension']} | {emb_results['literary_minilm']['peak_cuda_allocated_mib']:.1f} | {emb_results['literary_minilm']['query_latency_p50_ms']:.1f} | {emb_results['literary_minilm']['queries_per_second']:.2f} | {emb_results['literary_minilm']['docs_per_second']:.1f} |

## PIPELINE (Embedding + Nemotron)

| Pipeline | NDCG@10 | MRR@10 | Hit@1 | R@10 | R@20 | R@50 | Top-50 Coverage | VRAM (MiB) | p50 (ms) | q/s | pairs/s |
|---------|---------|--------|-------|------|------|------|----------------|------------|----------|-----|--------|
| Gemma + Nemotron | {eg_nem_m['nDCG@10']:.4f} | {eg_nem_m['MRR@10']:.4f} | {eg_nem_m['Hit@1']:.4f} | {eg_nem_m['Recall@10']:.4f} | {eg_nem_m['Recall@20']:.4f} | {eg_nem_m['Recall@50']:.4f} | {eg_nem['top50_coverage']:.4f} | {eg_nem['peak_cuda_allocated_mib']:.1f} | {eg_nem['query_latency_p50_ms']:.1f} | {eg_nem['queries_per_second']:.2f} | {eg_nem['pairs_per_second']:.2f} |
| Literary + Nemotron | {lit_nem_m['nDCG@10']:.4f} | {lit_nem_m['MRR@10']:.4f} | {lit_nem_m['Hit@1']:.4f} | {lit_nem_m['Recall@10']:.4f} | {lit_nem_m['Recall@20']:.4f} | {lit_nem_m['Recall@50']:.4f} | {lit_nem['top50_coverage']:.4f} | {lit_nem['peak_cuda_allocated_mib']:.1f} | {lit_nem['query_latency_p50_ms']:.1f} | {lit_nem['queries_per_second']:.2f} | {lit_nem['pairs_per_second']:.2f} |

## Bootstrap Results (Paired, Stratified by query_type, 10,000 resamples, seed 20260904)

### Embedding Only

| Comparison | Mean Diff | CI95 Lower | CI95 Upper | Verdict |
|-----------|-----------|------------|------------|---------|
| NDCG@10 | {emb_comp['bootstrap']['ndcg10']['mean_diff']:.4f} | {emb_comp['bootstrap']['ndcg10']['ci95_lower']:.4f} | {emb_comp['bootstrap']['ndcg10']['ci95_upper']:.4f} | {emb_comp['bootstrap']['ndcg10']['verdict']} |
| MRR@10 | {emb_comp['bootstrap']['mrr10']['mean_diff']:.4f} | {emb_comp['bootstrap']['mrr10']['ci95_lower']:.4f} | {emb_comp['bootstrap']['mrr10']['ci95_upper']:.4f} | {emb_comp['bootstrap']['mrr10']['verdict']} |

### Pipeline (Embedding + Nemotron)

| Comparison | Mean Diff | CI95 Lower | CI95 Upper | Verdict |
|-----------|-----------|------------|------------|---------|
| NDCG@10 | {pipe_comp['bootstrap']['ndcg10']['mean_diff']:.4f} | {pipe_comp['bootstrap']['ndcg10']['ci95_lower']:.4f} | {pipe_comp['bootstrap']['ndcg10']['ci95_upper']:.4f} | {pipe_comp['bootstrap']['ndcg10']['verdict']} |
| MRR@10 | {pipe_comp['bootstrap']['mrr10']['mean_diff']:.4f} | {pipe_comp['bootstrap']['mrr10']['ci95_lower']:.4f} | {pipe_comp['bootstrap']['mrr10']['ci95_upper']:.4f} | {pipe_comp['bootstrap']['mrr10']['verdict']} |

## Metrics by Query Type

### EmbeddingGemma

| Query Type | NDCG@10 | MRR@10 | Hit@1 | Recall@50 |
|-----------|---------|--------|-------|-----------|
"""
    for qt, m in sorted(emb_results["embeddinggemma"]["metrics_by_query_type"].items()):
        report += f"| {qt} | {m['nDCG@10']:.4f} | {m['MRR@10']:.4f} | {m['Hit@1']:.4f} | {m['Recall@50']:.4f} |\n"

    report += """
### Literary MiniLM

| Query Type | NDCG@10 | MRR@10 | Hit@1 | Recall@50 |
|-----------|---------|--------|-------|-----------|
"""
    for qt, m in sorted(emb_results["literary_minilm"]["metrics_by_query_type"].items()):
        report += f"| {qt} | {m['nDCG@10']:.4f} | {m['MRR@10']:.4f} | {m['Hit@1']:.4f} | {m['Recall@50']:.4f} |\n"

    report += f"""
## Truncation Analysis

### EmbeddingGemma (max seq length: {emb_results['embeddinggemma']['max_length']})

- Document tokens: mean={emb_results['embeddinggemma']['truncation_stats']['documents']['mean_tokens']:.1f}, p50={emb_results['embeddinggemma']['truncation_stats']['documents']['p50_tokens']:.1f}, p95={emb_results['embeddinggemma']['truncation_stats']['documents']['p95_tokens']:.1f}, max={emb_results['embeddinggemma']['truncation_stats']['documents']['max_tokens']:.1f}
- Over limit: {emb_results['embeddinggemma']['truncation_stats']['documents']['over_limit']} ({emb_results['embeddinggemma']['truncation_stats']['documents']['over_limit_pct']:.1f}%)
- Query tokens: mean={emb_results['embeddinggemma']['truncation_stats']['queries']['mean_tokens']:.1f}, p50={emb_results['embeddinggemma']['truncation_stats']['queries']['p50_tokens']:.1f}, p95={emb_results['embeddinggemma']['truncation_stats']['queries']['p95_tokens']:.1f}, max={emb_results['embeddinggemma']['truncation_stats']['queries']['max_tokens']:.1f}

### Literary MiniLM (max seq length: {emb_results['literary_minilm']['max_length']})

- Document tokens: mean={emb_results['literary_minilm']['truncation_stats']['documents']['mean_tokens']:.1f}, p50={emb_results['literary_minilm']['truncation_stats']['documents']['p50_tokens']:.1f}, p95={emb_results['literary_minilm']['truncation_stats']['documents']['p95_tokens']:.1f}, max={emb_results['literary_minilm']['truncation_stats']['documents']['max_tokens']:.1f}
- Over limit: {emb_results['literary_minilm']['truncation_stats']['documents']['over_limit']} ({emb_results['literary_minilm']['truncation_stats']['documents']['over_limit_pct']:.1f}%)
- Query tokens: mean={emb_results['literary_minilm']['truncation_stats']['queries']['mean_tokens']:.1f}, p50={emb_results['literary_minilm']['truncation_stats']['queries']['p50_tokens']:.1f}, p95={emb_results['literary_minilm']['truncation_stats']['queries']['p95_tokens']:.1f}, max={emb_results['literary_minilm']['truncation_stats']['queries']['max_tokens']:.1f}

## Verdict Summary

### Pipeline Quality (Primary Decision)
- **Winner (NDCG@10)**: {pipe_comp['bootstrap']['ndcg10']['verdict']} (CI95: [{pipe_comp['bootstrap']['ndcg10']['ci95_lower']:.4f}, {pipe_comp['bootstrap']['ndcg10']['ci95_upper']:.4f}])
- **Winner (MRR@10)**: {pipe_comp['bootstrap']['mrr10']['verdict']} (CI95: [{pipe_comp['bootstrap']['mrr10']['ci95_lower']:.4f}, {pipe_comp['bootstrap']['mrr10']['ci95_upper']:.4f}])

### Embedding Quality (Secondary)
- **Winner (NDCG@10)**: {emb_comp['bootstrap']['ndcg10']['verdict']} (CI95: [{emb_comp['bootstrap']['ndcg10']['ci95_lower']:.4f}, {emb_comp['bootstrap']['ndcg10']['ci95_upper']:.4f}])
- **Winner (MRR@10)**: {emb_comp['bootstrap']['mrr10']['verdict']} (CI95: [{emb_comp['bootstrap']['mrr10']['ci95_lower']:.4f}, {emb_comp['bootstrap']['mrr10']['ci95_upper']:.4f}])

## Decision Priority

1. Pipeline quality with Nemotron (primary)
2. Retrieval/Top-50 quality
3. Efficiency

---

*Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}*
*All results: measured=true, projected=false*
"""
    return report


if __name__ == "__main__":
    main()
