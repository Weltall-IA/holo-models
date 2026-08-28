import json
from huggingface_hub import list_repo_files

candidates = [
    {"id": "A", "name": "Fable-Heretic", "repo": "armand0e/Qwen3.8-27B-Fable-Distill-Heretic-ara-GGUF", "target": "Q3_K_M"},
    {"id": "B", "name": "T10", "repo": "mradermacher/Qwen3.8-27B-Uncensored-Heretic-T10-BF16-i1-GGUF", "target": "i1-IQ3_M"},
    {"id": "C", "name": "Bucoid-ARA", "repo": "Bucoid/Qwen3.8-27B-Heretic-Ara-16GB-VRAM-IQ4-XS-MTP-GGUF", "target": "IQ4_XS"},
    {"id": "D", "name": "GRUG-v1.1", "repo": "mradermacher/grug-v1.1-qwen-3.8-27b-i1-GGUF", "target": "i1-IQ3_M"},
    {"id": "E", "name": "Ektome", "repo": "mradermacher/Ektome-Qwen3.8-27B-PristinelyUncensored-i1-GGUF", "target": "i1-IQ3_M"},
    {"id": "F", "name": "RVN-baseline", "repo": "0bserverx/Qwen3.8-27B-Heretic-Abliterated-Uncensored-GGUF", "target": "Q3_K_M"},
]

results = {}
for cand in candidates:
    print(f"=== Candidate {cand['id']}: {cand['name']} ({cand['repo']}) Target: {cand['target']} ===")
    try:
        files = list_repo_files(cand['repo'])
        matches = []
        target_clean = cand['target'].lower().replace("-", "_")
        for f in files:
            fl = f.lower().replace("-", "_")
            if fl.endswith('.gguf') and target_clean in fl and 'mmproj' not in fl:
                matches.append(f)
        print("Matches:", matches)
        if not matches:
            all_ggufs = [f for f in files if f.lower().endswith('.gguf')]
            print("All GGUF files:", all_ggufs)
        results[cand['id']] = {
            "cand": cand,
            "matches": matches,
            "all_files": files
        }
    except Exception as e:
        print("Error:", e)
        results[cand['id']] = {"error": str(e)}

with open("tasks/qwen38-27b-16gb-quick-v1/check_remote_results.json", "w") as f:
    json.dump(results, f, indent=2)
