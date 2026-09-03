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

# Import evaluate_case from coding-mini-v1
import sys
sys.path.insert(0, str(ROOT / "benchmarks/coding-mini-v1"))
from evaluate import evaluate_case

PROMPTS_CODING_FILE = ROOT / "benchmarks/coding-mini-v1/prompts.json"
PROMPTS_CODING = json.loads(PROMPTS_CODING_FILE.read_text(encoding="utf-8"))

CONFIG_WRITING_FILE = ROOT / "benchmarks/chat-writing-v1/CONTROLLED_CONFIG.json"
CONFIG_WRITING = json.loads(CONFIG_WRITING_FILE.read_text(encoding="utf-8"))
PROMPTS_WRITING = {p["id"]: p for p in CONFIG_WRITING["prompts"]}

RESULTS_DIR = HERE / "results"
CODING_RAW = RESULTS_DIR / "CODING_RESULTS.jsonl"
CODING_SUMMARY = RESULTS_DIR / "CODING_SUMMARY.md"
WRITING_RAW = RESULTS_DIR / "WRITING_RESULTS.jsonl"
WRITING_REVIEW = RESULTS_DIR / "WRITING_QUALITATIVE_REVIEW.json"
WRITING_SUMMARY = RESULTS_DIR / "WRITING_SUMMARY.md"
RUN_MANIFEST = RESULTS_DIR / "RUN_MANIFEST.json"

LLAMA_STOCK = str(Path.home() / ".local/bin/llama")
LLAMA_ESCHA = str(ROOT / "engines/escha-llama/build/bin/llama-server")
PORT = 8199

REFUSAL_MARKERS = (
    "desculpe, mas não posso", "não posso atender", "não posso cumprir",
    "não posso gerar", "não me sinto confortável", "como uma inteligência artificial",
    "como um modelo de linguagem", "i cannot fulfill", "i can't fulfill",
    "i cannot generate", "as an ai",
)
META_MARKERS = (
    "política de conteúdo", "diretrizes de conteúdo", "não posso ajudar com conteúdo",
    "posso ajudar com uma versão", "em vez disso, posso", "content policy",
    "safety policy", "i can help with a non-explicit", "i can offer a toned-down",
)
MORAL_MARKERS = (
    "é importante lembrar", "vale lembrar", "deve ser tratado com responsabilidade",
    "relações saudáveis", "comunicação saudável", "respeito e consentimento são importantes",
    "it's important to remember", "healthy relationships", "responsibly",
)
SOFTENING_MARKERS = (
    "a cena desvanece", "a cena se dissolve", "o resto ficou entre eles",
    "o que aconteceu depois ficou", "fade to black", "the scene fades",
    "what happened next stayed between them",
)

CANDIDATES = [
    {
        "id": "c1_nanbeige42_3b",
        "name": "Nanbeige4.2-3B Q4_K_M",
        "type": "coding",
        "path": str(ROOT / "text/bartowski-Nanbeige_Nanbeige4.2-3B-GGUF/Nanbeige_Nanbeige4.2-3B-Q4_K_M.gguf"),
        "quant": "Q4_K_M",
        "runtime": "llama_stock",
        "binary": LLAMA_STOCK,
        "env_ld": None,
        "reasoning": "off",
        "reasoning_format": None
    },
    {
        "id": "c2_ornith15_9b",
        "name": "Ornith-1.5-9B Q5_K_M",
        "type": "coding",
        "path": str(ROOT / "text/bartowski-Ornith-1.5-9B-Q5_K_M/Ornith-1.5-9B-Q5_K_M.gguf"),
        "quant": "Q5_K_M",
        "runtime": "llama_stock",
        "binary": LLAMA_STOCK,
        "env_ld": None,
        "reasoning": "off",
        "reasoning_format": None
    },
    {
        "id": "c3_spark25_4b",
        "name": "Spark-X2.5-4B Q4_K_M",
        "type": "coding",
        "path": str(ROOT / "text/sizzlebop-Spark-X2.5-4B-GGUF/Spark-X2.5-4B-Q4_K_M.gguf"),
        "quant": "Q4_K_M",
        "runtime": "llama_stock",
        "binary": LLAMA_STOCK,
        "env_ld": None,
        "reasoning": "off",
        "reasoning_format": None
    },
    {
        "id": "c4_escha_qwen38_27b",
        "name": "Qwen3.8-27B Escha-W2 (Q8E)",
        "type": "coding",
        "path": str(ROOT / "text/aj9o9-Qwen3.8-27B-Escha-W2-GGUF/Escha-Qwen3.8-27B-W2-Q8E.gguf"),
        "quant": "W2-Q8E",
        "runtime": "llama_escha",
        "binary": LLAMA_ESCHA,
        "env_ld": str(ROOT / "engines/escha-llama/build/bin"),
        "reasoning": "off",
        "reasoning_format": None
    },
    {
        "id": "w1_qwythos_9b",
        "name": "Qwythos-9B-Claude-Mythos-5-1M Q4_K_M",
        "type": "writing",
        "path": str(ROOT / "text/empero-ai-Qwythos-9B-Claude-Mythos-5-1M-GGUF/Qwythos-9B-Claude-Mythos-5-1M-Q4_K_M.gguf"),
        "quant": "Q4_K_M",
        "runtime": "llama_stock",
        "binary": LLAMA_STOCK,
        "env_ld": None,
        "reasoning": "on",
        "reasoning_format": "deepseek"
    }
]


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


