---
license: other
license_name: nvidia-open-model-license
license_link: >-
  https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/
tags:
  - text
  - reranker
  - cross-encoder
  - retrieval
  - semantic-search
pipeline_tag: text-ranking
language:
  - multilingual
library_name: transformers
---

## **Model Overview**

### **Description**

The Llama Nemotron Reranking 1B model is optimized for providing a logit score that represents how relevant a document(s) is to a given query. The model was fine-tuned for **multilingual, cross-lingual** text question-answering retrieval, with support for **long documents (up to 8192 tokens)**.  This model was evaluated on 26 languages: English, Arabic, Bengali, Chinese, Czech, Danish, Dutch, Finnish, French, German, Hebrew, Hindi, Hungarian, Indonesian, Italian, Japanese, Korean, Norwegian, Persian, Polish, Portuguese, Russian, Spanish, Swedish, Thai, and Turkish.


This model is a component in a text retrieval system to improve the overall accuracy. A text retrieval system often uses an embedding model (dense) or lexical search (sparse) index to return relevant text passages given the input. A reranking model can be used to rerank the potential candidate into a final order. The reranking model has the question-passage pairs as an input and therefore, can process cross attention between the words. It’s not feasible to apply a Ranking model on all documents in the knowledge base, therefore, ranking models are often deployed in combination with embedding models.


This model is ready for commercial use.


The Llama Nemotron Reranking 1B model is a part of the NeMo Retriever collection of NIM, which provide state-of-the-art, commercially-ready models and microservices, optimized for the lowest latency and highest throughput. It features a production-ready information retrieval pipeline with enterprise support. The models that form the core of this solution have been trained using responsibly selected, auditable data sources. With multiple pre-trained models available as starting points, developers can also readily customize them for their domain-specific use cases, such as information technology, human resource help assistants, and research & development research assistants.

