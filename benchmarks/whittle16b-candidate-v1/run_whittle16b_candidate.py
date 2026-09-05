#!/usr/bin/env python3
"""
Whittle 16B v2 Candidate Full Pipeline per SPEC.md
Implements STAGE A, B, C with gates, logging, manifests, summary, profile.
"""
import json
import os
import re
import hashlib
import subprocess
import threading
import time
import urllib.request
import urllib.error
import statistics
import datetime
from pathlib import Path

ROOT = Path("/home/alpha/Playstoria/models").resolve()
BENCH_DIR = ROOT / "benchmarks/whittle16b-candidate-v1"
RESULTS_DIR = BENCH_DIR / "results"
PREFLIGHT_DIR = RESULTS_DIR / "gpu-preflight"
LOGS_DIR = RESULTS_DIR / "logs"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
PREFLIGHT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Paths
MODEL_DIR = ROOT / "text/logic65-Qwen3.8-Whittle-16B-v2-Q4_K_M"
MODEL_GGUF = MODEL_DIR / "Qwen3.8-Whittle-16B-v2-Q4_K_M.gguf"
PROFILE_MD = MODEL_DIR / "Qwen3.8-Whittle-16B-v2-Q4_K_M.md"

DRAFT_MODEL = ROOT / "text/z-lab-Qwen3.8-27B-DFlash2-GGUF/Qwen3.8-27B-DFlash2-Q4_K_M.gguf"

# Benchmark sources
PROMPTS_FILE = ROOT / "benchmarks/coding-mini-v1/prompts.json"
PROMPTS = json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))
CASES_FILE = ROOT / "benchmarks/gsq-froggeric-agent-tools-v1/CASES.json"
CASES_DATA = json.loads(CASES_FILE.read_text(encoding="utf-8"))

# Add evaluate to path
import sys
sys.path.insert(0, str(ROOT / "benchmarks/coding-mini-v1"))
from evaluate import evaluate_case

LLAMA_BIN = Path.home() / ".local/bin/llama"
# Also check alternative
real_llama = ROOT / "engines/llama.cpp/build/bin/llama-server"

# Config per SPEC
SEED = 9137
TEMP_AUTHOR = 0.7
TOP_P_AUTHOR = 0.95
MIN_P_AUTHOR = 0.05
CTX = 8192
THREADS = 8
PORT_A = 8197
PORT_B = 8198
PORT_C = 8197

# Sampling author recipe: dry, repeat penalty
DRY_MULTIPLIER = 0.8
DRY_BASE = 1.75
DRY_ALLOWED = 4
REPEAT_PENALTY = 1.15
REPEAT_LAST_N = 512

# Completion budget at least 2048, use 3072 for safety (PY original 1536 -> 3072, CPP 2048 -> 3072)
MAX_TOKENS_AUTHOR = 3072  # ensures thinking + code fits, at least 2048

# Historical controls (do not rerun)
HIST_GSQ_BASE = {"pass": "6/6", "tok_s": 24.70}
HIST_GSQ_DFLASH2 = {"pass": "6/6", "tok_s": 46.00}
HIST_GSQ_AGENT = {"strict": "7/8", "score": "70/80"}
HIST_WHITTLE_MOE = {"pass": "1/6", "tok_s": 19.39, "vram": 15194}

def log(msg):
    print(msg, flush=True)

def vram_mib():
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], text=True, timeout=5)
        return int(out.strip().splitlines()[0])
    except Exception:
        return None

def run_cmd(cmd, timeout=5):
    try:
        return subprocess.check_output(cmd, text=True, timeout=timeout)
    except Exception as e:
        return f"ERROR: {e}"

def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8*1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def gguf_metadata(path: Path):
    # Try using gguf-dump via python library if available, fallback to simple
    try:
        # Use gguf-py reader
        sys.path.insert(0, str(ROOT / "engines/geo-llama/gguf-py"))
        from gguf import GGUFReader
        r = GGUFReader(str(path))
        fields = {}
        for f in r.fields.values():
            try:
                name = f.name
                # try to get value
                # fields have different types, just capture some
                if name in ["general.architecture", "general.name", "tokenizer.ggml.model", "general.quantization_version", "general.file_type"]:
                    fields[name] = str(f.parts[0] if hasattr(f, 'parts') else f.data)
            except:
                pass
        # Also try to get architecture via header
        arch = None
        quant = None
        # simple fallback
        return fields
    except Exception as e:
        return {"error": str(e)}

def get_runtime_version():
    try:
        out = subprocess.check_output([str(LLAMA_BIN), "version"], text=True, timeout=10)
        return out.strip()
    except Exception as e:
        try:
            out2 = subprocess.check_output([str(real_llama), "--version"], text=True, timeout=10)
            return out2.strip()
        except Exception as e2:
            return f"ERROR {e} / {e2}"

def run_gpu_preflight(stage_name, output_file: Path, max_retries=10, retry_delay=5):
    log(f"\n[Preflight] Checking Clean-GPU Gate for {stage_name}...")
    for attempt in range(1, max_retries+1):
        smi_out = run_cmd(["nvidia-smi"], timeout=5)
        # 5 samples, 1 sec apart
        pmon_out = run_cmd(["nvidia-smi", "pmon", "-s", "u", "-c", "5", "-d", "1"], timeout=10)
        # Parse pmon
        sm_counts = {}
        # Need to group per pid across 5 samples
        # pmon output includes header lines starting with #
        # Sample count = 5 cycles, each cycle lists pids. So we count occurrences per pid where sm>=25
        for line in pmon_out.splitlines():
            line=line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            # columns: # gpu pid type sm mem enc dec jpg ofa command
            # typical: 0 1234 C+G 8 5 - - - - cmd
            pid = parts[1]
            sm_str = parts[3]
            # cmd is last column, parts[8] onwards
            cmd = parts[8] if len(parts)>8 else ""
            # ignore our own processes: llama, llama-server, python
            if cmd in ("llama", "llama-server", "python", "python3", "llama-server-impl"):
                continue
            # also ignore if pid is our python process? not needed
            try:
                sm_val = int(sm_str.replace('-','0'))
                if sm_val >= 25:
                    sm_counts[pid] = sm_counts.get(pid, 0) + 1
            except:
                pass
        heavy = [pid for pid,c in sm_counts.items() if c>=3]
        content = f"=== NVIDIA-SMI ===\n{smi_out}\n\n=== PMON (5 samples, 1s) ===\n{pmon_out}\n\nCounts >=25% SM per PID: {sm_counts}\nHeavy PIDs (>=3 samples >=25%): {heavy}\nAttempt: {attempt}\n"
        if not heavy:
            log(f"[Preflight] Clean-GPU Gate PASSED for {stage_name} on attempt {attempt}")
            output_file.write_text(content + "\nClean Gate: PASSED\n", encoding="utf-8")
            return {
                "passed": True,
                "attempt": attempt,
                "file": str(output_file.relative_to(ROOT)),
                "smi_snapshot": smi_out[:4000],
                "pmon_snapshot": pmon_out[:8000]
            }
        log(f"[Preflight] Attempt {attempt}/{max_retries}: Heavy external GPU load PIDs {heavy} counts {sm_counts} -> wait {retry_delay}s")
        if attempt == max_retries:
            output_file.write_text(content + "\nClean Gate: FAILED\n", encoding="utf-8")
            raise RuntimeError(f"Clean-GPU Gate FAILED for {stage_name} after {max_retries}")
        time.sleep(retry_delay)
    raise RuntimeError("preflight exhausted")

def wait_health(port, timeout=180):
    deadline = time.time()+timeout
    while time.time()<deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as r:
                data=json.loads(r.read().decode())
                if data.get("status")=="ok":
                    return True
        except Exception:
            time.sleep(1)
    return False

def post_stream(payload, port):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
    started=time.perf_counter()
    first_token=None
    content_parts=[]
    reasoning_parts=[]
    usage={}
    timings={}
    finish_reason=None
    peak=vram_mib()
    stop=threading.Event()
    def sampler():
        nonlocal peak
        while not stop.wait(0.05):
            v=vram_mib()
            if v is not None and (peak is None or v>peak):
                peak=v
    th=threading.Thread(target=sampler, daemon=True)
    th.start()
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            for line_bytes in resp:
                line=line_bytes.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                item=line[5:].strip()
                if item=="[DONE]":
                    break
                try:
                    chunk=json.loads(item)
                except:
                    continue
                choices=chunk.get("choices") or []
                if choices:
                    c0=choices[0]
                    if c0.get("finish_reason"):
                        finish_reason=c0.get("finish_reason")
                    delta=c0.get("delta") or {}
                    # message variant
                    c=delta.get("content") or ""
                    r=delta.get("reasoning_content") or delta.get("reasoning") or ""
                    # legacy think tags in content
                    if c:
                        if first_token is None:
                            first_token=time.perf_counter()
                        content_parts.append(c)
                    if r:
                        reasoning_parts.append(r)
                if chunk.get("usage"):
                    usage=chunk["usage"]
                if chunk.get("timings"):
                    timings=chunk["timings"]
                # some servers send usage in last chunk as choices finish
                # also timings may be nested?
    except urllib.error.HTTPError as e:
        body=e.read().decode(errors="replace")
        finish_reason=f"HTTPError {e.code}: {body[:500]}"
        content_parts.append(body)
    except Exception as e:
        finish_reason=f"Error {e}"
    finally:
        stop.set()
        th.join(timeout=2)
    ended=time.perf_counter()
    text="".join(content_parts).strip()
    reasoning_text="".join(reasoning_parts).strip()
    return {
        "text": text,
        "reasoning_text": reasoning_text,
        "finish_reason": finish_reason,
        "usage": usage,
        "timings": timings,
        "wall_time_s": round(ended-started,4),
        "ttft_s": None if first_token is None else round(first_token-started,4),
        "peak_vram_mib": peak,
        "raw_content_len": len(text),
        "raw_reasoning_len": len(reasoning_text),
    }

def detect_loop_truncation(text, reasoning_text, finish_reason, max_tokens):
    # truncation detection
    truncated=False
    loop=False
    # finish_reason length indicates truncation
    if finish_reason=="length":
        truncated=True
    elif finish_reason and "length" in str(finish_reason):
        truncated=True
    # completion_tokens near max_tokens
    # loop detection: repeated lines or repeated 20-char sequences
    # simple check: if text contains same line repeated 5+ times
    lines=text.splitlines()
    if len(lines)>10:
        # check repeating block
        for i in range(len(lines)-5):
            if lines[i]==lines[i+1]==lines[i+2]==lines[i+3]==lines[i+4]:
                loop=True
                break
    # also check for very long repetition of token substring
    # if text length > 1000 and repeated substring
    if not loop and len(text)>500:
        # check if any 50-char substring repeats 5 times consecutively? approximate
        for window in [20,30,50]:
            for i in range(0, min(len(text)-window*5, 2000), window):
                segment=text[i:i+window]
                if segment.strip() and text.count(segment) > 20:
                    # potential loop but not definitive
                    # check consecutive
                    if segment*3 in text:
                        loop=True
                        break
            if loop:
                break
    thinking_finished = True
    # If reasoning_text exists, thinking should have finished. If text still contains <think> without closing, then not finished.
    combined = reasoning_text + " " + text
    if "<think>" in text or "<think>" in reasoning_text:
        # check if closing tag exists
        if combined.count("<think>") > combined.count("</think>"):
            thinking_finished=False
    # For reasoning_content separate, we assume finished if finish_reason is stop and we got content
    if finish_reason and "length" in str(finish_reason):
        thinking_finished=False
    return {"truncated": truncated, "loop": loop, "thinking_finished": thinking_finished}

