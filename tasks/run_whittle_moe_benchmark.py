#!/usr/bin/env python3
import json
import os
import re
import statistics
import subprocess
import threading
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path("/home/alpha/Playstoria/models").resolve()
RESULTS_DIR = ROOT / "benchmarks/coding-mini-v1/results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

import sys
sys.path.insert(0, str(ROOT / "benchmarks/coding-mini-v1"))
from evaluate import evaluate_case

PROMPTS_FILE = ROOT / "benchmarks/coding-mini-v1/prompts.json"
PROMPTS = json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))

LLAMA_BIN = str(ROOT / "engines/llama.cpp/build/bin/llama-server")
WHITTLE_MODEL = str(ROOT / "text/logic65-Qwen3.8-Whittle-MoE-27B-A17.8B-GGUF/Whittle-MoE-27B-A18B-v2.2.1-Q3_K_M.gguf")
DFLASH_MODEL = str(ROOT / "text/z-lab-Qwen3.8-27B-DFlash2-GGUF/Qwen3.8-27B-DFlash2-Q4_K_M.gguf")

PORT = 8196
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
                    return True
        except Exception:
            time.sleep(1)
    return False

def post_stream(payload):
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    first_token = None
    content_parts = []
    reasoning_parts = []
    usage = {}
    timings = {}
    finish_reason = None
    peak = vram_mib()
    stop = threading.Event()

    def sampler():
        nonlocal peak
        while not stop.wait(0.05):
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
                    r = delta.get("reasoning_content") or ""
                    if c:
                        if first_token is None:
                            first_token = time.perf_counter()
                        content_parts.append(c)
                    if r:
                        reasoning_parts.append(r)
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
        "reasoning_text": "".join(reasoning_parts).strip(),
        "finish_reason": finish_reason,
        "usage": usage,
        "timings": timings,
        "wall_time_s": round(ended - started, 4),
        "ttft_s": None if first_token is None else round(first_token - started, 4),
        "peak_vram_mib": peak,
    }

def run_suite(mode="native"):
    print(f"\n{'='*75}")
    print(f"Running Whittle-MoE-27B-A18B-v2.2.1-Q3_K_M (Mode: {mode.upper()})")
    print(f"{'='*75}")

    subprocess.run(["pkill", "-9", "-f", f"--port {PORT}"], capture_output=True)
    time.sleep(2)

    server_cmd = [
        LLAMA_BIN,
        "-m", WHITTLE_MODEL,
        "--fit", "off",
        "-ctk", "q8_0",
        "-ctv", "q4_0",
        "-ngl", "99",
        "-fa", "on",
        "-np", "1",
        "-t", str(THREADS),
        "-c", str(CTX),
        "--host", "127.0.0.1",
        "--port", str(PORT),
        "--jinja",
        "--reasoning", "off",
        "--no-ui"
    ]

    if mode == "dflash2":
        server_cmd.extend([
            "-md", DFLASH_MODEL,
            "-ngld", "99",
            "--spec-type", "draft-dflash",
            "--spec-draft-n-max", "7"
        ])

    log_path = f"/tmp/server_whittle_{mode}.log"
    log_fp = open(log_path, "w", encoding="utf-8")
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = f"{ROOT}/engines/llama.cpp/build/bin:{env.get('LD_LIBRARY_PATH', '')}"

    proc = subprocess.Popen(server_cmd, stdout=log_fp, stderr=subprocess.STDOUT, env=env)

    rows = []
    try:
        print(f"Waiting for Whittle server ({mode})...")
        if not wait_health(120):
            print(f"Server failed to become healthy. Log: {log_path}")
            return rows, 1

        print("Server healthy! Running warmup...")
        post_stream({
            "messages": [{"role": "user", "content": "Write a comment."}],
            "max_tokens": 16,
            "temperature": 0.2,
            "stream": True
        })

        for case in PROMPTS:
            cid = case["id"]
            print(f"-> Executing {cid} ({case['name']})...")
            payload = {
                "messages": [{"role": "user", "content": case["prompt"]}],
                "temperature": TEMP,
                "top_p": TOP_P,
                "seed": SEED,
                "max_tokens": case["max_tokens"],
                "stream": True
            }
            res = post_stream(payload)
            eval_res = evaluate_case(cid, res["text"])
            timings = res.get("timings", {})
            usage = res.get("usage", {})

            row = {
                "candidate_id": f"whittle_moe_27b_a18b_{mode}",
                "model_name": f"Whittle-MoE-27B-A18B-v2.2.1-Q3_K_M ({mode})",
                "case_id": cid,
                "case_name": case["name"],
                "language": case["language"],
                "difficulty": case["difficulty"],
                "seed": SEED,
                "compile_pass": eval_res["compile_pass"],
                "public_pass": eval_res["public_pass"],
                "hidden_pass": eval_res["hidden_pass"],
                "passed": eval_res["passed"],
                "eval_error": eval_res.get("error"),
                "raw_text": res["text"],
                "extracted_code": eval_res["extracted_code"],
                "predicted_per_second": timings.get("predicted_per_second"),
                "prompt_per_second": timings.get("prompt_per_second"),
                "prompt_ms": timings.get("prompt_ms"),
                "wall_time_s": res["wall_time_s"],
                "ttft_s": res["ttft_s"],
                "peak_vram_mib": res["peak_vram_mib"],
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "draft_n": timings.get("draft_n", 0),
                "draft_n_accepted": timings.get("draft_n_accepted", 0),
            }

            if mode == "dflash2":
                # Parse log for mean accepted length
                log_fp.flush()
                with open(log_path, "r", encoding="utf-8", errors="replace") as lf:
                    log_text = lf.read()
                matches = list(re.finditer(r"mean len\s*=\s*([0-9]+\.[0-9]+)", log_text))
                if matches:
                    row["mean_accepted_length"] = float(matches[-1].group(1))

            status_str = "PASS" if row["passed"] else f"FAIL (compile={row['compile_pass']}, pub={row['public_pass']}, hid={row['hidden_pass']})"
            draft_info = f" | Draft Acc: {row['draft_n_accepted']}/{row['draft_n']}" if mode == "dflash2" else ""
            print(f"   [{cid}] {status_str} | Speed: {row.get('predicted_per_second', 0):.2f} tok/s | Time: {row['wall_time_s']:.2f}s{draft_info} | VRAM: {row['peak_vram_mib']} MiB")
            if not row["passed"] and row.get("eval_error"):
                print(f"      Error detail: {row['eval_error'][:250]}...")
            rows.append(row)

        return rows, 0
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

