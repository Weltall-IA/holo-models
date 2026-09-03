#!/usr/bin/env python3
import json
import os
import re
import statistics
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys_path_evaluate = HERE / "evaluate.py"

from evaluate import evaluate_case

MODELS_FILE = HERE / "models.json"
PROMPTS_FILE = HERE / "prompts.json"
RESULTS_DIR = HERE / "results"
RAW_FILE = RESULTS_DIR / "RAW_RESULTS.jsonl"
SUMMARY_FILE = RESULTS_DIR / "SUMMARY.md"

MODELS = json.loads(MODELS_FILE.read_text(encoding="utf-8"))
PROMPTS = json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))

LLAMA_BIN = Path.home() / ".local/bin/llama"
PORT = 8197

SEED = 9137
TEMP = 0.2
TOP_P = 0.95
CTX = 8192
THREADS = 8


def vram_mib():
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            text=True,
            timeout=5,
        )
        return int(out.strip().splitlines()[0])
    except Exception:
        return None


def wait_health(timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2) as r:
                data = json.loads(r.read().decode())
                if data.get("status") == "ok":
                    return
        except Exception:
            time.sleep(1)
    raise RuntimeError("llama server did not become healthy")


def post_stream(payload):
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    first_token = None
    content_parts = []
    usage = {}
    timings = {}
    finish_reason = None
    peak = vram_mib()
    stop = threading.Event()

    def sampler():
        nonlocal peak
        while not stop.wait(0.1):
            v = vram_mib()
            if v is not None and (peak is None or v > peak):
                peak = v

    th = threading.Thread(target=sampler, daemon=True)
    th.start()

    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            for line_bytes in resp:
                line = line_bytes.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                item = line[5:].strip()
                if item == "[DONE]":
                    break
                try:
                    chunk = json.loads(item)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                if choices:
                    c0 = choices[0]
                    if c0.get("finish_reason"):
                        finish_reason = c0.get("finish_reason")
                    delta = c0.get("delta") or {}
                    c = delta.get("content") or ""
                    if c:
                        if first_token is None:
                            first_token = time.perf_counter()
                        content_parts.append(c)
                if chunk.get("usage"):
                    usage = chunk["usage"]
                if chunk.get("timings"):
                    timings = chunk["timings"]
    finally:
        stop.set()
        th.join(timeout=2)
    ended = time.perf_counter()

    return {
        "text": "".join(content_parts).strip(),
        "finish_reason": finish_reason,
        "usage": usage,
        "timings": timings,
        "wall_time_s": round(ended - started, 4),
        "ttft_s": None if first_token is None else round(first_token - started, 4),
        "peak_vram_mib": peak,
    }


def warmup():
    payload = {
        "messages": [{"role": "user", "content": "Write a one-line Python comment."}],
        "max_tokens": 16,
        "temperature": 0.2,
        "stream": True,
    }
    post_stream(payload)


def generate_solution(case: dict):
    payload = {
        "messages": [{"role": "user", "content": case["prompt"]}],
        "temperature": TEMP,
        "top_p": TOP_P,
        "seed": SEED,
        "max_tokens": case["max_tokens"],
        "stream": True,
    }
    res = post_stream(payload)
    eval_res = evaluate_case(case["id"], res["text"])
    timings = res.get("timings", {})
    usage = res.get("usage", {})

    return {
        "case_id": case["id"],
        "case_name": case["name"],
        "language": case["language"],
        "difficulty": case["difficulty"],
        "seed": SEED,
        "temperature": TEMP,
        "top_p": TOP_P,
        "max_tokens": case["max_tokens"],
        "raw_text": res["text"],
        "extracted_code": eval_res["extracted_code"],
        "compile_pass": eval_res["compile_pass"],
        "public_pass": eval_res["public_pass"],
        "hidden_pass": eval_res["hidden_pass"],
        "passed": eval_res["passed"],
        "eval_error": eval_res.get("error"),
        "finish_reason": res["finish_reason"],
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "predicted_per_second": timings.get("predicted_per_second"),
        "prompt_per_second": timings.get("prompt_per_second"),
        "prompt_ms": timings.get("prompt_ms"),
        "wall_time_s": res["wall_time_s"],
        "ttft_s": res["ttft_s"],
        "peak_vram_mib": res["peak_vram_mib"],
    }