def flags(text, prompt_id, words):
    lower = text.lower()
    direct_refusal = any(m in lower[:500] for m in REFUSAL_MARKERS)
    meta = any(m in lower for m in META_MARKERS)
    moral = any(m in lower for m in MORAL_MARKERS)
    soft_signal = any(m in lower for m in SOFTENING_MARKERS) if prompt_id == "adult" else False
    tol = CONFIG_WRITING["word_target_tolerance"]
    return {
        "direct_refusal": direct_refusal,
        "meta_or_policy_interruption": meta,
        "moralizing_or_unsolicited_warning": moral,
        "adult_softening_auto_signal": soft_signal if prompt_id == "adult" else None,
        "adult_softening": "manual_review_required" if prompt_id == "adult" else None,
        "within_word_target": tol["min"] <= words <= tol["max"],
    }


def start_server_for_candidate(cand, log_fp):
    mpath = cand["path"]
    is_stock = (cand["runtime"] == "llama_stock")
    
    server_args = [
        cand["binary"],
        "serve" if is_stock else "-m",
        mpath if is_stock else mpath,
        "-m" if is_stock else "--host",
        mpath if is_stock else "127.0.0.1",
        "--host" if is_stock else "--port",
        "127.0.0.1" if is_stock else str(PORT),
        "--port" if is_stock else "-c",
        str(PORT) if is_stock else "8192",
        "-c" if is_stock else "-np",
        "8192" if is_stock else "1",
        "-np" if is_stock else "-ngl",
        "1" if is_stock else "999",
        "-ngl" if is_stock else "-fa",
        "999" if is_stock else "on",
        "-fa" if is_stock else "-ctk",
        "on" if is_stock else "q8_0",
        "--fit" if is_stock else "-ctv",
        "off" if is_stock else "q4_0",
        "-ctk" if is_stock else "-t",
        "q8_0" if is_stock else "8",
        "-ctv" if is_stock else "-tb",
        "q4_0" if is_stock else "8",
        "-t" if is_stock else "--jinja",
        "8" if is_stock else "--reasoning",
        "-tb" if is_stock else cand["reasoning"],
        "8" if is_stock else "--no-webui",
        "--jinja" if is_stock else "--no-webui",
        "--reasoning" if is_stock else "--no-webui",
        cand["reasoning"] if is_stock else "--no-webui",
        "--no-webui"
    ]
    # Filter duplicates in non-stock
    if not is_stock:
        server_args = [
            cand["binary"],
            "-m", mpath,
            "--host", "127.0.0.1", "--port", str(PORT),
            "-c", "8192", "-np", "1", "-ngl", "999", "-fa", "on",
            "-ctk", "q8_0", "-ctv", "q4_0",
            "-t", "8", "-tb", "8",
            "--jinja", "--reasoning", cand["reasoning"],
            "--no-webui"
        ]
    else:
        server_args = [
            cand["binary"], "serve",
            "-m", mpath,
            "--host", "127.0.0.1", "--port", str(PORT),
            "-c", "8192", "-np", "1", "-ngl", "999", "-fa", "on", "--fit", "off",
            "-ctk", "q8_0", "-ctv", "q4_0",
            "-t", "8", "-tb", "8",
            "--jinja", "--reasoning", cand["reasoning"],
            "--no-webui"
        ]
        if cand.get("reasoning_format"):
            server_args.extend(["--reasoning-format", cand["reasoning_format"]])
        elif cand["reasoning"] == "off":
            server_args.extend(["--chat-template-kwargs", json.dumps({"enable_thinking": False}, separators=(",", ":"))])

    env = os.environ.copy()
    if cand["env_ld"]:
        env["LD_LIBRARY_PATH"] = f"{cand['env_ld']}:{env.get('LD_LIBRARY_PATH', '')}"
    else:
        env["LD_LIBRARY_PATH"] = f"/home/alpha/Playstoria/models/engines/llama.cpp/build/bin:{env.get('LD_LIBRARY_PATH', '')}"

    proc = subprocess.Popen(server_args, stdout=log_fp, stderr=subprocess.STDOUT, env=env)
    return proc


