# jina-reranker-v3.5 — legacy projected result notice

This file previously presented `0.9162` as if it were a measured MRR@10 result on the historical 240-query benchmark. It was not directly measured.

The actually measured reranker-v1.5 reconstruction used 150 queries and produced, on that reconstructed panel:

- Jina v3.5 mean MRR@10: 0.8087
- Nemotron 1B v2 mean MRR@10: 0.8221
- Qwen3-Reranker-0.6B mean MRR@10: 0.8180
- Jina v3.5 on mDenseOn: 0.8043
- Nemotron 1B v2 on mDenseOn: 0.8138

The old `0.9162` number was obtained by extrapolating the observed 150-query delta onto the historical 240-query Nemotron score. That extrapolation is not a valid benchmark measurement and must not be used for model selection.

The historical 240-query benchmark is retained as legacy evidence, but the new `reranker-v2-unbiased` benchmark is the decision benchmark going forward.
