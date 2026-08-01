---
language:
- en
license: apache-2.0
tags:
- sentence-transformers
- cross-encoder
- reranker
- generated_from_trainer
- dataset_size:143393475
- loss:MSELoss
base_model: jhu-clsp/ettin-encoder-150m
pipeline_tag: text-ranking
library_name: sentence-transformers
metrics:
- map
- mrr@10
- ndcg@10
model-index:
- name: ettin-reranker-150m-v1
  results:
  - task:
      type: cross-encoder-reranking
      name: Cross Encoder Reranking
    dataset:
      name: NanoMSMARCO R100
      type: NanoMSMARCO_R100
    metrics:
    - type: map
      value: 0.6425
      name: Map
    - type: mrr@10
      value: 0.6459
      name: Mrr@10
    - type: ndcg@10
      value: 0.7243
      name: Ndcg@10
  - task:
      type: cross-encoder-reranking
      name: Cross Encoder Reranking
    dataset:
      name: NanoNFCorpus R100
      type: NanoNFCorpus_R100
    metrics:
    - type: map
      value: 0.3657
      name: Map
    - type: mrr@10
      value: 0.5762
      name: Mrr@10
    - type: ndcg@10
      value: 0.4067
      name: Ndcg@10
  - task:
      type: cross-encoder-reranking
      name: Cross Encoder Reranking
    dataset:
      name: NanoNQ R100
      type: NanoNQ_R100
    metrics:
    - type: map
      value: 0.7484
      name: Map
    - type: mrr@10
      value: 0.7678
      name: Mrr@10
    - type: ndcg@10
      value: 0.7992
      name: Ndcg@10
  - task:
      type: cross-encoder-reranking
      name: Cross Encoder Reranking
    dataset:
      name: NanoFiQA2018 R100
      type: NanoFiQA2018_R100
    metrics:
    - type: map
      value: 0.563
      name: Map
    - type: mrr@10
      value: 0.6733
      name: Mrr@10
    - type: ndcg@10
      value: 0.6127
      name: Ndcg@10
  - task:
      type: cross-encoder-reranking
      name: Cross Encoder Reranking
    dataset:
      name: NanoTouche2020 R100
      type: NanoTouche2020_R100
    metrics:
    - type: map
      value: 0.472
      name: Map
    - type: mrr@10
      value: 0.8155
      name: Mrr@10
    - type: ndcg@10
      value: 0.5518
      name: Ndcg@10
  - task:
      type: cross-encoder-reranking
      name: Cross Encoder Reranking
    dataset:
      name: NanoSciFact R100
      type: NanoSciFact_R100
    metrics:
    - type: map
      value: 0.716
      name: Map
    - type: mrr@10
      value: 0.713
      name: Mrr@10
    - type: ndcg@10
      value: 0.7613
      name: Ndcg@10
  - task:
      type: cross-encoder-reranking
      name: Cross Encoder Reranking
    dataset:
      name: NanoHotpotQA R100
      type: NanoHotpotQA_R100
    metrics:
    - type: map
      value: 0.9307
      name: Map
    - type: mrr@10
      value: 1.0
      name: Mrr@10
    - type: ndcg@10
      value: 0.9573
      name: Ndcg@10
  - task:
      type: cross-encoder-reranking
      name: Cross Encoder Reranking
    dataset:
      name: NanoArguAna R100
      type: NanoArguAna_R100
    metrics:
    - type: map
      value: 0.6597
      name: Map
    - type: mrr@10
      value: 0.6579
      name: Mrr@10
    - type: ndcg@10
      value: 0.7375
      name: Ndcg@10
  - task:
      type: cross-encoder-reranking
      name: Cross Encoder Reranking
    dataset:
      name: NanoFEVER R100
      type: NanoFEVER_R100
    metrics:
    - type: map
      value: 0.9436
      name: Map
    - type: mrr@10
      value: 0.975
      name: Mrr@10
    - type: ndcg@10
      value: 0.96
      name: Ndcg@10
  - task:
      type: cross-encoder-reranking
      name: Cross Encoder Reranking
    dataset:
      name: NanoDBPedia R100
      type: NanoDBPedia_R100
    metrics:
    - type: map
      value: 0.679
      name: Map
    - type: mrr@10
      value: 0.8939
      name: Mrr@10
    - type: ndcg@10
      value: 0.7494
      name: Ndcg@10
  - task:
      type: cross-encoder-reranking
      name: Cross Encoder Reranking
    dataset:
      name: NanoClimateFEVER R100
      type: NanoClimateFEVER_R100
    metrics:
    - type: map
      value: 0.4903
      name: Map
    - type: mrr@10
      value: 0.7496
      name: Mrr@10
    - type: ndcg@10
      value: 0.5722
      name: Ndcg@10
  - task:
      type: cross-encoder-reranking
      name: Cross Encoder Reranking
    dataset:
      name: NanoSCIDOCS R100
      type: NanoSCIDOCS_R100
    metrics:
    - type: map
      value: 0.3227
      name: Map
    - type: mrr@10
      value: 0.5548
      name: Mrr@10
    - type: ndcg@10
      value: 0.3742
      name: Ndcg@10
  - task:
      type: cross-encoder-reranking
      name: Cross Encoder Reranking
    dataset:
      name: NanoQuoraRetrieval R100
      type: NanoQuoraRetrieval_R100
    metrics:
    - type: map
      value: 0.9608
      name: Map
    - type: mrr@10
      value: 0.98
      name: Mrr@10
    - type: ndcg@10
      value: 0.9753
      name: Ndcg@10
  - task:
      type: cross-encoder-nano-beir
      name: Cross Encoder Nano BEIR
    dataset:
      name: NanoBEIR R100 mean
      type: NanoBEIR_R100_mean
    metrics:
    - type: map
      value: 0.6534
      name: Map
    - type: mrr@10
      value: 0.7695
      name: Mrr@10
    - type: ndcg@10
      value: 0.7063
      name: Ndcg@10
---

# ettin-reranker-150m-v1

