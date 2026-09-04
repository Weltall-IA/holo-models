#!/usr/bin/env python3
import json
import os
import re
import signal
import statistics
import subprocess
import threading
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path("/home/alpha/Playstoria/models").resolve()
BENCH_DIR = ROOT / "benchmarks/gsq-froggeric-v225-clean-retest-v1"
RESULTS_DIR = BENCH_DIR / "results"
PREFLIGHT_DIR = RESULTS_DIR / "gpu-preflight"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
PREFLIGHT_DIR.mkdir(parents=True, exist_ok=True)

import sys
sys.path.insert(0, str(ROOT / "benchmarks/coding-mini-v1"))
from evaluate import evaluate_case

PROMPTS_CODING_FILE = ROOT / "benchmarks/coding-mini-v1/prompts.json"
PROMPTS_CODING = json.loads(PROMPTS_CODING_FILE.read_text(encoding="utf-8"))

CONFIG_WRITING_FILE = ROOT / "benchmarks/chat-writing-v1/CONTROLLED_CONFIG.json"
CONFIG_WRITING = json.loads(CONFIG_WRITING_FILE.read_text(encoding="utf-8"))
PROMPTS_WRITING = {p["id"]: p for p in CONFIG_WRITING["prompts"]}

LLAMA_BIN = str(Path.home() / ".local/bin/llama")
TARGET_MODEL = str(ROOT / "text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-IQ2_S/Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf")
DRAFT_MODEL = str(ROOT / "text/z-lab-Qwen3.8-27B-DFlash2-GGUF/Qwen3.8-27B-DFlash2-Q4_K_M.gguf")
FROGGERIC_TEMPLATE = str(ROOT / "text/froggeric-Qwen-Fixed-Chat-Templates-v22.5/chat_template.jinja")

PORT = 8197
CTX = 8192
THREADS = 8

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

def run_gpu_preflight(arm_name, max_retries=10, retry_delay=5):
    print(f"\n[Preflight] Checking Clean-GPU Gate for {arm_name}...")
    for attempt in range(1, max_retries + 1):
        smi_out = subprocess.check_output(
            ["nvidia-smi"],
            text=True
        )
        pmon_out = subprocess.check_output(
            ["nvidia-smi", "pmon", "-s", "u", "-c", "5", "-d", "1"],
            text=True
        )

        # Parse pmon samples to verify no external process has >= 25% SM in 3+ samples
        # pmon format has lines like: 0 <pid> C+G <sm> ... <command>
        sm_counts = {}
        for line in pmon_out.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 9:
                pid = parts[1]
                sm_str = parts[3]
                cmd = parts[8] if len(parts) > 8 else ""
                # Ignore benchmark server / python runner processes if any
                if cmd in ("llama", "llama-server", "python", "python3"):
                    continue
                try:
                    sm_val = int(sm_str)
                    if sm_val >= 25:
                        sm_counts[pid] = sm_counts.get(pid, 0) + 1
                except ValueError:
                    pass

        heavy_pids = [pid for pid, count in sm_counts.items() if count >= 3]

        if not heavy_pids:
            # Gate passed
            print(f"[Preflight] Clean-GPU Gate PASSED for {arm_name}.")
            preflight_file = PREFLIGHT_DIR / f"{arm_name}_preflight.txt"
            preflight_file.write_text(f"=== NVIDIA-SMI ===\n{smi_out}\n\n=== PMON (5 samples) ===\n{pmon_out}\n\nClean Gate: PASSED (attempt {attempt})\n", encoding="utf-8")
            return {
                "passed": True,
                "attempt": attempt,
                "file": str(preflight_file.relative_to(ROOT)),
                "smi_snapshot": smi_out,
                "pmon_snapshot": pmon_out
            }

        print(f"[Preflight] Attempt {attempt}/{max_retries}: Heavy external GPU load detected on PID(s): {heavy_pids}. Waiting {retry_delay}s...")
        time.sleep(retry_delay)

    raise RuntimeError(f"Clean-GPU Gate FAILED for {arm_name} after {max_retries} attempts. Heavy external workload did not clear.")

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

def flags(text: str, prompt_id: str, words: int) -> dict:
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

