import json
import os
import signal
import subprocess
import time
import urllib.request
import urllib.error
import threading

MODEL_PATH = "/home/alpha/Playstoria/models/text/aj9o9-Qwen3.8-27B-Escha-W2-GGUF/Escha-Qwen3.8-27B-W2-Q8E.gguf"
SERVER_BIN = "/home/alpha/Playstoria/models/engines/escha-llama/build/bin/llama-server"
PROMPT = "Write a long numbered sequence of concise software engineering observations. Continue until the generation limit. Do not stop early."

def get_vram():
    out = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=memory.used,memory.free,memory.total", "--format=csv,noheader,nounits"],
        text=True
    ).strip()
    used, free, total = [int(x.strip()) for x in out.split(",")]
    return used, free, total

def poll_peak_vram(stop_event, peak_container):
    while not stop_event.is_set():
        used, _, _ = get_vram()
        if used > peak_container[0]:
            peak_container[0] = used
        time.sleep(0.05)

def run_profile(name, ctk, ctv):
    print(f"\n================ Running Profile: {name} (ctk={ctk}, ctv={ctv}) ================")
    cmd = [
        SERVER_BIN,
        "-m", MODEL_PATH,
        "-ngl", "99",
        "-fa", "on",
        "-np", "1",
        "-t", "8",
        "-c", "8192",
        "--host", "127.0.0.1",
        "--port", "8080",
        "-ctk", ctk,
        "-ctv", ctv,
    ]
    log_file = f"/home/alpha/Playstoria/models/benchmarks/escha-runtime-micro-v1/server_{name}.log"
    os.makedirs("/home/alpha/Playstoria/models/benchmarks/escha-runtime-micro-v1", exist_ok=True)
    with open(log_file, "w") as f_log:
        proc = subprocess.Popen(cmd, stdout=f_log, stderr=subprocess.STDOUT, text=True)

    print("Waiting for server to start...")
    ready = False
    for _ in range(60):
        try:
            req = urllib.request.Request("http://127.0.0.1:8080/health")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(1)

    if not ready:
        proc.kill()
        raise RuntimeError(f"Server failed to start for {name}. Check {log_file}")

    print("Server ready. Recording idle VRAM...")
    time.sleep(2)
    idle_vram, _, _ = get_vram()
    print(f"Idle VRAM: {idle_vram} MiB")

    results = []
    overall_peak_vram = idle_vram

    for i in range(1, 6):
        print(f"Running iteration {i}/5...")
        peak_container = [idle_vram]
        stop_event = threading.Event()
        monitor_thread = threading.Thread(target=poll_peak_vram, args=(stop_event, peak_container))
        monitor_thread.start()

        payload = {
            "prompt": PROMPT,
            "n_predict": 256,
            "temperature": 0.0,
            "ignore_eos": True,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:8080/completion",
            data=data,
            headers={"Content-Type": "application/json"}
        )

        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=120) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
        t1 = time.perf_counter()

        stop_event.set()
        monitor_thread.join()

        iteration_peak = peak_container[0]
        if iteration_peak > overall_peak_vram:
            overall_peak_vram = iteration_peak

        timings = resp_data.get("timings", {})
        predicted_n = timings.get("predicted_n", 0)
        predicted_ms = timings.get("predicted_ms", 0.0)
        predicted_per_second = timings.get("predicted_per_second", 0.0)
        prompt_n = timings.get("prompt_n", 0)
        prompt_ms = timings.get("prompt_ms", 0.0)
        prompt_per_second = timings.get("prompt_per_second", 0.0)

        print(f"  Run {i}: prompt={prompt_n} toks in {prompt_ms:.2f}ms ({prompt_per_second:.2f} t/s), gen={predicted_n} toks in {predicted_ms:.2f}ms ({predicted_per_second:.2f} t/s), wall={t1-t0:.2f}s, peak_vram={iteration_peak} MiB")
        results.append({
            "run": i,
            "prompt_n": prompt_n,
            "prompt_ms": prompt_ms,
            "prompt_per_second": prompt_per_second,
            "predicted_n": predicted_n,
            "predicted_ms": predicted_ms,
            "predicted_per_second": predicted_per_second,
            "wall_time_s": t1 - t0,
            "peak_vram_mib": iteration_peak,
            "content_sample": resp_data.get("content", "")[:100]
        })

    print(f"Stopping server (PID {proc.pid})...")
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    time.sleep(2)
    post_vram, _, _ = get_vram()
    print(f"Post-stop VRAM: {post_vram} MiB")

    summary = {
        "profile": name,
        "ctk": ctk,
        "ctv": ctv,
        "idle_vram_mib": idle_vram,
        "peak_vram_mib": overall_peak_vram,
        "runs": results
    }

    return summary

def main():
    print("Starting Phase 1B microbenchmarks...")
    summary_a = run_profile("Profile_A_Q8_Q4", "q8_0", "q4_0")
    summary_b = run_profile("Profile_B_Q8_Q8", "q8_0", "q8_0")

    summary_file = "/home/alpha/Playstoria/models/benchmarks/escha-runtime-micro-v1/phase1b_summary.json"
    with open(summary_file, "w") as f:
        json.dump({"profile_a": summary_a, "profile_b": summary_b}, f, indent=2)
    print(f"\nPhase 1B completed. Summary saved to {summary_file}")

if __name__ == "__main__":
    main()
