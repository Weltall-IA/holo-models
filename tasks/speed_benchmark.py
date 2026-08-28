import os
import subprocess
import time
import requests
import json

LLAMA_SERVER = "/home/alpha/Playstoria/models/engines/deepgrove-llama.cpp/build/bin/llama-server"
LD_PATH = "/home/alpha/Playstoria/models/engines/deepgrove-llama.cpp/build/bin"

MODELS_TO_TEST = [
    {
        "name": "Qwen3.8-9B-Distill-uncensored-heretic (Q4_K_M)",
        "path": "text/petruhonk-Qwen3.8-9B-Distill-uncensored-heretic/Qwen3.8-9B-Distill-uncensored-heretic.i1-Q4_K_M.gguf"
    },
    {
        "name": "RVN-IQ3_M-multilingual-mtp",
        "path": "text/0bserverx-Qwen3.8-27B-Heretic-RVN-IQ3_M-multilingual-MTP/RVN-IQ3_M-multilingual-mtp.gguf"
    },
    {
        "name": "HauhauCS Aggressive IQ3_XS",
        "path": "text/HauhauCS-Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-IQ3_XS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-IQ3_XS.gguf"
    }
]

def get_vram_mib():
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], text=True)
        return int(out.strip().split("\n")[0])
    except Exception:
        return 0

def test_model(m, port=8089):
    print(f"\n=======================================================")
    print(f"Testing speed for: {m['name']}")
    print(f"Path: {m['path']}")
    print(f"=======================================================")
    
    if not os.path.exists(m["path"]):
        print(f"File {m['path']} does not exist!")
        return {"name": m["name"], "error": "File not found"}
        
    idle_vram = get_vram_mib()
    
    cmd = [
        LLAMA_SERVER,
        "-m", os.path.abspath(m["path"]),
        "--host", "127.0.0.1",
        "--port", str(port),
        "-c", "4096",
        "-ngl", "999",
        "--cache-type-k", "q4_0",
        "--cache-type-v", "q4_0",
        "-fa", "on",
        "--parallel", "1",
        "--threads", "8",
        "--threads-batch", "8",
        "--jinja"
    ]
    
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = f"{LD_PATH}:{env.get('LD_LIBRARY_PATH', '')}"
    env["OMP_NUM_THREADS"] = "8"
    
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    
    # Wait for server ready
    ready = False
    start_t = time.time()
    while time.time() - start_t < 90:
        try:
            r = requests.get(f"http://127.0.0.1:{port}/health", timeout=1)
            if r.status_code == 200:
                ready = True
                break
        except Exception:
            pass
        time.sleep(0.5)
        
    if not ready:
        try: proc.kill()
        except: pass
        return {"name": m["name"], "error": "Failed to boot / OOM"}
        
    loaded_vram = get_vram_mib()
    
    # Warmup
    try:
        requests.post(f"http://127.0.0.1:{port}/v1/chat/completions", json={
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 10
        }, timeout=30)
    except Exception:
        pass
        
    # Speed test run 1: short prompt, 256 tokens generation
    payload = {
        "messages": [
            {"role": "user", "content": "Write an extensive essay detailing the history and principles of quantum computing."}
        ],
        "max_tokens": 256,
        "temperature": 0.2,
        "top_p": 0.95,
        "stream": False
    }
    
    res = requests.post(f"http://127.0.0.1:{port}/v1/chat/completions", json=payload, timeout=60)
    data = res.json()
    
    peak_vram = get_vram_mib()
    timings = data.get("timings", {})
    usage = data.get("usage", {})
    
    tok_per_sec = timings.get("predicted_per_second", 0.0)
    prompt_per_sec = timings.get("prompt_per_second", 0.0)
    ttft_s = (timings.get("prompt_ms", 0.0) or 0.0) / 1000.0
    comp_tokens = usage.get("completion_tokens", 0)
    
    # Clean shutdown
    try:
        proc.kill()
        proc.wait(timeout=5)
    except Exception:
        pass
    try:
        subprocess.run(["pkill", "-9", "-f", f"--port {port}"], capture_output=True, timeout=2)
    except Exception:
        pass
    time.sleep(2)
    
    print(f"Results for {m['name']}:")
    print(f"  - Decode Speed: {tok_per_sec:.2f} tok/s")
    print(f"  - Prompt Processing: {prompt_per_sec:.2f} tok/s (TTFT: {ttft_s:.4f}s)")
    print(f"  - Generated Tokens: {comp_tokens}")
    print(f"  - Idle VRAM: {idle_vram} MiB | Loaded/Peak VRAM: {peak_vram} MiB")
    
    return {
        "name": m["name"],
        "tok_per_sec": round(tok_per_sec, 2),
        "prompt_tok_per_sec": round(prompt_per_sec, 2),
        "ttft_s": round(ttft_s, 4),
        "completion_tokens": comp_tokens,
        "idle_vram_mib": idle_vram,
        "peak_vram_mib": peak_vram,
        "vram_delta_mib": peak_vram - idle_vram
    }

if __name__ == "__main__":
    results = []
    for m in MODELS_TO_TEST:
        res = test_model(m)
        results.append(res)
    print("\n\n================ FINAL SPEED SUMMARY ================")
    print(json.dumps(results, indent=2))
