import os
import signal
import subprocess
import time
import requests

def get_gpu_vram_mib():
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            text=True
        )
        return int(out.strip().split("\n")[0])
    except Exception:
        return 0

class LlamaServerProcess:
    def __init__(
        self,
        model_path: str,
        ctx_size: int = 16384,
        port: int = 8089,
        kv_cache_type: str = "q4_0",
        flash_attn: bool = True,
        ngl: int = 999
    ):
        self.model_path = model_path
        self.ctx_size = ctx_size
        self.port = port
        self.kv_cache_type = kv_cache_type
        self.flash_attn = flash_attn
        self.ngl = ngl
        self.process = None
        self.base_url = f"http://127.0.0.1:{port}"
        self.idle_vram = 0
        self.peak_vram = 0

    def start(self, timeout_secs: int = 120):
        # Ensure any old server is stopped and GPU memory settled
        try:
            subprocess.run(["pkill", "-9", "-f", "llama-server"], capture_output=True, timeout=2)
        except Exception:
            pass
        time.sleep(2)
        
        self.idle_vram = get_gpu_vram_mib()
        self.peak_vram = self.idle_vram
        
        server_bin = "engines/deepgrove-llama.cpp/build/bin/llama-server"
        ld_path = "engines/deepgrove-llama.cpp/build/bin"
        
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = f"{ld_path}:{env.get('LD_LIBRARY_PATH', '')}"
        
        cmd = [
            server_bin,
            "-m", self.model_path,
            "-c", str(self.ctx_size),
            "-ngl", str(self.ngl),
            "--parallel", "1",
            "--port", str(self.port),
            "--host", "127.0.0.1",
            "-ctk", self.kv_cache_type,
            "-ctv", self.kv_cache_type,
        ]
        if self.flash_attn:
            cmd.extend(["-fa", "on"])
            
        log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "llama_server.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self.log_file = open(log_path, "a", encoding="utf-8")
        self.log_file.write(f"\n\n--- Starting server at {time.ctime()} ---\n{' '.join(cmd)}\n")
        self.log_file.flush()

        print(f"Starting llama-server: {' '.join(cmd)}", flush=True)
        self.process = subprocess.Popen(
            cmd,
            env=env,
            stdout=self.log_file,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Wait for server to become healthy on /health
        start_t = time.time()
        ready = False
        while time.time() - start_t < timeout_secs:
            current_vram = get_gpu_vram_mib()
            if current_vram > self.peak_vram:
                self.peak_vram = current_vram
                
            if self.process.poll() is not None:
                self.log_file.flush()
                with open(log_path, "r", encoding="utf-8", errors="ignore") as lf:
                    last_lines = lf.readlines()[-30:]
                raise RuntimeError(f"Server exited prematurely with code {self.process.returncode}:\n{''.join(last_lines)}")
                
            try:
                res = requests.get(f"{self.base_url}/health", timeout=1)
                if res.status_code == 200:
                    ready = True
                    break
            except Exception:
                pass
            time.sleep(0.5)
            
        if not ready:
            self.stop()
            raise TimeoutError(f"Server failed to become ready within {timeout_secs}s")
            
        print(f"Server ready on {self.base_url} (Idle VRAM: {self.idle_vram} MiB, Loaded VRAM: {self.peak_vram} MiB)", flush=True)

    def is_alive(self) -> bool:
        if self.process is None:
            return False
        if self.process.poll() is not None:
            return False
        try:
            res = requests.get(f"{self.base_url}/health", timeout=1)
            return res.status_code == 200
        except Exception:
            return False

    def ensure_alive(self):
        if not self.is_alive():
            print("Server is not alive! Attempting restart...", flush=True)
            self.stop()
            self.start()
            self.warmup()

    def update_peak_vram(self):
        v = get_gpu_vram_mib()
        if v > self.peak_vram:
            self.peak_vram = v
        return self.peak_vram

    def warmup(self):
        print("Performing warmup request...")
        try:
            res = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                    "temperature": 0.2
                },
                timeout=30
            )
            self.update_peak_vram()
            print("Warmup complete.")
        except Exception as e:
            print(f"Warmup error: {e}")

    def stop(self):
        if self.process:
            print(f"Stopping llama-server on port {self.port}...", flush=True)
            try:
                os.kill(self.process.pid, signal.SIGKILL)
            except Exception:
                pass
            try:
                self.process.kill()
                self.process.wait(timeout=2)
            except Exception:
                pass
            self.process = None
            
        try:
            subprocess.run(["pkill", "-9", "-f", "llama-server"], capture_output=True, timeout=2)
        except Exception:
            pass
            
        if hasattr(self, "log_file") and self.log_file:
            try:
                self.log_file.close()
            except Exception:
                pass
            self.log_file = None
            
        # Give OS / driver a moment to reclaim VRAM
        time.sleep(2)
        print(f"Stopped. VRAM now: {get_gpu_vram_mib()} MiB (Peak observed: {self.peak_vram} MiB)", flush=True)