def main():
    print("Beginning Evaluation Cycle for Candidate 2: Whittle-MoE Qwen3.8-27B A17.8B/A18B (v2.2.1 Q3_K_M)")
    native_rows, code = run_suite(mode="native")
    if code != 0:
        print("Native benchmark failed to run.")
        return

    pass_count = sum(1 for r in native_rows if r["passed"])
    py_pass = sum(1 for r in native_rows if r["passed"] and r["language"] == "python")
    cpp_pass = sum(1 for r in native_rows if r["passed"] and r["language"] == "cpp")
    speeds = [r["predicted_per_second"] for r in native_rows if r.get("predicted_per_second")]
    med_speed = statistics.median(speeds) if speeds else 0
    peak_vram = max(r["peak_vram_mib"] for r in native_rows)

    print("\n" + "="*70)
    print(f"WHITTLE NATIVE SUMMARY: {pass_count}/6 PASS (Python: {py_pass}/3, C++: {cpp_pass}/3)")
    print(f"Median Speed: {med_speed:.2f} tok/s | Peak VRAM: {peak_vram} MiB")
    print("="*70)

    dflash_rows = []
    if pass_count >= 5:
        print(f"\nCandidate 2 passed gate ({pass_count}/6 >= 5/6)! Proceeding to DFlash2 benchmark...")
        dflash_rows, df_code = run_suite(mode="dflash2")
    else:
        print(f"\nCandidate 2 failed gate ({pass_count}/6 < 5/6). Skipping DFlash2 as specified.")

    output_data = {
        "candidate": "Whittle-MoE-27B-A18B-v2.2.1-Q3_K_M",
        "repo": "logic65/Qwen3.8-Whittle-MoE-27B-A17.8B-GGUF",
        "gguf_file": "Whittle-MoE-27B-A18B-v2.2.1-Q3_K_M.gguf",
        "sha256": "b32cc1f4f4661925e163937213932c4571e88d3d5da381ed79515cffae46e305",
        "size_bytes": 13874251328,
        "native_rows": native_rows,
        "dflash_rows": dflash_rows,
        "summary": {
            "native_pass": pass_count,
            "native_py_pass": py_pass,
            "native_cpp_pass": cpp_pass,
            "native_med_speed": round(med_speed, 2),
            "native_peak_vram": peak_vram,
            "dflash_pass": sum(1 for r in dflash_rows if r["passed"]) if dflash_rows else None,
            "dflash_med_speed": round(statistics.median([r["predicted_per_second"] for r in dflash_rows if r.get("predicted_per_second")]), 2) if dflash_rows else None,
            "dflash_peak_vram": max([r["peak_vram_mib"] for r in dflash_rows]) if dflash_rows else None,
        }
    }

    out_file = RESULTS_DIR / "WHITTLE_MOE_BENCHMARK_RESULTS.json"
    out_file.write_text(json.dumps(output_data, indent=2), encoding="utf-8")
    print(f"\nWhittle benchmark results saved to {out_file}")

if __name__ == "__main__":
    main()