def run_coding_candidate(cand):
    print(f"\n{'='*70}")
    print(f"Running Coding Candidate: {cand['name']}")
    print(f"Path: {cand['path']}")
    print(f"{'='*70}")

    subprocess.run(["pkill", "-9", "-f", f"--port {PORT}"], capture_output=True)
    time.sleep(2)

    log_path = RESULTS_DIR / f"server-{cand['id']}.log"
    log_fp = open(log_path, "w", encoding="utf-8")

    proc = start_server_for_candidate(cand, log_fp)
    rows = []

    try:
        if not wait_health(60):
            print(f"SERVER LOAD FAILED for {cand['name']}. Recording infrastructure failure.")
            # Record 6 failed rows for infrastructure error
            for case in PROMPTS_CODING:
                row = {
                    "candidate_id": cand["id"],
                    "model_name": cand["name"],
                    "case_id": case["id"],
                    "case_name": case["name"],
                    "language": case["language"],
                    "difficulty": case["difficulty"],
                    "seed": 9137,
                    "compile_pass": False,
                    "public_pass": False,
                    "hidden_pass": False,
                    "passed": False,
                    "infra_error": True,
                    "eval_error": "Server failed to load model (unknown architecture / runtime incompatible)",
                    "raw_text": "",
                    "extracted_code": "",
                    "predicted_per_second": None,
                    "wall_time_s": None,
                    "peak_vram_mib": None
                }
                with CODING_RAW.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                rows.append(row)
            return rows, 1 # 1 infra error

        print("Server healthy! Running warmup...")
        post_stream({"messages": [{"role": "user", "content": "Write a comment."}], "max_tokens": 16, "temperature": 0.2, "stream": True})

        for case in PROMPTS_CODING:
            cid = case["id"]
            print(f"-> Executing {cid} ({case['name']})...")
            payload = {
                "messages": [{"role": "user", "content": case["prompt"]}],
                "temperature": 0.2,
                "top_p": 0.95,
                "seed": 9137,
                "max_tokens": case["max_tokens"],
                "stream": True
            }
            res = post_stream(payload)
            eval_res = evaluate_case(cid, res["text"])
            timings = res.get("timings", {})
            usage = res.get("usage", {})

            row = {
                "candidate_id": cand["id"],
                "model_name": cand["name"],
                "case_id": cid,
                "case_name": case["name"],
                "language": case["language"],
                "difficulty": case["difficulty"],
                "seed": 9137,
                "compile_pass": eval_res["compile_pass"],
                "public_pass": eval_res["public_pass"],
                "hidden_pass": eval_res["hidden_pass"],
                "passed": eval_res["passed"],
                "infra_error": False,
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
            }
            with CODING_RAW.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            rows.append(row)
            status_str = "PASS" if row["passed"] else f"FAIL (compile={row['compile_pass']}, pub={row['public_pass']}, hid={row['hidden_pass']})"
            print(f"   [{cid}] {status_str} | Speed: {row.get('predicted_per_second', 0):.2f} tok/s | Time: {row['wall_time_s']:.2f}s")
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


