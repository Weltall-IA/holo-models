#!/usr/bin/env python3
import os
import sys
import time
import json
import subprocess
import threading
import urllib.request
from pathlib import Path

ROOT = Path("/home/alpha/Playstoria/models").resolve()
MODEL_PATH = ROOT / "text/mradermacher-grug-v1.1-qwen-3.8-27b-i1-IQ3_M/grug-v1.1-qwen-3.8-27b.i1-IQ3_M.gguf"
LLAMA_BIN = Path.home() / ".local/bin/llama"
TASK_DIR = ROOT / "tasks/grug-reasoning-smoke-v1"
NO_THINK_JINJA = TASK_DIR / "grug-no-think.jinja"
PORT = 8195

PROMPT = "Escreva exatamente dois parágrafos curtos sobre um homem esperando um trem durante a chuva. Responda somente com a história."
SEED = 9137
TEMP = 0.2
TOP_P = 0.95
MAX_TOKENS = 256
CTX = 4096

PROFILES = [
    {
        "id": "profile_a_control",
        "name": "Perfil A — Controle Atual (Template Embutido + --reasoning off + chat-template-kwargs)",
        "chat_template_desc": "Template Jinja embutido no GGUF (contém renderização incondicional de <think> quando enable_thinking não é detectado pelo parser)",
        "server_args": [
            str(LLAMA_BIN), "serve",
            "-m", str(MODEL_PATH),
            "--host", "127.0.0.1", "--port", str(PORT),
            "-c", str(CTX), "-np", "1", "-ngl", "999",
            "-fa", "on", "--fit", "off",
            "-ctk", "q8_0", "-ctv", "q4_0",
            "-t", "8", "-tb", "8",
            "--jinja", "--reasoning", "off",
            "--chat-template-kwargs", json.dumps({"enable_thinking": False}, separators=(",", ":")),
            "--no-webui"
        ]
    },
    {
        "id": "profile_b_no_think_template",
        "name": "Perfil B — Template Customizado Sem <think> (add_generation_prompt limpo + --reasoning off)",
        "chat_template_desc": "Template Jinja local 'grug-no-think.jinja' com add_generation_prompt modificado para emitir apenas <|im_start|>assistant\\n",
        "server_args": [
            str(LLAMA_BIN), "serve",
            "-m", str(MODEL_PATH),
            "--host", "127.0.0.1", "--port", str(PORT),
            "-c", str(CTX), "-np", "1", "-ngl", "999",
            "-fa", "on", "--fit", "off",
            "-ctk", "q8_0", "-ctv", "q4_0",
            "-t", "8", "-tb", "8",
            "--jinja", "--reasoning", "off",
            "--chat-template-file", str(NO_THINK_JINJA),
            "--no-webui"
        ]
    },
    {
        "id": "profile_c_native_reasoning",
        "name": "Perfil C — Parser Nativo de Reasoning (Template Embutido + --reasoning on --reasoning-format deepseek)",
        "chat_template_desc": "Template Jinja embutido no GGUF + extração nativa de tags <think>...</think> para reasoning_content via --reasoning-format deepseek",
        "server_args": [
            str(LLAMA_BIN), "serve",
            "-m", str(MODEL_PATH),
            "--host", "127.0.0.1", "--port", str(PORT),
            "-c", str(CTX), "-np", "1", "-ngl", "999",
            "-fa", "on", "--fit", "off",
            "-ctk", "q8_0", "-ctv", "q4_0",
            "-t", "8", "-tb", "8",
            "--jinja", "--reasoning", "on",
            "--reasoning-format", "deepseek",
            "--no-webui"
        ]
    }
]

def get_vram_mib():
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            text=True, timeout=5
        )
        return int(out.strip().splitlines()[0])
    except Exception:
        return None