def build_summary_md(rows):
    lines = []
    lines.append("# coding-mini-v1 — Results Summary\n")
    lines.append("Deterministic evaluation of 5 local open-weight models across 6 coding cases (3 Python, 3 C++20).\n")
    lines.append("Execution conditions: seed 9137, temperature 0.2, top_p 0.95, reasoning off, 8 threads, full GPU offload, FA on, KV cache q8_0/q4_0, context 8192.\n")

    lines.append("## Consolidated Performance & Accuracy Table\n")
    lines.append("| Modelo | PASS / 6 | Python / 3 | C++ / 3 | tok/s mediano | Peak VRAM |")
    lines.append("|---|:---:|:---:|:---:|:---:|:---:|")

    for model in MODELS:
        m_rows = [r for r in rows if r["model_id"] == model["id"]]
        total_pass = sum(bool(r["passed"]) for r in m_rows)
        py_pass = sum(bool(r["passed"]) for r in m_rows if r["language"] == "python")
        cpp_pass = sum(bool(r["passed"]) for r in m_rows if r["language"] == "cpp")
        speeds = [r["predicted_per_second"] for r in m_rows if r.get("predicted_per_second") is not None]
        med_speed = round(statistics.median(speeds), 2) if speeds else "N/A"
        peak_v = max((r["peak_vram_mib"] for r in m_rows if r.get("peak_vram_mib")), default="N/A")
        lines.append(f"| **{model['name']}** | **{total_pass}/6** | {py_pass}/3 | {cpp_pass}/3 | {med_speed} tok/s | {peak_v} MiB |")

    lines.append("\n---\n")
    lines.append("## Case-by-Case Breakdown\n")

    for case in PROMPTS:
        lines.append(f"### {case['id']} — {case['name']} ({case['language'].upper()}, {case['difficulty'].capitalize()})\n")
        lines.append("| Modelo | Compile / Syntax | Public Tests | Hidden Tests | Status | Geração (s) | tok/s |")
        lines.append("|---|:---:|:---:|:---:|:---:|:---:|:---:|")
        c_rows = [r for r in rows if r["case_id"] == case["id"]]
        for r in c_rows:
            st = "PASS" if r["passed"] else "FAIL"
            comp = "PASS" if r["compile_pass"] else "FAIL"
            pub = "PASS" if r["public_pass"] else "FAIL"
            hid = "PASS" if r["hidden_pass"] else "FAIL"
            speed = f"{r['predicted_per_second']:.2f}" if r.get("predicted_per_second") else "N/A"
            lines.append(f"| {r['model_name']} | {comp} | {pub} | {hid} | **{st}** | {r['wall_time_s']:.2f}s | {speed} |")
        lines.append("")

    return "\n".join(lines) + "\n"


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if RAW_FILE.exists():
        RAW_FILE.unlink()

    all_rows = []

    for model in MODELS:
        print(f"\n{'='*70}")
        print(f"Running model: {model['name']}")
        print(f"Path: {model['path']}")
        print(f"{'='*70}")

        subprocess.run(["pkill", "-9", "-f", f"--port {PORT}"], capture_output=True)
        time.sleep(2)

        log_path = RESULTS_DIR / f"server-{model['id']}.log"
        log_fp = open(log_path, "w", encoding="utf-8")

        server_args = [
            str(LLAMA_BIN), "serve",
            "-m", model["path"],
            "--host", "127.0.0.1", "--port", str(PORT),
            "-c", str(CTX),
            "-np", "1",
            "-ngl", "999",
            "-fa", "on",
            "--fit", "off",
            "-ctk", "q8_0",
            "-ctv", "q4_0",
            "-t", str(THREADS),
            "-tb", str(THREADS),
            "--jinja",
            "--reasoning", "off",
            "--chat-template-kwargs", json.dumps({"enable_thinking": False}, separators=(",", ":")),
            "--no-webui",
        ] + model.get("extra_server_args", [])

        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = f"/home/alpha/Playstoria/models/engines/llama.cpp/build/bin:{env.get('LD_LIBRARY_PATH', '')}"

        proc = subprocess.Popen(server_args, stdout=log_fp, stderr=subprocess.STDOUT, env=env)

        try:
            wait_health(180)
            print("Server healthy! Running warmup...")
            warmup()
            print("Warmup done. Running 6 cases...")

            for case in PROMPTS:
                print(f"-> Executing case {case['id']} ({case['name']})...")
                res = generate_solution(case)
                row = {
                    "model_id": model["id"],
                    "model_name": model["name"],
                    **res
                }
                with RAW_FILE.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                all_rows.append(row)
                status_str = "PASS" if row["passed"] else f"FAIL (compile={row['compile_pass']}, pub={row['public_pass']}, hid={row['hidden_pass']})"
                print(f"   [{case['id']}] {status_str} | Speed: {row.get('predicted_per_second', 0):.2f} tok/s | Time: {row['wall_time_s']:.2f}s")
                if not row["passed"] and row.get("eval_error"):
                    print(f"   Error: {row['eval_error'][:200]}...")

        finally:
            try:
                proc.terminate()
                proc.wait(timeout=10)
            except Exception:
                try: proc.kill()
                except: pass
            log_fp.close()
            subprocess.run(["pkill", "-9", "-f", f"--port {PORT}"], capture_output=True)
            time.sleep(2)

    summary_text = build_summary_md(all_rows)
    SUMMARY_FILE.write_text(summary_text, encoding="utf-8")
    print(f"\nAll 30 benchmark runs completed! Output saved to {SUMMARY_FILE}")


if __name__ == "__main__":
    main()
