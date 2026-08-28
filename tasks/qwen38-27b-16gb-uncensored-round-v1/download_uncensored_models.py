import hashlib
import json
import os
import time
from huggingface_hub import HfApi, hf_hub_download

TARGETS = [
    {
        "id": "ektome",
        "label": "Ektome PristinelyUncensored i1-IQ3_M",
        "repo_id": "mradermacher/Ektome-Qwen3.8-27B-PristinelyUncensored-i1-GGUF",
        "filename": "Ektome-Qwen3.8-27B-PristinelyUncensored.i1-IQ3_M.gguf",
        "target_dir": "text/mradermacher-Ektome-Qwen3.8-27B-PristinelyUncensored-i1-IQ3_M",
        "aux_files": []
    },
    {
        "id": "ara",
        "label": "Heretic ARA i1-IQ3_M",
        "repo_id": "mradermacher/Qwen3.8-27B-heretic-ara-i1-GGUF",
        "filename": "Qwen3.8-27B-heretic-ara.i1-IQ3_M.gguf",
        "target_dir": "text/mradermacher-Qwen3.8-27B-heretic-ara-i1-IQ3_M",
        "aux_files": []
    },
    {
        "id": "ultimate",
        "label": "ULTIMATE UNCENSORED Hybrid 16GB",
        "repo_id": "lemonyins/Qwen3.8-27B-ULTIMATE-UNCENSORED-MTP-IQ4-GGUF-16GB",
        "filename": "Qwen3.8-27B-ULTIMATE-UNCENSORED-MTP-IQ4-16GB.gguf",
        "target_dir": "text/lemonyins-Qwen3.8-27B-ULTIMATE-UNCENSORED-MTP-IQ4-16GB",
        "aux_files": ["chat_template.jinja"]
    }
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
    out_dir = "tasks/qwen38-27b-16gb-uncensored-round-v1"
    os.makedirs(out_dir, exist_ok=True)
    
    results = []
    
    for t in TARGETS:
        print(f"\n=======================================================")
        print(f"Target: {t['label']} ({t['id']})")
        print(f"Repo: {t['repo_id']}")
        print(f"File: {t['filename']}")
        print(f"Directory: {t['target_dir']}")
        print(f"=======================================================")
        
        info = api.repo_info(repo_id=t['repo_id'], files_metadata=True)
        commit_sha = info.sha
        remote_file_info = next((f for f in info.siblings if f.rfilename == t['filename']), None)
        remote_size = remote_file_info.size if remote_file_info else None
        
        os.makedirs(t['target_dir'], exist_ok=True)
        final_path = os.path.join(t['target_dir'], t['filename'])
        
        if os.path.exists(final_path):
            local_size = os.path.getsize(final_path)
            print(f"File already exists locally ({local_size} bytes). Remote is {remote_size} bytes.")
            if remote_size and local_size != remote_size:
                print("Size mismatch! Removing corrupted file...")
                os.remove(final_path)
                
        if not os.path.exists(final_path):
            print(f"Downloading {t['filename']} from {t['repo_id']}...")
            start_t = time.time()
            downloaded = hf_hub_download(
                repo_id=t['repo_id'],
                filename=t['filename'],
                local_dir=t['target_dir']
            )
            elapsed = time.time() - start_t
            print(f"Downloaded {t['filename']} in {elapsed:.1f}s")
            final_path = downloaded
            
        file_size = os.path.getsize(final_path)
        sha256 = compute_sha256(final_path)
        print(f"Main GGUF Size: {file_size} bytes ({file_size / (1024**3):.2f} GiB)")
        print(f"Main GGUF SHA256: {sha256}")
        
        aux_results = []
        for aux in t['aux_files']:
            aux_path = os.path.join(t['target_dir'], aux)
            if not os.path.exists(aux_path):
                print(f"Downloading auxiliary file: {aux}...")
                downloaded_aux = hf_hub_download(
                    repo_id=t['repo_id'],
                    filename=aux,
                    local_dir=t['target_dir']
                )
                aux_path = downloaded_aux
            aux_size = os.path.getsize(aux_path)
            aux_sha256 = compute_sha256(aux_path)
            print(f"Aux File: {aux} ({aux_size} bytes, SHA256: {aux_sha256})")
            aux_results.append({
                "filename": aux,
                "local_path": os.path.abspath(aux_path),
                "size_bytes": aux_size,
                "sha256": aux_sha256
            })
            
        record = {
            "id": t["id"],
            "label": t["label"],
            "repo_id": t["repo_id"],
            "commit_sha": commit_sha,
            "filename": t["filename"],
            "local_path": os.path.abspath(final_path),
            "size_bytes": file_size,
            "size_gib": round(file_size / (1024**3), 2),
            "sha256": sha256,
            "aux_files": aux_results
        }
        results.append(record)
        
        with open(os.path.join(out_dir, "models.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
            
    print("\nAll downloads and verifications complete!")

if __name__ == "__main__":
    main()