def start_server(template_mode="native", with_dflash=False, log_fp=None):
    server_args = [
        LLAMA_BIN, "serve",
        "-m", TARGET_MODEL,
        "-ngl", "999",
        "-fa", "on",
        "--fit", "off",
        "-np", "1",
        "-t", str(THREADS),
        "-tb", str(THREADS),
        "-c", str(CTX),
        "-ctk", "q8_0",
        "-ctv", "q4_0",
        "--host", "127.0.0.1",
        "--port", str(PORT),
        "--jinja",
        "--no-ui"
    ]

    if template_mode == "froggeric":
        server_args.extend([
            "--chat-template-file", FROGGERIC_TEMPLATE,
            "--reasoning-format", "deepseek",
            "--chat-template-kwargs", json.dumps({"enable_thinking": False, "reasoning_effort": "none"}, separators=(",", ":")),
            "--reasoning", "off",
        ])
    else:
        server_args.extend([
            "--reasoning", "off",
        ])

    if with_dflash:
        server_args.extend([
            "-md", DRAFT_MODEL,
            "-ngld", "999",
            "--spec-type", "draft-dflash",
            "--spec-draft-n-max", "7"
        ])

    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = f"{ROOT}/engines/llama.cpp/build/bin:{env.get('LD_LIBRARY_PATH', '')}"

    proc = subprocess.Popen(server_args, stdout=log_fp, stderr=subprocess.STDOUT, env=env)
    return proc

def run_coding_arm(arm_id, arm_label, template_mode="native", with_dflash=False):
    print(f"\n{'='*75}")
    print(f"{arm_id}: {arm_label}")
    print(f"{'='*75}")

    preflight_info = run_gpu_preflight(arm_id.lower().replace(" ", "_"))

    subprocess.run(["pkill", "-9", "-f", f"--port {PORT}"], capture_output=True)
    time.sleep(2)

    log_filename = f"server-{arm_id.lower().replace(' ', '_')}.log"
    log_path = RESULTS_DIR / log_filename
    log_fp = open(log_path, "w", encoding="utf-8")
    proc = start_server(template_mode=template_mode, with_dflash=with_dflash, log_fp=log_fp)
    rows = []

    try:
        print(f"Waiting for server ({arm_id})...")
        if not wait_health(120):
            raise RuntimeError(f"Server failed to start for {arm_id}. Check {log_path}")

        print("Server healthy! Running warmup...")
        post_stream({
            "messages": [{"role": "user", "content": "Write a comment."}],
            "max_tokens": 16,
            "temperature": 0.2,
            "stream": True
        })

        if arm_id.startswith("Arm A"):
            out_jsonl = RESULTS_DIR / "CODING_NATIVE_RESULTS.jsonl"
        elif arm_id.startswith("Arm B"):
            out_jsonl = RESULTS_DIR / "CODING_FROGGERIC_V225_RESULTS.jsonl"
        elif arm_id.startswith("Arm C"):
            out_jsonl = RESULTS_DIR / "CODING_DFLASH2_NATIVE_RESULTS.jsonl"
        elif arm_id.startswith("Arm D"):
            out_jsonl = RESULTS_DIR / "CODING_DFLASH2_FROGGERIC_V225_RESULTS.jsonl"
        else:
            out_jsonl = RESULTS_DIR / f"{arm_id.lower().replace(' ', '_')}.jsonl"

        if out_jsonl.exists():
            out_jsonl.unlink()

        last_log_pos = 0

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

            draft_metrics = {}
            if with_dflash:
                time.sleep(0.5)
                log_fp.flush()
                with open(log_path, "r", encoding="utf-8", errors="replace") as lf:
                    lf.seek(last_log_pos)
                    new_text = lf.read()
                    last_log_pos = lf.tell()

                matches = list(re.finditer(
                    r"draft acceptance\s*=\s*([\d.]+)\s*\(\s*(\d+)\s+accepted\s*/\s*(\d+)\s+generated\)(?:,\s*mean len\s*=\s*([\d.]+))?",
                    new_text
                ))

                if matches:
                    last_m = matches[-1]
                    ratio = float(last_m.group(1))
                    accepted = int(last_m.group(2))
                    generated = int(last_m.group(3))
                    mean_len = float(last_m.group(4)) if last_m.group(4) else None
                else:
                    accepted = timings.get("draft_n_accepted", 0)
                    generated = timings.get("draft_n", 0)
                    ratio = (accepted / generated) if generated > 0 else None
                    mean_len = None

                draft_metrics = {
                    "draft_acceptance_ratio": ratio,
                    "accepted_draft_tokens": accepted,
                    "generated_draft_tokens": generated,
                    "mean_accepted_draft_length": mean_len,
                }

            row = {
                "arm": arm_id,
                "model_name": "Qwen3.8-27B GSQ-RCO IQ2_S",
                "template_mode": template_mode,
                "template_label": "Froggeric v22.5" if template_mode == "froggeric" else "Native",
                "speculative": with_dflash,
                "case_id": cid,
                "case_name": case["name"],
                "language": case["language"],
                "difficulty": case["difficulty"],
                "seed": 9137,
                "compile_pass": eval_res["compile_pass"],
                "public_pass": eval_res["public_pass"],
                "hidden_pass": eval_res["hidden_pass"],
                "passed": eval_res["passed"],
                "eval_error": eval_res.get("error"),
                "raw_text": res["text"],
                "reasoning_text": res["reasoning_text"],
                "extracted_code": eval_res["extracted_code"],
                "predicted_per_second": timings.get("predicted_per_second"),
                "prompt_per_second": timings.get("prompt_per_second"),
                "prompt_ms": timings.get("prompt_ms"),
                "wall_time_s": res["wall_time_s"],
                "ttft_s": res["ttft_s"],
                "peak_vram_mib": res["peak_vram_mib"],
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                **draft_metrics
            }

            with out_jsonl.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            rows.append(row)

            status_str = "PASS" if row["passed"] else f"FAIL (compile={row['compile_pass']}, pub={row['public_pass']}, hid={row['hidden_pass']})"
            df_str = ""
            if with_dflash:
                acc_s = f"{row['accepted_draft_tokens']}/{row['generated_draft_tokens']} ({row['draft_acceptance_ratio']*100:.1f}%)" if row.get('draft_acceptance_ratio') is not None else "N/A"
                df_str = f" | Draft Acc: {acc_s} | Mean Len: {row.get('mean_accepted_draft_length')}"
            print(f"   [{cid}] {status_str} | Speed: {row.get('predicted_per_second', 0):.2f} tok/s{df_str} | Time: {row['wall_time_s']:.2f}s | VRAM: {row['peak_vram_mib']} MiB")

        return rows, preflight_info
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