def prepare_model_metadata():
    log("\n[Metadata] Collecting GGUF metadata...")
    if not MODEL_GGUF.exists():
        raise FileNotFoundError(f"GGUF not found at {MODEL_GGUF}")
    size_bytes = MODEL_GGUF.stat().st_size
    size_gib = size_bytes / (1024**3)
    log(f"  Size bytes: {size_bytes} ({size_gib:.2f} GiB)")
    log(f"  Computing SHA256 (may take ~30s)...")
    sha = sha256_file(MODEL_GGUF)
    log(f"  SHA256: {sha}")
    # HF revision
    hf_revision = "unknown"
    hf_repo = "logic65/Qwen3.8-Whittle-16B"
    # Try to read from cache snapshot
    try:
        cache_ref = Path.home() / ".cache/huggingface/hub/models--logic65--Qwen3.8-Whittle-16B/refs/main"
        if cache_ref.exists():
            hf_revision = cache_ref.read_text().strip()
    except:
        pass
    # Also try to get snapshot dir name
    try:
        snap_dir = Path.home() / ".cache/huggingface/hub/models--logic65--Qwen3.8-Whittle-16B/snapshots"
        if snap_dir.exists():
            subs = list(snap_dir.iterdir())
            if subs:
                # prefer dir that contains gguf
                for s in subs:
                    if (s/"gguf").exists():
                        hf_revision = s.name
                        break
                else:
                    hf_revision = subs[0].name
    except:
        pass
    log(f"  HF revision: {hf_revision}")
    # GGUF metadata
    gguf_meta = gguf_metadata(MODEL_GGUF)
    log(f"  GGUF meta sample: {str(gguf_meta)[:1000]}")
    # Runtime version
    runtime_ver = get_runtime_version()
    log(f"  Runtime: {runtime_ver}")
    # Also try to get file command
    arch_quant = "unknown"
    try:
        # try to extract via strings? Use gguf dump if available
        # Fallback: use python gguf reader to get general fields
        import sys
        sys.path.insert(0, str(ROOT / "engines/geo-llama/gguf-py"))
        from gguf import GGUFReader
        reader = GGUFReader(str(MODEL_GGUF))
        # Count layers, arch etc.
        # Dump some fields
        fields_str=""
        for k,v in reader.fields.items():
            if k in ["general.architecture","general.basename","general.size_label","general.quantization_version"]:
                try:
                    fields_str += f"{k}={v} "
                except: pass
        gguf_meta["reader_fields"] = fields_str
    except Exception as e:
        gguf_meta["reader_error"] = str(e)
    return {
        "size_bytes": size_bytes,
        "size_gib": round(size_gib,2),
        "sha256": sha,
        "hf_repo": hf_repo,
        "hf_revision": hf_revision,
        "hf_gguf_path": "gguf/Qwen3.8-Whittle-16B-v2-Q4_K_M.gguf",
        "gguf_metadata": gguf_meta,
        "runtime_version": runtime_ver,
        "filename": MODEL_GGUF.name,
    }

def server_args_base(port, mode="native"):
    # Common args per SPEC: RTX 5060 Ti 16GB, 8 threads, full offload, FA on, fit off, ctx 8192, np1, q8_0/q4_0
    args = [
        str(LLAMA_BIN), "serve",
        "-m", str(MODEL_GGUF),
        "--host", "127.0.0.1", "--port", str(port),
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
        # Author anti-loop recipe
        "--dry-multiplier", str(DRY_MULTIPLIER),
        "--dry-base", str(DRY_BASE),
        "--dry-allowed-length", str(DRY_ALLOWED),
        "--repeat-penalty", str(REPEAT_PENALTY),
        "--repeat-last-n", str(REPEAT_LAST_N),
        "--no-webui",
    ]
    if mode == "native":
        # Thinking enabled native
        args.extend([
            "--reasoning", "on",
            "--reasoning-format", "auto",
            # enable thinking in template
            "--chat-template-kwargs", json.dumps({"enable_thinking": True}, separators=(",", ":")),
        ])
    elif mode == "dflash2":
        args.extend([
            "-md", str(DRAFT_MODEL),
            "--spec-type", "draft-dflash",
            "--spec-draft-n-max", "7",
            "-ngld", "999",
            "--reasoning", "on",
            "--reasoning-format", "auto",
            "--chat-template-kwargs", json.dumps({"enable_thinking": True}, separators=(",", ":")),
        ])
    elif mode == "agent":
        args.extend([
            "--reasoning", "on",
            "--reasoning-format", "auto",
            "--chat-template-kwargs", json.dumps({"enable_thinking": True, "tool_call_format": "json"}, separators=(",", ":")),
        ])
    return args

def start_server(port, mode, log_path: Path):
    args = server_args_base(port, mode)
    log(f"  Server args: {' '.join(args[:20])} ...")
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = f"{ROOT}/engines/llama.cpp/build/bin:{env.get('LD_LIBRARY_PATH','')}"
    log_fp = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(args, stdout=log_fp, stderr=subprocess.STDOUT, env=env)
    return proc, log_fp

def wait_health_wrapper(port, proc, log_path):
    if not wait_health(port, timeout=180):
        log(f"  Server failed to start, log tail:")
        try:
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
            log(tail)
        except:
            pass
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except:
            try: proc.kill()
            except: pass
        raise RuntimeError(f"Server on port {port} failed to become healthy")

# STAGE A
def run_stage_a(metadata, preflight_info):
    log("\n"+"="*80)
    log("STAGE A — Native Whittle 16B coding gate (AUTHOR_RECIPE, thinking ON)")
    log("="*80)
    port = PORT_A
    subprocess.run(["pkill","-9","-f", f"--port {port}"], capture_output=True)
    time.sleep(2)
    log_path = LOGS_DIR / "server-whittle16b-native.log"
    # ensure clean
    if log_path.exists():
        log_path.unlink()
    proc, log_fp = start_server(port, mode="native", log_path=log_path)
    rows=[]
    try:
        log("  Waiting for server healthy...")
        wait_health_wrapper(port, proc, log_path)
        log("  Server healthy! Warmup...")
        # warmup with short prompt
        warm = post_stream({
            "messages": [{"role":"user","content":"Write a one-line Python comment."}],
            "max_tokens": 16,
            "temperature": TEMP_AUTHOR,
            "top_p": TOP_P_AUTHOR,
            "seed": SEED,
            "stream": True
        }, port)
        log(f"  Warmup done: {warm['wall_time_s']}s ttft {warm['ttft_s']} peak {warm['peak_vram_mib']}")
        for case in PROMPTS:
            cid=case["id"]
            cname=case["name"]
            lang=case["language"]
            # Use author max_tokens at least 2048, we use MAX_TOKENS_AUTHOR (3072)
            max_tok = max(MAX_TOKENS_AUTHOR, case.get("max_tokens", 2048))
            # For CPP hard maybe need more
            if cid=="CPP03":
                max_tok = max(max_tok, 3072)
            log(f"\n-> Executing {cid} ({cname}) {lang} max_tokens={max_tok} ...")
            payload={
                "messages": [{"role":"user","content":case["prompt"]}],
                "temperature": TEMP_AUTHOR,
                "top_p": TOP_P_AUTHOR,
                "min_p": MIN_P_AUTHOR,
                "seed": SEED,
                "max_tokens": max_tok,
                "stream": True
            }
            res=post_stream(payload, port)
            eval_res=evaluate_case(cid, res["text"])
            timings=res.get("timings",{})
            usage=res.get("usage",{})
            # Detect loop/truncation
            detect=detect_loop_truncation(res["text"], res["reasoning_text"], res["finish_reason"], max_tok)
            # reasoning terminated cleanly?
            # Combine reasoning + text length
            completion_len = usage.get("completion_tokens")
            if completion_len is None:
                # fallback estimate via predicted_n
                completion_len = timings.get("predicted_n")
            row={
                "case_id": cid,
                "case_name": cname,
                "language": lang,
                "difficulty": case.get("difficulty"),
                "seed": SEED,
                "temperature": TEMP_AUTHOR,
                "top_p": TOP_P_AUTHOR,
                "min_p": MIN_P_AUTHOR,
                "max_tokens": max_tok,
                "prompt": case["prompt"][:200] + "...",  # truncated for storage, but keep full elsewhere? For json we keep prompt full maybe large
                "raw_text": res["text"],
                "reasoning_text": res["reasoning_text"],
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
                "completion_len": completion_len,
                "raw_content_len_chars": len(res["text"]),
                "reasoning_len_chars": len(res["reasoning_text"]),
                "truncated": detect["truncated"],
                "loop_detected": detect["loop"],
                "thinking_finished": detect["thinking_finished"],
                "model_id": "whittle16b_v2_q4km_author_recipe",
                "model_name": "logic65/Qwen3.8-Whittle-16B-v2-Q4_K_M (AUTHOR_RECIPE thinking ON)",
            }
            # Also keep full prompt for evaluation? Already evaluated
            status="PASS" if row["passed"] else f"FAIL (compile={row['compile_pass']}, pub={row['public_pass']}, hid={row['hidden_pass']})"
            log(f"   [{cid}] {status} | tok/s {row.get('predicted_per_second')} | prompt_tok/s {row.get('prompt_per_second')} | wall {row['wall_time_s']}s | TTFT {row['ttft_s']}s | VRAM {row['peak_vram_mib']}MiB | comp_len {row['completion_len']} | finish {row['finish_reason']} | trunc {row['truncated']} loop {row['loop_detected']} thinking_ok {row['thinking_finished']}")
            if not row["passed"] and row.get("eval_error"):
                log(f"      eval_error: {row['eval_error'][:500]}")
            rows.append(row)
            # small sleep to let GPU stabilize
            time.sleep(0.5)
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except:
            try: proc.kill()
            except: pass
        log_fp.close()
        subprocess.run(["pkill","-9","-f", f"--port {port}"], capture_output=True)
        time.sleep(2)
    # Write jsonl
    out_path = RESULTS_DIR / "WHITTLE16B_NATIVE_CODING.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False)+"\n")
    log(f"\n[STAGE A] Completed. Results written to {out_path}")
    # Summary stats
    total_pass=sum(1 for r in rows if r["passed"])
    py_pass=sum(1 for r in rows if r["passed"] and r["language"]=="python")
    cpp_pass=sum(1 for r in rows if r["passed"] and r["language"]=="cpp")
    speeds=[r["predicted_per_second"] for r in rows if r.get("predicted_per_second") is not None]
    med_speed=statistics.median(speeds) if speeds else None
    peak_vram=max((r["peak_vram_mib"] for r in rows if r.get("peak_vram_mib")), default=None)
    log(f"[STAGE A] PASS {total_pass}/6 (PY {py_pass}/3 CPP {cpp_pass}/3) med tok/s {med_speed} peak VRAM {peak_vram}")
    return rows, total_pass, med_speed, peak_vram