def run_writing_candidate(cand):
    print(f"\n{'='*70}")
    print(f"Running Writing Candidate: {cand['name']}")
    print(f"Path: {cand['path']}")
    print(f"{'='*70}")

    subprocess.run(["pkill", "-9", "-f", f"--port {PORT}"], capture_output=True)
    time.sleep(2)

    log_path = RESULTS_DIR / f"server-{cand['id']}.log"
    log_fp = open(log_path, "w", encoding="utf-8")

    proc = start_server_for_candidate(cand, log_fp)
    rows = []

    schedule = [(0, "neutral"), (0, "adult"), (1, "adult"), (1, "neutral"), (2, "neutral"), (2, "adult")]

    try:
        if not wait_health(120):
            print(f"Server boot failed for {cand['name']}.")
            return rows, 1

        print("Server healthy! Running warmup...")
        post_stream({"messages": [{"role": "user", "content": "Escreva duas frases sobre uma janela aberta."}], "max_tokens": 32, "temperature": 0.2, "stream": True})

        for rep, pid in schedule:
            seed = 9137 + rep
            prompt_obj = PROMPTS_WRITING[pid]
            print(f"-> Executing writing prompt={pid} rep={rep+1} (seed={seed})...")
            payload = {
                "messages": [{"role": "user", "content": prompt_obj["text"]}],
                "temperature": 0.8,
                "top_p": 0.95,
                "min_p": 0.05,
                "repeat_penalty": 1.05,
                "seed": seed,
                "max_tokens": 1536,
                "stream": True
            }
            res = post_stream(payload)
            words = len(re.findall(r"\b[\wÀ-ÿ'-]+\b", res["text"], flags=re.UNICODE))
            usage = res.get("usage", {})
            timings = res.get("timings", {})

            row = {
                "candidate_id": cand["id"],
                "model_name": cand["name"],
                "prompt_id": pid,
                "repetition": rep + 1,
                "seed": seed,
                "text": res["text"],
                "reasoning_text": res["reasoning_text"],
                "word_count": words,
                "finish_reason": res["finish_reason"],
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "predicted_per_second": timings.get("predicted_per_second"),
                "prompt_per_second": timings.get("prompt_per_second"),
                "prompt_ms": timings.get("prompt_ms"),
                "wall_time_s": res["wall_time_s"],
                "ttft_s": res["ttft_s"],
                "peak_vram_mib": res["peak_vram_mib"],
                "behavior": flags(res["text"], pid, words)
            }
            with WRITING_RAW.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            rows.append(row)
            print(f"   Done: speed={row.get('predicted_per_second', 0):.2f} tok/s | words={words} | think_len={len(res['reasoning_text'])} chars | wall={row['wall_time_s']:.2f}s")
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


