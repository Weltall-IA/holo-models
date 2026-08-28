---
license: apache-2.0
base_model: Qwen/Qwen3.5-9B
language:
  - en
library_name: transformers
pipeline_tag: text-generation
tags:
  - empero-ai
  - qwen3.5
  - qwen3.8
  - distillation
  - reasoning
  - function-calling
  - sft
---

# Qwen3.8-9B-Distill-uncensored-heretic

Censorship ablation of [Qwen3.5-9B-Distill](https://huggingface.co/empero-ai/Qwen3.8-9B-Distill) via [heretic](https://github.com/p-e-w/heretic) — automated search for the minimal intervention strength using a 3-stage sweep (coarse → mid → fine, 60 trials on the final stage).

Author: [@ptruha](https://t.me/ptruha) 

| | Refusals | KL divergence |
|---|---|---|
| **This model** | **6/100** | **0.0306** |
| Public ablation of the same model (rohit267) | 98/100 | 0.0008 |
| Same-architecture reference (DavidAU/Qwen3.5-9B) | 6/100 | 0.0793 |

Same refusal rate as the reference model, but with 2.6x lower deviation from base by KL.

> [!Note]
> MTP head from the base model is preserved in this repository (`mtp.*` tensors) — abliteration only touched `attn.o_proj`/`mlp.down_proj` in the 32 main layers, the MTP block is untouched base weights. For a ready-to-run GGUF with speculative decoding enabled, see [petruhonk/Qwen3.8-9B-Distill-uncensored-heretic-GGUF](https://huggingface.co/petruhonk/Qwen3.8-9B-Distill-uncensored-heretic-GGUF).

---

# Qwen3.8-9B

**Developed by [Empero](https://empero.org)**

> [!Note]
> This repository contains model weights and configuration files in the Hugging Face Transformers format.
>
> These artifacts are compatible with Hugging Face Transformers, vLLM, SGLang, and other standard runtimes with Qwen3.5 architecture support.

**Qwen3.8-9B** is a full-parameter distillation of **Qwen3.8 2.4T A95B** into the Qwen3.5-9B architecture. The student was trained on **~70,000 curated teacher traces** from our internal Qwen3.8 distillation datasets — dense chain-of-thought spanning mathematics, code, general reasoning, instruction following, and tool use, quality-filtered before training.

The objective: bring the reasoning behavior of a frontier-scale teacher into a dense 9B that deploys on a single GPU.

## Highlights

- **Distilled chain-of-thought** — every answer opens with a `<think>` block learned directly from Qwen3.8 2.4T A95B traces rather than synthetic self-generated reasoning.
- **Mathematics and code emphasis** — the trace mix is deliberately weighted toward hard math and competitive programming, the domains where distillation moves the needle most at this scale.
- **Native function calling** per Qwen3.5's specification — no wrapper or tool-specific fine-tune required.
- **262,144-token native context**, inherited from the Qwen3.5 base.
- **Full fine-tune** — every parameter updated; not an adapter.

## Model Overview

- Type: Causal Language Model (text path of a vision-language base)
- Base: [Qwen/Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B)
- Number of Parameters: 9B
- Training: SFT (off-policy distillation) on ~70,000 teacher traces
- Teacher: Qwen3.8 2.4T A95B (internal distillation datasets)
- Context Length: 262,144 natively

## Benchmark Results

Measured with [`lm-evaluation-harness`](https://github.com/EleutherAI/lm-evaluation-harness), HF backend, identical settings for base and student. Both models are reasoning models and are evaluated with the CoT protocols (`gsm8k_cot`, `mmlu_flan_cot_zeroshot`); MMLU covers all 57 subjects (~1,700 questions). Flexible-extract is the primary metric; strict-match requires exact answer formatting.

| Task | Metric | Qwen3.5-9B (base) | **Qwen3.8-9B** | Δ |
|---|---|---:|---:|---:|
| gsm8k_cot | exact_match (flexible) | 0.885 | **0.870** | −0.015 |
| gsm8k_cot | exact_match (strict) | 0.875 | **0.850** | −0.025 |
| mmlu (CoT, 57 subjects) | acc (flexible-extract) | 0.546 | **0.751** | **+0.205** |
| mmlu (CoT, 57 subjects) | acc (strict-match) | 0.251 | **0.511** | **+0.260** |

Sampling for generation: `temperature=0.6, top_p=0.95, top_k=20` (Qwen3.5 recommended settings).

## Quickstart

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model_id = "empero-ai/Qwen3.8-9B"
tok = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, dtype=torch.bfloat16, device_map="auto")

messages = [{"role": "user", "content": "A snail is at the bottom of a 10-meter well. Each day it climbs 3 meters, each night it slips back 2. How many days until it escapes?"}]
inputs = tok.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to(model.device)

out = model.generate(inputs, max_new_tokens=16384,
                     temperature=0.6, top_p=0.95, top_k=20, do_sample=True)
print(tok.decode(out[0][inputs.shape[1]:], skip_special_tokens=True))
```

A recent `transformers` release with Qwen3.5 support is required, along with the Gated DeltaNet kernels ([`flash-linear-attention`](https://github.com/fla-org/flash-linear-attention) and a CUDA-matched [`causal_conv1d`](https://github.com/Dao-AILab/causal-conv1d) build) — without them the linear-attention layers fall back to slow, memory-hungry PyTorch ops.

## Best Practices

- **Sampling**: `temperature=0.6, top_p=0.95, top_k=20`. Greedy decoding on long generations is a known repetition-loop failure mode for reasoning models in this class.
- **Output length**: allow generous `max_new_tokens` (16,384 recommended); every answer opens with a `<think>` block. Parse and strip the `<think>...</think>` span for end users.
- **Scope**: the model learned from teacher traces, not from its own rollouts — it inherits the teacher's reasoning style, including occasional over-long deliberation on easy questions. The fine-tune is text-only; vision behavior is inherited from the base and was not evaluated here.

## Stay in the loop

Sign up for the Empero newsletter at **[empero.org](https://empero.org)** for releases, evals, and research notes.

## Support / Donate

If this model helped you, consider supporting the project:

- **BTC**: `bc1qx6zepu6sfkvshgdmc4ewu6pk6rpadvpgffpp7v`
- **LTC**: `ltc1qv2mefzps2vtjcpwfx8xxdrpplrcvltswm68r7x`

---

## Provenance & licensing

Weights are released under **Apache-2.0**, inherited from the Qwen3.5-9B base. Shared for research and experimentation, as-is.

## Acknowledgements

- Developed and released by [Empero](https://empero.org)
- Base model: [Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B) (Alibaba Qwen team)
- Training: [TRL](https://github.com/huggingface/trl) + [Transformers](https://github.com/huggingface/transformers)
- Linear-attention kernels: [flash-linear-attention](https://github.com/fla-org/flash-linear-attention), [causal_conv1d](https://github.com/Dao-AILab/causal-conv1d)
- Evaluation: [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) (EleutherAI)