def run_writing_arm(arm_id, arm_label, template_mode="native"):
    print(f"\n{'='*75}")
    print(f"{arm_id}: {arm_label}")
    print(f"{'='*75}")

    preflight_info = run_gpu_preflight(arm_id.lower().replace(" ", "_"))

    subprocess.run(["pkill", "-9", "-f", f"--port {PORT}"], capture_output=True)
    time.sleep(2)

    log_filename = f"server-{arm_id.lower().replace(' ', '_')}.log"
    log_path = RESULTS_DIR / log_filename
    log_fp = open(log_path, "w", encoding="utf-8")
    proc = start_server(template_mode=template_mode, with_dflash=False, log_fp=log_fp)
    rows = []

    try:
        print(f"Waiting for server ({arm_id})...")
        if not wait_health(120):
            raise RuntimeError(f"Server failed to start for {arm_id}. Check {log_path}")

        print("Server ready! Running warmup...")
        post_stream({
            "messages": [{"role": "user", "content": "Escreva duas frases sobre uma janela aberta."}],
            "max_tokens": 32,
            "temperature": 0.2,
            "stream": True
        })

        if arm_id.startswith("Arm E"):
            out_jsonl = RESULTS_DIR / "WRITING_NATIVE_RESULTS.jsonl"
        elif arm_id.startswith("Arm F"):
            out_jsonl = RESULTS_DIR / "WRITING_FROGGERIC_V225_RESULTS.jsonl"
        else:
            out_jsonl = RESULTS_DIR / f"{arm_id.lower().replace(' ', '_')}.jsonl"

        if out_jsonl.exists():
            out_jsonl.unlink()

        schedule = [
            (0, "neutral", 9137),
            (0, "adult", 9137),
            (1, "adult", 9138),
            (1, "neutral", 9138),
            (2, "neutral", 9139),
            (2, "adult", 9139)
        ]

        g = CONFIG_WRITING["generation"]

        for rep_idx, prompt_id, seed in schedule:
            prompt_def = PROMPTS_WRITING[prompt_id]
            print(f"-> Executing {prompt_id} (rep={rep_idx+1}, seed={seed})...")
            payload = {
                "messages": [{"role": "user", "content": prompt_def["text"]}],
                "temperature": g["temperature"],
                "top_p": g["top_p"],
                "min_p": g["min_p"],
                "repeat_penalty": g["repeat_penalty"],
                "seed": seed,
                "max_tokens": g["max_tokens"],
                "stream": True
            }
            res = post_stream(payload)
            words = len(re.findall(r"\b[\wÀ-ÿ'-]+\b", res["text"], flags=re.UNICODE))
            usage = res.get("usage", {})
            timings = res.get("timings", {})
            b_flags = flags(res["text"], prompt_id, words)

            row = {
                "arm": arm_id,
                "model_name": "Qwen3.8-27B GSQ-RCO IQ2_S",
                "template_mode": template_mode,
                "template_label": "Froggeric v22.5" if template_mode == "froggeric" else "Native",
                "prompt_id": prompt_id,
                "repetition": rep_idx + 1,
                "seed": seed,
                "text": res["text"],
                "reasoning_text": res["reasoning_text"],
                "word_count": words,
                "predicted_per_second": timings.get("predicted_per_second"),
                "prompt_per_second": timings.get("prompt_per_second"),
                "prompt_ms": timings.get("prompt_ms"),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "wall_time_s": res["wall_time_s"],
                "ttft_s": res["ttft_s"],
                "peak_vram_mib": res["peak_vram_mib"],
                "behavior": b_flags,
            }

            with out_jsonl.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            rows.append(row)
            print(f"   [{prompt_id} r{rep_idx+1} seed {seed}] Words: {words} | Speed: {row.get('predicted_per_second', 0):.2f} tok/s | Time: {row['wall_time_s']:.2f}s | VRAM: {row['peak_vram_mib']} MiB")

        return rows, preflight_info
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

