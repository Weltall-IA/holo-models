# Reranker V2 — Unbiased Benchmark

Decision benchmark for reranker selection, deliberately separated from the legacy 150/240-query experiments.

Two independent tracks:

- `GENERAL`: five external NanoBEIR datasets with published BM25 candidate rankings.
- `HOLO`: 304 pt-BR/English queries anchored to 76 intents and 32 canonical Holo source families.

The tracks are never averaged together.

## Core rules

1. Candidate pools are frozen before reranking and shared by every model.
2. The pure-reranker pool is positive-complete; raw first-stage top-50 is retained separately for pipeline recall.
3. Hard negatives come from BM25 retrieval, not random sampling.
4. Primary metric: NDCG@10. Secondary: MRR@10, MAP, Hit@1, Recall@10, Recall@20.
5. NDCG@10 and MRR@10 use paired 95% bootstrap intervals.
6. GENERAL bootstraps within each dataset and uses equal-weight macro averaging.
7. HOLO bootstraps by 32 canonical source families, so paraphrases do not count as independent evidence.
8. Quality and efficiency are separate. VRAM/latency never alter the quality score.
9. No projected or extrapolated scores are allowed.
10. Raw per-query metrics and rankings are retained.
11. Each model uses its official/native inference path; fairness is enforced by identical query/candidate inputs.

Initial panel:

- `nvidia/llama-nemotron-rerank-1b-v2`
- `jinaai/jina-reranker-v3.5`
- `Qwen/Qwen3-Reranker-0.6B`
- `cross-encoder/ettin-reranker-400m-v1`

## Validate the harness

```bash
cd benchmarks/reranker-v2-unbiased
python -m py_compile metrics.py holo_gold.py prepare_general.py prepare_holo.py run_benchmark.py report.py
python -m unittest discover -s tests -v
```

Install runtime dependencies in the repository environment if they are not already present:

```bash
python -m pip install -r requirements.txt
```

## GENERAL

Freeze the external candidate pools once:

```bash
python prepare_general.py
```

Run the four models on exactly those frozen pools:

```bash
python run_benchmark.py --data-dir data/general-v1
```

Generate the paired report only after all four measured result files exist:

```bash
python report.py --data-dir data/general-v1
```

## HOLO

The source checkout should be the canonical `holo-agent-tooling` checkout. By default the script expects it next to the `holo-models` repository.

```bash
python prepare_holo.py --tooling-root ../../holo-agent-tooling
python run_benchmark.py --data-dir data/holo-v1
python report.py --data-dir data/holo-v1
```

`prepare_holo.py` refuses a dirty tooling checkout by default. If a dirty tree is intentionally being benchmarked, `--allow-dirty` records that fact and the frozen file hashes still identify the exact corpus.

Models may also be run one at a time without changing the frozen data, for example:

```bash
python run_benchmark.py --data-dir data/general-v1 --models jina_v35
python run_benchmark.py --data-dir data/general-v1 --models nemotron_1b_v2
```

Do not use `--force` unless intentionally replacing a run on the same frozen dataset. Do not copy legacy MRR values into V2 result files.

See `METHODOLOGY.md` and `manifest.json` for the exact protocol.
