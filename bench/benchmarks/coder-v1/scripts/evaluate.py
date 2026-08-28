#!/usr/bin/env python3
"""Avaliador do benchmark coder-v1 (abordagem evalplus).

Compara a saída da solução gerada com a solução canônica em cada input
(base_input = HumanEval oficial; plus_input_mini = amostra fixa do HumanEval+).

Uso:
    python3 evaluate.py <modelo> <saida_dir>
"""
import json
import os
import re
import sys

MODEL = sys.argv[1]
OUT_DIR = sys.argv[2]

data = json.load(open("benchmarks/coder-v1/data/humaneval_plus_mini_official.json"))
by_id = {t["task_id"]: t for t in data}
gens = json.load(open(f"{OUT_DIR}/humaneval_gen.json"))


def extract_code(content):
    """Extrai o bloco Python da resposta."""
    if not content:
        return ""
    m = re.search(r"```(?:python)?\s*\n(.*?)```", content, re.S)
    if m:
        return m.group(1).strip()
    # sem fence: tenta pegar a partir da assinatura da função
    return content.strip()


def load_entry(module_text, entry_point):
    """Executa o módulo e retorna a função entry_point, ou (None, erro)."""
    ns = {}
    try:
        code = compile(module_text, "<gen>", "exec")
        exec(code, ns)
    except Exception as e:
        return None, f"compile/import: {type(e).__name__}: {e}"
    if entry_point not in ns:
        return None, f"entry_point '{entry_point}' nao definido"
    return ns[entry_point], None


def call_safe(fn, args, kwargs):
    try:
        return fn(*args, **kwargs), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

def approx(a, b, atol):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= atol
    if isinstance(a, bool) and isinstance(b, bool):
        return a == b
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(approx(x, y, atol) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(approx(a[k], b[k], atol) for k in a)
    if a is None and b is None:
        return True
    try:
        return a == b
    except Exception:
        return False


def run_inputs(fn, inputs, atol, ref_fn):
    """Roda fn contra inputs; ref_fn é a solução canônica p/ o expected.
    Formato do EvalPlus: cada input é uma lista de args posicionais → fn(*inp)."""
    fail_reason = None
    for inp in inputs:
        expected, ref_err = call_safe(ref_fn, inp, {})
        if ref_err:
            return False, f"ref: {ref_err}"
        got, err = call_safe(fn, inp, {})
        if err:
            return False, err
        if not approx(got, expected, atol):
            return False, f"output mismatch: got {str(got)[:80]} != expected {str(expected)[:80]}"
    return True, None


def main():
    results = []
    for g in gens:
        task = by_id[g["task_id"]]
        solution = extract_code(g["content"])
        module_text = task["prompt"] + "\n" + solution
        ref_text = task["prompt"] + "\n" + task["canonical_solution"]

        cand, err = load_entry(module_text, task["entry_point"])
        ref, ref_err = load_entry(ref_text, task["entry_point"])

        if err or ref_err:
            results.append({
                "task_id": g["task_id"],
                "pass_base": False,
                "pass_plus": False,
                "err": err or ref_err,
            })
            continue

        ok_base, err_base = run_inputs(cand, task["base_input"], task["atol"], ref)
        ok_plus, err_plus = run_inputs(cand, task["plus_input_mini"], task["atol"], ref)

        results.append({
            "task_id": g["task_id"],
            "pass_base": ok_base,
            "pass_plus": ok_plus,
            "err": err_plus or err_base,
        })

    n_base = sum(r["pass_base"] for r in results)
    n_plus = sum(r["pass_plus"] for r in results)
    broke_plus = sum(1 for r in results if r["pass_base"] and not r["pass_plus"])

    summary = {
        "model": MODEL,
        "total": len(results),
        "pass_base": n_base,
        "pass_plus": n_plus,
        "pass_at_1_base": round(n_base / len(results), 4),
        "pass_at_1_plus": round(n_plus / len(results), 4),
        "broke_in_plus": broke_plus,
    }
    with open(f"{OUT_DIR}/eval_summary.json", "w") as f:
        json.dump(summary, f, indent=1)
    with open(f"{OUT_DIR}/eval_detail.json", "w") as f:
        json.dump(results, f, indent=1)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
