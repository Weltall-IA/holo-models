# Methodology

## Tracks

### GENERAL

Use external NanoBEIR datasets only. Default set:

- NanoMSMARCO
- NanoNQ
- NanoNFCorpus
- NanoFiQA
- NanoSciFact

The external track is intended to reduce repository-specific overfitting and should remain unchanged once a benchmark version is released.

### HOLO

Use a held-out Holo dataset with 300–500 queries spanning:

- technical documentation
- code/repository navigation
- SKILL.md selection
- tool selection
- configuration/file lookup
- Portuguese and English
- deliberately confusable near-miss documents

The HOLO test set must be authored/frozen before inspecting model outputs. Development examples, prompt-tuning examples, and benchmark queries must be disjoint.

## Candidate generation

Candidate generation is a separate stage from reranking.

For every query:

1. Run one frozen first-stage retriever configuration.
2. Select top 50 documents.
3. Ensure all judged positives are represented only according to the declared candidate policy; never inject positives differently per reranker.
4. Save query ID, candidate IDs, first-stage rank, first-stage score, and relevance labels.
5. Hash the candidate-pool file.

Every reranker receives the exact same ordered candidate IDs.

Hard negatives are therefore retrieval-derived semantic confounders rather than random documents.

## Metrics

Primary:

- NDCG@10

Secondary:

- MRR@10
- MAP
- Hit@1
- Recall@10
- Recall@20

Metrics are computed per query first, then aggregated.

## Statistical comparison

For NDCG@10 and MRR@10:

- paired bootstrap over query IDs
- fixed seed `20260904`
- 10,000 resamples by default
- report mean and percentile 95% CI

For pairwise model comparisons, bootstrap the per-query metric difference `A - B` using the same resampled query indices.

Decision rule:

- CI entirely > 0: A wins
- CI entirely < 0: B wins
- CI crosses 0: statistically inconclusive

Do not call a model the quality winner solely from a tiny aggregate delta whose paired CI crosses zero.

## Efficiency

Measured separately from quality:

- peak GPU allocated memory
- peak process RSS
- p50 latency per query/list
- p95 latency per query/list
- queries/lists per second
- total wall time

Warmup requests are excluded from latency statistics.

## Reproducibility

Every run records:

- model ID and resolved revision when available
- inference adapter
- dtype
- max length/context
- batch/list size
- torch/transformers/sentence-transformers versions
- GPU name
- CUDA version
- random seeds
- candidate-pool SHA256
- dataset manifest SHA256

No historical score may be copied into a V2 result table as if measured. Legacy scores may appear only in a clearly labeled appendix.