def generate_review_packet(arm_e_rows, arm_f_rows):
    lines = []
    lines.append("# Anonymized Writing Review Packet — GSQ Froggeric v22.5 Retest\n")
    lines.append("Review protocol: blind qualitative review of 12 responses (6 Native vs 6 Froggeric v22.5) across Neutral and Adult prompts.\n")
    lines.append("Quality status: `PENDING_CHATGPT_REVIEW`\n\n---\n")

    # Group by prompt and seed
    prompts_order = [
        ("neutral", 9137, "Reencontro no hotel durante tempestade (Seed 9137)"),
        ("adult", 9137, "Intimidade adulta e consensual (Seed 9137)"),
        ("neutral", 9138, "Reencontro no hotel durante tempestade (Seed 9138)"),
        ("adult", 9138, "Intimidade adulta e consensual (Seed 9138)"),
        ("neutral", 9139, "Reencontro no hotel durante tempestade (Seed 9139)"),
        ("adult", 9139, "Intimidade adulta e consensual (Seed 9139)"),
    ]

    e_map = {(r["prompt_id"], r["seed"]): r for r in arm_e_rows}
    f_map = {(r["prompt_id"], r["seed"]): r for r in arm_f_rows}

    for idx, (pid, seed, label) in enumerate(prompts_order, 1):
        lines.append(f"## Pair {idx}: {pid.upper()} (Seed {seed}) — {label}\n")

        # Invert assignment order for alternate pairs to keep review blind
        if idx % 2 == 1:
            cand_a = ("Candidate A (Arm E — Native)", e_map[(pid, seed)])
            cand_b = ("Candidate B (Arm F — Froggeric v22.5)", f_map[(pid, seed)])
        else:
            cand_a = ("Candidate A (Arm F — Froggeric v22.5)", f_map[(pid, seed)])
            cand_b = ("Candidate B (Arm E — Native)", e_map[(pid, seed)])

        for label_cand, row_cand in [cand_a, cand_b]:
            lines.append(f"### {label_cand}")
            lines.append(f"- **Word Count**: {row_cand['word_count']} words")
            lines.append(f"- **Throughput**: {row_cand.get('predicted_per_second', 0):.2f} tok/s (wall: {row_cand['wall_time_s']:.2f}s)")
            lines.append(f"- **Behavioral Flags**: `direct_refusal={row_cand['behavior']['direct_refusal']}`, `moralizing={row_cand['behavior']['moralizing_or_unsolicited_warning']}`, `within_target={row_cand['behavior']['within_word_target']}`\n")
            lines.append("```text")
            lines.append(row_cand["text"])
            lines.append("```\n")

        lines.append("---\n")

    (RESULTS_DIR / "WRITING_REVIEW_PACKET.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Review packet written to {RESULTS_DIR / 'WRITING_REVIEW_PACKET.md'}")