def run_stage_b_smoke(metadata, preflight_info):
    log("\n"+"="*80)
    log("STAGE B — DFLASH2 SMOKE (PY01 only)")
    log("="*80)
    port=PORT_B
    subprocess.run(["pkill","-9","-f", f"--port {port}"], capture_output=True)
    time.sleep(2)
    log_path = LOGS_DIR / "server-whittle16b-dflash2-smoke.log"
    if log_path.exists():
        log_path.unlink()
    proc, log_fp = start_server(port, mode="dflash2", log_path=log_path)
    smoke_result=None
    status="UNKNOWN"
    try:
        log("  Waiting for DFlash2 server healthy...")
        if not wait_health(port, timeout=180):
            # Check log for errors
            log_tail=""
            try:
                log_tail=log_path.read_text(encoding="utf-8", errors="replace")[-8000:]
            except: pass
            log(f"  Smoke health failed, log tail:\n{log_tail}")
            # Mark incompatible
            smoke_result={"compatible": False, "error": "health timeout", "log": log_tail}
            status="DFLASH2_INCOMPATIBLE_OR_UNUSABLE"
        else:
            log("  Server healthy! Smoke warmup...")
            warm=post_stream({"messages":[{"role":"user","content":"Write a one-line Python comment."}],"max_tokens":16,"temperature":TEMP_AUTHOR,"top_p":TOP_P_AUTHOR,"seed":SEED,"stream":True}, port)
            log(f"  Warmup {warm['wall_time_s']}s")
            # Find PY01 prompt
            py01 = next(c for c in PROMPTS if c["id"]=="PY01")
            max_tok = max(MAX_TOKENS_AUTHOR, py01.get("max_tokens",2048))
            payload={"messages":[{"role":"user","content":py01["prompt"]}],"temperature":TEMP_AUTHOR,"top_p":TOP_P_AUTHOR,"min_p":MIN_P_AUTHOR,"seed":SEED,"max_tokens":max_tok,"stream":True}
            res=post_stream(payload, port)
            eval_res=evaluate_case("PY01", res["text"])
            timings=res.get("timings",{})
            usage=res.get("usage",{})
            # Check for errors in log: look for draft acceptance or errors
            log_fp.flush()
            log_text=""
            try:
                log_text=log_path.read_text(encoding="utf-8", errors="replace")[-8000:]
            except: pass
            # Detect incompatibility markers
            incompat_keywords=["vocab","tokenizer","speculative","draft","mismatch","OOM","out of memory","incompatible","failed to load","BABORT","exception"]
            lower_log=log_text.lower()
            has_error=False
            err_detail=""
            for kw in incompat_keywords:
                if kw.lower() in lower_log and "error" in lower_log:
                    # Need more precise: look for error lines
                    pass
            # Actually check if server returned error or text empty or compile fails due to weird output
            # We consider smoke PASS if we got valid code and no obvious server error and finish_reason not error
            if res["finish_reason"] and "HTTPError" in str(res["finish_reason"]):
                has_error=True
                err_detail=res["finish_reason"]
            elif not res["text"]:
                has_error=True
                err_detail="empty output"
            elif "incompatible" in lower_log or "vocab" in lower_log and "mismatch" in lower_log:
                has_error=True
                err_detail="vocab mismatch in log"
            # Also check timings for draft metrics
            draft_acceptance=None
            accepted=None
            generated=None
            mean_len=None
            # parse draft acceptance from log (like earlier pattern)
            matches=list(re.finditer(r"draft acceptance\s*=\s*([\d.]+)\s*\(\s*(\d+)\s+accepted\s*/\s*(\d+)\s+generated\)(?:,\s*mean len\s*=\s*([\d.]+))?", log_text))
            if matches:
                last=matches[-1]
                draft_acceptance=float(last.group(1))
                accepted=int(last.group(2))
                generated=int(last.group(3))
                mean_len=float(last.group(4)) if last.group(4) else None
            log(f"  PY01 smoke result: compile {eval_res['compile_pass']} pub {eval_res['public_pass']} hid {eval_res['hidden_pass']} passed {eval_res['passed']}")
            log(f"  draft acceptance {draft_acceptance} {accepted}/{generated} mean {mean_len}")
            log(f"  wall {res['wall_time_s']} ttft {res['ttft_s']} vram {res['peak_vram_mib']} finish {res['finish_reason']}")
            if has_error:
                smoke_result={"compatible": False, "error": err_detail, "log": log_text, "res": res, "eval": eval_res}
                status="DFLASH2_INCOMPATIBLE_OR_UNUSABLE"
            else:
                # Even if compile fails due to model logic, we still consider compatible if server didn't crash
                # But if output is invalid gibberish, that counts as unusable
                # We'll consider compatible if server responded and timings present
                smoke_result={"compatible": True, "res": res, "eval": eval_res, "draft": {"acceptance":draft_acceptance,"accepted":accepted,"generated":generated,"mean":mean_len}, "log": log_text}
                status="DFLASH2_COMPATIBLE"
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except:
            try: proc.kill()
            except: pass
        log_fp.close()
        subprocess.run(["pkill","-9","-f", f"--port {port}"], capture_output=True)
        time.sleep(2)
    # Move smoke log to dflash2 log if not incompatible? Keep both
    # Also save smoke result json
    smoke_out = RESULTS_DIR / "WHITTLE16B_DFLASH2_SMOKE.json"
    smoke_out.write_text(json.dumps({"status": status, "result": smoke_result}, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"  Smoke status: {status}")
    return status, smoke_result

def run_stage_b_full(metadata):
    log("\n"+"="*80)
    log("STAGE B — DFLASH2 FULL (6 cases)")
    log("="*80)
    port=PORT_B
    subprocess.run(["pkill","-9","-f", f"--port {port}"], capture_output=True)
    time.sleep(2)
    log_path = LOGS_DIR / "server-whittle16b-dflash2.log"
    if log_path.exists():
        log_path.unlink()
    proc, log_fp = start_server(port, mode="dflash2", log_path=log_path)
    rows=[]
    try:
        log("  Waiting for DFlash2 server healthy...")
        wait_health_wrapper(port, proc, log_path)
        log("  Healthy! Warmup...")
        warm=post_stream({"messages":[{"role":"user","content":"Write a one-line Python comment."}],"max_tokens":16,"temperature":TEMP_AUTHOR,"top_p":TOP_P_AUTHOR,"seed":SEED,"stream":True}, port)
        log(f"  Warmup done {warm['wall_time_s']}s")
        last_log_pos=0
        try:
            last_log_pos=log_fp.tell()
        except:
            last_log_pos=0
        for case in PROMPTS:
            cid=case["id"]
            cname=case["name"]
            max_tok=max(MAX_TOKENS_AUTHOR, case.get("max_tokens",2048))
            if cid=="CPP03":
                max_tok=max(max_tok,3072)
            log(f"\n-> DFlash2 executing {cid} ({cname}) max_tokens {max_tok}")
            payload={"messages":[{"role":"user","content":case["prompt"]}],"temperature":TEMP_AUTHOR,"top_p":TOP_P_AUTHOR,"min_p":MIN_P_AUTHOR,"seed":SEED,"max_tokens":max_tok,"stream":True}
            res=post_stream(payload, port)
            eval_res=evaluate_case(cid, res["text"])
            timings=res.get("timings",{})
            usage=res.get("usage",{})
            detect=detect_loop_truncation(res["text"], res["reasoning_text"], res["finish_reason"], max_tok)
            # parse draft metrics incremental
            log_fp.flush()
            draft_metrics={"draft_acceptance_ratio":None,"accepted_draft_tokens":None,"generated_draft_tokens":None,"mean_accepted_draft_length":None}
            try:
                with log_path.open("r", encoding="utf-8", errors="replace") as lf:
                    lf.seek(last_log_pos)
                    new_text=lf.read()
                    last_log_pos=lf.tell()
                matches=list(re.finditer(r"draft acceptance\s*=\s*([\d.]+)\s*\(\s*(\d+)\s+accepted\s*/\s*(\d+)\s+generated\)(?:,\s*mean len\s*=\s*([\d.]+))?", new_text))
                if matches:
                    last=matches[-1]
                    draft_metrics["draft_acceptance_ratio"]=float(last.group(1))
                    draft_metrics["accepted_draft_tokens"]=int(last.group(2))
                    draft_metrics["generated_draft_tokens"]=int(last.group(3))
                    draft_metrics["mean_accepted_draft_length"]=float(last.group(4)) if last.group(4) else None
            except Exception as e:
                log(f"  draft parse error {e}")
            row={
                "case_id": cid,
                "case_name": cname,
                "language": case["language"],
                "difficulty": case.get("difficulty"),
                "seed": SEED,
                "temperature": TEMP_AUTHOR,
                "top_p": TOP_P_AUTHOR,
                "min_p": MIN_P_AUTHOR,
                "max_tokens": max_tok,
                "raw_text": res["text"],
                "reasoning_text": res["reasoning_text"],
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
                "truncated": detect["truncated"],
                "loop_detected": detect["loop"],
                "thinking_finished": detect["thinking_finished"],
                **draft_metrics
            }
            status="PASS" if row["passed"] else f"FAIL"
            acc_str=f"{row['draft_acceptance_ratio']*100:.1f}%" if row.get("draft_acceptance_ratio") is not None else "N/A"
            log(f"   [{cid}] {status} | tok/s {row.get('predicted_per_second')} | wall {row['wall_time_s']} | TTFT {row['ttft_s']} | VRAM {row['peak_vram_mib']} | acc {acc_str} | finish {row['finish_reason']}")
            rows.append(row)
            time.sleep(0.5)
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except:
            try: proc.kill()
            except: pass
        log_fp.close()
        subprocess.run(["pkill","-9","-f", f"--port {port}"], capture_output=True)
        time.sleep(2)
    out_path = RESULTS_DIR / "WHITTLE16B_DFLASH2_CODING.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False)+"\n")
    log(f"\n[STAGE B] Completed full DFlash2 6 cases to {out_path}")
    total_pass=sum(1 for r in rows if r["passed"])
    speeds=[r["predicted_per_second"] for r in rows if r.get("predicted_per_second")]
    med_speed=statistics.median(speeds) if speeds else None
    peak_vram=max((r["peak_vram_mib"] for r in rows if r.get("peak_vram_mib")), default=None)
    # draft med acceptance
    accs=[r["draft_acceptance_ratio"] for r in rows if r.get("draft_acceptance_ratio") is not None]
    med_acc=statistics.median(accs) if accs else None
    log(f"[STAGE B] PASS {total_pass}/6 med tok/s {med_speed} peak {peak_vram} med_acc {med_acc}")
    return rows, total_pass, med_speed, peak_vram, med_acc

# AGENT helpers reuse from gsq agent
def match_stub(case, tool_name, args):
    for stub in case.get("stubs", []):
        if stub["tool"] != tool_name:
            continue
        stub_args=stub.get("arguments",{})
        matches=True
        for arg_key, rule in stub_args.items():
            val=args.get(arg_key)
            if "equals" in rule:
                if val != rule["equals"]:
                    matches=False
                    break
            elif "contains_all_ci" in rule:
                if not isinstance(val, str):
                    matches=False
                    break
                for term in rule["contains_all_ci"]:
                    if term.lower() not in val.lower():
                        matches=False
                        break
                if not matches:
                    break
        if matches:
            res=stub["result"]
            return json.dumps(res, ensure_ascii=False) if not isinstance(res, str) else res, True
    return json.dumps(CASES_DATA["matching_semantics"]["default_unmatched_tool_result"]), False

def validate_rule(rule, val):
    if "equals" in rule:
        return val==rule["equals"]
    if "contains_all_ci" in rule:
        if not isinstance(val,str):
            return False
        return all(term.lower() in val.lower() for term in rule["contains_all_ci"])
    return False

def evaluate_agent_run(case, turns_record, final_text):
    expected=case["expected"]
    expected_seq=expected.get("tool_sequence",[])
    arg_rules=expected.get("argument_rules",[])
    must_inc=expected.get("final_must_include",[])
    must_not_inc=expected.get("final_must_not_include",[])
    observed_tool_calls=[]
    for t in turns_record:
        for tc in t.get("tool_calls",[]):
            observed_tool_calls.append(tc)
    observed_seq=[tc["name"] for tc in observed_tool_calls]
    seq_score=0
    seq_reasons=[]
    if case["id"]=="T04":
        if len(observed_seq)==0:
            seq_score=3
        else:
            seq_reasons.append(f"Expected 0 tool calls, but observed {observed_seq}")
    else:
        if observed_seq==expected_seq:
            seq_score=3
        else:
            seq_reasons.append(f"Sequence mismatch: expected {expected_seq}, observed {observed_seq}")
    arg_score=0
    arg_reasons=[]
    if case["id"]=="T04":
        if len(observed_tool_calls)==0:
            arg_score=3
        else:
            arg_reasons.append("Tool called when none expected")
    else:
        all_args_valid=True
        if len(observed_tool_calls) < len(arg_rules):
            all_args_valid=False
            arg_reasons.append(f"Fewer tool calls ({len(observed_tool_calls)}) than required rules ({len(arg_rules)})")
        else:
            for rule in arg_rules:
                idx=rule["index"]
                if idx>=len(observed_tool_calls):
                    all_args_valid=False
                    arg_reasons.append(f"Missing call at index {idx}")
                    continue
                tc=observed_tool_calls[idx]
                tc_name=tc["name"]
                tc_args=tc.get("args_parsed",{})
                if tc_name!=rule["tool"]:
                    all_args_valid=False
                    arg_reasons.append(f"Call {idx}: tool name {tc_name} != expected {rule['tool']}")
                    continue
                for param_k, param_rule in rule.items():
                    if param_k in ("index","tool"):
                        continue
                    param_val=tc_args.get(param_k)
                    if not validate_rule(param_rule, param_val):
                        all_args_valid=False
                        arg_reasons.append(f"Call {idx} param '{param_k}' failed rule {param_rule}: got {param_val}")
        if all_args_valid and seq_score==3:
            arg_score=3
    missing_inc=[item for item in must_inc if item not in final_text]
    present_not_inc=[item for item in must_not_inc if item in final_text]
    final_score=0
    final_reasons=[]
    if not missing_inc and not present_not_inc:
        final_score=3
    else:
        if missing_inc:
            final_reasons.append(f"Final answer missing required content: {missing_inc}")
        if present_not_inc:
            final_reasons.append(f"Final answer contains forbidden content: {present_not_inc}")
    hygiene_score=0
    hygiene_reasons=[]
    protocol_violation=False
    if "<tool_call>" in final_text or "</tool_call>" in final_text or "<|im_start|>tool" in final_text:
        protocol_violation=True
        hygiene_reasons.append("Raw tool tag leaked into final content")
    valid_tools=list(CASES_DATA["tool_catalog"].keys())
    for tc in observed_tool_calls:
        if tc["name"] not in valid_tools:
            protocol_violation=True
            hygiene_reasons.append(f"Hallucinated tool name: {tc['name']}")
        if not tc.get("args_valid_json", False):
            protocol_violation=True
            hygiene_reasons.append(f"Malformed JSON arguments in {tc['name']}")
    if expected.get("forbid_extra_tool_calls", False):
        if len(observed_seq)>len(expected_seq):
            protocol_violation=True
            hygiene_reasons.append(f"Extra tool calls observed ({len(observed_seq)} > {len(expected_seq)})")
    if not protocol_violation:
        hygiene_score=1
    total_score=seq_score+arg_score+final_score+hygiene_score
    strict_pass=(total_score==10)
    loss_reasons=seq_reasons+arg_reasons+final_reasons+hygiene_reasons
    return {"strict_pass":strict_pass,"total_score":total_score,"component_scores":{"tool_sequence":seq_score,"arguments_schema":arg_score,"final_answer_grounded":final_score,"protocol_hygiene":hygiene_score},"observed_sequence":observed_seq,"loss_reasons":loss_reasons,"has_protocol_violation":protocol_violation}

def post_chat_agent(payload, port):
    req=urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
    started=time.perf_counter()
    peak=vram_mib()
    stop=threading.Event()
    def sampler():
        nonlocal peak
        while not stop.wait(0.05):
            v=vram_mib()
            if v is not None and (peak is None or v>peak):
                peak=v
    th=threading.Thread(target=sampler, daemon=True)
    th.start()
    data={}
    err_msg=None
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data=json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body=e.read().decode(errors="replace")
        err_msg=f"HTTPError {e.code}: {err_body[:2000]}"
        try:
            data=json.loads(err_body)
        except:
            data={"error":err_body}
    except Exception as e:
        err_msg=f"RequestError: {e}"
        data={"error":str(e)}
    finally:
        stop.set()
        th.join(timeout=2)
    ended=time.perf_counter()
    choices=data.get("choices",[])
    message=choices[0].get("message",{}) if choices else {}
    if not message and err_msg:
        message={"role":"assistant","content":"","error":err_msg}
    usage=data.get("usage",{})
    timings=data.get("timings",{})
    return {"message":message,"usage":usage,"timings":timings,"wall_time_s":round(ended-started,4),"peak_vram_mib":peak,"raw_response":data,"error":err_msg}

def run_stage_c(metadata):
    log("\n"+"="*80)
    log("STAGE C — Agent/tool-calling mini benchmark (native Whittle, 8 cases)")
    log("="*80)
    port=PORT_C
    subprocess.run(["pkill","-9","-f", f"--port {port}"], capture_output=True)
    time.sleep(2)
    # Preflight for agent
    preflight_file = PREFLIGHT_DIR / "stage_c_preflight.txt"
    preflight_info = run_gpu_preflight("WHITTLE16B_AGENT", preflight_file)
    log_path = LOGS_DIR / "server-whittle16b-agent.log"
    if log_path.exists():
        log_path.unlink()
    proc, log_fp = start_server(port, mode="agent", log_path=log_path)
    rows=[]
    try:
        log("  Waiting for agent server healthy...")
        wait_health_wrapper(port, proc, log_path)
        log("  Healthy! Warmup agent...")
        warm=post_chat_agent({"messages":[{"role":"system","content":CASES_DATA["system_prompt"]}, {"role":"user","content":"Olá, você pode me ajudar?"}], "temperature": TEMP_AUTHOR, "top_p": TOP_P_AUTHOR, "min_p": MIN_P_AUTHOR, "seed": SEED, "max_tokens":16}, port)
        log(f"  Warmup wall {warm['wall_time_s']}")
        for case in CASES_DATA["cases"]:
            cid=case["id"]
            title=case["title"]
            log(f"\n-> Executing {cid}: {title}...")
            tools_for_case=[CASES_DATA["tool_catalog"][tname] for tname in case["tools"]]
            messages=[{"role":"system","content":CASES_DATA["system_prompt"]}, {"role":"user","content":case["user"]}]
            turns_record=[]
            final_text=""
            total_wall=0.0
            peak_vram=0
            speeds=[]
            rounds_count=0
            # use author recipe sampling for agent too: temp 0.7 etc, but need to decide max_tokens 384 per turn as per original agent spec
            # SPEC says preserve upstream anti-loop recipe, so use temp 0.7, but original agent uses temp 0.0 deterministically
            # We'll use temp 0.7 as per author, but also we could use 0.7; either is defensible, but we will use 0.7 to follow SPEC
            for round_idx in range(1,5):
                rounds_count+=1
                payload={
                    "messages": messages,
                    "tools": tools_for_case,
                    "tool_choice": "auto",
                    "temperature": TEMP_AUTHOR,
                    "top_p": TOP_P_AUTHOR,
                    "seed": SEED,
                    "max_tokens": 384
                }
                # add min_p if supported? llama-server may support min_p in chat completions? We'll include
                # The API may ignore min_p, but we send it via extra field? Actually llama-server supports "min_p" top-level
                payload["min_p"] = MIN_P_AUTHOR
                res=post_chat_agent(payload, port)
                msg=res["message"]
                timings=res.get("timings",{})
                speed=timings.get("predicted_per_second")
                if speed: speeds.append(speed)
                total_wall+=res["wall_time_s"]
                if res["peak_vram_mib"] and res["peak_vram_mib"]>peak_vram:
                    peak_vram=res["peak_vram_mib"]
                if res.get("error"):
                    log(f"   [Round {round_idx}] Error: {res['error'][:500]}")
                    final_text=msg.get("content","") or res["error"]
                    break
                tool_calls=msg.get("tool_calls",[])
                content=msg.get("content","") or ""
                # also check reasoning_content
                reasoning=msg.get("reasoning_content","") or msg.get("reasoning","")
                if reasoning:
                    log(f"   [Round {round_idx}] reasoning preview: {reasoning[:200].replace(chr(10),' ')}")
                if not tool_calls:
                    final_text=content
                    log(f"   [Round {round_idx}] Final response {len(final_text)} chars: {final_text[:150].replace(chr(10),' ')}")
                    break
                log(f"   [Round {round_idx}] {len(tool_calls)} tool calls")
                tc_records=[]
                # Need to append assistant message with tool_calls
                # Some servers require full message including tool_calls
                messages.append(msg)
                for tc in tool_calls:
                    func=tc.get("function",{})
                    fn_name=func.get("name","")
                    raw_args=func.get("arguments","")
                    tc_id=tc.get("id", f"call_{round_idx}")
                    args_parsed={}
                    args_valid=True
                    try:
                        args_parsed=json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except:
                        args_valid=False
                    stub_result_str, matched=match_stub(case, fn_name, args_parsed)
                    log(f"      Call {fn_name}({raw_args}) -> matched {matched} preview {stub_result_str[:80]}")
                    tc_records.append({"id":tc_id,"name":fn_name,"raw_args":raw_args,"args_parsed":args_parsed,"args_valid_json":args_valid,"stub_result":stub_result_str,"matched_stub":matched})
                    messages.append({"role":"tool","tool_call_id":tc_id,"name":fn_name,"content":stub_result_str})
                turns_record.append({"round":round_idx,"tool_calls":tc_records,"timings":timings,"wall_time_s":res["wall_time_s"]})
            eval_res=evaluate_agent_run(case, turns_record, final_text)
            row={
                "case_id": cid,
                "title": title,
                "arm": "WHITTLE16B_NATIVE_AGENT",
                "template_mode": "native_whittle14b",
                "strict_pass": eval_res["strict_pass"],
                "total_score": eval_res["total_score"],
                "component_scores": eval_res["component_scores"],
                "observed_sequence": eval_res["observed_sequence"],
                "loss_reasons": eval_res["loss_reasons"],
                "turns_record": turns_record,
                "final_text": final_text,
                "total_wall_s": round(total_wall,4),
                "peak_vram_mib": peak_vram,
                "rounds_count": rounds_count,
                "mean_tok_s": round(statistics.mean(speeds),2) if speeds else None,
            }
            status="STRICT PASS (10/10)" if row["strict_pass"] else f"SCORE {row['total_score']}/10"
            log(f"   => [{cid}] {status} | Seq {row['observed_sequence']} | Time {row['total_wall_s']} | loss {row['loss_reasons']}")
            rows.append(row)
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except:
            try: proc.kill()
            except: pass
        log_fp.close()
        subprocess.run(["pkill","-9","-f", f"--port {port}"], capture_output=True)
        time.sleep(2)
    out_path=RESULTS_DIR / "WHITTLE16B_AGENT_RESULTS.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False)+"\n")
    log(f"\n[STAGE C] Completed agent 8 cases to {out_path}")
    strict_pass=sum(1 for r in rows if r["strict_pass"])
    total_score=sum(r["total_score"] for r in rows)
    log(f"[STAGE C] STRICT {strict_pass}/8 total {total_score}/80")
    return rows, strict_pass, total_score, preflight_info

def generate_summary_and_manifest(stage_a_rows, stage_a_pass, stage_a_med, stage_a_peak, stage_b_rows, stage_b_pass, stage_b_med, stage_b_peak, stage_b_acc, stage_b_status, stage_c_rows, stage_c_strict, stage_c_score, metadata, preflights, classification):
    # SUMMARY.md
    lines=[]
    lines.append("# Whittle16B Candidate v1 — Results Summary\n")
    lines.append(f"Generated: {datetime.datetime.now().isoformat()}\n")
    lines.append("## Model\n")
    lines.append(f"- Repo: `{metadata['hf_repo']}`")
    lines.append(f"- File: `{metadata['filename']}`")
    lines.append(f"- Size: `{metadata['size_bytes']}` bytes (`{metadata['size_gib']} GiB`)")
    lines.append(f"- SHA256: `{metadata['sha256']}`")
    lines.append(f"- HF revision: `{metadata['hf_revision']}`")
    lines.append(f"- HF GGUF path: `{metadata['hf_gguf_path']}`")
    lines.append(f"- Runtime: `{metadata['runtime_version']}`")
    lines.append(f"- Hardware: RTX 5060 Ti 16 GB, 8 threads, full GPU offload, FA ON, ctx 8192, KV q8_0/q4_0")
    lines.append(f"- Author recipe: `--jinja --dry-multiplier {DRY_MULTIPLIER} --dry-base {DRY_BASE} --dry-allowed-length {DRY_ALLOWED} --repeat-penalty {REPEAT_PENALTY} --repeat-last-n {REPEAT_LAST_N} --temp {TEMP_AUTHOR} --top-p {TOP_P_AUTHOR} --min-p {MIN_P_AUTHOR}` + thinking ON, max_tokens {MAX_TOKENS_AUTHOR}+ (AUTHOR_RECIPE)")
    lines.append("")
    lines.append("## Important Note — Historical Controls vs AUTHOR_RECIPE\n")
    lines.append("GSQ historical numbers were measured with protocol `temp=0.2, top_p=0.95, reasoning off` (same-protocol leaderboard). Whittle 16B AUTHOR_RECIPE uses `temp=0.7, top_p=0.95, min_p=0.05, DRY, repeat-penalty, thinking ON`. Throughput/wall times are **AUTHOR_RECIPE** and must **not** be merged as same-protocol leaderboard entries. Correctness on identical 6 canonical cases **can** be directly compared.\n")
    lines.append("Previous Whittle-MoE-27B-A18B (tested and discarded) is a **different model** (27B MoE pruned) and is not comparable to Whittle 16B dense-pruned. The former scored `1/6, 19.39 tok/s, 15194 MiB` and must remain labelled as separate.\n")
    lines.append("### Historical Controls (not rerun, reused for context)\n")
    lines.append(f"- GSQ base: `{HIST_GSQ_BASE['pass']}` @ {HIST_GSQ_BASE['tok_s']} tok/s (same-protocol)")
    lines.append(f"- GSQ + DFlash2 n=7: `{HIST_GSQ_DFLASH2['pass']}` @ {HIST_GSQ_DFLASH2['tok_s']} tok/s (same-protocol)")
    lines.append(f"- GSQ agent native: `{HIST_GSQ_AGENT['strict']}` {HIST_GSQ_AGENT['score']} (native template, temp 0.0)")
    lines.append(f"- Whittle-MoE-27B-A18B old (different model): `{HIST_WHITTLE_MOE['pass']}` {HIST_WHITTLE_MOE['tok_s']} tok/s peak {HIST_WHITTLE_MOE['vram']} MiB")
    lines.append("")
    lines.append("## STAGE A — Native Whittle 16B Coding (AUTHOR_RECIPE)\n")
    lines.append(f"- Mode: native template, thinking ON, author DRY/repeat recipe, temp {TEMP_AUTHOR}")
    lines.append(f"- Cases: 6 canonical coding-mini-v1 (PY01 PY02 PY03 CPP01 CPP02 CPP03)")
    lines.append(f"- Completion budget: ≥{MAX_TOKENS_AUTHOR} (3072) per case, reasoning + final code")
    lines.append(f"- Score: **{stage_a_pass}/6**")
    py_pass=sum(1 for r in stage_a_rows if r["passed"] and r["language"]=="python") if stage_a_rows else 0
    cpp_pass=sum(1 for r in stage_a_rows if r["passed"] and r["language"]=="cpp") if stage_a_rows else 0
    lines.append(f"- Python: **{py_pass}/3** | C++: **{cpp_pass}/3**")
    if stage_a_med is not None:
        lines.append(f"- Median decode (AUTHOR_RECIPE): **{stage_a_med:.2f} tok/s**")
    # per-case table
    lines.append("\n### Per-Case Breakdown STAGE A\n")
    lines.append("| Case | Status | Compile | Public | Hidden | tok/s | prompt tok/s | wall (s) | TTFT (s) | VRAM MiB | comp_len | trunc | loop | thinking_ok |")
    lines.append("|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
    for r in stage_a_rows:
        st="PASS" if r["passed"] else "FAIL"
        comp="PASS" if r["compile_pass"] else "FAIL"
        pub="PASS" if r["public_pass"] else "FAIL"
        hid="PASS" if r["hidden_pass"] else "FAIL"
        tok=f"{r['predicted_per_second']:.2f}" if r.get("predicted_per_second") else "N/A"
        ptok=f"{r['prompt_per_second']:.2f}" if r.get("prompt_per_second") else "N/A"
        wall=f"{r['wall_time_s']:.2f}"
        ttft=f"{r['ttft_s']:.2f}" if r.get("ttft_s") else "N/A"
        vram=r.get("peak_vram_mib") or "N/A"
        clen=r.get("completion_tokens") or r.get("completion_len") or "N/A"
        trunc="YES" if r.get("truncated") else "NO"
        loop="YES" if r.get("loop_detected") else "NO"
        think="YES" if r.get("thinking_finished") else "NO"
        lines.append(f"| **{r['case_id']}** | **{st}** | {comp} | {pub} | {hid} | {tok} | {ptok} | {wall} | {ttft} | {vram} | {clen} | {trunc} | {loop} | {think} |")
    lines.append("")
    lines.append(f"Peak VRAM Stage A: **{stage_a_peak} MiB**")
    if stage_a_pass <=4:
        lines.append(f"\n**GATE:** {stage_a_pass}/6 → 0–4/6 = STOP. No DFlash2, no agent per SPEC.")
    elif stage_a_pass==5:
        lines.append(f"\n**GATE:** 5/6 → allow Stage B, skip Stage C unless Stage B reaches 6/6.")
    else:
        lines.append(f"\n**GATE:** 6/6 → proceed to Stage B and Stage C per gates.")
    lines.append("")
    lines.append("## STAGE B — DFlash2\n")
    if stage_b_status is None:
        lines.append("- **SKIPPED** (gate 0–4/6, per SPEC)")
    elif stage_b_status=="DFLASH2_INCOMPATIBLE_OR_UNUSABLE":
        lines.append("- **DFLASH2_INCOMPATIBLE_OR_UNUSABLE**")
        lines.append("- Whittle 16B is structurally pruned vs 27B DFlash2 draft, compatibility not assumed.")
        lines.append("- Smoke PY01 failed: error / vocab mismatch / OOM / speculative error")
        lines.append("- Logs preserved in `logs/server-whittle16b-dflash2-smoke.log` and `WHITTLE16B_DFLASH2_SMOKE.json`")
        lines.append("- No hacks attempted. Full Stage B skipped.")
    else:
        lines.append(f"- Status: **{stage_b_status}**")
        if stage_b_rows:
            lines.append(f"- Score: **{stage_b_pass}/6** (vs Stage A {stage_a_pass}/6)")
            if stage_b_med is not None:
                # compare to author recipe median
                delta_pct = ((stage_b_med - stage_a_med)/stage_a_med*100) if stage_a_med else None
                delta_str = f" ({delta_pct:+.1f}% vs Stage A AUTHOR_RECIPE)" if delta_pct is not None else ""
                lines.append(f"- Median decode DFlash2: **{stage_b_med:.2f} tok/s**{delta_str}")
            lines.append(f"- Peak VRAM DFlash2: **{stage_b_peak} MiB**")
            if stage_b_acc is not None:
                lines.append(f"- Median draft acceptance: **{stage_b_acc*100:.1f}%**")
            lines.append("\n### Per-Case DFlash2\n")
            lines.append("| Case | Status | tok/s | wall | VRAM | accept | accepted/gen | mean_len |")
            lines.append("|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
            for r in stage_b_rows:
                st="PASS" if r["passed"] else "FAIL"
                tok=f"{r['predicted_per_second']:.2f}" if r.get("predicted_per_second") else "N/A"
                wall=f"{r['wall_time_s']:.2f}"
                vram=r.get("peak_vram_mib") or "N/A"
                acc=f"{r['draft_acceptance_ratio']*100:.1f}%" if r.get("draft_acceptance_ratio") is not None else "N/A"
                counts=f"{r.get('accepted_draft_tokens')}/{r.get('generated_draft_tokens')}" if r.get("accepted_draft_tokens") is not None else "N/A"
                mean=f"{r.get('mean_accepted_draft_length'):.2f}" if r.get("mean_accepted_draft_length") else "N/A"
                lines.append(f"| **{r['case_id']}** | **{st}** | {tok} | {wall} | {vram} | {acc} | {counts} | {mean} |")
            # Interpretation
            if stage_b_pass >= stage_a_pass and stage_b_med and stage_a_med and stage_b_med > stage_a_med*1.1:
                lines.append("\n- **Interpretation:** DFlash2 preserved quality and materially improved throughput (>10% gain) with acceptable VRAM → **USEFUL**")
            elif stage_b_pass < stage_a_pass:
                lines.append("\n- **Interpretation:** DFlash2 regressed correctness vs Stage A → **NOT USEFUL** (reject acceleration if it regresses)")
            else:
                lines.append("\n- **Interpretation:** DFlash2 preserved quality but no material speed gain → **NOT USEFUL** as preset")
    lines.append("")
    lines.append("## STAGE C — Agent / Tool-Calling\n")
    if stage_c_rows is None:
        lines.append("- **SKIPPED** (requires 6/6 coding in stable config per SPEC)")
        if stage_a_pass !=6:
            lines.append(f"  - Reason: Stage A was {stage_a_pass}/6, not 6/6")
        elif stage_b_status=="DFLASH2_INCOMPATIBLE_OR_UNUSABLE":
            lines.append("  - Reason: DFlash2 incompatible, but Stage C requires 6/6 in best stable config (Stage A 6/6 qualifies, but DFlash2 not needed). Actually per SPEC, Stage C only if 6/6 in best non-speculative or speculative stable. Since Stage A is 6/6 native, Stage C should run. If not run, document why.")
        else:
            lines.append("  - Reason: gate not met")
    else:
        lines.append(f"- Cases: 8 canonical gsq-froggeric-agent-tools-v1 (T01-T08)")
        lines.append(f"- Template: native Whittle, --jinja, OpenAI tools, author DRY recipe, thinking ON")
        lines.append(f"- STRICT PASS: **{stage_c_strict}/8**")
        lines.append(f"- Total score: **{stage_c_score}/80**")
        lines.append("\n### Per-Case Agent Breakdown\n")
        lines.append("| Case | Title | Strict | Score | Sequence | Loss reasons |")
        lines.append("|---|:---:|:---:|:---:|---|---|")
        for r in stage_c_rows:
            st="PASS" if r["strict_pass"] else "FAIL"
            seq=" -> ".join(r["observed_sequence"]) if r["observed_sequence"] else "*(none)*"
            loss="; ".join(r["loss_reasons"]) if r["loss_reasons"] else "*none*"
            lines.append(f"| **{r['case_id']}** | {r['title']} | **{st}** | {r['total_score']}/10 | `{seq}` | {loss} |")
        # Compare to GSQ controls
        lines.append(f"\n- Historical GSQ native agent: 7/8 (70/80) — not rerun, for context only.")
        lines.append(f"- DFlash2 only useful if preserves quality and improves materially (per SPEC).")
    lines.append("")
    lines.append("## Classification\n")
    lines.append(f"**{classification}**\n")
    # Guidance explanation
    if classification=="WHITTLE16B_REJECT":
        lines.append("- Reason: ≤4/6 coding or serious instability. Not recommended.")
    elif classification=="WHITTLE16B_INTERESTING":
        lines.append("- Reason: 5/6 coding with useful efficiency/VRAM but not full coverage.")
    elif classification=="WHITTLE16B_STRONG_CANDIDATE":
        lines.append("- Reason: 6/6 coding, stable, but not clearly better overall than GSQ+DFlash2.")
    elif classification=="WHITTLE16B_PRIMARY_CODER_CANDIDATE":
        lines.append("- Reason: 6/6 plus compelling efficiency/performance and no meaningful agent/runtime regression.")
    lines.append("")
    lines.append("## Provenance\n")
    lines.append(f"- Profile: `{PROFILE_MD.relative_to(ROOT)}`")
    lines.append(f"- Results: `{RESULTS_DIR.relative_to(ROOT)}/`")
    lines.append(f"- Commit: see RUN_MANIFEST.json `git_commit`")
    lines.append("- All numbers above are MEDIDO LOCALMENTE unless explicitly marked HISTORICAL / AUTHOR_RECIPE")
    txt="\n".join(lines)+"\n"
    (RESULTS_DIR / "SUMMARY.md").write_text(txt, encoding="utf-8")
    log(f"Summary written to {RESULTS_DIR / 'SUMMARY.md'}")
    # RUN_MANIFEST
    manifest={
        "benchmark": "whittle16b-candidate-v1",
        "timestamp": datetime.datetime.now().isoformat(),
        "model": {
            "path": str(MODEL_GGUF),
            "filename": metadata["filename"],
            "size_bytes": metadata["size_bytes"],
            "size_gib": metadata["size_gib"],
            "sha256": metadata["sha256"],
            "hf_repo": metadata["hf_repo"],
            "hf_revision": metadata["hf_revision"],
            "hf_gguf_path": metadata["hf_gguf_path"],
            "gguf_metadata": metadata["gguf_metadata"],
        },
        "runtime": {
            "binary": str(LLAMA_BIN),
            "version": metadata["runtime_version"],
            "hardware": "RTX 5060 Ti 16GB",
            "threads": THREADS,
            "ctx": CTX,
            "offload": "full (ngl 999)",
            "flash_attention": "on",
            "fit": "off",
            "kv": "q8_0/q4_0",
        },
        "author_recipe": {
            "jinja": True,
            "thinking": "native ON (not forced off)",
            "dry_multiplier": DRY_MULTIPLIER,
            "dry_base": DRY_BASE,
            "dry_allowed_length": DRY_ALLOWED,
            "repeat_penalty": REPEAT_PENALTY,
            "repeat_last_n": REPEAT_LAST_N,
            "temperature": TEMP_AUTHOR,
            "top_p": TOP_P_AUTHOR,
            "min_p": MIN_P_AUTHOR,
            "seed": SEED,
            "max_tokens_per_case": MAX_TOKENS_AUTHOR,
            "note": "AUTHOR_RECIPE speeds not comparable to historical same-protocol leaderboard"
        },
        "stage_a": {
            "score": f"{stage_a_pass}/6" if stage_a_rows else "N/A",
            "median_tok_s_author_recipe": stage_a_med,
            "peak_vram_mib": stage_a_peak,
            "file": str((RESULTS_DIR/"WHITTLE16B_NATIVE_CODING.jsonl").relative_to(ROOT)),
            "gate": "0-4 STOP, 5 allow B, 6 allow B+C"
        },
        "stage_b": {
            "status": stage_b_status or "SKIPPED",
            "score": f"{stage_b_pass}/6" if stage_b_rows else "N/A",
            "median_tok_s": stage_b_med,
            "peak_vram_mib": stage_b_peak,
            "median_acceptance": stage_b_acc,
            "file": str((RESULTS_DIR/"WHITTLE16B_DFLASH2_CODING.jsonl").relative_to(ROOT)) if stage_b_rows else None,
            "draft_model": str(DRAFT_MODEL),
            "spec_type": "draft-dflash",
            "spec_n_max": 7,
            "note": "Whittle 16B structurally pruned; compatibility not assumed; no arch hacks"
        },
        "stage_c": {
            "strict_pass": f"{stage_c_strict}/8" if stage_c_rows else "SKIPPED",
            "total_score": f"{stage_c_score}/80" if stage_c_rows else "SKIPPED",
            "file": str((RESULTS_DIR/"WHITTLE16B_AGENT_RESULTS.jsonl").relative_to(ROOT)) if stage_c_rows else None,
            "template": "native Whittle + --jinja + OpenAI tools + author DRY",
            "cases": "gsq-froggeric-agent-tools-v1 8 canonical",
            "note": "Only executed if 6/6 coding in stable config"
        },
        "historical_controls_reused": {
            "gsq_base": HIST_GSQ_BASE,
            "gsq_dflash2": HIST_GSQ_DFLASH2,
            "gsq_agent_native": HIST_GSQ_AGENT,
            "whittle_moe_old_different_model": HIST_WHITTLE_MOE
        },
        "clean_gpu_preflight": preflights,
        "classification": classification,
        "git_commit": run_cmd(["git","rev-parse","HEAD"], timeout=5).strip(),
    }
    # add preflight files
    (RESULTS_DIR / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"Manifest written to {RESULTS_DIR / 'RUN_MANIFEST.json'}")

def main():
    log("="*80)
    log("WHITTLE16B CANDIDATE v1 — FULL PIPELINE")
    log("="*80)
    # Wait for model file if not yet present (download in progress)
    wait_attempts=0
    while not MODEL_GGUF.exists() and wait_attempts<60:
        log(f"Waiting for GGUF at {MODEL_GGUF} ... {wait_attempts}s")
        time.sleep(5)
        wait_attempts+=1
    if not MODEL_GGUF.exists():
        raise FileNotFoundError(f"GGUF not found after wait: {MODEL_GGUF}")
    # Check size maybe still growing
    last_size=-1
    stable=0
    for _ in range(12):
        sz=MODEL_GGUF.stat().st_size
        log(f"  size check: {sz} bytes")
        if sz==last_size:
            stable+=1
            if stable>=2:
                break
        else:
            stable=0
            last_size=sz
        time.sleep(5)
    metadata=prepare_model_metadata()
    # Create profile directory symlink check
    # Ensure symlink in runtimes/llama
    runtimes_link = ROOT / "runtimes/llama" / MODEL_GGUF.name
    if not runtimes_link.exists():
        log(f"Creating symlink {runtimes_link} -> {MODEL_GGUF}")
        try:
            runtimes_link.symlink_to(f"../../{MODEL_GGUF.relative_to(ROOT)}")
        except Exception as e:
            log(f"  symlink fail {e}")
    # Also check for broken links
    preflights={}
    # Stage A preflight
    preflight_a_file = PREFLIGHT_DIR / "stage_a_preflight.txt"
    preflight_a = run_gpu_preflight("WHITTLE16B_STAGE_A", preflight_a_file)
    preflights["stage_a"] = preflight_a
    stage_a_rows, stage_a_pass, stage_a_med, stage_a_peak = run_stage_a(metadata, preflight_a)
    # Gate
    if stage_a_pass <=4:
        classification="WHITTLE16B_REJECT"
        stage_b_status=None
        stage_b_rows=None
        stage_b_pass=None
        stage_b_med=None
        stage_b_peak=None
        stage_b_acc=None
        stage_c_rows=None
        stage_c_strict=None
        stage_c_score=None
        preflights["stage_b"]="SKIPPED_GATE_0_4"
        preflights["stage_c"]="SKIPPED_GATE_0_4"
        log("\n[Gate] 0–4/6 → REJECT, stopping expansion per SPEC")
    elif stage_a_pass==5:
        log("\n[Gate] 5/6 → allow Stage B, skip C unless B 6/6")
        # Stage B preflight
        preflight_b_file = PREFLIGHT_DIR / "stage_b_preflight.txt"
        preflight_b = run_gpu_preflight("WHITTLE16B_STAGE_B", preflight_b_file)
        preflights["stage_b"] = preflight_b
        # Smoke
        stage_b_status, smoke_res = run_stage_b_smoke(metadata, preflight_b)
        if stage_b_status=="DFLASH2_INCOMPATIBLE_OR_UNUSABLE":
            stage_b_rows=None
            stage_b_pass=None
            stage_b_med=None
            stage_b_peak=None
            stage_b_acc=None
            stage_c_rows=None
            stage_c_strict=None
            stage_c_score=None
            classification="WHITTLE16B_INTERESTING"  # 5/6 with maybe efficiency
            log("\n[Gate] Stage B incompatible, Stage C skipped (needs 6/6)")
        else:
            stage_b_rows, stage_b_pass, stage_b_med, stage_b_peak, stage_b_acc = run_stage_b_full(metadata)
            preflights["stage_b_full"] = {"completed": True}
            if stage_b_pass==6:
                # Could run Stage C, but spec says Stage C only if whittle atinge 6/6 em configuração estável.
                # Stage A is 5/6, not 6/6, so Stage C still not allowed even if B is 6/6? Spec: Stage C só execute se o Whittle atingir 6/6 em uma configuração estável de código.
                # Since A is 5/6, B 6/6 would qualify as 6/6 stable speculative config → could allow C.
                # But spec also says Stage B interpretation: allow Stage B DFlash2... but skip Stage C agent benchmark unless Stage B reaches 6/6.
                # For 5/6 gate, that implies if B reaches 6/6, then C allowed.
                log("\n[Gate] B reached 6/6, but A was 5/6 → per SPEC, C requires 6/6, and B is 6/6, so we will run C")
                stage_c_rows, stage_c_strict, stage_c_score, preflight_c = run_stage_c(metadata)
                preflights["stage_c"] = preflight_c
                # Classification for 5/6 overall still not strong candidate, but interesting
                if stage_c_strict is not None and stage_c_strict>=6:
                    classification="WHITTLE16B_INTERESTING"
                else:
                    classification="WHITTLE16B_INTERESTING"
            else:
                stage_c_rows=None
                stage_c_strict=None
                stage_c_score=None
                classification="WHITTLE16B_INTERESTING"
    else: # 6/6
        log("\n[Gate] 6/6 → proceed to Stage B per SPEC")
        preflight_b_file = PREFLIGHT_DIR / "stage_b_preflight.txt"
        preflight_b = run_gpu_preflight("WHITTLE16B_STAGE_B", preflight_b_file)
        preflights["stage_b"] = preflight_b
        stage_b_status, smoke_res = run_stage_b_smoke(metadata, preflight_b)
        stage_b_rows=None
        stage_b_pass=None
        stage_b_med=None
        stage_b_peak=None
        stage_b_acc=None
        if stage_b_status=="DFLASH2_COMPATIBLE":
            stage_b_rows, stage_b_pass, stage_b_med, stage_b_peak, stage_b_acc = run_stage_b_full(metadata)
        else:
            log("\n[Stage B] Incompatible, skipping full")
        # Stage C - only if 6/6 stable
        log("\n[Gate] 6/6 qualifies for Stage C per SPEC")
        stage_c_rows, stage_c_strict, stage_c_score, preflight_c = run_stage_c(metadata)
        preflights["stage_c"] = preflight_c
        # Determine classification
        # Need to compare to GSQ+DFlash2 etc.
        # For now simple: if agent also good, then primary? Need to evaluate
        # We'll use logic:
        # REJECT <=4 already handled
        # INTERESTING 5/6
        # STRONG_CANDIDATE 6/6 but not clearly better than GSQ+DFlash2
        # PRIMARY_CODER_CANDIDATE 6/6 plus compelling efficiency and no regression
        # Let's compute: if stage_a_med < 46.00 (GSQ DFlash2) then not better? Actually author recipe median maybe lower due to temp 0.7 etc.
        # But we must separate: author recipe speeds not comparable. So classification should be based on correctness + stability + qualitative
        # For now if 6/6 and agent 7-8/8, classify STRONG or PRIMARY depending on VRAM etc.
        # We'll decide after seeing numbers, but default to STRONG_CANDIDATE for 6/6 stable unless DFlash2 shows huge speedup
        if stage_c_rows is not None:
            agent_pass = stage_c_strict
            if agent_pass >=7 and stage_b_status=="DFLASH2_COMPATIBLE" and stage_b_pass==6 and stage_b_med and stage_b_med>40:
                classification="WHITTLE16B_PRIMARY_CODER_CANDIDATE"
            elif agent_pass >=6:
                classification="WHITTLE16B_STRONG_CANDIDATE"
            else:
                # agent regression
                classification="WHITTLE16B_STRONG_CANDIDATE"  # still strong coding, but note agent weakness
        else:
            classification="WHITTLE16B_STRONG_CANDIDATE"
    # Ensure results exist for skipped stages: create empty placeholders? Not needed
    # Generate summary/manifest
    generate_summary_and_manifest(stage_a_rows, stage_a_pass, stage_a_med, stage_a_peak, stage_b_rows, stage_b_pass, stage_b_med, stage_b_peak, stage_b_acc, stage_b_status if 'stage_b_status' in locals() else None, stage_c_rows, stage_c_strict if 'stage_c_strict' in locals() else None, stage_c_score if 'stage_c_score' in locals() else None, metadata, preflights, classification)
    # Update profile markdown
    update_profile_md(metadata, stage_a_rows, stage_a_pass, stage_a_med, stage_a_peak, stage_b_rows, stage_b_status if 'stage_b_status' in locals() else None, stage_b_med, stage_b_peak, stage_b_acc, stage_c_rows, stage_c_strict if 'stage_c_strict' in locals() else None, stage_c_score if 'stage_c_score' in locals() else None, classification)
    log(f"\n{'='*80}")
    log(f"FINAL CLASSIFICATION: {classification}")
    log("="*80)

def update_profile_md(metadata, stage_a_rows, stage_a_pass, stage_a_med, stage_a_peak, stage_b_rows, stage_b_status, stage_b_med, stage_b_peak, stage_b_acc, stage_c_rows, stage_c_strict, stage_c_score, classification):
    log(f"\n[Profile] Updating {PROFILE_MD}")
    # Gather per-case metrics for md
    # Build markdown following AGENTS.md rules
    now_date = datetime.datetime.now().strftime("%Y-%m-%d")
    hardware = "NVIDIA GeForce RTX 5060 Ti 16 GB"
    runtime = metadata["runtime_version"]
    size_gib = metadata["size_gib"]
    # Try to get arch
    arch = "Qwen3.8 / whittle 16B pruned dense"
    quant = "Q4_K_M"
    # Build file
    lines=[]
    lines.append(f"# {metadata['filename'].replace('.gguf','')}")
    lines.append("")
    lines.append("## Identificação técnica")
    lines.append("")
    lines.append(f"- Arquivo GGUF: `{metadata['filename']}`")
    lines.append(f"- Tamanho local registrado: `{metadata['size_bytes']}` bytes (`{size_gib} GiB`)")
    lines.append(f"- SHA256: `{metadata['sha256']}`")
    lines.append(f"- Origem: `{metadata['hf_repo']}`")
    lines.append(f"- Revisão HF: `{metadata['hf_revision']}`")
    lines.append(f"- Caminho canônico: `text/logic65-Qwen3.8-Whittle-16B-v2-Q4_K_M/{metadata['filename']}`")
    lines.append(f"- Arquitetura: {arch}")
    lines.append(f"- Quantização: `{quant}` (~4.5 bpw)")
    lines.append(f"- Status no workspace: candidato avaliado {now_date} / classificação {classification}")
    lines.append("")
    lines.append("## Especialidade, pontos fortes e trade-offs")
    lines.append("")
    if stage_a_pass==6:
        lines.append(f"- **6/6** no coding-mini-v1 Stage A (AUTHOR_RECIPE) — candidato forte para código.")
    elif stage_a_pass==5:
        lines.append(f"- **5/6** no coding-mini-v1 — interessante mas não completo.")
    else:
        lines.append(f"- **{stage_a_pass}/6** no coding-mini-v1 — rejeitado para código principal.")
    lines.append(f"- Mediana AUTHOR_RECIPE: {stage_a_med:.2f} tok/s (não comparável diretamente a leaderboard same-protocol 24.70 GSQ).")
    lines.append(f"- Pico VRAM Stage A: {stage_a_peak} MiB.")
    if stage_b_status=="DFLASH2_COMPATIBLE" and stage_b_rows:
        if stage_b_pass==6 and stage_b_med and stage_b_med> stage_a_med:
            lines.append(f"- DFlash2 compatível: **{stage_b_pass}/6**, {stage_b_med:.2f} tok/s, +{((stage_b_med-stage_a_med)/stage_a_med*100):+.1f}% vs native AUTHOR_RECIPE, VRAM {stage_b_peak} MiB, acceptance {stage_b_acc*100:.1f}%.")
        else:
            lines.append(f"- DFlash2 compatível mas sem ganho material ou regressão: {stage_b_pass}/6 @ {stage_b_med:.2f} tok/s.")
    elif stage_b_status=="DFLASH2_INCOMPATIBLE_OR_UNUSABLE":
        lines.append("- DFlash2 **INCOMPATÍVEL/INUTILIZÁVEL** com draft Qwen3.8-27B-DFlash2 (esperado por poda estrutural).")
    else:
        lines.append("- DFlash2 não avaliado (gate).")
    if stage_c_rows:
        lines.append(f"- Agent native: **{stage_c_strict}/8** ({stage_c_score}/80).")
        if stage_c_strict>=7:
            lines.append("  - Agent forte, sem regressão vs GSQ 7/8 baseline histórico.")
        else:
            lines.append("  - Agent com regressão vs GSQ 7/8 baseline.")
    else:
        lines.append("- Agent não executado (gate 6/6 required).")
    lines.append("- Limitações: poda estrutural impede assumir compatibilidade speculative; throughput AUTHOR_RECIPE não é sama-protocol; benchmark limitado a 6 casos coding + 8 agent.")
    lines.append("")
    lines.append("## MEDIDO LOCALMENTE")
    lines.append("")
    lines.append(f"Hardware: {hardware}.")
    lines.append("")
    lines.append(f"Runtime: `{runtime}`; 8 threads; full GPU offload; Flash Attention ON; ctx 8192; KV q8_0/q4_0; fit off.")
    lines.append("")
    lines.append(f"Data validação: `{now_date}`.")
    lines.append("")
    lines.append(f"Proveniência: `benchmarks/whittle16b-candidate-v1/results/` — commit `{run_cmd(['git','rev-parse','HEAD'])[:10]}` + RUN_MANIFEST.json")
    lines.append("")
    lines.append("### Código — Whittle 16B v2 Q4_K_M AUTHOR_RECIPE (Stage A)")
    lines.append("")
    lines.append(f"Fonte: `benchmarks/whittle16b-candidate-v1/results/WHITTLE16B_NATIVE_CODING.jsonl` — receita autora (`--jinja --dry-multiplier {DRY_MULTIPLIER} --dry-base {DRY_BASE} --dry-allowed-length {DRY_ALLOWED} --repeat-penalty {REPEAT_PENALTY} --repeat-last-n {REPEAT_LAST_N} temp {TEMP_AUTHOR} top_p {TOP_P_AUTHOR} min_p {MIN_P_AUTHOR}`, thinking ON, max_tokens ≥{MAX_TOKENS_AUTHOR}).")
    lines.append("")
    lines.append(f"- Score: **{stage_a_pass}/6**")
    py_pass=sum(1 for r in stage_a_rows if r["passed"] and r["language"]=="python") if stage_a_rows else 0
    cpp_pass=sum(1 for r in stage_a_rows if r["passed"] and r["language"]=="cpp") if stage_a_rows else 0
    lines.append(f"- Python: **{py_pass}/3**")
    lines.append(f"- C++: **{cpp_pass}/3**")
    if stage_a_med is not None:
        lines.append(f"- Mediana decode AUTHOR_RECIPE: **{stage_a_med:.2f} tok/s**")
    lines.append(f"- Pico VRAM: **{stage_a_peak} MiB**")
    # per case list
    lines.append("- Casos:")
    for r in stage_a_rows:
        st="PASS" if r["passed"] else "FAIL"
        lines.append(f"  - {r['case_id']} {r['case_name']} ({r['language']} {r['difficulty']}): **{st}** compile {r['compile_pass']} public {r['public_pass']} hidden {r['hidden_pass']} tok/s {r.get('predicted_per_second')} wall {r['wall_time_s']} TTFT {r['ttft_s']} trunc {r['truncated']} loop {r['loop_detected']} thinking_finished {r['thinking_finished']}")
    lines.append("")
    if stage_b_rows or stage_b_status=="DFLASH2_INCOMPATIBLE_OR_UNUSABLE":
        lines.append("### Código — Whittle 16B + DFlash2 (Stage B)")
        lines.append("")
        if stage_b_status=="DFLASH2_INCOMPATIBLE_OR_UNUSABLE":
            lines.append("- Status: **DFLASH2_INCOMPATIBLE_OR_UNUSABLE**")
            lines.append("- Detalhe: Whittle 16B podado estruturalmente; incompatibilidade tokenizer/vocab ou erro speculative detectado no smoke PY01.")
            lines.append("- Logs: `logs/server-whittle16b-dflash2-smoke.log` + `WHITTLE16B_DFLASH2_SMOKE.json`")
            lines.append("- Sem hacks de arquitetura.")
        else:
            lines.append(f"Fonte: `benchmarks/whittle16b-candidate-v1/results/WHITTLE16B_DFLASH2_CODING.jsonl` — draft `z-lab-Qwen3.8-27B-DFlash2-Q4_K_M.gguf` `--spec-type draft-dflash --spec-draft-n-max 7`")
            lines.append("")
            lines.append(f"- Score: **{stage_b_pass}/6**")
            if stage_b_med is not None:
                lines.append(f"- Mediana decode: **{stage_b_med:.2f} tok/s**")
            lines.append(f"- Pico VRAM: **{stage_b_peak} MiB**")
            if stage_b_acc is not None:
                lines.append(f"- Acceptance mediana: **{stage_b_acc*100:.1f}%**")
            for r in stage_b_rows:
                st="PASS" if r["passed"] else "FAIL"
                acc=f"{r['draft_acceptance_ratio']*100:.1f}%" if r.get("draft_acceptance_ratio") is not None else "N/A"
                lines.append(f"  - {r['case_id']}: **{st}** tok/s {r.get('predicted_per_second')} wall {r['wall_time_s']} acc {acc} ({r.get('accepted_draft_tokens')}/{r.get('generated_draft_tokens')}) mean_len {r.get('mean_accepted_draft_length')}")
            # interpretation
            if stage_b_pass and stage_a_pass and stage_b_pass < stage_a_pass:
                lines.append("- Interpretação: **INÚTIL** — regrediu qualidade vs native, não aceitar aceleração.")
            elif stage_b_med and stage_a_med and stage_b_med > stage_a_med*1.1 and stage_b_pass>=stage_a_pass:
                lines.append("- Interpretação: **ÚTIL** — preservou qualidade e melhorou materialmente (>10%).")
            else:
                lines.append("- Interpretação: **NÃO ÚTIL** — sem ganho material ou instável.")
        lines.append("")
    else:
        lines.append("### Código — Whittle 16B + DFlash2")
        lines.append("")
        lines.append("- N/A / não testado (gate 0–4/6 skip per SPEC)")
        lines.append("")
    if stage_c_rows:
        lines.append("### Agent — Whittle 16B native (Stage C)")
        lines.append("")
        lines.append(f"Fonte: `benchmarks/whittle16b-candidate-v1/results/WHITTLE16B_AGENT_RESULTS.jsonl` — template nativo Whittle + --jinja + OpenAI tools + author DRY + thinking ON")
        lines.append("")
        lines.append(f"- STRICT PASS: **{stage_c_strict}/8**")
        lines.append(f"- Score: **{stage_c_score}/80**")
        for r in stage_c_rows:
            st="PASS" if r["strict_pass"] else "FAIL"
            lines.append(f"  - {r['case_id']} {r['title']}: **{st}** {r['total_score']}/10 seq {r['observed_sequence']} loss {r['loss_reasons']}")
        lines.append("")
    else:
        lines.append("### Agent — Whittle 16B")
        lines.append("")
        lines.append("- N/A / não testado (gate: requer 6/6 coding estável). Se Stage A foi 5/6, agente não é elegível.")
        lines.append("")
    lines.append("## DECLARADO PELO AUTOR/ORIGEM")
    lines.append("")
    lines.append("- Origem HF: `logic65/Qwen3.8-Whittle-16B` (pruned 27B→~16.8B healed), recomendado GGUF `gguf/Qwen3.8-Whittle-16B-v2-Q4_K_M.gguf`.")
    lines.append(f"- Receita autora: `--jinja --dry-multiplier {DRY_MULTIPLIER} --dry-base {DRY_BASE} --dry-allowed-length {DRY_ALLOWED} --repeat-penalty {REPEAT_PENALTY} --repeat-last-n {REPEAT_LAST_N} --temp {TEMP_AUTHOR} --top-p {TOP_P_AUTHOR} --min-p {MIN_P_AUTHOR}` + thinking model.")
    lines.append("- Autor afirma THINKING MODEL; benchmark usou reasoning ON nativo com orçamento ≥2048 tokens (3072 usado).")
    lines.append("- Modelo estruturalmente podado → DFlash2 compatibility NÃO assumida.")
    lines.append("- Scores externos do card não foram usados para classificação; apenas medições locais.")
    lines.append("")
    lines.append("## Preset recomendado")
    lines.append("")
    # Preset based on measured
    if classification in ["WHITTLE16B_REJECT","WHITTLE16B_INTERESTING"] or stage_a_pass<=4:
        lines.append("```bash")
        lines.append("# Whittle 16B v2 Q4_K_M — receita autora (coding) — NÃO é preset padrão atual por gate 0–4/6 ou 5/6")
        lines.append(f"/home/alpha/.local/bin/llama serve \\")
        lines.append(f"  -m {MODEL_GGUF} \\")
        lines.append(f"  -c 8192 -np 1 -ngl 999 -fa on --fit off -ctk q8_0 -ctv q4_0 -t 8 -tb 8 \\")
        lines.append(f"  --jinja --reasoning on --reasoning-format auto --chat-template-kwargs '{{\"enable_thinking\":true}}' \\")
        lines.append(f"  --dry-multiplier {DRY_MULTIPLIER} --dry-base {DRY_BASE} --dry-allowed-length {DRY_ALLOWED} --repeat-penalty {REPEAT_PENALTY} --repeat-last-n {REPEAT_LAST_N}")
        lines.append("```")
        lines.append("- **Não usar como coder principal** até atingir 6/6 estável. GSQ continua preset padrão (ver `text/ISTA-DASLab-Qwen3.8-27B-GSQ-RCO-IQ2_S/`).")
    else:
        # 6/6 case
        if stage_b_status=="DFLASH2_COMPATIBLE" and stage_b_pass==6 and stage_b_med and stage_b_med> stage_a_med*1.1:
            lines.append("```bash")
            lines.append("# Whittle 16B v2 Q4_K_M + DFlash2 n=7 — validado, aceleração útil (quando DFlash2 compatível)")
            lines.append(f"/home/alpha/.local/bin/llama serve \\")
            lines.append(f"  -m {MODEL_GGUF} \\")
            lines.append(f"  -md {DRAFT_MODEL} --spec-type draft-dflash --spec-draft-n-max 7 -ngld 999 \\")
            lines.append(f"  -c 8192 -np 1 -ngl 999 -fa on --fit off -ctk q8_0 -ctv q4_0 -t 8 -tb 8 \\")
            lines.append(f"  --jinja --reasoning on --reasoning-format auto --chat-template-kwargs '{{\"enable_thinking\":true}}' \\")
            lines.append(f"  --dry-multiplier {DRY_MULTIPLIER} --dry-base {DRY_BASE} --dry-allowed-length {DRY_ALLOWED} --repeat-penalty {REPEAT_PENALTY} --repeat-last-n {REPEAT_LAST_N}")
            lines.append("```")
            lines.append("- DFlash2 considerado útil apenas se preservar qualidade e ganho material; acima medido como útil.")
        else:
            lines.append("```bash")
            lines.append("# Whittle 16B v2 Q4_K_M — receita autora nativa (sem DFlash2)")
            lines.append(f"/home/alpha/.local/bin/llama serve \\")
            lines.append(f"  -m {MODEL_GGUF} \\")
            lines.append(f"  -c 8192 -np 1 -ngl 999 -fa on --fit off -ctk q8_0 -ctv q4_0 -t 8 -tb 8 \\")
            lines.append(f"  --jinja --reasoning on --reasoning-format auto --chat-template-kwargs '{{\"enable_thinking\":true}}' \\")
            lines.append(f"  --dry-multiplier {DRY_MULTIPLIER} --dry-base {DRY_BASE} --dry-allowed-length {DRY_ALLOWED} --repeat-penalty {REPEAT_PENALTY} --repeat-last-n {REPEAT_LAST_N}")
            lines.append("```")
            if stage_b_status=="DFLASH2_INCOMPATIBLE_OR_UNUSABLE":
                lines.append("- DFlash2 incompatível nesta arquitetura; preset sem draft.")
    lines.append("")
    lines.append("## Limitações")
    lines.append("")
    lines.append(f"- Benchmark limitado a {stage_a_pass}/6 coding + {stage_c_strict if stage_c_strict is not None else 'N/A'}/8 agent; não cobre chat geral, escrita longa, ou tarefas repo-level.")
    lines.append("- Throughput AUTHOR_RECIPE não comparável a histórico same-protocol; usar apenas para custo operacional.")
    lines.append("- Poda estrutural — não assumir compatibilidade com futuros drafts speculative sem teste.")
    lines.append("- Amostras de GPU preflight em `results/gpu-preflight/`; todas passaram gate <25% SM.")
    lines.append(f"- Classificação final: **{classification}** — não promover com base em card HF.")
    lines.append("")
    lines.append("## Proveniência & validação")
    lines.append("")
    lines.append(f"- Benchmark raiz: `benchmarks/whittle16b-candidate-v1/SPEC.md`")
    lines.append(f"- Resultados: `benchmarks/whittle16b-candidate-v1/results/`")
    lines.append(f"- Manifest: `benchmarks/whittle16b-candidate-v1/results/RUN_MANIFEST.json`")
    lines.append(f"- Data: {now_date} / hardware {hardware} / runtime {runtime}")
    txt="\n".join(lines)+"\n"
    PROFILE_MD.write_text(txt, encoding="utf-8")
    log(f"Profile written")

if __name__=="__main__":
    main()