def wait_for_server(timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False

def post_stream(payload):
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    started = time.perf_counter()
    content_parts = []
    reasoning_parts = []
    usage = {}
    timings = {}
    raw_chunks = []
    finish_reason = None
    peak = get_vram_mib()
    stop = threading.Event()

    def sampler():
        nonlocal peak
        while not stop.wait(0.1):
            v = get_vram_mib()
            if v is not None and (peak is None or v > peak):
                peak = v

    th = threading.Thread(target=sampler, daemon=True)
    th.start()

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            for line_bytes in resp:
                line = line_bytes.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                item = line[5:].strip()
                if item == "[DONE]":
                    break
                try:
                    chunk = json.loads(item)
                except Exception:
                    continue
                raw_chunks.append(chunk)
                choices = chunk.get("choices") or []
                if choices:
                    c0 = choices[0]
                    if c0.get("finish_reason"):
                        finish_reason = c0.get("finish_reason")
                    delta = c0.get("delta") or {}
                    c = delta.get("content") or ""
                    r = delta.get("reasoning_content") or ""
                    if c:
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

    full_content = "".join(content_parts).strip()
    full_reasoning = "".join(reasoning_parts).strip()

    return {
        "content": full_content,
        "reasoning_content": full_reasoning,
        "finish_reason": finish_reason,
        "usage": usage,
        "timings": timings,
        "wall_time_s": round(ended - started, 4),
        "peak_vram_mib": peak,
        "raw_chunks_sample": raw_chunks[:5] + (raw_chunks[-3:] if len(raw_chunks) > 8 else [])
    }

def run_profile(prof):
    print(f"\n{'='*70}")
    print(f"Executing: {prof['name']}")
    print(f"{'='*70}")

    subprocess.run(["pkill", "-9", "-f", f"--port {PORT}"], capture_output=True)
    time.sleep(2)

    log_path = TASK_DIR / f"server-{prof['id']}.log"
    log_fp = open(log_path, "w", encoding="utf-8")

    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = f"/home/alpha/Playstoria/models/engines/llama.cpp/build/bin:{env.get('LD_LIBRARY_PATH', '')}"

    proc = subprocess.Popen(prof["server_args"], stdout=log_fp, stderr=subprocess.STDOUT, env=env)

    try:
        print("Waiting for server ready...")
        if not wait_for_server(180):
            print("ERROR: Server failed to start!")
            return {"profile": prof["id"], "error": "server_boot_timeout"}
        print("Server is ready! Sending request...")

        payload = {
            "messages": [{"role": "user", "content": PROMPT}],
            "temperature": TEMP,
            "top_p": TOP_P,
            "seed": SEED,
            "max_tokens": MAX_TOKENS,
            "stream": True
        }

        res = post_stream(payload)
        content = res["content"]
        reasoning = res["reasoning_content"]

        starts_think = content.startswith("<think>") or reasoning.startswith("<think>")
        contains_think_close = "</think>" in content or "</think>" in reasoning

        # Language heuristic
        # If content has portuguese words
        pt_words = {"homem", "estação", "trem", "chuva", "plataforma", "casaco", "frio", "olhou", "pingos", "noite", "trilhos", "esperava"}
        en_words = {"write", "portuguese", "words", "flash", "fiction", "character", "setting", "scene", "man", "waiting", "train", "rain"}
        
        c_words = set(content.lower().split())
        r_words = set(reasoning.lower().split())

        lang_content = "portuguese" if len(c_words.intersection(pt_words)) >= 2 else ("english" if len(c_words.intersection(en_words)) >= 2 else "unknown/empty")
        lang_reasoning = "english" if len(r_words.intersection(en_words)) >= 2 else ("portuguese" if len(r_words.intersection(pt_words)) >= 2 else "none")

        pred_tps = res["timings"].get("predicted_per_second")
        if pred_tps is None and res["wall_time_s"] > 0:
            pred_tps = round(res["usage"].get("completion_tokens", 0) / res["wall_time_s"], 2)

        print(f"Results for {prof['id']}:")
        print(f"  * Content length: {len(content)} chars ({len(content.split())} words)")
        print(f"  * Reasoning length: {len(reasoning)} chars ({len(reasoning.split())} words)")
        print(f"  * Starts with <think>? {starts_think}")
        print(f"  * Contains </think>? {contains_think_close}")
        print(f"  * Content Language: {lang_content}")
        print(f"  * Reasoning Language: {lang_reasoning}")
        print(f"  * Speed: {pred_tps} tok/s")
        print(f"  * Wall time: {res['wall_time_s']}s")
        print(f"  * Peak VRAM: {res['peak_vram_mib']} MiB")
        print(f"  * Content Preview:\n{content[:250]}")
        if reasoning:
            print(f"  * Reasoning Preview:\n{reasoning[:250]}")

        return {
            "profile_id": prof["id"],
            "profile_name": prof["name"],
            "server_command": " ".join(prof["server_args"]),
            "chat_template_used": prof["chat_template_desc"],
            "prompt": PROMPT,
            "seed": SEED,
            "temperature": TEMP,
            "top_p": TOP_P,
            "max_tokens": MAX_TOKENS,
            "ctx": CTX,
            "raw_response": {
                "content": content,
                "reasoning_content": reasoning,
                "finish_reason": res["finish_reason"],
                "usage": res["usage"],
                "timings": res["timings"]
            },
            "content": content,
            "reasoning_content": reasoning,
            "starts_with_think": starts_think,
            "contains_think_close": contains_think_close,
            "content_language": lang_content,
            "reasoning_language": lang_reasoning,
            "finished_normally": res["finish_reason"] in ("stop", "length", None),
            "predicted_per_second": pred_tps,
            "wall_time_s": res["wall_time_s"],
            "peak_vram_mib": res["peak_vram_mib"]
        }

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
    results = []
    for prof in PROFILES:
        r = run_profile(prof)
        results.append(r)

    out_json = TASK_DIR / "RESULTS.json"
    out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nAll smoke test profiles completed! Saved to {out_json}")

if __name__ == "__main__":
    main()