We are excited to announce the open sourcing of this commercial embedding model. For users interested in deploying this model in production environments, it is also available via the model API in NVIDIA Inference Microservices (NIM) at [llama-nemotron-rerank-1b-v2](https://build.nvidia.com/nvidia/llama-3_2-nv-rerankqa-1b-v2).

### **License/Terms of use**

Use of this model is governed by the [NVIDIA Open Model License Agreement](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/). Additional Information: [Llama 3.2 Community Model License Agreement](https://www.llama.com/llama3_2/license/).

### **Intended use**

The Llama Nemotron Reranking 1B model is most suitable for users who want to improve their multilingual retrieval tasks by reranking a set of candidates for a given question.

### **Model Architecture**

**Architecture Type:** Transformer <br>
**Network Architecture:** Fine-tuned ranker model from the `meta-llama/Llama-3.2-1B` model.

The Llama Nemotron Reranking 1B model is a transformer cross-encoder fine-tuned with contrastive learning. We employ bi-directional attention when fine-tuning for higher accuracy. The last embedding output by the decoder model is used with a mean pooling strategy, and a binary classification head is fine-tuned for the ranking task.

Ranking models for text ranking are typically trained as a cross-encoder for sentence classification. This involves predicting the relevancy of a sentence pair (for example, question and chunked passages). The CrossEntropy loss is used to maximize the likelihood of passages containing information to answer the question and minimize the likelihood for (negative) passages that do not contain information to answer the question.

We trained the model on public datasets described in the Dataset and Training section.

### **Input**

**Input Type:** Pair of Texts <br>
**Input Format:** List of text pairs <br>
**Input Parameters:** 1D <br>
**Other Properties Related to Input:** The model was trained on question and answering over text documents from multiple languages. It was evaluated to work successfully with up to a sequence length of 8192 tokens. Longer texts are recommended to be either chunked or truncated.

### **Output**

**Output Type:** Floats <br>
**Output Format:** List of floats <br>
**Output Parameters:** 1D <br>
**Other Properties Related to Output:** Each value corresponds to a raw logit. Users can choose to apply a Sigmoid activation function to the logits to convert them into probabilities during model usage.

### **Installation**

The model requires transformers version 4.44 or above.

```bash
pip install transformers>=4.44
```

### **Usage**
```python
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

model_name_or_path = "nvidia/llama-nemotron-rerank-1b-v2"

device = "cuda:0"
max_length = 512

queries = [
    "how much protein should a female eat?",
]
documents = [
    "As a general guideline, the CDC's average requirement of protein for women ages 19 to 70 is 46 grams per day. But, as you can see from this chart, you'll need to increase that if you're expecting or training for a marathon. Check out the chart below to see how much protein you should be eating each day.",
    "Definition of summit for English Language Learners. : 1  the highest point of a mountain : the top of a mountain. : 2  the highest level. : 3  a meeting or series of meetings between the leaders of two or more governments.",
    "Calorie intake should not fall below 1,200 a day in women or 1,500 a day in men, except under the supervision of a health professional."
]

# Create pairs from queries and documents
pairs = [[q, d] for q in queries for d in documents]

def prompt_template(q, p):
    """Format query and passage with a prompt template."""
    return f"question:{q} \n \n passage:{p}"


tokenizer = AutoTokenizer.from_pretrained(
    model_name_or_path,
    trust_remote_code=True,
    padding_side="left"
)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model_kwargs = {
    "trust_remote_code": True,
    "torch_dtype": torch.bfloat16,
}

print(f"Loading model from {model_name_or_path}...")
model = AutoModelForSequenceClassification.from_pretrained(
    model_name_or_path,
    **model_kwargs
).eval()

if model.config.pad_token_id is None:
    model.config.pad_token_id = tokenizer.eos_token_id

model = model.to(device)


# Apply prompt template and tokenize as single sequence
texts = [prompt_template(query, doc) for query, doc in pairs]
batch_dict = tokenizer(
    texts,
    padding=True,
    truncation=True,
    return_tensors="pt",
    max_length=max_length,
)

# Move to device
batch_dict = {k: v.to(device) for k, v in batch_dict.items()}

with torch.inference_mode():
    logits = model(**batch_dict).logits
    scores = logits.view(-1).cpu().tolist()

for i, (pair, score) in enumerate(zip(pairs, scores)):
    query, doc = pair
    print(f"  Query: {query}")
    print(f"  Document: {doc[:100]}{'...' if len(doc) > 100 else ''}")
    print(f"  Score: {score:.4f}")

#   Query: how much protein should a female eat?
#   Document: As a general guideline, the CDC's average requirement of protein for women ages 19 to 70 is 46 grams...
#   Score: 20.6250
#   Query: how much protein should a female eat?
#   Document: Definition of summit for English Language Learners. : 1  the highest point of a mountain : the top o...
#   Score: -23.1250
#   Query: how much protein should a female eat?
#   Document: Calorie intake should not fall below 1,200 a day in women or 1,500 a day in men, except under the su...
#   Score: -0.2617
```

#### vLLM Usage

1. Ensure you are using `vllm>=0.14.0`.
2. A score template **must** be provided via `--chat-template` to correctly format
   query-document pairs. Without it, the `question:... passage:...` prompt format
   is not applied and results will be incorrect.

Create the score template file and start the server:
```bash
python3 -c "
t = (
    'question:{{ (messages | selectattr(\"role\", \"eq\", \"query\") | first).content }}'
    ' \n \n '
    'passage:{{ (messages | selectattr(\"role\", \"eq\", \"document\") | first).content }}'
)
open('nemotron-rerank.jinja', 'w').write(t)
"

vllm serve nvidia/llama-nemotron-rerank-1b-v2 \
    --trust-remote-code \
    --chat-template nemotron-rerank.jinja
```

If you already have a local copy of the model, you can also pass the local
path instead of the HF repo ID.

Optional flags:

- `--dtype <float32|bfloat16|float16>` to force precision (the default is `auto`, which resolves from model config; this model defaults to BF16).
- `--data-parallel-size <num_gpus_to_use>` for multi-GPU serving.
- `--port 8000` to set the server port.

Online serving example (`/rerank` API):

```python
import requests

query = "What is machine learning?"
documents = [
    "Machine learning is a branch of AI that learns patterns from data.",
    "Python is a programming language commonly used for data science.",
    "Neural networks are one family of machine learning models.",
    "Bananas are a good source of potassium.",
]

response = requests.post(
    "http://localhost:8000/rerank",
    json={
        "model": "nvidia/llama-nemotron-rerank-1b-v2",
        "query": query,
        "documents": documents,
        "top_n": 3,
    },
    timeout=30,
)
response.raise_for_status()
for item in response.json()["results"]:
    print(item["index"], item["relevance_score"])
```

Offline inference example (Python API, no server required):

```python
from vllm import LLM

SCORE_TEMPLATE = (
    "question:{{ (messages | selectattr(\"role\", \"eq\", \"query\") | first).content }}"
    " \n \n "
    "passage:{{ (messages | selectattr(\"role\", \"eq\", \"document\") | first).content }}"
)

llm = LLM(
    model="nvidia/llama-nemotron-rerank-1b-v2",
    runner="pooling",
    trust_remote_code=True,
)

query = "What is machine learning?"
documents = [
    "Machine learning is a branch of AI that learns patterns from data.",
    "Python is a programming language commonly used for data science.",
    "Neural networks are one family of machine learning models.",
    "Bananas are a good source of potassium.",
]

outputs = llm.score(query, documents, chat_template=SCORE_TEMPLATE)
for document, output in zip(documents, outputs):
    print(document[:80], output.outputs.score)
```

### **Software Integration**

**Runtime:** Llama Nemotron Reranking 1B NIM <br>
**Supported Hardware Microarchitecture Compatibility**: NVIDIA Ampere, NVIDIA Hopper, NVIDIA Lovelace <br>
**Supported Operating System(s):** Linux

### **Model Version(s)**

Llama Nemotron Reranking 1B <br>
Short Name: llama-nemotron-rerank-1b-v2

## **Training Dataset & Evaluation**

### **Training Dataset**

The development of large-scale public open-QA datasets has enabled tremendous progress in powerful embedding models. However, one popular dataset named [MSMARCO](https://microsoft.github.io/msmarco/) restricts ‌commercial licensing, limiting the use of these models in commercial settings. To address this, NVIDIA created its own training dataset blend based on public QA datasets, which each have a license for commercial applications.

**Data Collection Method by dataset**: Automated, Unknown <br>

**Labeling Method by dataset:** Automated, Unknown <br>

**Properties:** This model was trained on 800k samples from public datasets.

### **Evaluation Results**

We evaluate the pipelines on a set of evaluation benchmarks. We applied the ranking model to the candidates retrieved from a retrieval embedding model.

Overall, the pipeline llama-nemotron-embed-1b-v2 + llama-nemotron-rerank-1b-v2 provides high BEIR+TechQA accuracy with multilingual and crosslingual support. The llama-nemotron-embed-1b-v2 ranking model is 3.5x smaller than the nv-rerankqa-mistral-4b-v3 model.

We evaluated the NVIDIA Retrieval QA Embedding Model in comparison to literature open & commercial retriever models on academic benchmarks for question-answering \- [NQ](https://huggingface.co/datasets/BeIR/nq), [HotpotQA](https://huggingface.co/datasets/hotpot_qa) and [FiQA (Finance Q\&A)](https://huggingface.co/datasets/BeIR/fiqa) from BeIR benchmark and TechQA dataset. In this benchmark, the metric used was Recall@5. As described, we need to apply the ranking model on the output of an embedding model.

| Open & Commercial Reranker Models | Average Recall@5 on NQ, HotpotQA, FiQA, TechQA dataset |
| ----- | ----- |
| llama-nemotron-embed-1b-v2 + llama-nemotron-rerank-1b-v2 | 73.64% |
| llama-nemotron-embed-1b-v2 | 68.60% |
| nv-embedqa-e5-v5 \+ nv-rerankQA-mistral-4b-v3 | 75.45% |
| nv-embedqa-e5-v5 | 62.07% |
| nv-embedqa-e5-v4 | 57.65% |
| e5-large\_unsupervised | 48.03% |
| BM25 | 44.67% |

We evaluated the model’s multilingual capabilities on the [MIRACL](https://github.com/project-miracl/miracl) academic benchmark \- a multilingual retrieval dataset, across 15 languages, and on an additional 11 languages that were translated from the English and Spanish versions of MIRACL. The reported scores are based on a custom subsampled version by selecting hard negatives for each query to reduce the corpus size.

| Open & Commercial Retrieval Models | Average Recall@5 on MIRACL multilingual datasets |
| :---- | :---- |
| llama-nemotron-embed-1b-v2 + llama-nemotron-rerank-1b-v2 | 65.80% |
| llama-nemotron-embed-1b-v2 | 60.75% |
| nv-embedqa-mistral-7b-v2 | 50.42% |
| BM25 | 26.51% |

We evaluated the cross-lingual capabilities on the academic benchmark [MLQA](https://github.com/facebookresearch/MLQA/) based on 7 languages (Arabic, Chinese, English, German, Hindi, Spanish, Vietnamese). We consider only evaluation datasets when the query and documents are in different languages. We calculate the average Recall@5 across the 42 different language pairs.

| Open & Commercial Retrieval Models | Average Recall@5 on MLQA dataset with different languages |
| :---- | :---- |
| llama-nemotron-embed-1b-v2 + llama-nemotron-rerank-1b-v2 | 86.83% |
| llama-nemotron-embed-1b-v2 | 79.86% |
| nv-embedqa-mistral-7b-v2 | 68.38% |
| BM25 | 13.01% |

We evaluated the support of long documents on the academic benchmark [Multilingual Long-Document Retrieval (MLDR)](https://huggingface.co/datasets/Shitao/MLDR) built on Wikipedia and mC4, covering 12 typologically diverse languages . The English version has a median length of 2399 tokens and 90th percentile of 7483 tokens using the llama 3.2 tokenizer.

| Open & Commercial Retrieval Models | Average Recall@5 on MLDR |
| :---- | :---- |
| llama-nemotron-embed-1b-v2 + llama-nemotron-rerank-1b-v2 | 70.69% |
| llama-nemotron-embed-1b-v2 | 59.55% |
| nv-embedqa-mistral-7b-v2 | 43.24% |
| BM25 | 71.39% |

**Data Collection Method by dataset**:
Unknown

**Labeling Method by dataset:**
Unknown

**Properties**
The evaluation datasets are based on three [MTEB/BEIR](https://github.com/beir-cellar/beir) TextQA datasets, the TechQA dataset, MIRACL, MLDR and MLQA multilingual retrieval datasets, which are all public datasets. The sizes range between 10,000s up to 5M depending on the dataset.

**Inference**
**Engine:** TensorRT <br>
**Test Hardware:**  H100 PCIe/SXM, A100 PCIe/SXM, L40s, L4, and A10G

## **Ethical Considerations**

NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their supporting model team to ensure this model meets requirements for the relevant industry and use case and addresses unforeseen product misuse.

For more detailed information on ethical considerations for this model, please see the Explainability, Bias, Safety, and Privacy sections.

Please report security vulnerabilities or NVIDIA AI Concerns [here](https://www.nvidia.com/en-us/support/submit-security-vulnerability/).

## Get Help

### Enterprise Support
Get access to knowledge base articles and support cases or  submit a ticket at the [NVIDIA AI Enterprise Support Services page.](https://www.nvidia.com/en-us/data-center/products/ai-enterprise-suite/support/).

### NVIDIA NIM Documentation
Visit the [NeMo Retriever docs page](https://docs.nvidia.com/nemo/retriever/index.html) for release documentation, deployment guides and more.

## Bias

| Field | Response |
| ----- | ----- |
| Participation considerations from adversely impacted groups [protected classes](https://www.senate.ca.gov/content/protected-classes) in model design and testing | None |
| Measures taken to mitigate against unwanted bias | None |


## Explainability

| Field | Response |
| ----- | ----- |
| Intended Application & Domain: | Passage ranking for question and answer retrieval |
| Model Type: | Transformer encoder |
| Intended User: | Generative AI creators working with conversational AI models - users who want to build a multilingual question and answer application over a large text corpus, leveraging the latest dense retrieval technologies. |
| Output: | Array of float numbers (Dense Vector Representation for the input text) |
| Describe how the model works: | Model transforms the tokenized input text into a dense vector representation. |
| Performance Metrics: | Accuracy, Throughput, and Latency |
| Potential Known Risks: | This model does not always guarantee to retrieve the correct passage(s) for a given query. |
| Licensing & Terms of Use: | Use of this model is governed by the [NVIDIA Open Model License Agreement](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/). Additional Information: [Llama 3.2 Community Model License Agreement](https://www.llama.com/llama3_2/license/). |
| Technical Limitations | The model’s max sequence length is 8192. Therefore, the longer text inputs should be truncated.   |
| Name the adversely impacted groups this has been tested to deliver comparable outcomes regardless of: | N/A |
| Verified to have met prescribed NVIDIA quality standards: | Yes |

## Privacy

| Field | Response |
| ----- | ----- |
| Generatable or reverse engineerable personally-identifiable information (PII)? | None |
| Was consent obtained for any personal data used? | Not Applicable |
| PII used to create this model? | None |
| How often is the dataset reviewed? | Before Every Release |
| Is a mechanism in place to honor data subject right of access or deletion of personal data? | No |
| If personal data was collected for the development of the model, was it collected directly by NVIDIA? | Not Applicable |
| If personal data was  collected for the development of the model by NVIDIA, do you maintain or have access to disclosures made to data subjects? | Not Applicable |
| If personal data was collected for the development of this AI model, was it minimized to only what was required? | Not Applicable |
| Is there provenance for all datasets used in training? | Yes |
| Does data labeling (annotation, metadata) comply with privacy laws? | Yes |
| Is data compliant with data subject requests for data correction or removal, if such a request was made? | No, not possible with externally-sourced data. |


## Safety

| Field | Response |
| ----- | ----- |
| Model Application(s): | Text Reranking for Retrieval |
| Describe the physical safety impact (if present). | Not Applicable |
| Use Case Restrictions: | Use of this model is governed by the [NVIDIA Open Model License Agreement](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/). Additional Information: [Llama 3.2 Community Model License Agreement](https://www.llama.com/llama3_2/license/).  |
| Model and dataset restrictions: | The Principle of least privilege (PoLP) is applied limiting access for dataset generation and model development. Restrictions enforce dataset access during training, and dataset license constraints adhered to. |
