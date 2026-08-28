#!/usr/bin/env python3
"""Harness de geração do benchmark coder-v1.

Gera soluções para HumanEval (164) e respostas para os 40 prompts de recusa,
chamando um servidor OpenAI-compatível local. Parâmetros padronizados entre
modelos: temperature=0.2, top_p=0.95, seed=42, max_tokens=4096, 1 tentativa.

Uso:
    python3 generate.py <modelo> <base_url> <saida_dir>
"""
import json
import os
import sys
import time
import subprocess

from openai import OpenAI


MODEL = sys.argv[1]
BASE_URL = sys.argv[2]
OUT_DIR = sys.argv[3]
os.makedirs(OUT_DIR, exist_ok=True)

# Config equivalente entre modelos: thinking OFF (nativo de cada template),
# mesma temperatura/top_p/seed/max_tokens, 1 tentativa, sem drafter.
CONFIGS = {
    "muse": {"chat_template_kwargs": {"reasoning_strength": "none"}},
    "hikari": {"chat_template_kwargs": {"enable_thinking": False}},
    "maple": {"chat_template_kwargs": {"enable_thinking": False}},
    "maple-ablit": {"chat_template_kwargs": {"enable_thinking": False}},
}
EXTRA = CONFIGS.get(MODEL, {})
EXTRA_BODY = {"chat_template_kwargs": EXTRA.get("chat_template_kwargs", {})} if EXTRA else {}

TEMP = 0.2
TOP_P = 0.95
SEED = 42
MAX_TOKENS = 2048

client = OpenAI(base_url=BASE_URL, api_key="local")


def chat(prompt, max_tokens=MAX_TOKENS):
    """Uma chamada padronizada; retorna (content, reasoning, usage, elapsed, toks)."""
    t0 = time.time()
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMP,
            top_p=TOP_P,
            seed=SEED,
            max_tokens=max_tokens,
            extra_body=EXTRA_BODY,
        )
        msg = resp.choices[0].message
        elapsed = time.time() - t0
        content = (msg.content or "").strip()
        reasoning = (getattr(msg, "reasoning_content", None) or "").strip()
        usage = resp.usage
        n_tok = (usage.completion_tokens if usage else 0) or 1
        toks = n_tok / elapsed if elapsed > 0 else 0
        return content, reasoning, usage, elapsed, toks
    except Exception as e:
        return "", "", None, time.time() - t0, 0.0


def main():
    data = json.load(open("benchmarks/coder-v1/data/humaneval_plus.json"))
    harms = json.load(open("benchmarks/coder-v1/data/harmbench_40.json"))

    he_file = f"{OUT_DIR}/humaneval_gen.json"
    skip_he = os.environ.get("REFUSAL_ONLY") == "1" and os.path.isfile(he_file)
    gens = json.load(open(he_file)) if skip_he else []
    total_toks = 0
    total_time = 0.0

    # --- HumanEval: gerações brutas ---
    if not skip_he:
        for i, task in enumerate(data):
            prompt = task["prompt"]  # prompt do HumanEval já tem o esqueleto da função
            content, reasoning, usage, elapsed, toks = chat(prompt)
            gens.append({
                "task_id": task["task_id"],
                "prompt": prompt,
                "content": content,
                "reasoning": reasoning,
                "usage": usage.model_dump() if usage else None,
                "elapsed_s": round(elapsed, 3),
                "tok_s": round(toks, 2),
            })
            if usage:
                total_toks += usage.completion_tokens
            total_time += elapsed
            if (i + 1) % 20 == 0:
                print(f"  HE {i+1}/164 | tok/s acum {total_toks/total_time:.1f}", flush=True)

        with open(he_file, "w") as f:
            json.dump(gens, f, indent=1)
    else:
        print("  HE: reutilizando humaneval_gen.json existente", flush=True)

    # --- Recusas: 40 prompts ---
    rec = []
    for h in harms:
        prompt = h["behavior"]
        content, reasoning, usage, elapsed, toks = chat(prompt, max_tokens=1024)
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

    print(f"DONE {MODEL}: HE={len(gens)} REF={len(rec)} | tempo total {total_time:.0f}s")


if __name__ == "__main__":
    main()
