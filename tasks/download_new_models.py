import os
import time
import hashlib
import json
from huggingface_hub import HfApi, hf_hub_download, snapshot_download

# Read token
TOKEN_PATH = "/home/alpha/Playstoria/.hf_token"
token = None
if os.path.exists(TOKEN_PATH):
    with open(TOKEN_PATH, "r") as f:
        token = f.read().strip()

api = HfApi(token=token)

def compute_sha256(filepath):
    print(f"Computing SHA256 for {filepath}...")
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(16 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def download_model_1():
    print("\n=======================================================")
    print("1. Downloading petruhonk/Qwen3.8-9B-Distill-uncensored-heretic")
    print("=======================================================")
    repo_id = "petruhonk/Qwen3.8-9B-Distill-uncensored-heretic"
    target_dir = "text/petruhonk-Qwen3.8-9B-Distill-uncensored-heretic"
    os.makedirs(target_dir, exist_ok=True)
    
    t0 = time.time()
    snapshot_download(
        repo_id=repo_id,
        local_dir=target_dir,
        token=token
    )
    print(f"Downloaded repo in {time.time() - t0:.1f}s")
    
    # Also download GGUF Q8_0 from petruhonk GGUF repo for speed test
    gguf_repo = "petruhonk/Qwen3.8-9B-Distill-uncensored-heretic-GGUF"
    gguf_file = "Qwen3.8-9B-Distill-Heretic-Uncensored-Q8_0.gguf"
    print(f"\nDownloading GGUF {gguf_file} from {gguf_repo} for speed test...")
    hf_hub_download(
        repo_id=gguf_repo,
        filename=gguf_file,
        local_dir=target_dir,
        token=token
    )
    gguf_path = os.path.join(target_dir, gguf_file)
    print(f"GGUF size: {os.path.getsize(gguf_path)} bytes, SHA256: {compute_sha256(gguf_path)}")

def download_model_2():
    print("\n=======================================================")
    print("2. Downloading RVN-IQ3_M-multilingual-mtp")
    print("=======================================================")
    repo_id = "0bserverx/Qwen3.8-27B-Heretic-Abliterated-Uncensored-GGUF"
    filename = "RVN-IQ3_M-multilingual-mtp.gguf"
    target_dir = "text/0bserverx-Qwen3.8-27B-Heretic-RVN-IQ3_M-multilingual-MTP"
    os.makedirs(target_dir, exist_ok=True)
    
    final_path = os.path.join(target_dir, filename)
    if not os.path.exists(final_path):
        t0 = time.time()
        hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=target_dir,
            token=token
        )
        print(f"Downloaded {filename} in {time.time() - t0:.1f}s")
    print(f"File size: {os.path.getsize(final_path)} bytes, SHA256: {compute_sha256(final_path)}")

def download_model_3():
    print("\n=======================================================")
    print("3. Downloading HauhauCS Aggressive IQ3_XS")
    print("=======================================================")
    repo_id = "HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF"
    filename = "Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-IQ3_XS.gguf"
    target_dir = "text/HauhauCS-Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-IQ3_XS"
    os.makedirs(target_dir, exist_ok=True)
    
    final_path = os.path.join(target_dir, filename)
    if not os.path.exists(final_path):
        t0 = time.time()
        hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=target_dir,
            token=token
        )
        print(f"Downloaded {filename} in {time.time() - t0:.1f}s")
    print(f"File size: {os.path.getsize(final_path)} bytes, SHA256: {compute_sha256(final_path)}")

if __name__ == "__main__":
    download_model_1()
    download_model_2()
    download_model_3()
    print("\nAll 3 downloads completed successfully.")
