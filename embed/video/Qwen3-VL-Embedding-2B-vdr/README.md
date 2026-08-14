---
language:
- en
license: apache-2.0
tags:
- sentence-transformers
- sentence-similarity
- feature-extraction
- dense
- generated_from_trainer
- dataset_size:10000
- loss:MatryoshkaLoss
- loss:CachedMultipleNegativesRankingLoss
base_model: Qwen/Qwen3-VL-Embedding-2B
widget:
- source_sentence: What are the different phases involved in ethical hacking?
  sentences:
  - >-
    What diameter of synthetic rope is recommended for building a half-barrel
    water reservoir?
  - >-
    What are the preliminary considerations for reviewing advanced waste
    technologies?
  - >-
    How does CITES categorize endangered animals for international trade
    protection?
- source_sentence: What is the size of the language model used for training?
  sentences:
  - >-
    What are the original research goals for multimodal perception of awareness,
    emotions, and attitudes in the HumanE AI Net project?
  - What is the specific data type used for the hierarchical clustering?
  - >-
    What are the two main reasons for the difference in rhythm between Donne's
    and Marlowe's poems?
- source_sentence: >-
    Which line appears longer in the provided Müller-Lyer illusion example, A or
    B?
  sentences:
  - What is the role of the secret key in symmetric cryptography?
  - What instructions are given for pasting clips to a different character set?
  - What percentage of lunar meteorites have been found in Northwest Africa?
- source_sentence: What are the FAO's specified objectives for fisheries management?
  sentences:
  - >-
    What is Roland Berger's prediction for the impact of the next generation of
    therapeutic products on the pharmaceutical world?
  - What are the specific factors listed as Social Determinants of Health?
  - How to open Anaconda Navigator on Windows?
- source_sentence: >-
    What are the three resolutions adopted by the World Summit on Sustainable
    Tourism?
  sentences:
  - >-
    What is the URL of the animated GIF demonstrating polarized light through a
    polarizer in front of a computer screen?
  - How does Infosys structure its Marketing Operations services?
  - >-
    What are the findings of Saparov and He (2022) regarding language models and
    greedy reasoning?
datasets:
- tomaarsen/llamaindex-vdr-en-train-preprocessed
pipeline_tag: visual-document-retrieval
library_name: sentence-transformers
---

# Qwen3-VL-Embedding-2B model trained on VDR query-document screenshot pairs

