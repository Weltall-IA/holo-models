import hashlib
import json
import os
import shutil
import time
from huggingface_hub import HfApi, hf_hub_download

CANDIDATES = [
    {
        "id": "A_fable_heretic",
        "name": "Fable-Heretic",
        "repo_id": "armand0e/Qwen3.8-27B-Fable-Distill-Heretic-ara-GGUF",
        "filename": "Qwen3.8-27B-Fable-Distill-Heretic-ara-Q3_K_M.gguf",
        "quant": "Q3_K_M",
        "target_dir": "text/armand0e-Qwen3.8-27B-Fable-Distill-Heretic-ara-Q3_K_M",
    },
    {
        "id": "B_t10",
        "name": "T10",
        "repo_id": "mradermacher/Qwen3.8-27B-Uncensored-Heretic-T10-BF16-i1-GGUF",
        "filename": "Qwen3.8-27B-Uncensored-Heretic-T10-BF16.i1-IQ3_M.gguf",
        "quant": "i1-IQ3_M",
        "target_dir": "text/mradermacher-Qwen3.8-27B-Uncensored-Heretic-T10-BF16-i1-IQ3_M",
    },
    {
        "id": "C_bucoid_ara",
        "name": "Bucoid ARA",
        "repo_id": "Bucoid/Qwen3.8-27B-Heretic-Ara-16GB-VRAM-IQ4-XS-MTP-GGUF",
        "filename": "Qwen3.8-27B-Heretic-Ara-iq4_xs-3.0.gguf",
        "quant": "IQ4_XS",
        "target_dir": "text/Bucoid-Qwen3.8-27B-Heretic-Ara-IQ4_XS",
    },
    {
        "id": "D_grug_v11",
        "name": "GRUG v1.1",
        "repo_id": "mradermacher/grug-v1.1-qwen-3.8-27b-i1-GGUF",
        "filename": "grug-v1.1-qwen-3.8-27b.i1-IQ3_M.gguf",
        "quant": "i1-IQ3_M",
        "target_dir": "text/mradermacher-grug-v1.1-qwen-3.8-27b-i1-IQ3_M",
    },
    {
        "id": "E_ektome",
        "name": "Ektome",
        "repo_id": "mradermacher/Ektome-Qwen3.8-27B-PristinelyUncensored-i1-GGUF",
        "filename": "Ektome-Qwen3.8-27B-PristinelyUncensored.i1-IQ3_M.gguf",
        "quant": "i1-IQ3_M",
        "target_dir": "text/mradermacher-Ektome-Qwen3.8-27B-PristinelyUncensored-i1-IQ3_M",
    },
    {
        "id": "F_rvn_baseline",
        "name": "RVN baseline",
        "repo_id": "0bserverx/Qwen3.8-27B-Heretic-Abliterated-Uncensored-GGUF",
        "filename": "RVN-Q3_K_M.gguf",
        "quant": "Q3_K_M",
        "target_dir": "text/0bserverx-Qwen3.8-27B-Heretic-Abliterated-Uncensored-Q3_K_M",
    },
]

def compute_sha256(filepath):
    print(f"Computing SHA256 for {filepath}...")
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(16 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def main():
    api = HfApi()
    results = []
    
    for c in CANDIDATES:
        print(f"\n=======================================================")
        print(f"Processing candidate: {c['name']} ({c['id']})")
        print(f"Repo: {c['repo_id']}")
        print(f"File: {c['filename']}")
        print(f"Target dir: {c['target_dir']}")
        print(f"=======================================================")
        
        info = api.repo_info(repo_id=c['repo_id'], files_metadata=True)
        commit_sha = info.sha
        remote_file_info = next((f for f in info.siblings if f.rfilename == c['filename']), None)
        remote_size = remote_file_info.size if remote_file_info else None
        
        os.makedirs(c['target_dir'], exist_ok=True)
        final_path = os.path.join(c['target_dir'], c['filename'])
        
        if os.path.exists(final_path):
            local_size = os.path.getsize(final_path)
            print(f"File already exists locally ({local_size} bytes). Checking size vs remote ({remote_size} bytes)...")
            if remote_size and local_size == remote_size:
                print("Local size matches remote.")
            else:
                print("Size mismatch! Re-downloading...")
                os.remove(final_path)
        
        if not os.path.exists(final_path):
            print(f"Downloading {c['filename']} from {c['repo_id']}...")
            start_t = time.time()
            downloaded_path = hf_hub_download(
                repo_id=c['repo_id'],
                filename=c['filename'],
                local_dir=c['target_dir'],
            )
            elapsed = time.time() - start_t
            print(f"Downloaded in {elapsed:.1f}s to {downloaded_path}")
            final_path = downloaded_path
            
        file_size = os.path.getsize(final_path)
        sha256 = compute_sha256(final_path)
        print(f"Size: {file_size} bytes ({file_size / (1024**3):.2f} GiB)")
        print(f"SHA256: {sha256}")
        
        item = {
            "id": c["id"],
            "name": c["name"],
            "repo_id": c["repo_id"],
            "filename": c["filename"],
            "commit_sha": commit_sha,
            "quant": c["quant"],
            "local_path": os.path.abspath(final_path),
            "size_bytes": file_size,
            "size_gib": round(file_size / (1024**3), 2),
            "sha256": sha256
        }
        results.append(item)
        
        # Save progress
        with open("tasks/qwen38-27b-16gb-quick-v1/models.json", "w") as f:
            json.dump(results, f, indent=2)
            
    print("\nAll downloads completed and recorded successfully.")

if __name__ == "__main__":
    main()
