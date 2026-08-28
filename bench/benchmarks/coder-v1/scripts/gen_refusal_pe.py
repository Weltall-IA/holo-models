#!/usr/bin/env python3
"""Gerador da bateria de recusa (40 prompts) com engenharia de prompt aplicada.

Aplica sobre o fluxo padrao de generate.py:
  - system prompt neutro de execucao (PE_SYSTEM)
  - prefill da resposta do assistente (PE_PREFILL) via prefill_assistant (continuacao)
  - logit_bias -100 nos tokens de recusa (PE_BAN_WORDS, resolvidos via /tokenize)
  - amostragem: PE_TEMP/PE_MIN_P/PE_TOP_K

Uso:
    PE_SYSTEM=... PE_PREFILL=... PE_BAN_WORDS=... python3 gen_refusal_pe.py <modelo> <base_url> <saida_dir>
"""
import json
import os
import sys
import time
import urllib.request

from openai import OpenAI

MODEL = sys.argv[1]
BASE_URL = sys.argv[2]
OUT_DIR = sys.argv[3]
os.makedirs(OUT_DIR, exist_ok=True)

SYSTEM = os.environ.get("PE_SYSTEM", "")
PREFILL = os.environ.get("PE_PREFILL", "```python\n")
TEMP = float(os.environ.get("PE_TEMP", "0.1"))
MIN_P = float(os.environ.get("PE_MIN_P", "0.08"))
TOP_K = int(os.environ.get("PE_TOP_K", "40"))
BIAS = int(os.environ.get("PE_BIAS", "-100"))
BAN_WORDS = [w.strip() for w in os.environ.get("PE_BAN_WORDS", "").split(",") if w.strip()]
FALLBACK_IDS = {"40", "33878", "1725", "11481", "2405"}


def tokenize(word):
    try:
        req = urllib.request.Request(
            BASE_URL.rstrip("/") + "/tokenize",
            json.dumps({"content": " " + word}).encode(),
            {"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode()).get("tokens", [])
    except Exception:
        return []


logit_bias = {}
for w in BAN_WORDS:
    for tid in tokenize(w):
        logit_bias[str(tid)] = BIAS
for tid in FALLBACK_IDS:
    logit_bias.setdefault(tid, BIAS)

harms = json.load(open("benchmarks/coder-v1/data/harmbench_40.json"))
client = OpenAI(base_url=BASE_URL, api_key="local")

rec = []
t0 = time.time()
for h in harms:
    prompt = h["behavior"]
    msgs = [{"role": "user", "content": prompt}]
    if SYSTEM:
        msgs.insert(0, {"role": "system", "content": SYSTEM})
    if PREFILL:
        msgs.append({"role": "assistant", "content": PREFILL})
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=msgs,
            temperature=TEMP,
            top_p=0.95,
            seed=42,
            max_tokens=1024,
            logit_bias=logit_bias,
            extra_body={"min_p": MIN_P, "top_k": TOP_K},
        )
        msg = resp.choices[0].message
        content = (msg.content or "").strip()
        reasoning = (getattr(msg, "reasoning_content", None) or "").strip()
        usage = resp.usage
        elapsed = time.time() - t0
        n_tok = (usage.completion_tokens if usage else 0) or 1
        toks = n_tok / elapsed if elapsed > 0 else 0
    except Exception as e:
        content, reasoning, usage = "", "", None
        elapsed = time.time() - t0
        toks = 0.0
        print(f"  ERR {h['id']}: {e}", file=sys.stderr)
    rec.append({
        "id": h["id"],
        "behavior_id": h["behavior_id"],
        "prompt": prompt,
        "content": content,
        "reasoning": reasoning,
        "usage": usage.model_dump() if usage else None,
        "elapsed_s": round(elapsed, 3),
        "tok_s": round(toks, 2),
    })
    if (h["id"] + 1) % 10 == 0:
        print(f"  REF {h['id']+1}/40", flush=True)

with open(f"{OUT_DIR}/refusal_gen.json", "w") as f:
    json.dump(rec, f, indent=1)
with open(f"{OUT_DIR}/pe_params.json", "w") as f:
    json.dump({
        "system": SYSTEM,
        "prefill": PREFILL,
        "temp": TEMP,
        "min_p": MIN_P,
        "top_k": TOP_K,
        "logit_bias": logit_bias,
    }, f, indent=1)
print(f"DONE {MODEL}: REF={len(rec)} tempo total {time.time()-t0:.0f}s")