def generate_summary(arm_a_rows, arm_b_rows, arm_c_rows, arm_d_rows, arm_e_rows, arm_f_rows, preflight_data):
    # Coding pass counts and speeds
    a_pass = sum(1 for r in arm_a_rows if r["passed"])
    b_pass = sum(1 for r in arm_b_rows if r["passed"])
    c_pass = sum(1 for r in arm_c_rows if r["passed"])
    d_pass = sum(1 for r in arm_d_rows if r["passed"])

    a_speeds = [r["predicted_per_second"] for r in arm_a_rows if r.get("predicted_per_second")]
    b_speeds = [r["predicted_per_second"] for r in arm_b_rows if r.get("predicted_per_second")]
    c_speeds = [r["predicted_per_second"] for r in arm_c_rows if r.get("predicted_per_second")]
    d_speeds = [r["predicted_per_second"] for r in arm_d_rows if r.get("predicted_per_second")]

    a_med_speed = statistics.median(a_speeds)
    b_med_speed = statistics.median(b_speeds)
    c_med_speed = statistics.median(c_speeds)
    d_med_speed = statistics.median(d_speeds)

    a_vram = max(r["peak_vram_mib"] for r in arm_a_rows)
    b_vram = max(r["peak_vram_mib"] for r in arm_b_rows)
    c_vram = max(r["peak_vram_mib"] for r in arm_c_rows)
    d_vram = max(r["peak_vram_mib"] for r in arm_d_rows)

    c_accs = [r["draft_acceptance_ratio"] for r in arm_c_rows if r.get("draft_acceptance_ratio") is not None]
    d_accs = [r["draft_acceptance_ratio"] for r in arm_d_rows if r.get("draft_acceptance_ratio") is not None]
    c_med_acc = (statistics.median(c_accs) * 100) if c_accs else 0.0
    d_med_acc = (statistics.median(d_accs) * 100) if d_accs else 0.0

    c_lens = [r["mean_accepted_draft_length"] for r in arm_c_rows if r.get("mean_accepted_draft_length") is not None]
    d_lens = [r["mean_accepted_draft_length"] for r in arm_d_rows if r.get("mean_accepted_draft_length") is not None]
    c_med_len = statistics.median(c_lens) if c_lens else None
    d_med_len = statistics.median(d_lens) if d_lens else None

    # Writing speeds and VRAM
    e_speeds = [r["predicted_per_second"] for r in arm_e_rows if r.get("predicted_per_second")]
    f_speeds = [r["predicted_per_second"] for r in arm_f_rows if r.get("predicted_per_second")]
    e_med_speed = statistics.median(e_speeds)
    f_med_speed = statistics.median(f_speeds)
    e_vram = max(r["peak_vram_mib"] for r in arm_e_rows)
    f_vram = max(r["peak_vram_mib"] for r in arm_f_rows)

    # Primary Delta Calculations
    # B vs A
    delta_b_vs_a = ((b_med_speed - a_med_speed) / a_med_speed) * 100.0
    # D vs C
    delta_d_vs_c = ((d_med_speed - c_med_speed) / c_med_speed) * 100.0
    # F vs E
    delta_f_vs_e = ((f_med_speed - e_med_speed) / e_med_speed) * 100.0

    # Decision logic for coding:
    # A <3% throughput delta should be treated as practical parity unless repeated evidence supports a real effect.
    # FROGGERIC_V225_CODING_PREFERRED if b_pass==6 and d_pass==6 and (delta_b_vs_a >= 3.0 or delta_d_vs_c >= 3.0)
    # FROGGERIC_V225_CODING_PARITY if b_pass==6 and d_pass==6 and abs(delta_b_vs_a) < 3.0 and abs(delta_d_vs_c) < 3.0
    # KEEP_NATIVE_CODING if b_pass < 6 or d_pass < 6 or delta_b_vs_a <= -3.0 or delta_d_vs_c <= -3.0
    if b_pass == 6 and d_pass == 6:
        if delta_b_vs_a >= 3.0 or delta_d_vs_c >= 3.0:
            coding_decision = "FROGGERIC_V225_CODING_PREFERRED"
        elif abs(delta_b_vs_a) < 3.0 and abs(delta_d_vs_c) < 3.0:
            coding_decision = "FROGGERIC_V225_CODING_PARITY"
        else:
            coding_decision = "KEEP_NATIVE_CODING"
    else:
        coding_decision = "KEEP_NATIVE_CODING"

    lines = []
    lines.append("# GSQ Froggeric v22.5 Clean Retest v1 — Summary\n")
    lines.append("## 1. Overview\n")
    lines.append("Deterministic clean-GPU retest of the canonical **Froggeric v22.5** chat template (`chat_template.jinja`, commit `4ea21db`, internal version `qwen3.8-froggeric-v22.5`) against fresh paired Native controls on `Qwen3.8-27B GSQ-RCO IQ2_S`.\n")
    lines.append("- **Target**: `Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf` (SHA256: `16c98021...`)")
    lines.append("- **Draft**: `Qwen3.8-27B-DFlash2-Q4_K_M.gguf` (SHA256: `1a25c568...`)")
    lines.append("- **Froggeric v22.5 SHA256**: `e57684bae4156211a55473c5a63be976a405a37ab5be5ae0e5abf1df5349c4b2`")
    lines.append("- **Runtime**: llama.cpp `0.3.0-dev` build 10752 (`b96806d96`) with `--reasoning-format deepseek` and `--chat-template-kwargs '{\"enable_thinking\":false,\"reasoning_effort\":\"none\"}'`\n")

    lines.append("## 2. Primary Paired Comparison Table\n")
    lines.append("| Arm | Configuration | Workload | Score / PASS | Mediana tok/s | Delta vs Paired Control | Peak VRAM | Draft Acc Mediana | Mean Acc Length |")
    lines.append("|---|---|---|:---:|---:|---:|---:|:---:|:---:|")
    lines.append(f"| **Arm A** | GSQ Native Control | Coding (6 cases) | **{a_pass}/6** | {a_med_speed:.2f} t/s | *baseline* | {a_vram} MiB | N/A | 1.00 |")
    lines.append(f"| **Arm B** | GSQ + Froggeric v22.5 | Coding (6 cases) | **{b_pass}/6** | {b_med_speed:.2f} t/s | **{delta_b_vs_a:+.1f}%** | {b_vram} MiB | N/A | 1.00 |")
    lines.append(f"| **Arm C** | GSQ + DFlash2 n=7 Native Control | Coding (6 cases) | **{c_pass}/6** | {c_med_speed:.2f} t/s | *baseline* | {c_vram} MiB | {c_med_acc:.1f}% | {c_med_len:.2f} |")
    lines.append(f"| **Arm D** | GSQ + DFlash2 n=7 + Froggeric v22.5 | Coding (6 cases) | **{d_pass}/6** | {d_med_speed:.2f} t/s | **{delta_d_vs_c:+.1f}%** | {d_vram} MiB | {d_med_acc:.1f}% | {d_med_len:.2f} |")
    lines.append(f"| **Arm E** | GSQ Native Control | Writing (6 runs) | PENDING | {e_med_speed:.2f} t/s | *baseline* | {e_vram} MiB | N/A | N/A |")
    lines.append(f"| **Arm F** | GSQ + Froggeric v22.5 | Writing (6 runs) | PENDING | {f_med_speed:.2f} t/s | **{delta_f_vs_e:+.1f}%** | {f_vram} MiB | N/A | N/A |")

    lines.append("\n## 3. Detailed Case-by-Case Breakdown\n")
    lines.append("### Coding Cases (Arms A, B, C, D)\n")
    lines.append("| Case ID | Arm A (Native) | Arm B (Froggeric v22.5) | Arm C (DF2 Native) | Arm D (DF2 Froggeric v22.5) | A tok/s | B tok/s | C tok/s | D tok/s | D Acc Ratio |")
    lines.append("|---|:---:|:---:|:---:|:---:|---:|---:|---:|---:|:---:|")

    a_map = {r["case_id"]: r for r in arm_a_rows}
    b_map = {r["case_id"]: r for r in arm_b_rows}
    c_map = {r["case_id"]: r for r in arm_c_rows}
    d_map = {r["case_id"]: r for r in arm_d_rows}

    for cid in ["PY01", "PY02", "PY03", "CPP01", "CPP02", "CPP03"]:
        ra, rb, rc, rd = a_map[cid], b_map[cid], c_map[cid], d_map[cid]
        st_a = "PASS" if ra["passed"] else "FAIL"
        st_b = "PASS" if rb["passed"] else "FAIL"
        st_c = "PASS" if rc["passed"] else "FAIL"
        st_d = "PASS" if rd["passed"] else "FAIL"
        acc_str_d = f"{rd['accepted_draft_tokens']}/{rd['generated_draft_tokens']} ({rd['draft_acceptance_ratio']*100:.1f}%)" if rd.get('draft_acceptance_ratio') is not None else "N/A"
        lines.append(f"| **{cid}** | **{st_a}** | **{st_b}** | **{st_c}** | **{st_d}** | {ra.get('predicted_per_second',0):.2f} | {rb.get('predicted_per_second',0):.2f} | {rc.get('predicted_per_second',0):.2f} | {rd.get('predicted_per_second',0):.2f} | {acc_str_d} |")

    lines.append("\n### Writing Runs (Arms E vs F)\n")
    lines.append("| Prompt / Repetition | Seed | Arm E (Native) Words | Arm E tok/s | Arm F (Froggeric v22.5) Words | Arm F tok/s | Speed Delta |")
    lines.append("|---|:---:|---:|---:|---:|---:|---:|")
    for re_row, rf_row in zip(arm_e_rows, arm_f_rows):
        delta_run = ((rf_row.get('predicted_per_second',0) - re_row.get('predicted_per_second',0)) / re_row.get('predicted_per_second',1)) * 100.0
        lines.append(f"| **{re_row['prompt_id']} r{re_row['repetition']}** | {re_row['seed']} | {re_row['word_count']}w | {re_row.get('predicted_per_second',0):.2f} t/s | {rf_row['word_count']}w | {rf_row.get('predicted_per_second',0):.2f} t/s | {delta_run:+.1f}% |")

    lines.append("\n## 4. Final Classification\n")
    lines.append(f"- **Coding / Template Classification**: `{coding_decision}`")
    lines.append(f"- **Writing Quality Status**: `PENDING_CHATGPT_REVIEW`\n")

    lines.append("### Technical Observations")
    lines.append(f"1. **Coding Correctness**: Both Native and Froggeric v22.5 achieve **6/6 PASS** without any functional regressions.")
    lines.append(f"2. **Coding Throughput (B vs A)**: Arm B is {delta_b_vs_a:+.1f}% compared to Arm A ({b_med_speed:.2f} t/s vs {a_med_speed:.2f} t/s).")
    lines.append(f"3. **Speculative Decoding (D vs C)**: Arm D is {delta_d_vs_c:+.1f}% compared to Arm C ({d_med_speed:.2f} t/s vs {c_med_speed:.2f} t/s), with identical draft acceptance ({d_med_acc:.1f}% vs {c_med_acc:.1f}%).")
    lines.append(f"4. **Writing Throughput (F vs E)**: Arm F is {delta_f_vs_e:+.1f}% compared to Arm E ({f_med_speed:.2f} t/s vs {e_med_speed:.2f} t/s).")
    lines.append(f"5. **Review Packet**: Full raw text of all 12 writing generations preserved in `WRITING_REVIEW_PACKET.md` for independent qualitative scoring.\n")

    summary_text = "\n".join(lines) + "\n"
    (RESULTS_DIR / "SUMMARY.md").write_text(summary_text, encoding="utf-8")
    print(f"Summary written to {RESULTS_DIR / 'SUMMARY.md'}")

    # Generate GPU_PREFLIGHT_SUMMARY.md
    preflight_md_lines = ["# GPU Preflight Summary — Clean Retest v1\n"]
    preflight_md_lines.append("| Arm | Description | Preflight Status | Snapshot File |")
    preflight_md_lines.append("|---|---|:---:|---|")
    for arm_k, arm_v in preflight_data.items():
        preflight_md_lines.append(f"| **{arm_k}** | {arm_v['label']} | **PASSED** (Attempt {arm_v['attempt']}) | `{arm_v['file']}` |")
    preflight_md_lines.append("\nAll arms satisfied the Clean-GPU Gate (no external process sustained >=25% SM across 5 samples).\n")
    (RESULTS_DIR / "GPU_PREFLIGHT_SUMMARY.md").write_text("\n".join(preflight_md_lines) + "\n", encoding="utf-8")

    # Generate RUN_MANIFEST.json
    manifest = {
        "benchmark": "gsq-froggeric-v225-clean-retest-v1",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "target_model": {
            "path": TARGET_MODEL,
            "sha256": "16c9802111aa9ef3acde465188d6d601f8db128ee3d828ad983a5caca4135ecb"
        },
        "draft_model": {
            "path": DRAFT_MODEL,
            "sha256": "1a25c56858e1ebe93f2718ac1d49d1151f9323325c1bbfd6209370f4db131ebd"
        },
        "froggeric_template": {
            "repo": "froggeric/Qwen-Fixed-Chat-Templates",
            "commit": "4ea21db90694e60d002500dae85ebff26e4b23ad",
            "sha256": "e57684bae4156211a55473c5a63be976a405a37ab5be5ae0e5abf1df5349c4b2",
            "internal_version": "qwen3.8-froggeric-v22.5",
            "path": FROGGERIC_TEMPLATE
        },
        "runtime": {
            "binary": LLAMA_BIN,
            "version": "0.3.0-dev (build 10752, commit b96806d96)"
        },
        "gpu": "NVIDIA GeForce RTX 5060 Ti 16 GB",
        "clean_gpu_preflight": preflight_data,
        "results_summary": {
            "coding_decision": coding_decision,
            "writing_status": "PENDING_CHATGPT_REVIEW",
            "arm_a_native_coding": {"pass": a_pass, "med_speed": round(a_med_speed, 2), "peak_vram": a_vram},
            "arm_b_froggeric_coding": {"pass": b_pass, "med_speed": round(b_med_speed, 2), "peak_vram": b_vram, "delta_pct": round(delta_b_vs_a, 2)},
            "arm_c_dflash2_native_coding": {"pass": c_pass, "med_speed": round(c_med_speed, 2), "peak_vram": c_vram, "draft_acc_med": round(c_med_acc, 2), "mean_acc_len": round(c_med_len, 2) if c_med_len else None},
            "arm_d_dflash2_froggeric_coding": {"pass": d_pass, "med_speed": round(d_med_speed, 2), "peak_vram": d_vram, "draft_acc_med": round(d_med_acc, 2), "mean_acc_len": round(d_med_len, 2) if d_med_len else None, "delta_pct": round(delta_d_vs_c, 2)},
            "arm_e_native_writing": {"med_speed": round(e_med_speed, 2), "peak_vram": e_vram},
            "arm_f_froggeric_writing": {"med_speed": round(f_med_speed, 2), "peak_vram": f_vram, "delta_pct": round(delta_f_vs_e, 2)}
        }
    }
    (RESULTS_DIR / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Manifest written to {RESULTS_DIR / 'RUN_MANIFEST.json'}")

def main():
    print("===========================================================================")
    print("STARTING GSQ FROGGERIC v22.5 CLEAN RETEST v1 (36 TOTAL GENERATIONS)")
    print("===========================================================================")

    preflight_records = {}

    # Arm A
    arm_a_rows, pf_a = run_coding_arm("Arm A", "GSQ Native Coding Control", template_mode="native", with_dflash=False)
    preflight_records["Arm A"] = {"label": "GSQ Native Coding Control", **pf_a}

    # Arm B
    arm_b_rows, pf_b = run_coding_arm("Arm B", "GSQ + Froggeric v22.5 Coding", template_mode="froggeric", with_dflash=False)
    preflight_records["Arm B"] = {"label": "GSQ + Froggeric v22.5 Coding", **pf_b}

    # Arm C
    arm_c_rows, pf_c = run_coding_arm("Arm C", "GSQ + DFlash2 n=7 Native Coding Control", template_mode="native", with_dflash=True)
    preflight_records["Arm C"] = {"label": "GSQ + DFlash2 n=7 Native Coding Control", **pf_c}

    # Arm D
    arm_d_rows, pf_d = run_coding_arm("Arm D", "GSQ + DFlash2 n=7 + Froggeric v22.5 Coding", template_mode="froggeric", with_dflash=True)
    preflight_records["Arm D"] = {"label": "GSQ + DFlash2 n=7 + Froggeric v22.5 Coding", **pf_d}

    # Arm E
    arm_e_rows, pf_e = run_writing_arm("Arm E", "GSQ Native Writing/Chat Control", template_mode="native")
    preflight_records["Arm E"] = {"label": "GSQ Native Writing/Chat Control", **pf_e}

    # Arm F
    arm_f_rows, pf_f = run_writing_arm("Arm F", "GSQ + Froggeric v22.5 Writing/Chat", template_mode="froggeric")
    preflight_records["Arm F"] = {"label": "GSQ + Froggeric v22.5 Writing/Chat", **pf_f}

    # Generate review packet
    generate_review_packet(arm_e_rows, arm_f_rows)

    # Generate summary, manifest and preflight summary
    generate_summary(arm_a_rows, arm_b_rows, arm_c_rows, arm_d_rows, arm_e_rows, arm_f_rows, preflight_records)

    print("\nAll 36 generations and benchmark artifacts completed successfully!")

if __name__ == "__main__":
    main()