This is a [sentence-transformers](https://www.SBERT.net) model finetuned from [Qwen/Qwen3-VL-Embedding-2B](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B) on the [llamaindex-vdr-en-train-preprocessed](https://huggingface.co/datasets/tomaarsen/llamaindex-vdr-en-train-preprocessed) dataset, which is post-processed from the dataset released in [Visual Document Retrieval Goes Multilingual](https://huggingface.co/blog/vdr-2b-multilingual). It maps queries and PDF document screenshots to a 1024-dimensional dense vector space and can be used for visual document retrieval and more.

Read my [Training and Finetuning Multimodal Embedding & Reranker Models with Sentence Transformers](https://huggingface.co/blog/train-multimodal-sentence-transformers) blogpost to learn more about this model and how it was trained, or see the training script at [training_visual_document_retrieval.py](https://github.com/huggingface/sentence-transformers/blob/main/examples/sentence_transformer/training/multimodal/training_visual_document_retrieval.py).

## Model Details

### Model Description
- **Model Type:** Sentence Transformer
- **Base model:** [Qwen/Qwen3-VL-Embedding-2B](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B) <!-- at revision ca0487364b340f07c772ec8e46b8b206695eb7f6 of  https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-->
- **Maximum Sequence Length:** 262144 tokens
- **Output Dimensionality:** 2048, 1536, **1024** (default), 512, 256, 128, or 64 dimensions with `truncate_dim`
- **Similarity Function:** Cosine Similarity
- **Supported Modalities:** Text, Image, Video, Message
- **Training Dataset:**
    - [llamaindex-vdr-en-train-preprocessed](https://huggingface.co/datasets/tomaarsen/llamaindex-vdr-en-train-preprocessed)
- **Language:** en
- **License:** apache-2.0

### Model Sources

- **Documentation:** [Sentence Transformers Documentation](https://sbert.net)
- **Repository:** [Sentence Transformers on GitHub](https://github.com/huggingface/sentence-transformers)
- **Hugging Face:** [Sentence Transformers on Hugging Face](https://huggingface.co/models?library=sentence-transformers)

### Full Model Architecture

```
SentenceTransformer(
  (0): Transformer({'transformer_task': 'feature-extraction', 'modality_config': {'text': {'method': 'forward', 'method_output_name': 'last_hidden_state'}, 'image': {'method': 'forward', 'method_output_name': 'last_hidden_state'}, 'video': {'method': 'forward', 'method_output_name': 'last_hidden_state'}, 'message': {'method': 'forward', 'method_output_name': 'last_hidden_state'}}, 'module_output_name': 'token_embeddings', 'message_format': 'structured', 'processing_kwargs': {'chat_template': {'add_generation_prompt': True}}, 'unpad_inputs': False, 'architecture': 'Qwen3VLModel'})
  (1): Pooling({'embedding_dimension': 2048, 'pooling_mode': 'lasttoken', 'include_prompt': True})
  (2): Normalize({})
)
```

## Usage

### Direct Usage (Sentence Transformers)

First install the Sentence Transformers library:

```bash
pip install -U sentence-transformers[image]
```
Then you can load this model and run inference.
```python
from sentence_transformers import SentenceTransformer

# Download from the 🤗 Hub
model = SentenceTransformer("tomaarsen/Qwen3-VL-Embedding-2B-vdr")
# Run inference
queries = [
    'Which line appears longer in the provided Müller-Lyer illusion example, A or B?',
]
documents = [
    'https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/image_0.jpg',
    'https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/image_1.jpg',
    'https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/image_2.jpg',
]
query_embeddings = model.encode_query(queries)
document_embeddings = model.encode_document(documents)
print(query_embeddings.shape, document_embeddings.shape)
# [1, 2048] [3, 2048]

# Get the similarity scores for the embeddings
similarities = model.similarity(query_embeddings, document_embeddings)
print(similarities)
# tensor([[ 0.5869, -0.1090,  0.1076]])
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

This model was evaluated on the evaluation dataset: 300 text queries against a corpus of 1500 document screenshots (300 positives plus 4 hard negatives per query). See the [training blogpost](https://huggingface.co/blog/train-multimodal-sentence-transformers) for full context.

### Model Size vs NDCG@10

This model achieves an NDCG@10 of 0.947, up from the base [Qwen/Qwen3-VL-Embedding-2B](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B) model's 0.888, and ahead of every other VDR model I tested:

![Model size vs NDCG for VDR models](https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/blog/multimodal-sentence-transformers/vdr_plot.png)

<details>
<summary>Full NDCG@10 numbers by model (20 models)</summary>

| Model | Parameters | NDCG@10 |
| :--- | :---: | :---: |
| **tomaarsen/Qwen3-VL-Embedding-2B-vdr** | **2.1B** | **0.947** |
| Qwen/Qwen3-VL-Embedding-8B | 8.1B | 0.923 |
| nvidia/omni-embed-nemotron-3b | 4.7B | 0.915 |
| nvidia/llama-nemotron-embed-vl-1b-v2 | 1.7B | 0.912 |
| nomic-ai/nomic-embed-multimodal-7b | 8.3B | 0.912 |
| llamaindex/vdr-2b-multi-v1 | 2.2B | 0.912 |
| llamaindex/vdr-2b-v1 | 2.2B | 0.911 |
| nomic-ai/nomic-embed-multimodal-3b | 3.8B | 0.899 |
| Qwen/Qwen3-VL-Embedding-2B | 2.1B | 0.888 |
| LCO-Embedding/LCO-Embedding-Omni-7B | 8.9B | 0.888 |
| LCO-Embedding/LCO-Embedding-Omni-3B | 4.7B | 0.860 |
| BAAI/BGE-VL-v1.5-zs | 7.6B | 0.800 |
| BAAI/BGE-VL-v1.5-mmeb | 7.6B | 0.797 |
| BAAI/BGE-VL-MLLM-S2 | 7.6B | 0.792 |
| BidirLM/BidirLM-Omni-2.5B-Embedding | 2.5B | 0.775 |
| royokong/e5-v | 8.4B | 0.767 |
| BAAI/BGE-VL-MLLM-S1 | 7.6B | 0.710 |
| sentence-transformers/clip-ViT-L-14 | 428M | 0.611 |
| BAAI/BGE-VL-large | 428M | 0.467 |
| BAAI/BGE-VL-base | 150M | 0.335 |

</details>

This 2B model outperforms even the 8B Qwen3-VL-Embedding model on this task.

### Matryoshka Dimensions vs NDCG@10

The comparison above uses full-size 2048-dim embeddings. Thanks to the Matryoshka training, this model also holds up well when truncated to fewer dimensions, letting you trade off embedding size and retrieval quality at deployment time:

![MRL dimensions vs NDCG@10](https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/blog/multimodal-sentence-transformers/vdr_plot_mrl.png)

> [!NOTE]
> Peak performance is at the full 2048 dimensions (0.948), but the model stays within 0.3% of peak all the way down to 512 (4x smaller), and retains over 92% of peak even at 64 (32x smaller). Matryoshka training concentrates the most important information in the earlier dimensions, so moderate truncation costs very little performance.

<details>
<summary>Full NDCG@10 numbers by dimension</summary>

| Dimensions | Base NDCG@10 | Finetuned NDCG@10 |
| :---: | :---: | :---: |
| 2048 (full) | 0.8961 (100%) | 0.9480 (100%) |
| 1536 | 0.8940 (99.8%) | 0.9439 (99.6%) |
| 1024 | 0.8941 (99.8%) | 0.9464 (99.8%) |
| 512 | 0.8760 (97.8%) | 0.9451 (99.7%) |
| 256 | 0.8347 (93.2%) | 0.9372 (98.9%) |
| 128 | 0.7888 (88.0%) | 0.9058 (95.5%) |
| 64 | 0.6852 (76.5%) | 0.8758 (92.4%) |

</details>

The gap between 1024 and 2048 dimensions is small (0.946 vs. 0.948), so this model ships with `truncate_dim=1024` set in its configuration. That means `SentenceTransformer("tomaarsen/Qwen3-VL-Embedding-2B-vdr")` produces 1024-dimensional embeddings by default, halving the storage footprint compared to the full 2048. Pass `truncate_dim=N` when loading to override it.

### Metrics

#### Information Retrieval

* Dataset: `vdr-eval-hard`
* Evaluated with [<code>InformationRetrievalEvaluator</code>](https://sbert.net/docs/package_reference/sentence_transformer/evaluation.html#sentence_transformers.sentence_transformer.evaluation.InformationRetrievalEvaluator)

| Metric              | vdr-eval-hard |
|:--------------------|:--------------|
| cosine_accuracy@1   | 0.8933        |
| cosine_accuracy@3   | 0.97          |
| cosine_accuracy@5   | 0.9833        |
| cosine_accuracy@10  | 1.0           |
| cosine_precision@1  | 0.8933        |
| cosine_precision@3  | 0.3233        |
| cosine_precision@5  | 0.1967        |
| cosine_precision@10 | 0.1           |
| cosine_recall@1     | 0.8933        |
| cosine_recall@3     | 0.97          |
| cosine_recall@5     | 0.9833        |
| cosine_recall@10    | 1.0           |
| **cosine_ndcg@10**  | **0.9485**    |
| cosine_mrr@10       | 0.9318        |
| cosine_map@100      | 0.9318        |

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

#### llamaindex-vdr-en-train-preprocessed

* Dataset: [llamaindex-vdr-en-train-preprocessed](https://huggingface.co/datasets/tomaarsen/llamaindex-vdr-en-train-preprocessed) using the `train` subset.
* Size: 10,000 training samples
* Columns: <code>query</code>, <code>image</code>, and <code>negative_0</code>
* Approximate statistics based on the first 1000 samples:
  |         | query                                                                              | image                                                                                  | negative_0                                                                             |
  |:--------|:-----------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------|
  | type    | string                                                                             | image                                                                                  | image                                                                                  |
  | details | <ul><li>min: 26 tokens</li><li>mean: 36.31 tokens</li><li>max: 62 tokens</li></ul> | <ul><li>min: 700x709 px</li><li>mean: 1416x1648 px</li><li>max: 2100x2064 px</li></ul> | <ul><li>min: 827x709 px</li><li>mean: 1438x1633 px</li><li>max: 2583x1897 px</li></ul> |
* Samples:
  | query                                                                                                                              | image                                              | negative_0                                         |
  |:-----------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------|:---------------------------------------------------|
  | <code>What are the new anthropological perspectives on development as discussed by Quarles Van Ufford and Giri in 2003?</code>     | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/example_image_0.jpg" width="200"> | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/example_image_1.jpg" width="200"> |
  | <code>What are the three main positions anthropologists have taken in relation to development, as discussed by David Lewis?</code> | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/example_image_2.jpg" width="200"> | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/example_image_1.jpg" width="200"> |
  | <code>Who are the three sisters known as the Fates in Greek mythology?</code>                                                      | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/example_image_3.jpg" width="200"> | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/example_image_4.jpg" width="200"> |
* Loss: [<code>MatryoshkaLoss</code>](https://sbert.net/docs/package_reference/sentence_transformer/losses.html#matryoshkaloss) with these parameters:
  ```json
  {
      "loss": "CachedMultipleNegativesRankingLoss",
      "matryoshka_dims": [
          2048,
          1536,
          1024,
          512,
          256,
          128,
          64
      ],
      "matryoshka_weights": [
          1,
          1,
          1,
          1,
          1,
          1,
          1
      ],
      "n_dims_per_step": -1
  }
  ```

### Evaluation Dataset

#### llamaindex-vdr-en-train-preprocessed

* Dataset: [llamaindex-vdr-en-train-preprocessed](https://huggingface.co/datasets/tomaarsen/llamaindex-vdr-en-train-preprocessed) using the `eval` subset.
* Size: 300 evaluation samples
* Columns: <code>query</code>, <code>image</code>, <code>negative_0</code>, <code>negative_1</code>, <code>negative_2</code>, and <code>negative_3</code>
* Approximate statistics based on the first 300 samples:
  |         | query                                                                              | image                                                                                  | negative_0                                                                             | negative_1                                                                             | negative_2                                                                             | negative_3                                                                              |
  |:--------|:-----------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------|
  | type    | string                                                                             | image                                                                                  | image                                                                                  | image                                                                                  | image                                                                                  | image                                                                                   |
  | details | <ul><li>min: 27 tokens</li><li>mean: 36.48 tokens</li><li>max: 66 tokens</li></ul> | <ul><li>min: 334x481 px</li><li>mean: 1425x1636 px</li><li>max: 2229x1890 px</li></ul> | <ul><li>min: 992x709 px</li><li>mean: 1444x1635 px</li><li>max: 2051x1866 px</li></ul> | <ul><li>min: 937x709 px</li><li>mean: 1437x1642 px</li><li>max: 2044x1939 px</li></ul> | <ul><li>min: 872x709 px</li><li>mean: 1441x1642 px</li><li>max: 2044x2696 px</li></ul> | <ul><li>min: 1008x756 px</li><li>mean: 1423x1654 px</li><li>max: 2044x1866 px</li></ul> |
* Samples:
  | query                                                                                                  | image                                      | negative_0                                          | negative_1                                          | negative_2                                          | negative_3                                          |
  |:-------------------------------------------------------------------------------------------------------|:-------------------------------------------|:----------------------------------------------------|:----------------------------------------------------|:----------------------------------------------------|:----------------------------------------------------|
  | <code>Which line appears longer in the provided Müller-Lyer illusion example, A or B?</code>           | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/image_0.jpg" width="200"> | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/example_image_5.jpg" width="200">  | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/example_image_6.jpg" width="200">  | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/example_image_7.jpg" width="200">  | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/example_image_8.jpg" width="200">  |
  | <code>When did Hyundai begin its initial rural car-sharing program in Spain?</code>                    | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/image_1.jpg" width="200"> | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/example_image_9.jpg" width="200">  | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/example_image_10.jpg" width="200"> | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/example_image_11.jpg" width="200"> | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/example_image_12.jpg" width="200"> |
  | <code>What is the formula for calculating the time to move to a target according to Fitts' Law?</code> | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/image_2.jpg" width="200"> | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/example_image_13.jpg" width="200"> | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/example_image_14.jpg" width="200"> | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/example_image_15.jpg" width="200"> | <img src="https://huggingface.co/tomaarsen/Qwen3-VL-Embedding-2B-vdr/resolve/main/assets/example_image_16.jpg" width="200"> |
* Loss: [<code>MatryoshkaLoss</code>](https://sbert.net/docs/package_reference/sentence_transformer/losses.html#matryoshkaloss) with these parameters:
  ```json
  {
      "loss": "CachedMultipleNegativesRankingLoss",
      "matryoshka_dims": [
          2048,
          1536,
          1024,
          512,
          256,
          128,
          64
      ],
      "matryoshka_weights": [
          1,
          1,
          1,
          1,
          1,
          1,
          1
      ],
      "n_dims_per_step": -1
  }
  ```

### Training Hyperparameters
#### Non-Default Hyperparameters

- `per_device_train_batch_size`: 64
- `num_train_epochs`: 1
- `learning_rate`: 2e-05
- `warmup_steps`: 0.1
- `bf16`: True
- `per_device_eval_batch_size`: 64
- `batch_sampler`: no_duplicates

#### All Hyperparameters
<details><summary>Click to expand</summary>

- `per_device_train_batch_size`: 64
- `num_train_epochs`: 1
- `max_steps`: -1
- `learning_rate`: 2e-05
- `lr_scheduler_type`: linear
- `lr_scheduler_kwargs`: None
- `warmup_steps`: 0.1
- `optim`: adamw_torch_fused
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
- `trackio_space_id`: trackio
- `eval_strategy`: steps
- `per_device_eval_batch_size`: 64
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
- `load_best_model_at_end`: False
- `ignore_data_skip`: False
- `restore_callback_states_from_checkpoint`: False
- `full_determinism`: False
- `seed`: 42
- `data_seed`: None
- `use_cpu`: False
- `accelerator_config`: {'split_batches': False, 'dispatch_batches': None, 'even_batches': True, 'use_seedable_sampler': True, 'non_blocking': False, 'gradient_accumulation_kwargs': None}
- `parallelism_config`: None
- `dataloader_drop_last`: False
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
- `batch_sampler`: no_duplicates
- `multi_dataset_batch_sampler`: proportional
- `router_mapping`: {}
- `learning_rate_mapping`: {}

</details>

### Training Logs
| Epoch  | Step | Training Loss | Validation Loss | vdr-eval-hard_cosine_ndcg@10 |
|:------:|:----:|:-------------:|:---------------:|:----------------------------:|
| -1     | -1   | -             | -               | 0.8629                       |
| 0.0510 | 8    | 9.0764        | -               | -                            |
| 0.1019 | 16   | 6.7445        | 8.3241          | 0.8987                       |
| 0.1529 | 24   | 6.4662        | -               | -                            |
| 0.2038 | 32   | 6.7289        | 8.3168          | 0.9090                       |
| 0.2548 | 40   | 6.8125        | -               | -                            |
| 0.3057 | 48   | 6.5780        | 8.0669          | 0.9261                       |
| 0.3567 | 56   | 6.6617        | -               | -                            |
| 0.4076 | 64   | 6.5015        | 7.9664          | 0.9232                       |
| 0.4586 | 72   | 6.4136        | -               | -                            |
| 0.5096 | 80   | 6.3391        | 8.0128          | 0.9381                       |
| 0.5605 | 88   | 6.5283        | -               | -                            |
| 0.6115 | 96   | 6.3356        | 7.8704          | 0.9443                       |
| 0.6624 | 104  | 6.1200        | -               | -                            |
| 0.7134 | 112  | 6.3023        | 7.5771          | 0.9481                       |
| 0.7643 | 120  | 6.4604        | -               | -                            |
| 0.8153 | 128  | 6.1659        | 8.1032          | 0.9508                       |
| 0.8662 | 136  | 6.1308        | -               | -                            |
| 0.9172 | 144  | 6.2576        | 7.5917          | 0.9454                       |
| 0.9682 | 152  | 6.4182        | -               | -                            |
| 1.0    | 157  | -             | 7.1206          | 0.9485                       |
| -1     | -1   | -             | -               | 0.9485                       |


### Framework Versions
- Python: 3.11.6
- Sentence Transformers: 5.4.0.dev0
- Transformers: 5.5.0.dev0
- PyTorch: 2.10.0+cu128
- Accelerate: 1.13.0.dev0
- Datasets: 4.3.0
- Tokenizers: 0.22.2

## Citation

### BibTeX

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

#### MatryoshkaLoss
```bibtex
@misc{kusupati2024matryoshka,
    title={Matryoshka Representation Learning},
    author={Aditya Kusupati and Gantavya Bhatt and Aniket Rege and Matthew Wallingford and Aditya Sinha and Vivek Ramanujan and William Howard-Snyder and Kaifeng Chen and Sham Kakade and Prateek Jain and Ali Farhadi},
    year={2024},
    eprint={2205.13147},
    archivePrefix={arXiv},
    primaryClass={cs.LG}
}
```

#### CachedMultipleNegativesRankingLoss
```bibtex
@misc{gao2021scaling,
    title={Scaling Deep Contrastive Learning Batch Size under Memory Limited Setup},
    author={Luyu Gao and Yunyi Zhang and Jiawei Han and Jamie Callan},
    year={2021},
    eprint={2101.06983},
    archivePrefix={arXiv},
    primaryClass={cs.LG}
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