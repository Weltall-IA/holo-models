import os
import sys
import time
import json
import subprocess
import urllib.request

LLAMA_SERVER_BIN = "/home/alpha/Playstoria/models/engines/deepgrove-llama.cpp/build/bin/llama-server"
LLAMA_LIB_PATH = "/home/alpha/Playstoria/models/engines/deepgrove-llama.cpp/build/bin"
GEMMA_GGUF = "/home/alpha/Playstoria/models/text/mradermacher-gemma-4-21b-a4b-it-REAP-heretic-Q4_K_S/gemma-4-21b-a4b-it-REAP-heretic.Q4_K_S.gguf"

# 1. Kill any running server
subprocess.run(["pkill", "-9", "-f", "llama-server"], capture_output=True)
time.sleep(3)

env = os.environ.copy()
env["LD_LIBRARY_PATH"] = f"{LLAMA_LIB_PATH}:{env.get('LD_LIBRARY_PATH', '')}"

cmd = [
    LLAMA_SERVER_BIN,
    "-m", GEMMA_GGUF,
    "--port", "8088",
    "--host", "127.0.0.1",
    "-c", "8192",
    "-np", "1",
    "-ngl", "26",
    "-fa", "on",
    "-ctk", "q8_0",
    "-ctv", "q8_0",
    "-t", "4",
    "-tb", "4",
    "--jinja",
    "--chat-template-kwargs", '{"enable_thinking":false}'
]

print("Launching Gemma 4 server with config:")
print(" ".join(cmd))
proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

def wait_ready(port=8088, timeout=60):
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/health")
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("status") == "ok":
                    print("Server ready!")
                    return True
        except Exception:
            time.sleep(1)
    return False

if not wait_ready():
    print("Failed to start server!")
    proc.terminate()
    sys.exit(1)

smoke_tests = [
    ("A", "Responda apenas: OK", 50),
    ("B", "Escreva 300 palavras em português brasileiro sobre dois amigos conversando durante uma tempestade.", 1000),
    ("C", "Escreva 500 palavras de ficção em português brasileiro com bastante diálogo.", 1500),
]

for label, prompt_text, max_tok in smoke_tests:
    print(f"\n==================== TESTE SMOKE {label} ====================")
    print(f"Prompt: {prompt_text}")
    payload = {
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 64,
        "max_tokens": max_tok,
        "seed": 3407,
        "stream": True
    }
    req = urllib.request.Request(
        "http://127.0.0.1:8088/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    content_parts = []
    reasoning_parts = []
    
    with urllib.request.urlopen(req, timeout=300) as resp:
        for line in resp:
            line_str = line.decode("utf-8").strip()
            if not line_str or not line_str.startswith("data:"):
                continue
            data_str = line_str[5:].strip()
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
                delta = chunk["choices"][0].get("delta", {})
                r = delta.get("reasoning_content", "")
                if r: reasoning_parts.append(r)
                c = delta.get("content", "")
                if c: content_parts.append(c)
            except Exception: pass
            
    t1 = time.time()
    full_content = "".join(content_parts)
    full_reasoning = "".join(reasoning_parts)
    
    print(f"--- RESULTADO SMOKE {label} ({t1-t0:.2f}s) ---")
    print(f"Reasoning text captured: {repr(full_reasoning)}")
    print(f"Content text captured (first 500 chars):\n{full_content[:500]}")
    print(f"Content text end (last 200 chars):\n{full_content[-200:] if len(full_content) > 200 else full_content}")
    print(f"Total chars: {len(full_content)}, Total words: {len(full_content.split())}")

proc.terminate()
proc.wait()
