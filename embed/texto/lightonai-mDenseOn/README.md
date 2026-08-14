---
tags:
- sentence-transformers
- sentence-similarity
- feature-extraction
- dense
- multilingual
- code search
- arxiv:2607.27178
pipeline_tag: sentence-similarity
library_name: sentence-transformers
license: apache-2.0
language:
- en
- fr
- de
- it
- es
- pt
- sv
- "no"
- ar
- code
base_model:
- lightonai/mDenseOn-unsupervised
base_model_relation: finetune
---

<div align="center">
<img src="https://cdn-uploads.huggingface.co/production/uploads/609bbe2f4932693ca2009d6a/D2x1Tlj0fMgn2Y9IwHlUx.png" alt="LightOn" width="512">

[![Website](https://img.shields.io/badge/LightOn-Website-blue?logo=google-chrome)](https://lighton.ai)
[![LinkedIn](https://img.shields.io/badge/LightOn-LinkedIn-0A66C2?logo=linkedin)](https://www.linkedin.com/company/lighton/)
[![X](https://img.shields.io/badge/@LightOnIO-X-black?logo=x)](https://x.com/LightOnIO)

  📚 [Collection](https://huggingface.co/collections/lightonai/mdenseon-and-mlateon) | 📝 [Multilingual Blog](https://huggingface.co/blog/lightonai/mdenseon-mlateon) | 📝 [English Blog](https://huggingface.co/blog/lightonai/denseon-lateon) | 📝 [Paper](https://arxiv.org/abs/2607.27178) 

</div>

<h1 align="center">mDenseOn</h1>

<h3 align="center">State-of-the-Art Multilingual Dense Retrieval Model by LightOn</h3>

<p align="center">
<a href="https://huggingface.co/lightonai/mDenseOn">mDenseOn</a> |
<a href="https://huggingface.co/lightonai/mLateOn">mLateOn</a> |
<a href="https://huggingface.co/lightonai/DenseOn">DenseOn</a> |
<a href="https://huggingface.co/lightonai/LateOn">LateOn</a> |
<a href="https://github.com/lightonai/pylate">PyLate</a> |
<a href="https://github.com/lightonai/fast-plaid">FastPlaid</a>
</p>

> 🎯 **TL;DR**: A 307M-parameter multilingual dense (single-vector) retrieval model achieving state-of-the-art results across **multilingual retrieval (MIRACL), long-document retrieval (MLDR), English general-domain retrieval (BEIR), and code retrieval (MTEB Code)**. Built by extending our validated open English data recipe to eight additional languages via translate-train, producing one of the largest open multilingual retrieval training sets to date (2.8B pairs).

## About the mDenseOn / mLateOn Family

With [DenseOn](https://huggingface.co/lightonai/DenseOn) and [LateOn](https://huggingface.co/lightonai/LateOn), we demonstrated that an open, carefully curated data recipe can match closed-data retrieval models on English. mDenseOn and mLateOn extend this recipe to multilingual, long-context, and code retrieval.

Rather than independently collecting multilingual corpora from scratch (which would be expensive, uneven across languages, and hard to curate at the same quality), we applied the **translate-train** approach: machine-translating our validated English data into eight target languages (French, German, Italian, Spanish, Portuguese, Swedish, Norwegian, and Arabic) and adding cross-lingual pairs for cross-lingual alignment.

For more information, please read our [multilingual models blog post](https://huggingface.co/blog/lightonai/mdenseon-mlateon), our [English models blog post](https://huggingface.co/blog/lightonai/denseon-lateon) and our [paper](https://arxiv.org/abs/2607.27178).

## mDenseOn

**mDenseOn** is a multilingual dense (single-vector) retrieval model built on mmBERT-base (307M parameters), trained by [LightOn](https://lighton.ai). It encodes queries and documents independently using cosine similarity with `query:`/`document:` prefixes and [CLS] pooling, supporting context lengths of up to **8,192 tokens**.

mDenseOn notably:
- Achieves **56.70 NDCG@10 on BEIR**, slightly surpassing the English-only DenseOn (56.20), confirming that multilingual capabilities do not come at the cost of English quality.
- Reaches **59.61 on MIRACL target languages**, competitive with similarly-sized models like EmbeddingGemma.
- Scores **64.98 on MLDR target languages**, competitive with most dense baselines
- Achieves **71.53 on MTEB Code**, the second-best sub-350M dense model, despite using only fine-tuning-stage code data and no code-specific pre-training.

Alongside mDenseOn, we also trained [mLateOn](https://huggingface.co/lightonai/mLateOn), a late-interaction variant using the same setup. mLateOn achieves substantially stronger results, especially on multilingual and long-context tasks, and generalizes to languages outside of the training set, effectively circumventing the main limitation of translate-train for dense models. If your use case permits multi-vector retrieval, we recommend mLateOn.

See our [multilingual blog post](https://huggingface.co/blog/lightonai/mdenseon-mlateon) for full results and analysis.

## Results

### Headline Results (NDCG@10)

**MIRACL<sub>tgt</sub>** and **MLDR<sub>tgt</sub>** include only the languages overlapping with our target languages; **MIRACL** and **MLDR** include all benchmark languages.

| Model | Size | BEIR | MIRACL<sub>tgt</sub> | MIRACL | MLDR<sub>tgt</sub> | MLDR | Code |
|---|---|---|---|---|---|---|---|
| **Our models** | | | | | | | |
| mLateOn | 307M | **57.56** | **65.61** | 67.04 | **87.69** | **77.92** | 73.48 |
| mDenseOn | 307M | 56.70 | 59.61 | 58.02 | 64.98 | 51.59 | 71.53 |
| **Dense baselines** | | | | | | | |
| pplx-embed-v1-0.6b | 596M | 56.70 | 63.18 | 68.20 | 57.08 | 43.98 | 75.18 |
| jina-v5-text-small | 677M | 56.70 | 61.03 | 66.56 | 53.00 | 43.83 | 73.01 |
| jina-v5-text-nano | 239M | 56.08 | 60.86 | 65.84 | 56.71 | 47.20 | 70.75 |
| arctic-embed-l-v2 | 568M | 55.55 | 60.78 | 66.53 | 57.01 | 48.03 | 53.17 |
| Qwen3-Embedding-0.6B | 596M | 55.33 | 57.64 | 60.62 | 59.11 | 50.06 | 73.75 |
| harrier-oss-v1-0.6b | 596M | 55.04 | 57.41 | 63.68 | 53.84 | 44.23 | 70.97 |
| harrier-oss-v1-270m | 268M | 50.82 | 48.95 | 57.11 | 52.31 | 42.63 | 63.79 |
| embeddinggemma-300m | 308M | 53.69 | 58.72 | 64.58 | 49.11 | 40.89 | 68.81 |
| gte-multilingual-base | 305M | 51.08 | 57.39 | 64.14 | 66.41 | 56.65 | 57.46 |
| voyage-4-nano | 340M | 49.96 | 49.29 | 58.65 | 62.10 | 51.97 | **76.43** |
| BGE-M3 | 568M | 48.78 | 62.22 | **69.62** | 61.16 | 52.47 | 51.49 |
| granite-311m-r2 | 312M | 49.24 | 53.38 | 59.74 | 50.53 | 41.86 | 63.50 |
| **Late-interaction baselines** | | | | | | | |
| pplx-embed-v1-late-0.6b | 596M | 56.11 | 63.67 | 69.55 | 68.69 | 55.51 | 63.29 |
| LFM2.5-ColBERT-350M | 353M | 54.50 | 57.40 | 42.45 | 78.39 | 61.05 | 51.62 |
| jina-colbert-v2 | 559M | 52.96 | 62.19 | 65.65 | 13.97 | 11.54 | 49.88 |
| GTE-ModernColBERT | 149M | 54.23 | 43.96 | 36.35 | 67.68 | 45.95 | 54.37 |
| ColBERT-Zero | 149M | 55.82 | 43.89 | 39.36 | 71.32 | 49.50 | 53.59 |

mDenseOn at 307M parameters is competitive with or outperforms models up to twice its size on most target-language axes. Among dense models of comparable size, it outperforms EmbeddingGemma and granite-311m-r2 on every target-language axis, and gte-multilingual-base on all but MLDR.

### Key Findings

**English quality improved**. mDenseOn reaches 56.70 on BEIR, slightly surpassing the English-only DenseOn (56.20), confirming that multilingual training need not degrade English performance.

**Strong target-language performance.** On the nine languages we translated into, mDenseOn is competitive with models trained on many more languages.

**Dense models generalize less to unseen languages.** On the full MIRACL and MLDR benchmarks (which include languages not seen during retrieval training), mDenseOn drops noticeably. This is expected for single-vector models, whose compressed representation transfers less readily to languages absent from fine-tuning. For broader language coverage without exhaustive translation, consider [mLateOn](https://huggingface.co/lightonai/mLateOn), which generalizes substantially better to unseen languages.

**Code retrieval from fine-tuning alone.** mDenseOn scores 71.53 on MTEB Code using only fine-tuning-stage code data (from LateOn-Code), with no code-specific pre-training. Adding code data at pre-training time may yield further gains.

## Related Checkpoints

| Model | Description | Link |
|:---|:---|:---|
| **mDenseOn** *(this card)* | Multilingual dense retriever (recommended for multilingual dense) | [`lightonai/mDenseOn`](https://huggingface.co/lightonai/mDenseOn) |
| mDenseOn-unsupervised | Multilingual dense, pre-training only | [`lightonai/mDenseOn-unsupervised`](https://huggingface.co/lightonai/mDenseOn-unsupervised) |
| mLateOn | Multilingual late-interaction retriever (strongest multilingual) | [`lightonai/mLateOn`](https://huggingface.co/lightonai/mLateOn) |
| mLateOn-unsupervised | Multilingual late-interaction, pre-training only | [`lightonai/mLateOn-unsupervised`](https://huggingface.co/lightonai/mLateOn-unsupervised) |
| DenseOn | English-only dense retriever | [`lightonai/DenseOn`](https://huggingface.co/lightonai/DenseOn) |
| DenseOn-unsupervised | English-only dense, pre-training only | [`lightonai/DenseOn-unsupervised`](https://huggingface.co/lightonai/DenseOn-unsupervised) |
| LateOn | English-only late-interaction retriever | [`lightonai/LateOn`](https://huggingface.co/lightonai/LateOn) |
| LateOn-unsupervised | English-only late-interaction, pre-training only | [`lightonai/LateOn-unsupervised`](https://huggingface.co/lightonai/LateOn-unsupervised) |

## Training Data

We release all datasets used to train our English and multilingual embedding models.

### Pre-training Data

* [**Multilingual pre-training curated data**](https://huggingface.co/datasets/lightonai/multilingual-embeddings-pre-training-curated) — **2.16B pairs**
* [**English pre-training curated data**](https://huggingface.co/datasets/lightonai/embeddings-pre-training-curated) — **665M pairs**

Together these form the **2.8B-pair** ready-to-train pre-training mixture. The multilingual corpus spans the eight target languages and includes a **220M-pair cross-lingual split**. The curated English corpus is built after filtering and deduplicating the raw English data. The complete **1.4B-pair** annotated parent dataset is released as [English pre-training unfiltered data](https://huggingface.co/datasets/lightonai/embeddings-pre-training).

### Fine-tuning Data

A ready-to-train fine-tuning mixture of **16.3M samples**, filtered with NV-Retriever methodology to remove false negatives: any mined candidate scoring above **95% of the positive's relevance** is discarded, and the **top 10** surviving hard negatives are kept per sample. The mixture is then annotated with the [mxbai-rerank-large-v2](https://huggingface.co/mixedbread-ai/mxbai-rerank-large-v2) cross-encoder for distillation. We release one dataset per language, plus two code splits:

* [**English**](https://huggingface.co/datasets/lightonai/embeddings-fine-tuning-filtered-en) 
* [**French**](https://huggingface.co/datasets/lightonai/embeddings-fine-tuning-filtered-fr)
* [**Spanish**](https://huggingface.co/datasets/lightonai/embeddings-fine-tuning-filtered-es)
* [**Italian**](https://huggingface.co/datasets/lightonai/embeddings-fine-tuning-filtered-it)
* [**German**](https://huggingface.co/datasets/lightonai/embeddings-fine-tuning-filtered-de)
* [**Portuguese**](https://huggingface.co/datasets/lightonai/embeddings-fine-tuning-filtered-pt)
* [**Arabic**](https://huggingface.co/datasets/lightonai/embeddings-fine-tuning-filtered-ar)
* [**Norwegian**](https://huggingface.co/datasets/lightonai/embeddings-fine-tuning-filtered-no)
* [**Swedish**](https://huggingface.co/datasets/lightonai/embeddings-fine-tuning-filtered-sv)
* [**Code**](https://huggingface.co/datasets/lightonai/embeddings-fine-tuning-filtered-code)
* [**Code Edit**](https://huggingface.co/datasets/lightonai/embeddings-fine-tuning-filtered-code-edit)

**Multilingual data.**
**MIRACL and MLDR** hard-negatives were mined directly in the available datasets with [snowflake-arctic-embed-l-v2.0](https://huggingface.co/Snowflake/snowflake-arctic-embed-l-v2.0) (**2,048 mined negatives per sample**) and the full unfiltered set is available at  [embeddings-fine-tuning-multilingual-unfiltered](https://huggingface.co/datasets/lightonai/embeddings-fine-tuning-multilingual-unfiltered). **All other splits** follow the translate-train recipe: we apply the mentioned NV-Retriever filtering to the [English fine-tuning unfiltered data](https://huggingface.co/datasets/lightonai/embeddings-fine-tuning), then machine-translate the filtered samples into the eight target languages, carrying the original relevance scores. The unfiltered English fine-tuning parent corpus contains **1.88M examples** with **2,048 mined negatives**, scored with [GTE-ModernBERT](https://huggingface.co/Alibaba-NLP/gte-modernbert-base).


**Code data.**
The **Code** dataset is derived from [LateOn-Code data](https://huggingface.co/datasets/lightonai/nv-embed-supervised-distill-dedup-code), where 2,048 negatives are mined with [GTE-ModernBERT](https://huggingface.co/Alibaba-NLP/gte-modernbert-base). The **Code Edit** dataset had no existing training set, so we built one from [CommitPackFT](https://huggingface.co/datasets/bigcode/commitpackft), decontaminated against the CodeEditSearch evaluation set by removing shared commit SHAs, exact normalized-text matches, and examples with **≥50% 13-gram containment overlap**. Hard-negatives are likewise mined with GTE-ModernBERT, and its unfiltered mined set is released alongside the multilingual data in [embeddings-fine-tuning-multilingual-unfiltered](https://huggingface.co/datasets/lightonai/embeddings-fine-tuning-multilingual-unfiltered).


For more information, please read our [multilingual blog post](https://huggingface.co/blog/lightonai/mdenseon-mlateon) and our [English blog post](https://huggingface.co/blog/lightonai/denseon-lateon).
Training scripts can be found [here](https://github.com/lightonai/mdenseon-mlateon).

## Model Details

### Model Description
- **Model Type:** Sentence Transformer
- **Base model:** [mmBERT-base](https://huggingface.co/jhu-clsp/mmBERT-base)
- **Maximum Sequence Length:** 8,192 tokens
- **Output Dimensionality:** 768 dimensions
- **Similarity Function:** Cosine Similarity
- **Pooling:** [CLS] token
- **Prompts:** `query:` for queries, `document:` for documents
- **Languages:** English, French, German, Italian, Spanish, Portuguese, Swedish, Norwegian, Arabic
- **License:** Apache 2.0

### Model Sources

- **Documentation:** [Sentence Transformers Documentation](https://sbert.net)
- **Repository:** [Sentence Transformers on GitHub](https://github.com/UKPLab/sentence-transformers)
- **Hugging Face:** [Sentence Transformers on Hugging Face](https://huggingface.co/models?library=sentence-transformers)

### Full Model Architecture

```
SentenceTransformer(
  (0): Transformer({'max_seq_length': 8192, 'do_lower_case': False, 'architecture': 'ModernBertModel'})
  (1): Pooling({'word_embedding_dimension': 768, 'pooling_mode_cls_token': True, 'pooling_mode_mean_tokens': False, 'pooling_mode_max_tokens': False, 'pooling_mode_mean_sqrt_len_tokens': False, 'pooling_mode_weightedmean_tokens': False, 'pooling_mode_lasttoken': False, 'include_prompt': True})
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
from sentence_transformers import SentenceTransformer

# Download from the Hub
model = SentenceTransformer("lightonai/mDenseOn")

# Run inference with multilingual queries and documents
queries = [
    "Quelle planète est connue comme la planète rouge ?",
    "Which planet is known as the Red Planet?",
]
documents = [
    "Venus wird oft als Zwilling der Erde bezeichnet wegen ihrer ähnlichen Größe.",
    "Mars, connu pour son apparence rougeâtre, est souvent appelé la planète rouge.",
    "Marte, conocido por su apariencia rojiza, es a menudo llamado el Planeta Rojo.",
    "Mars, known for its reddish appearance, is often referred to as the Red Planet.",
]

query_embeddings = model.encode(queries, prompt_name="query")
document_embeddings = model.encode(documents, prompt_name="document")
print(query_embeddings.shape, document_embeddings.shape)
# [2, 768] [4, 768]

# Get the similarity scores for the embeddings
similarities = model.similarity(query_embeddings, document_embeddings)
print(similarities)
```

### Framework Versions
- Python: 3.11.10
- Sentence Transformers: 5.1.1
- Transformers: 4.57.5
- PyTorch: 2.9.0+cu128
- Accelerate: 1.12.0
- Datasets: 3.6.0
- Tokenizers: 0.22.1

## Citation

### BibTeX

#### mDenseOn and mLateOn

```bibtex
@misc{sourty2026denseonlateonfullyopen,
  title         = {DenseOn with the LateOn: Fully Open Dense and Late-Interaction Models for Multilingual, Long-Context, and Code Search},
  author        = {Raphaël Sourty and Antoine Chaffin and Paulo Roberto Moura Junior and Amélie Chatelain},
  year          = {2026},
  eprint        = {2607.27178},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CL},
  url           = {https://arxiv.org/abs/2607.27178},
}
```

#### DenseOn and LateOn
```bibtex
@misc{sourty2026denseonlateon,
  title={DenseOn with the LateOn: Open State-of-the-Art Single and Multi-Vector Models},
  author={Sourty, Raphael and Chaffin, Antoine and Weller, Orion and Moura Junior, Paulo Roberto and Chatelain, Amelie},
  year={2026},
  howpublished={\url{https://huggingface.co/blog/lightonai/denseon-lateon}},
}
```

#### PyLate

```bibtex
@inproceedings{DBLP:conf/cikm/ChaffinS25,
  author       = {Antoine Chaffin and
                  Rapha{\"{e}}l Sourty},
  editor       = {Meeyoung Cha and
                  Chanyoung Park and
                  Noseong Park and
                  Carl Yang and
                  Senjuti Basu Roy and
                  Jessie Li and
                  Jaap Kamps and
                  Kijung Shin and
                  Bryan Hooi and
                  Lifang He},
  title        = {PyLate: Flexible Training and Retrieval for Late Interaction Models},
  booktitle    = {Proceedings of the 34th {ACM} International Conference on Information
                  and Knowledge Management, {CIKM} 2025, Seoul, Republic of Korea, November
                  10-14, 2025},
  pages        = {6334--6339},
  publisher    = {{ACM}},
  year         = {2025},
  url          = {https://github.com/lightonai/pylate},
  doi          = {10.1145/3746252.3761608},
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
    url = "https://arxiv.org/abs/1908.10084"
}
```

## Acknowledgements

We thank Eugene Yang for his feedback on adapting our English study to multilinguality through translate-train. We again thank Xin Zhang, Zach Nussbaum, Tom Aarsen, Bo Wang, Eugene Yang, Benjamin Clavié, Nandan Thakur, Oskar Hallström and Iacopo Poli for their valuable contributions and feedback on the original English study. We thank Orion Weller for building the FineWeb-derived Common Crawl split as well as for his feedback and help. We are grateful to the teams behind Sentence Transformers, BEIR, and MIRACL, and to the open-source retrieval community, in particular the authors of Nomic Embed.

This work was granted access to the HPC resources of [IDRIS](http://www.idris.fr/) under [GENCI](http://www.genci.fr/) allocations AS011016449, A0181016214, and A0171015706 (Jean Zay supercomputer). We also acknowledge the [Barcelona Supercomputing Center (BSC-CNS)](https://www.bsc.es/) for providing access to MareNostrum 5 under EuroHPC AI Factory Fast Lane project EHPC-AIF-2025FL01-445. This project is also supported by the OpenEuroLLM project, co-funded by the Digital Europe Programme under GA no. 101195233.