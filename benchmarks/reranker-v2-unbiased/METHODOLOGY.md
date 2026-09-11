# Methodology

## Tracks

### GENERAL

External-only NanoBEIR track using the published Sentence-Transformers BM25 candidate rankings:

- NanoMSMARCO
- NanoNQ
- NanoNFCorpus
- NanoFiQA2018
- NanoSciFact

Each dataset is reported separately. The headline GENERAL score is the equal-weight macro average across datasets, not a blend with HOLO.

### HOLO

The Holo-specific track contains 304 queries generated from 76 semantic intents anchored to 32 canonical source families in `Weltall-IA/holo-agent-tooling`.

Each intent has four phrasings: two pt-BR and two English. The relevant labels are canonical source paths chosen before any of the four rerankers is evaluated.

The corpus is frozen from the canonical Holo specification (`AGENTS.md`, `ARCHITECTURE.md`, `README.md`, `library/`, `capabilities/`, `core/`, and `harnesses/`). Candidate generation uses a lexical BM25 implementation independent of all evaluated neural rerankers.

The 304 phrasings are not treated as 304 independent statistical observations: HOLO bootstrap resampling is clustered by the 32 canonical source families.

## Candidate generation

Candidate generation is a separate stage from reranking.

For every query:

1. Produce one first-stage ranking before running any reranker.
2. Freeze the top 50 candidate IDs and hash the dataset files.
3. Preserve the raw first-stage top-50 as `pipeline_candidate_ids` for end-to-end candidate-recall reporting.
4. For the pure-reranker comparison, construct one shared positive-complete top-50 pool. If a judged positive is absent from the first-stage top-50, insert it only once at the tail by replacing the lowest-ranked negative.
5. Give the exact same `candidate_ids` to every reranker.

GENERAL uses the BM25 rankings published with the Sentence-Transformers NanoBEIR datasets. HOLO uses local lexical BM25 over the frozen canonical Holo corpus.

This intentionally separates two questions:

- end-to-end retrieval: did the first stage retrieve the relevant document at all?
- reranker quality: given the same candidate set containing the judged positives, which model orders it best?

## Metrics

Primary:

- NDCG@10

Secondary:

- MRR@10
- MAP
- Hit@1
- Recall@10
- Recall@20

Metrics are computed per query first. GENERAL uses an equal-weight macro across datasets. HOLO uses the query-level aggregate but its confidence intervals are clustered by source family.

## Statistical comparison

For NDCG@10 and MRR@10:

- fixed seed `20260904`
- 10,000 bootstrap resamples by default
- percentile 95% confidence intervals
- paired comparisons use the same frozen queries and candidates

GENERAL performs stratified resampling within each dataset and then equal-weights the dataset means.

HOLO resamples the 32 canonical source families, keeping all phrasings from a sampled family together. This prevents paraphrases of the same retrieval target from creating pseudo-replication.

Decision rule:

- paired CI entirely > 0: A wins
- paired CI entirely < 0: B wins
- paired CI crosses 0: statistically inconclusive

A higher point estimate is not called a quality win when the paired 95% CI crosses zero.

## Model adapters

Fairness is enforced at the query/candidate level, not by forcing incompatible models through one API.

- Nemotron 1B v2: native Transformers sequence-classification path and its documented `question:/passage:` single-sequence format.
- Jina v3.5: native listwise `model.rerank(...)` path.
- Qwen3-Reranker-0.6B: official Sentence-Transformers CrossEncoder path.
- Ettin 400M: official Sentence-Transformers CrossEncoder path.

## Efficiency

Measured separately from quality:

- peak GPU allocated memory
- peak GPU reserved memory
- peak process RSS
- p50 latency per query/list
- p95 latency per query/list
- queries/lists per second
- total wall time

Warmup requests are excluded from latency statistics. Efficiency never changes the quality score.

## Reproducibility

Every frozen dataset records source revision/state and SHA256 hashes. Every run records runtime/library versions, model source, adapter metadata, device, dtype where observable, candidate fingerprints, per-query metrics, raw rankings, and efficiency measurements.

The runner refuses mutated candidate files whose SHA256 differs from the freeze manifest.

No historical or projected score may enter a V2 result table as if measured. Legacy scores are context only.