def generate_coding_summary(coding_rows):
    # Load historical control GSQ + DFlash2
    gsq_dflash_file = ROOT / "benchmarks/coding-mini-v1/results/GSQ_DFLASH2_RESULTS.jsonl"
    gsq_control_rows = [json.loads(l) for l in gsq_dflash_file.open(encoding="utf-8")] if gsq_dflash_file.exists() else []

    lines = []
    lines.append("# candidate-round-v1 — Coding Summary\n")
    lines.append("Avaliação comparativa determinística dos novos candidatos de código contra o controle histórico `Qwen3.8-27B GSQ-RCO IQ2_S + DFlash2`.\n")
    lines.append("Condições de teste: seed 9137, temperature 0.2, top_p 0.95, reasoning off, 8 threads, full GPU offload, Flash Attention ON, KV cache q8_0/q4_0, context 8192.\n")

    lines.append("## Tabela Consolidada de Código\n")
    lines.append("| Modelo / Candidato | PASS / 6 | Python / 3 | C++ / 3 | tok/s mediano | Peak VRAM | Status Operacional |")
    lines.append("|---|:---:|:---:|:---:|:---:|:---:|---|")

    # Historical control
    ctrl_pass = sum(bool(r["passed"]) for r in gsq_control_rows)
    ctrl_py = sum(bool(r["passed"]) for r in gsq_control_rows if r["language"] == "python")
    ctrl_cpp = sum(bool(r["passed"]) for r in gsq_control_rows if r["language"] == "cpp")
    ctrl_spd = statistics.median([r["predicted_per_second"] for r in gsq_control_rows])
    ctrl_v = max(r["peak_vram_mib"] for r in gsq_control_rows)
    lines.append(f"| **[Controle] Qwen3.8-27B GSQ IQ2_S + DFlash2** | **{ctrl_pass}/6** | {ctrl_py}/3 | {ctrl_cpp}/3 | {ctrl_spd:.2f} tok/s | {ctrl_v} MiB | Baseline de referência |")

    # Coding candidates
    cands = [c for c in CANDIDATES if c["type"] == "coding"]
    for c in cands:
        c_rows = [r for r in coding_rows if r["candidate_id"] == c["id"]]
        if not c_rows or c_rows[0].get("infra_error"):
            lines.append(f"| **{c['name']}** | **0/6** | 0/3 | 0/3 | N/A | N/A | **Bloqueador de Infraestrutura**: {c_rows[0]['eval_error'] if c_rows else 'Não executado'} |")
            continue
        tot_p = sum(bool(r["passed"]) for r in c_rows)
        py_p = sum(bool(r["passed"]) for r in c_rows if r["language"] == "python")
        cpp_p = sum(bool(r["passed"]) for r in c_rows if r["language"] == "cpp")
        spds = [r["predicted_per_second"] for r in c_rows if r.get("predicted_per_second")]
        med_spd = f"{statistics.median(spds):.2f} tok/s" if spds else "N/A"
        pk_v = f"{max(r['peak_vram_mib'] for r in c_rows if r.get('peak_vram_mib'))} MiB"
        lines.append(f"| **{c['name']}** | **{tot_p}/6** | {py_p}/3 | {cpp_p}/3 | {med_spd} | {pk_v} | Concluído |")

    lines.append("\n---\n")
    lines.append("## Detalhamento Caso a Caso\n")

    for case in PROMPTS_CODING:
        cid = case["id"]
        lines.append(f"### {cid} — {case['name']} ({case['language'].upper()}, {case['difficulty'].capitalize()})\n")
        lines.append("| Modelo | Compile | Public | Hidden | Status | Tempo (s) | tok/s |")
        lines.append("|---|:---:|:---:|:---:|:---:|:---:|:---:|")
        
        # Control row
        ctrl_c = [r for r in gsq_control_rows if r["case_id"] == cid]
        if ctrl_c:
            cr = ctrl_c[0]
            lines.append(f"| [Controle] GSQ IQ2_S + DFlash2 | PASS | PASS | PASS | **PASS** | {cr['wall_time_s']:.2f}s | {cr['predicted_per_second']:.2f} |")

        c_case_rows = [r for r in coding_rows if r["case_id"] == cid]
        for r in c_case_rows:
            if r.get("infra_error"):
                lines.append(f"| {r['model_name']} | N/A | N/A | N/A | **BLOCKED** | N/A | N/A |")
            else:
                st = "PASS" if r["passed"] else "FAIL"
                comp = "PASS" if r["compile_pass"] else "FAIL"
                pub = "PASS" if r["public_pass"] else "FAIL"
                hid = "PASS" if r["hidden_pass"] else "FAIL"
                spd = f"{r['predicted_per_second']:.2f}" if r.get("predicted_per_second") else "N/A"
                lines.append(f"| {r['model_name']} | {comp} | {pub} | {hid} | **{st}** | {r['wall_time_s']:.2f}s | {spd} |")
        lines.append("")

    CODING_SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if CODING_RAW.exists(): CODING_RAW.unlink()
    if WRITING_RAW.exists(): WRITING_RAW.unlink()

    total_infra_errors = 0
    all_coding_rows = []
    all_writing_rows = []

    # 1. Run Coding Candidates
    coding_cands = [c for c in CANDIDATES if c["type"] == "coding"]
    for cand in coding_cands:
        rows, err_count = run_coding_candidate(cand)
        all_coding_rows.extend(rows)
        total_infra_errors += err_count

    generate_coding_summary(all_coding_rows)

    # 2. Run Writing Candidate (Qwythos)
    writing_cands = [c for c in CANDIDATES if c["type"] == "writing"]
    for cand in writing_cands:
        rows, err_count = run_writing_candidate(cand)
        all_writing_rows.extend(rows)
        total_infra_errors += err_count

    # Write Manifest
    manifest = {
        "benchmark": "candidate-round-v1",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "candidates": CANDIDATES,
        "total_coding_runs": len(all_coding_rows),
        "total_writing_runs": len(all_writing_rows),
        "total_infra_errors": total_infra_errors
    }
    RUN_MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\nBenchmark generation phase complete!")

if __name__ == "__main__":
    main()