This is a [Cross Encoder](https://www.sbert.net/docs/cross_encoder/usage/usage.html) model finetuned from [jhu-clsp/ettin-encoder-150m](https://huggingface.co/jhu-clsp/ettin-encoder-150m) on the [cross-encoder/ettin-reranker-v1-data](https://huggingface.co/datasets/cross-encoder/ettin-reranker-v1-data) dataset using the [sentence-transformers](https://www.SBERT.net) library. It computes scores for pairs of texts, which can be used for text reranking and semantic search.

See the [release blogpost](https://huggingface.co/blog/ettin-reranker) for details on the training recipe, evaluation results, and speed benchmarks against other public rerankers. The [Evaluation](#evaluation) section below also has the headline numbers.

## Model Details

### Model Description
- **Model Type:** Cross Encoder
- **Base model:** [jhu-clsp/ettin-encoder-150m](https://huggingface.co/jhu-clsp/ettin-encoder-150m) <!-- at revision 45d08642849e5c5701b162671ac811b7654bfd9f -->
- **Maximum Sequence Length:** 7999 tokens
- **Number of Output Labels:** 1 label
- **Supported Modality:** Text
- **Training Dataset:** [cross-encoder/ettin-reranker-v1-data](https://huggingface.co/datasets/cross-encoder/ettin-reranker-v1-data)
- **Language:** en
- **License:** apache-2.0

### Model Sources

- **Documentation:** [Sentence Transformers Documentation](https://sbert.net)
- **Documentation:** [Cross Encoder Documentation](https://www.sbert.net/docs/cross_encoder/usage/usage.html)
- **Repository:** [Sentence Transformers on GitHub](https://github.com/huggingface/sentence-transformers)
- **Hugging Face:** [Cross Encoders on Hugging Face](https://huggingface.co/models?library=sentence-transformers&other=cross-encoder)

### Full Model Architecture

```
CrossEncoder(
  (0): Transformer({'transformer_task': 'feature-extraction', 'modality_config': {'text': {'method': 'forward', 'method_output_name': 'last_hidden_state'}}, 'module_output_name': 'token_embeddings', 'architecture': 'ModernBertModel'})
  (1): Pooling({'embedding_dimension': 768, 'pooling_mode': 'cls', 'include_prompt': True})
  (2): Dense({'in_features': 768, 'out_features': 768, 'bias': False, 'activation_function': 'torch.nn.modules.activation.GELU', 'module_input_name': 'sentence_embedding', 'module_output_name': 'sentence_embedding'})
  (3): LayerNorm({'dimension': 768})
  (4): Dense({'in_features': 768, 'out_features': 1, 'bias': True, 'activation_function': 'torch.nn.modules.linear.Identity', 'module_input_name': 'sentence_embedding', 'module_output_name': 'scores'})
)
```

## Usage

### Direct Usage (Sentence Transformers)

First install the Sentence Transformers library:

```bash
pip install -U sentence-transformers
```

Then you can load this model and run inference.
```python
from sentence_transformers import CrossEncoder

# Download from the 🤗 Hub
model = CrossEncoder(
    "cross-encoder/ettin-reranker-150m-v1",
    model_kwargs={"dtype": "bfloat16", "attn_implementation": "flash_attention_2"},  # Optional: pip install kernels
)

# Get scores for pairs of inputs
query = "Which planet is known as the Red Planet?"
passages = [
    "Venus is often called Earth's twin because of its similar size and proximity.",
    "Mars, known for its reddish appearance, is often referred to as the Red Planet.",
    "Jupiter, the largest planet in our solar system, has a prominent red spot.",
    "Saturn, famous for its rings, is sometimes mistaken for the Red Planet.",
]
scores = model.predict([(query, passage) for passage in passages])
print(scores)
# [ 4.875  11.625   7.375  10.3125]

# Or rank passages by relevance to a single query
ranked = model.rank(query, passages)
print(ranked)
# [{'corpus_id': 1, 'score': np.float32(11.625)}, ...]
```

<!--
### Direct Usage (Transformers)

<details><summary>Click to see the direct usage in Transformers</summary>

</details>
-->

<!--
### Downstream Usage (Sentence Transformers)

You can finetune this model on your own dataset.

<details><summary>Click to expand</summary>

</details>
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

## Evaluation

### MTEB(eng, v2) Retrieval

Each model in the ettin-reranker-v1 family was evaluated on the full [`MTEB(eng, v2)` Retrieval benchmark](https://github.com/embeddings-benchmark/mteb) (10 tasks, top-100 reranked) using MTEB's [two-stage reranking flow](https://embeddings-benchmark.github.io/mteb/get_started/advanced_usage/two_stage_reranking/), pairing each reranker with six embedding models that span the speed/quality spectrum.
The dashed retriever-only line in each chart below is the headline number to beat. Anything below it means the reranker actively hurts the pipeline on average:

| | |
|-|-|
| ![MTEB(eng, v2) Retrieval with static-retrieval-mrl-en-v1 + reranker](https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/blog/ettin-reranker/mteb_ndcg10_static-retrieval-mrl-en-v1.png) | ![MTEB(eng, v2) Retrieval with all-MiniLM-L6-v2 + reranker](https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/blog/ettin-reranker/mteb_ndcg10_all-MiniLM-L6-v2.png) |
| ![MTEB(eng, v2) Retrieval with bge-small-en-v1.5 + reranker](https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/blog/ettin-reranker/mteb_ndcg10_bge-small-en-v1.5.png) | ![MTEB(eng, v2) Retrieval with nomic-embed-text-v1.5 + reranker](https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/blog/ettin-reranker/mteb_ndcg10_nomic-embed-text-v1.5.png) |
| ![MTEB(eng, v2) Retrieval with embeddinggemma-300m + reranker](https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/blog/ettin-reranker/mteb_ndcg10_embeddinggemma-300m.png) | ![MTEB(eng, v2) Retrieval with jina-embeddings-v5-text-small-retrieval + reranker](https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/blog/ettin-reranker/mteb_ndcg10_jina-embeddings-v5-text-small-retrieval.png) |

<details><summary>Full table of results (click to expand)</summary>

Mean NDCG@10 over the 6 embedder pairings, sorted by MTEB. The released ettin-reranker-v1 family is in **bold**, and the teacher [`mixedbread-ai/mxbai-rerank-large-v2`](https://huggingface.co/mixedbread-ai/mxbai-rerank-large-v2) is <u>underlined</u>.

| Reranker | Params | MTEB(eng, v2) Retrieval NDCG@10 |
| --- | ---: | ---: |
| [`Qwen/Qwen3-Reranker-4B`](https://huggingface.co/Qwen/Qwen3-Reranker-4B)<sup>†</sup> | 4.02B | 0.6367 |
| <u>[`mixedbread-ai/mxbai-rerank-large-v2`](https://huggingface.co/mixedbread-ai/mxbai-rerank-large-v2)</u> | <u>1.54B</u> | <u>0.6115</u> |
| **[`cross-encoder/ettin-reranker-1b-v1`](https://huggingface.co/cross-encoder/ettin-reranker-1b-v1)** | **1.00B** | **0.6114** |
| **[`cross-encoder/ettin-reranker-400m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-400m-v1)** | **401M** | **0.6091** |
| **[`cross-encoder/ettin-reranker-150m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-150m-v1)** | **151M** | **0.5994** |
| [`Qwen/Qwen3-Reranker-0.6B`](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B) | 596M | 0.5940 |
| [`mixedbread-ai/mxbai-rerank-base-v2`](https://huggingface.co/mixedbread-ai/mxbai-rerank-base-v2) | 494M | 0.5920 |
| **[`cross-encoder/ettin-reranker-68m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-68m-v1)** | **68.6M** | **0.5915** |
| [`jinaai/jina-reranker-m0`](https://huggingface.co/jinaai/jina-reranker-m0) | 2.44B | 0.5856 |
| [`Alibaba-NLP/gte-reranker-modernbert-base`](https://huggingface.co/Alibaba-NLP/gte-reranker-modernbert-base) | 150M | 0.5843 |
| **[`cross-encoder/ettin-reranker-32m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-32m-v1)** | **32.8M** | **0.5779** |
| [`ibm-granite/granite-embedding-reranker-english-r2`](https://huggingface.co/ibm-granite/granite-embedding-reranker-english-r2) | 150M | 0.5656 |
| **[`cross-encoder/ettin-reranker-17m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-17m-v1)** | **17.6M** | **0.5576** |
| [`BAAI/bge-reranker-v2-m3`](https://huggingface.co/BAAI/bge-reranker-v2-m3) | 568M | 0.5526 |
| [`zeroentropy/zerank-2-reranker`](https://huggingface.co/zeroentropy/zerank-2-reranker)<sup>†</sup> | 4.02B | 0.5300 |
| [`BAAI/bge-reranker-large`](https://huggingface.co/BAAI/bge-reranker-large) | 560M | 0.5098 |
| [`cross-encoder/ms-marco-MiniLM-L6-v2`](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2) | 22.7M | 0.5082 |
| [`cross-encoder/ms-marco-MiniLM-L12-v2`](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L12-v2) | 33.4M | 0.5066 |
| [`mixedbread-ai/mxbai-rerank-large-v1`](https://huggingface.co/mixedbread-ai/mxbai-rerank-large-v1) | 435M | 0.5063 |
| [`cross-encoder/ms-marco-MiniLM-L4-v2`](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L4-v2) | 19.2M | 0.4979 |
| [`mixedbread-ai/mxbai-rerank-xsmall-v1`](https://huggingface.co/mixedbread-ai/mxbai-rerank-xsmall-v1) | 70.8M | 0.4968 |
| [`BAAI/bge-reranker-base`](https://huggingface.co/BAAI/bge-reranker-base) | 278M | 0.4890 |
| [`mixedbread-ai/mxbai-rerank-base-v1`](https://huggingface.co/mixedbread-ai/mxbai-rerank-base-v1) | 184M | 0.4865 |

<sup>†</sup> Capped to `max_seq_length=8192` (the 4B Qwen3-based rerankers don't fit on a single H100 80GB at native context). Native-context evaluation is likely higher.

</details>

See the [release blogpost](https://huggingface.co/blog/ettin-reranker) for the full analysis and per-model commentary.

### Speed

All six released models were benchmarked against thirteen public rerankers on three hardware tiers, using [`sentence-transformers/natural-questions`](https://huggingface.co/datasets/sentence-transformers/natural-questions) at `max_length=512` with each model's best supported attention implementation. The full sweep over `fp32+SDPA`, `bf16+SDPA`, padded `bf16+FA2`, and unpadded `bf16+FA2` (showing why the ettin-reranker-v1 family is faster than other ModernBERT-based rerankers) is in the [release blogpost](https://huggingface.co/blog/ettin-reranker#speed). This table shows the throughput in pairs per second on a NVIDIA H100 80GB, all in `bfloat16`:

| Model | Params | Attn | pairs / second |
|---|---:|---|---|
| **[`cross-encoder/ettin-reranker-17m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-17m-v1)** | **17M** | FA2 | **7517** |
| **[`cross-encoder/ettin-reranker-32m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-32m-v1)** | **32M** | FA2 | **6602** |
| **[`cross-encoder/ettin-reranker-68m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-68m-v1)** | **68M** | FA2 | **4913** |
| [`cross-encoder/ms-marco-MiniLM-L4-v2`](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L4-v2) | 19M | FA2 | 4029 |
| [`cross-encoder/ms-marco-MiniLM-L6-v2`](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2) | 22M | FA2 | 3817 |
| [`cross-encoder/ms-marco-MiniLM-L12-v2`](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L12-v2) | 33M | FA2 | 3311 |
| **[`cross-encoder/ettin-reranker-150m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-150m-v1)** | **150M** | FA2 | **3237** |
| [`BAAI/bge-reranker-base`](https://huggingface.co/BAAI/bge-reranker-base) | 278M | FA2 | 2858 |
| [`mixedbread-ai/mxbai-rerank-xsmall-v1`](https://huggingface.co/mixedbread-ai/mxbai-rerank-xsmall-v1) | 70M | eager | 2636 |
| [`mixedbread-ai/mxbai-rerank-base-v1`](https://huggingface.co/mixedbread-ai/mxbai-rerank-base-v1) | 184M | eager | 1953 |
| **[`cross-encoder/ettin-reranker-400m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-400m-v1)** | **400M** | FA2 | **1738** |
| [`BAAI/bge-reranker-large`](https://huggingface.co/BAAI/bge-reranker-large) | 560M | FA2 | 1659 |
| [`BAAI/bge-reranker-v2-m3`](https://huggingface.co/BAAI/bge-reranker-v2-m3) | 568M | FA2 | 1569 |
| [`Alibaba-NLP/gte-reranker-modernbert-base`](https://huggingface.co/Alibaba-NLP/gte-reranker-modernbert-base) | 150M | FA2 | 1418 |
| [`ibm-granite/granite-embedding-reranker-english-r2`](https://huggingface.co/ibm-granite/granite-embedding-reranker-english-r2) | 150M | FA2 | 1404 |
| **[`cross-encoder/ettin-reranker-1b-v1`](https://huggingface.co/cross-encoder/ettin-reranker-1b-v1)** | **1B** | FA2 | **928** |
| [`mixedbread-ai/mxbai-rerank-large-v1`](https://huggingface.co/mixedbread-ai/mxbai-rerank-large-v1) | 435M | eager | 867 |
| [`mixedbread-ai/mxbai-rerank-base-v2`](https://huggingface.co/mixedbread-ai/mxbai-rerank-base-v2) | 494M | FA2 | 809 |
| <u>[`mixedbread-ai/mxbai-rerank-large-v2`](https://huggingface.co/mixedbread-ai/mxbai-rerank-large-v2)</u> | <u>1.5B</u> | FA2 | <u>387</u> |

<details><summary>Same benchmark on a consumer GPU (RTX 3090, 24 GB)</summary>

| Model | Params | Best attn | pairs / second |
|---|---:|---|---:|
| **[`cross-encoder/ettin-reranker-17m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-17m-v1)** | **17M** | FA2 | **9008** |
| [`cross-encoder/ms-marco-MiniLM-L4-v2`](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L4-v2) | 19M | FA2 | 5071 |
| **[`cross-encoder/ettin-reranker-32m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-32m-v1)** | **32M** | FA2 | **4497** |
| [`cross-encoder/ms-marco-MiniLM-L6-v2`](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2) | 22M | FA2 | 4234 |
| [`cross-encoder/ms-marco-MiniLM-L12-v2`](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L12-v2) | 33M | FA2 | 2847 |
| **[`cross-encoder/ettin-reranker-68m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-68m-v1)** | **68M** | FA2 | **1916** |
| [`mixedbread-ai/mxbai-rerank-xsmall-v1`](https://huggingface.co/mixedbread-ai/mxbai-rerank-xsmall-v1) | 70M | eager | 1677 |
| [`BAAI/bge-reranker-base`](https://huggingface.co/BAAI/bge-reranker-base) | 278M | FA2 | 1329 |
| **[`cross-encoder/ettin-reranker-150m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-150m-v1)** | **150M** | FA2 | **982** |
| [`mixedbread-ai/mxbai-rerank-base-v1`](https://huggingface.co/mixedbread-ai/mxbai-rerank-base-v1) | 184M | eager | 772 |
| [`ibm-granite/granite-embedding-reranker-english-r2`](https://huggingface.co/ibm-granite/granite-embedding-reranker-english-r2) | 150M | FA2 | 598 |
| [`Alibaba-NLP/gte-reranker-modernbert-base`](https://huggingface.co/Alibaba-NLP/gte-reranker-modernbert-base) | 150M | FA2 | 586 |
| [`BAAI/bge-reranker-large`](https://huggingface.co/BAAI/bge-reranker-large) | 560M | FA2 | 448 |
| [`BAAI/bge-reranker-v2-m3`](https://huggingface.co/BAAI/bge-reranker-v2-m3) | 568M | FA2 | 436 |
| **[`cross-encoder/ettin-reranker-400m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-400m-v1)** | **400M** | FA2 | **429** |
| [`mixedbread-ai/mxbai-rerank-large-v1`](https://huggingface.co/mixedbread-ai/mxbai-rerank-large-v1) | 435M | eager | 266 |
| [`mixedbread-ai/mxbai-rerank-base-v2`](https://huggingface.co/mixedbread-ai/mxbai-rerank-base-v2) | 494M | FA2 | 221 |
| **[`cross-encoder/ettin-reranker-1b-v1`](https://huggingface.co/cross-encoder/ettin-reranker-1b-v1)** | **1B** | FA2 | **189** |
| <u>[`mixedbread-ai/mxbai-rerank-large-v2`](https://huggingface.co/mixedbread-ai/mxbai-rerank-large-v2)</u> | <u>1.5B</u> | FA2 | <u>69</u> |

</details>

<details><summary>Same benchmark on CPU (Intel Core i7-13700K)</summary>

| Model | Params | Best attn | pairs / second |
|---|---:|---|---:|
| **[`cross-encoder/ettin-reranker-17m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-17m-v1)** | **17M** | SDPA | **267.4** |
| [`cross-encoder/ms-marco-MiniLM-L4-v2`](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L4-v2) | 19M | SDPA | 206.2 |
| [`cross-encoder/ms-marco-MiniLM-L6-v2`](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2) | 22M | SDPA | 143.9 |
| **[`cross-encoder/ettin-reranker-32m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-32m-v1)** | **32M** | SDPA | **92.5** |
| [`cross-encoder/ms-marco-MiniLM-L12-v2`](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L12-v2) | 33M | SDPA | 75.9 |
| [`mixedbread-ai/mxbai-rerank-xsmall-v1`](https://huggingface.co/mixedbread-ai/mxbai-rerank-xsmall-v1) | 70M | eager | 38.9 |
| **[`cross-encoder/ettin-reranker-68m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-68m-v1)** | **68M** | SDPA | **31.2** |
| [`BAAI/bge-reranker-base`](https://huggingface.co/BAAI/bge-reranker-base) | 278M | SDPA | 19.2 |
| [`Alibaba-NLP/gte-reranker-modernbert-base`](https://huggingface.co/Alibaba-NLP/gte-reranker-modernbert-base) | 150M | SDPA | 14.7 |
| [`ibm-granite/granite-embedding-reranker-english-r2`](https://huggingface.co/ibm-granite/granite-embedding-reranker-english-r2) | 150M | SDPA | 14.5 |
| **[`cross-encoder/ettin-reranker-150m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-150m-v1)** | **150M** | SDPA | **14.0** |
| [`mixedbread-ai/mxbai-rerank-base-v1`](https://huggingface.co/mixedbread-ai/mxbai-rerank-base-v1) | 184M | eager | 13.4 |
| [`BAAI/bge-reranker-large`](https://huggingface.co/BAAI/bge-reranker-large) | 560M | SDPA | 6.2 |
| [`BAAI/bge-reranker-v2-m3`](https://huggingface.co/BAAI/bge-reranker-v2-m3) | 568M | SDPA | 6.0 |
| **[`cross-encoder/ettin-reranker-400m-v1`](https://huggingface.co/cross-encoder/ettin-reranker-400m-v1)** | **400M** | SDPA | **5.2** |
| [`mixedbread-ai/mxbai-rerank-large-v1`](https://huggingface.co/mixedbread-ai/mxbai-rerank-large-v1) | 435M | eager | 4.3 |
| [`mixedbread-ai/mxbai-rerank-base-v2`](https://huggingface.co/mixedbread-ai/mxbai-rerank-base-v2) | 494M | SDPA | 3.5 |
| **[`cross-encoder/ettin-reranker-1b-v1`](https://huggingface.co/cross-encoder/ettin-reranker-1b-v1)** | **1B** | SDPA | **2.1** |

</details>


### Metrics

#### Cross Encoder Reranking

* Datasets: `NanoMSMARCO_R100`, `NanoNFCorpus_R100`, `NanoNQ_R100`, `NanoFiQA2018_R100`, `NanoTouche2020_R100`, `NanoSciFact_R100`, `NanoHotpotQA_R100`, `NanoArguAna_R100`, `NanoFEVER_R100`, `NanoDBPedia_R100`, `NanoClimateFEVER_R100`, `NanoSCIDOCS_R100` and `NanoQuoraRetrieval_R100`
* Evaluated with [<code>CrossEncoderRerankingEvaluator</code>](https://sbert.net/docs/package_reference/cross_encoder/evaluation.html#sentence_transformers.cross_encoder.evaluation.CrossEncoderRerankingEvaluator) with these parameters:
  ```json
  {
      "at_k": 10,
      "always_rerank_positives": true
  }
  ```

| Metric      | NanoMSMARCO_R100     | NanoNFCorpus_R100    | NanoNQ_R100          | NanoFiQA2018_R100    | NanoTouche2020_R100  | NanoSciFact_R100     | NanoHotpotQA_R100    | NanoArguAna_R100     | NanoFEVER_R100       | NanoDBPedia_R100     | NanoClimateFEVER_R100 | NanoSCIDOCS_R100     | NanoQuoraRetrieval_R100 |
|:------------|:---------------------|:---------------------|:---------------------|:---------------------|:---------------------|:---------------------|:---------------------|:---------------------|:---------------------|:---------------------|:----------------------|:---------------------|:------------------------|
| map         | 0.6425 (+0.1529)     | 0.3657 (+0.1047)     | 0.7484 (+0.3288)     | 0.5630 (+0.1979)     | 0.4720 (-0.0779)     | 0.7160 (+0.0463)     | 0.9307 (+0.1624)     | 0.6597 (+0.2491)     | 0.9436 (+0.1717)     | 0.6790 (+0.1671)     | 0.4903 (+0.2500)      | 0.3227 (+0.0484)     | 0.9608 (+0.1299)        |
| mrr@10      | 0.6459 (+0.1684)     | 0.5762 (+0.0764)     | 0.7678 (+0.3411)     | 0.6733 (+0.1825)     | 0.8155 (-0.0916)     | 0.7130 (+0.0350)     | 1.0000 (+0.0771)     | 0.6579 (+0.2648)     | 0.9750 (+0.1950)     | 0.8939 (+0.0932)     | 0.7496 (+0.3457)      | 0.5548 (-0.0047)     | 0.9800 (+0.1118)        |
| **ndcg@10** | **0.7243 (+0.1839)** | **0.4067 (+0.0816)** | **0.7992 (+0.2986)** | **0.6127 (+0.1753)** | **0.5518 (-0.1420)** | **0.7613 (+0.0514)** | **0.9573 (+0.1296)** | **0.7375 (+0.2486)** | **0.9600 (+0.1506)** | **0.7494 (+0.1350)** | **0.5722 (+0.2544)**  | **0.3742 (+0.0391)** | **0.9753 (+0.1067)**    |

#### Cross Encoder Nano BEIR

* Dataset: `NanoBEIR_R100_mean`
* Evaluated with [<code>CrossEncoderNanoBEIREvaluator</code>](https://sbert.net/docs/package_reference/cross_encoder/evaluation.html#sentence_transformers.cross_encoder.evaluation.CrossEncoderNanoBEIREvaluator) with these parameters:
  ```json
  {
      "dataset_names": [
          "msmarco",
          "nfcorpus",
          "nq",
          "fiqa2018",
          "touche2020",
          "scifact",
          "hotpotqa",
          "arguana",
          "fever",
          "dbpedia",
          "climatefever",
          "scidocs",
          "quoraretrieval"
      ],
      "dataset_id": "sentence-transformers/NanoBEIR-en",
      "rerank_k": 100,
      "at_k": 10,
      "always_rerank_positives": true
  }
  ```

| Metric      | Value                |
|:------------|:---------------------|
| map         | 0.6534 (+0.1486)     |
| mrr@10      | 0.7695 (+0.1381)     |
| **ndcg@10** | **0.7063 (+0.1318)** |

> [!NOTE]
> The [release blogpost](https://huggingface.co/blog/ettin-reranker) quotes a slightly higher NanoBEIR mean NDCG@10 of `0.7086` for this model, computed in `fp32` rather than the `bfloat16` used by the training-time evaluation above. Both numbers are valid.

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Dataset

#### ettin-reranker-v1-data

* Dataset: [cross-encoder/ettin-reranker-v1-data](https://huggingface.co/datasets/cross-encoder/ettin-reranker-v1-data)
* Size: 143,393,475 training samples
* Columns: <code>query</code>, <code>document</code>, and <code>label</code>
* Approximate statistics based on the first 1000 samples:
  |         | query                                                                                           | document                                                                                          | label                                                              |
  |:--------|:------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------|:-------------------------------------------------------------------|
  | type    | string                                                                                          | string                                                                                            | float                                                              |
  | details | <ul><li>min: 26 characters</li><li>mean: 55.52 characters</li><li>max: 249 characters</li></ul> | <ul><li>min: 63 characters</li><li>mean: 659.91 characters</li><li>max: 3975 characters</li></ul> | <ul><li>min: -2.94</li><li>mean: 8.51</li><li>max: 13.88</li></ul> |
* Samples:
  | query                                                                                         | document                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | label             |
  |:----------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:------------------|
  | <code>Help me with my Reborn performance</code>                                               | <code>I was reading the comment section for Dotacinema's world of dota video, and a bunch of people were complaining how there were a lot of bugs and some talked about PERFORMANCE ISSUES. But there were also people saying that reborn has actually IMPROVED their gameplay?<br><br><br>I am one of those people who is running into performance issues and would desperately like to know how some are getting BETTER performance while others like me are getting worse. I'm not complaining about bugs, I'm complaing about framerate, I use to get 60 fps solid in source 1 but I now have 40 or at worst 30 fps in source 2.<br>I have an i3 processor/gtx560ti/16gb RAM<br><br>i dont think it's a potato pc, so I dont know what's happening, I cleaned my computer recently so dust isnt affecting anything in anyway.<br>So if you gained or had IMPROVED performance in source 2 please list the settings you are enabling, so I can see where I am at fault. (v sync is off btw)<br><br>TLDR: Have bad performance now from source 2, if you have good p...</code> | <code>9.5</code>  |
  | <code>Really wanna try out the game and expansion, ~$60 is hefty. Likelihood of sales?</code> | <code>As per title, steam sells the game and its expansions for $60 total. Heavy price to drop. Are there sales on any other website? This game looks fantastic to immerse in otherwise and I'm pleased that this subreddit has at least some attention to help out new folks!</code>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | <code>9.25</code> |
  | <code>Your Avatar. [MGSV Spoilers]</code>                                                     | <code>Was anyone else suprised he actually replaces the snake model in some cutscenes. I've only tried the first Quiet cutscenes, i was just amazed I haven't seen anybody else say this yet.<br>Sorry if repost.</code>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | <code>5.25</code> |
* Loss: [<code>MSELoss</code>](https://sbert.net/docs/package_reference/cross_encoder/losses.html#mseloss) with these parameters:
  ```json
  {
      "activation_fn": "torch.nn.modules.linear.Identity"
  }
  ```

### Evaluation Dataset

#### ettin-reranker-v1-data

* Dataset: [cross-encoder/ettin-reranker-v1-data](https://huggingface.co/datasets/cross-encoder/ettin-reranker-v1-data)
* Size: 5,000 evaluation samples
* Columns: <code>query</code>, <code>document</code>, and <code>label</code>
* Approximate statistics based on the first 1000 samples:
  |         | query                                                                                           | document                                                                                        | label                                                              |
  |:--------|:------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------|:-------------------------------------------------------------------|
  | type    | string                                                                                          | string                                                                                          | float                                                              |
  | details | <ul><li>min: 14 characters</li><li>mean: 52.62 characters</li><li>max: 168 characters</li></ul> | <ul><li>min: 11 characters</li><li>mean: 50.12 characters</li><li>max: 184 characters</li></ul> | <ul><li>min: 4.44</li><li>mean: 13.49</li><li>max: 18.62</li></ul> |
* Samples:
  | query                                                             | document                                                                               | label                |
  |:------------------------------------------------------------------|:---------------------------------------------------------------------------------------|:---------------------|
  | <code>Why do we need binomial distribution?</code>                | <code>Why is the binomial distribution important?</code>                               | <code>11.375</code>  |
  | <code>I already have Windows 10, can I delete Windows.old?</code> | <code>After resetting windows 10, can I safely delete the "old windows" folder?</code> | <code>10.875</code>  |
  | <code>How can guys last longer during sex?</code>                 | <code>How do men last longer in bed?</code>                                            | <code>10.8125</code> |
* Loss: [<code>MSELoss</code>](https://sbert.net/docs/package_reference/cross_encoder/losses.html#mseloss) with these parameters:
  ```json
  {
      "activation_fn": "torch.nn.modules.linear.Identity"
  }
  ```

### Training Hyperparameters
#### Non-Default Hyperparameters

- `per_device_train_batch_size`: 3
- `num_train_epochs`: 1
- `learning_rate`: 1.5e-05
- `warmup_steps`: 0.03
- `bf16`: True
- `per_device_eval_batch_size`: 3
- `load_best_model_at_end`: True
- `seed`: 12

#### All Hyperparameters
<details><summary>Click to expand</summary>

- `per_device_train_batch_size`: 3
- `num_train_epochs`: 1
- `max_steps`: -1
- `learning_rate`: 1.5e-05
- `lr_scheduler_type`: linear
- `lr_scheduler_kwargs`: None
- `warmup_steps`: 0.03
- `optim`: adamw_torch
- `optim_args`: None
- `weight_decay`: 0.0
- `adam_beta1`: 0.9
- `adam_beta2`: 0.999
- `adam_epsilon`: 1e-08
- `optim_target_modules`: None
- `gradient_accumulation_steps`: 1
- `average_tokens_across_devices`: True
- `max_grad_norm`: 1.0
- `label_smoothing_factor`: 0.0
- `bf16`: True
- `fp16`: False
- `bf16_full_eval`: False
- `fp16_full_eval`: False
- `tf32`: None
- `gradient_checkpointing`: False
- `gradient_checkpointing_kwargs`: None
- `torch_compile`: False
- `torch_compile_backend`: None
- `torch_compile_mode`: None
- `use_liger_kernel`: False
- `liger_kernel_config`: None
- `use_cache`: False
- `neftune_noise_alpha`: None
- `torch_empty_cache_steps`: None
- `auto_find_batch_size`: False
- `log_on_each_node`: True
- `logging_nan_inf_filter`: True
- `include_num_input_tokens_seen`: no
- `log_level`: passive
- `log_level_replica`: warning
- `disable_tqdm`: False
- `project`: huggingface
- `trackio_space_id`: None
- `trackio_bucket_id`: None
- `trackio_static_space_id`: None
- `per_device_eval_batch_size`: 3
- `prediction_loss_only`: True
- `eval_on_start`: False
- `eval_do_concat_batches`: True
- `eval_use_gather_object`: False
- `eval_accumulation_steps`: None
- `include_for_metrics`: []
- `batch_eval_metrics`: False
- `save_only_model`: False
- `save_on_each_node`: False
- `enable_jit_checkpoint`: False
- `push_to_hub`: False
- `hub_private_repo`: None
- `hub_model_id`: None
- `hub_strategy`: every_save
- `hub_always_push`: False
- `hub_revision`: None
- `load_best_model_at_end`: True
- `ignore_data_skip`: False
- `restore_callback_states_from_checkpoint`: False
- `full_determinism`: False
- `seed`: 12
- `data_seed`: None
- `use_cpu`: False
- `accelerator_config`: {'split_batches': False, 'dispatch_batches': None, 'even_batches': True, 'use_seedable_sampler': True, 'non_blocking': False, 'gradient_accumulation_kwargs': None}
- `parallelism_config`: None
- `dataloader_drop_last`: True
- `dataloader_num_workers`: 0
- `dataloader_pin_memory`: True
- `dataloader_persistent_workers`: False
- `dataloader_prefetch_factor`: None
- `remove_unused_columns`: True
- `label_names`: None
- `train_sampling_strategy`: random
- `length_column_name`: length
- `ddp_find_unused_parameters`: None
- `ddp_bucket_cap_mb`: None
- `ddp_broadcast_buffers`: False
- `ddp_static_graph`: None
- `ddp_backend`: None
- `ddp_timeout`: 1800
- `fsdp`: []
- `fsdp_config`: {'min_num_params': 0, 'xla': False, 'xla_fsdp_v2': False, 'xla_fsdp_grad_ckpt': False}
- `deepspeed`: None
- `debug`: []
- `skip_memory_metrics`: True
- `do_predict`: False
- `resume_from_checkpoint`: None
- `warmup_ratio`: None
- `local_rank`: -1
- `prompts`: None
- `batch_sampler`: batch_sampler
- `multi_dataset_batch_sampler`: proportional
- `router_mapping`: {}
- `learning_rate_mapping`: {}

</details>

### Training Logs
| Epoch   | Step       | Training Loss | Validation Loss | NanoMSMARCO_R100_ndcg@10 | NanoNFCorpus_R100_ndcg@10 | NanoNQ_R100_ndcg@10  | NanoFiQA2018_R100_ndcg@10 | NanoTouche2020_R100_ndcg@10 | NanoSciFact_R100_ndcg@10 | NanoHotpotQA_R100_ndcg@10 | NanoArguAna_R100_ndcg@10 | NanoFEVER_R100_ndcg@10 | NanoDBPedia_R100_ndcg@10 | NanoClimateFEVER_R100_ndcg@10 | NanoSCIDOCS_R100_ndcg@10 | NanoQuoraRetrieval_R100_ndcg@10 | NanoBEIR_R100_mean_ndcg@10 |
|:-------:|:----------:|:-------------:|:---------------:|:------------------------:|:-------------------------:|:--------------------:|:-------------------------:|:---------------------------:|:------------------------:|:-------------------------:|:------------------------:|:----------------------:|:------------------------:|:-----------------------------:|:------------------------:|:-------------------------------:|:--------------------------:|
| -1      | -1         | -             | -               | 0.0539 (-0.4865)         | 0.2325 (-0.0925)          | 0.0386 (-0.4620)     | 0.0694 (-0.3680)          | 0.1889 (-0.5049)            | 0.0380 (-0.6719)         | 0.0553 (-0.7724)          | 0.0977 (-0.3912)         | 0.0579 (-0.7515)       | 0.1942 (-0.4202)         | 0.1156 (-0.2021)              | 0.0984 (-0.2367)         | 0.0298 (-0.8389)                | 0.0977 (-0.4768)           |
| 0.0000  | 1          | 80.2007       | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.0250  | 18672      | 3.6973        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.0500  | 37343      | -             | 0.7152          | 0.7114 (+0.1710)         | 0.4466 (+0.1216)          | 0.7887 (+0.2881)     | 0.5918 (+0.1544)          | 0.5677 (-0.1261)            | 0.7818 (+0.0719)         | 0.9502 (+0.1225)          | 0.6812 (+0.1924)         | 0.9211 (+0.1117)       | 0.7203 (+0.1059)         | 0.5429 (+0.2252)              | 0.3965 (+0.0613)         | 0.9665 (+0.0978)                | 0.6974 (+0.1229)           |
| 0.0500  | 37344      | 1.1915        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.0750  | 56016      | 1.0289        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.1000  | 74686      | -             | 0.6249          | 0.7006 (+0.1602)         | 0.4254 (+0.1003)          | 0.8031 (+0.3025)     | 0.5778 (+0.1403)          | 0.5672 (-0.1266)            | 0.7543 (+0.0444)         | 0.9452 (+0.1175)          | 0.6880 (+0.1992)         | 0.9356 (+0.1262)       | 0.7300 (+0.1156)         | 0.5544 (+0.2367)              | 0.3941 (+0.0590)         | 0.9590 (+0.0903)                | 0.6950 (+0.1204)           |
| 0.1000  | 74688      | 0.9532        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.1250  | 93360      | 0.9019        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.1500  | 112029     | -             | 0.5773          | 0.7342 (+0.1937)         | 0.4191 (+0.0940)          | 0.8085 (+0.3078)     | 0.6031 (+0.1656)          | 0.5585 (-0.1353)            | 0.7760 (+0.0661)         | 0.9560 (+0.1283)          | 0.6932 (+0.2044)         | 0.9256 (+0.1162)       | 0.7471 (+0.1327)         | 0.5626 (+0.2449)              | 0.4136 (+0.0785)         | 0.9721 (+0.1034)                | 0.7053 (+0.1308)           |
| 0.1500  | 112032     | 0.8659        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.1750  | 130704     | 0.8385        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.2000  | 149372     | -             | 0.5116          | 0.7199 (+0.1795)         | 0.4203 (+0.0952)          | 0.8069 (+0.3063)     | 0.6035 (+0.1660)          | 0.5615 (-0.1323)            | 0.7626 (+0.0527)         | 0.9547 (+0.1270)          | 0.7039 (+0.2151)         | 0.9336 (+0.1242)       | 0.7392 (+0.1248)         | 0.5489 (+0.2312)              | 0.3869 (+0.0518)         | 0.9648 (+0.0961)                | 0.7005 (+0.1260)           |
| 0.2000  | 149376     | 0.8144        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.2250  | 168048     | 0.7916        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.2500  | 186715     | -             | 0.5133          | 0.7189 (+0.1785)         | 0.4117 (+0.0867)          | 0.8097 (+0.3090)     | 0.6114 (+0.1740)          | 0.5689 (-0.1249)            | 0.7531 (+0.0432)         | 0.9564 (+0.1287)          | 0.7079 (+0.2191)         | 0.9362 (+0.1268)       | 0.7450 (+0.1306)         | 0.5496 (+0.2319)              | 0.3797 (+0.0446)         | 0.9712 (+0.1026)                | 0.7015 (+0.1270)           |
| 0.2500  | 186720     | 0.7749        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.2750  | 205392     | 0.7581        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.3000  | 224058     | -             | 0.4803          | 0.7353 (+0.1949)         | 0.4200 (+0.0950)          | 0.8052 (+0.3046)     | 0.6247 (+0.1873)          | 0.5554 (-0.1384)            | 0.7505 (+0.0406)         | 0.9575 (+0.1298)          | 0.7488 (+0.2599)         | 0.9432 (+0.1338)       | 0.7423 (+0.1279)         | 0.5628 (+0.2451)              | 0.3866 (+0.0515)         | 0.9681 (+0.0994)                | 0.7077 (+0.1332)           |
| 0.3000  | 224064     | 0.7453        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.3250  | 242736     | 0.7322        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.3500  | 261401     | -             | 0.4723          | 0.7304 (+0.1899)         | 0.4056 (+0.0806)          | 0.8163 (+0.3156)     | 0.6131 (+0.1756)          | 0.5591 (-0.1347)            | 0.7655 (+0.0556)         | 0.9565 (+0.1288)          | 0.7243 (+0.2355)         | 0.9402 (+0.1307)       | 0.7403 (+0.1259)         | 0.5710 (+0.2532)              | 0.3856 (+0.0505)         | 0.9784 (+0.1097)                | 0.7066 (+0.1321)           |
| 0.3500  | 261408     | 0.7194        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.3750  | 280080     | 0.7100        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.4000  | 298744     | -             | 0.4721          | 0.7425 (+0.2021)         | 0.4233 (+0.0982)          | 0.8043 (+0.3036)     | 0.6180 (+0.1806)          | 0.5520 (-0.1418)            | 0.7624 (+0.0525)         | 0.9543 (+0.1266)          | 0.7327 (+0.2439)         | 0.9439 (+0.1345)       | 0.7449 (+0.1305)         | 0.5753 (+0.2575)              | 0.3743 (+0.0392)         | 0.9799 (+0.1112)                | 0.7083 (+0.1337)           |
| 0.4000  | 298752     | 0.6993        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.4250  | 317424     | 0.6884        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.4500  | 336087     | -             | 0.4672          | 0.7290 (+0.1885)         | 0.4065 (+0.0814)          | 0.8180 (+0.3174)     | 0.6193 (+0.1818)          | 0.5577 (-0.1361)            | 0.7496 (+0.0397)         | 0.9541 (+0.1264)          | 0.7372 (+0.2483)         | 0.9396 (+0.1302)       | 0.7394 (+0.1251)         | 0.5767 (+0.2590)              | 0.3795 (+0.0444)         | 0.9744 (+0.1058)                | 0.7062 (+0.1317)           |
| 0.4500  | 336096     | 0.6803        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.4750  | 354768     | 0.6728        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| **0.5** | **373430** | **-**         | **0.4439**      | **0.7299 (+0.1895)**     | **0.4344 (+0.1093)**      | **0.8089 (+0.3083)** | **0.6072 (+0.1698)**      | **0.5556 (-0.1382)**        | **0.7586 (+0.0487)**     | **0.9576 (+0.1299)**      | **0.7345 (+0.2457)**     | **0.9479 (+0.1385)**   | **0.7403 (+0.1259)**     | **0.5763 (+0.2585)**          | **0.3834 (+0.0483)**     | **0.9771 (+0.1085)**            | **0.7086 (+0.1340)**       |
| 0.5000  | 373440     | 0.6645        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.5250  | 392112     | 0.6581        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.5500  | 410773     | -             | 0.4483          | 0.7301 (+0.1897)         | 0.4158 (+0.0908)          | 0.8135 (+0.3129)     | 0.6090 (+0.1716)          | 0.5470 (-0.1468)            | 0.7565 (+0.0466)         | 0.9588 (+0.1310)          | 0.7263 (+0.2375)         | 0.9521 (+0.1427)       | 0.7406 (+0.1263)         | 0.5677 (+0.2500)              | 0.3788 (+0.0437)         | 0.9842 (+0.1155)                | 0.7062 (+0.1317)           |
| 0.5500  | 410784     | 0.6520        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.5750  | 429456     | 0.6443        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.6000  | 448116     | -             | 0.4325          | 0.7250 (+0.1846)         | 0.4188 (+0.0938)          | 0.8112 (+0.3106)     | 0.6165 (+0.1791)          | 0.5513 (-0.1425)            | 0.7573 (+0.0474)         | 0.9626 (+0.1349)          | 0.7358 (+0.2470)         | 0.9521 (+0.1427)       | 0.7326 (+0.1183)         | 0.5645 (+0.2468)              | 0.3679 (+0.0328)         | 0.9764 (+0.1077)                | 0.7056 (+0.1310)           |
| 0.6000  | 448128     | 0.6397        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.6250  | 466800     | 0.6329        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.6500  | 485459     | -             | 0.4353          | 0.7331 (+0.1927)         | 0.4078 (+0.0827)          | 0.8045 (+0.3038)     | 0.6057 (+0.1683)          | 0.5525 (-0.1413)            | 0.7534 (+0.0435)         | 0.9540 (+0.1262)          | 0.7331 (+0.2443)         | 0.9546 (+0.1451)       | 0.7392 (+0.1248)         | 0.5750 (+0.2572)              | 0.3680 (+0.0329)         | 0.9790 (+0.1103)                | 0.7046 (+0.1300)           |
| 0.6500  | 485472     | 0.6294        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.6750  | 504144     | 0.6252        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.7000  | 522802     | -             | 0.4124          | 0.7238 (+0.1833)         | 0.4095 (+0.0845)          | 0.8082 (+0.3076)     | 0.6077 (+0.1703)          | 0.5545 (-0.1393)            | 0.7544 (+0.0445)         | 0.9604 (+0.1326)          | 0.7337 (+0.2449)         | 0.9505 (+0.1411)       | 0.7412 (+0.1268)         | 0.5784 (+0.2607)              | 0.3708 (+0.0357)         | 0.9734 (+0.1047)                | 0.7051 (+0.1306)           |
| 0.7000  | 522816     | 0.6185        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.7250  | 541488     | 0.6151        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.7500  | 560145     | -             | 0.4054          | 0.7264 (+0.1860)         | 0.4045 (+0.0795)          | 0.8081 (+0.3074)     | 0.6120 (+0.1746)          | 0.5503 (-0.1435)            | 0.7650 (+0.0551)         | 0.9603 (+0.1326)          | 0.7224 (+0.2336)         | 0.9572 (+0.1478)       | 0.7330 (+0.1187)         | 0.5690 (+0.2513)              | 0.3714 (+0.0363)         | 0.9760 (+0.1073)                | 0.7043 (+0.1297)           |
| 0.7500  | 560160     | 0.6109        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.7750  | 578832     | 0.6077        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.8000  | 597488     | -             | 0.3973          | 0.7206 (+0.1802)         | 0.4082 (+0.0832)          | 0.8000 (+0.2994)     | 0.6085 (+0.1711)          | 0.5477 (-0.1461)            | 0.7540 (+0.0441)         | 0.9551 (+0.1274)          | 0.7464 (+0.2576)         | 0.9567 (+0.1472)       | 0.7356 (+0.1212)         | 0.5760 (+0.2583)              | 0.3770 (+0.0418)         | 0.9814 (+0.1127)                | 0.7052 (+0.1306)           |
| 0.8000  | 597504     | 0.6042        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.8250  | 616176     | 0.5991        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.8500  | 634831     | -             | 0.3948          | 0.7159 (+0.1755)         | 0.4067 (+0.0816)          | 0.7989 (+0.2982)     | 0.6101 (+0.1726)          | 0.5469 (-0.1469)            | 0.7581 (+0.0482)         | 0.9574 (+0.1297)          | 0.7368 (+0.2480)         | 0.9523 (+0.1429)       | 0.7409 (+0.1265)         | 0.5749 (+0.2571)              | 0.3653 (+0.0302)         | 0.9787 (+0.1100)                | 0.7033 (+0.1287)           |
| 0.8500  | 634848     | 0.5962        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.8750  | 653520     | 0.5937        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.9000  | 672174     | -             | 0.3986          | 0.7181 (+0.1777)         | 0.4080 (+0.0829)          | 0.8053 (+0.3047)     | 0.6106 (+0.1732)          | 0.5596 (-0.1342)            | 0.7488 (+0.0389)         | 0.9605 (+0.1328)          | 0.7402 (+0.2514)         | 0.9600 (+0.1506)       | 0.7452 (+0.1308)         | 0.5720 (+0.2543)              | 0.3687 (+0.0335)         | 0.9758 (+0.1071)                | 0.7056 (+0.1311)           |
| 0.9000  | 672192     | 0.5905        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.9250  | 690864     | 0.5886        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.9500  | 709517     | -             | 0.3992          | 0.7285 (+0.1881)         | 0.4110 (+0.0860)          | 0.8043 (+0.3036)     | 0.6119 (+0.1744)          | 0.5564 (-0.1375)            | 0.7623 (+0.0524)         | 0.9612 (+0.1335)          | 0.7434 (+0.2546)         | 0.9567 (+0.1472)       | 0.7503 (+0.1360)         | 0.5736 (+0.2559)              | 0.3715 (+0.0363)         | 0.9758 (+0.1071)                | 0.7082 (+0.1337)           |
| 0.9500  | 709536     | 0.5856        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 0.9751  | 728208     | 0.5863        | -               | -                        | -                         | -                    | -                         | -                           | -                        | -                         | -                        | -                      | -                        | -                             | -                        | -                               | -                          |
| 1.0     | 746841     | -             | 0.3898          | 0.7243 (+0.1839)         | 0.4067 (+0.0816)          | 0.7992 (+0.2986)     | 0.6127 (+0.1753)          | 0.5518 (-0.1420)            | 0.7613 (+0.0514)         | 0.9573 (+0.1296)          | 0.7375 (+0.2486)         | 0.9600 (+0.1506)       | 0.7494 (+0.1350)         | 0.5722 (+0.2544)              | 0.3742 (+0.0391)         | 0.9753 (+0.1067)                | 0.7063 (+0.1318)           |

* The bold row denotes the saved checkpoint.

### Training Time
- **Training**: 18.5 hours
- **Evaluation**: 14.5 minutes
- **Total**: 18.7 hours

### Framework Versions
- Python: 3.11.15
- Sentence Transformers: 5.4.1
- Transformers: 5.7.0
- PyTorch: 2.7.0+cu126
- Accelerate: 1.13.0
- Datasets: 4.8.5
- Tokenizers: 0.22.2

## Citation

### BibTeX

#### Ettin Reranker Blogpost
```bibtex
@misc{aarsen2026ettin-reranker,
    title = "Introducing the Ettin Reranker Family",
    author = "Aarsen, Tom",
    year = "2026",
    publisher = "Hugging Face",
    url = "https://huggingface.co/blog/ettin-reranker",
}
```

#### Sentence Transformers
```bibtex
@inproceedings{reimers-2019-sentence-bert,
    title = "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
    author = "Reimers, Nils and Gurevych, Iryna",
    booktitle = "Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing",
    month = "11",
    year = "2019",
    publisher = "Association for Computational Linguistics",
    url = "https://arxiv.org/abs/1908.10084",
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->