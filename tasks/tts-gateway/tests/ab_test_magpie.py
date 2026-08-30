import io
import os
import sys
import time
import torch
import soundfile as sf
import numpy as np

# Ensure NeMo imports work
from nemo.collections.tts.models import MagpieTTSModel
from nemo.collections.tts.parts.utils import tts_dataset_utils

MODEL_PATH = os.path.expanduser(
    "~/Playstoria/models/audio/voz/nvidia-magpie_tts_multilingual_357m/magpie_tts_multilingual_357m.nemo"
)
OUTPUT_DIR = os.path.expanduser(
    "~/Playstoria/models/tasks/tts-gateway/tests/ab_test"
)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Test phrases
PHRASE_1 = "João chegou às 15:20 da tarde. Ele comprou 15 pães na padaria e perguntou: você também quer café?"
PHRASE_2 = "O Dr. Silva pagou R$ 34,50 pelo almoço com seu filho no restaurante."

SPEAKERS = {
    "sofia": 4,
    "leo": 3,
    "jason": 1
}

def run_test():
    print("=" * 70)
    print("MAGPIE TTS PORTUGUESE A/B INVESTIGATION & VALIDATION")
    print("=" * 70)

    # 1. Model inspection
    print(f"Loading MagpieTTSModel from {MODEL_PATH}...")
    t0 = time.time()
    model = MagpieTTSModel.restore_from(MODEL_PATH, map_location="cuda")
    model.eval()
    print(f"Model loaded in {time.time() - t0:.2f}s on cuda")

    print("\n--- Model Tokenizers Available in Checkpoint ---")
    available_tokenizers = list(model.tokenizer.tokenizers.keys())
    for t_name in available_tokenizers:
        tok = model.tokenizer.tokenizers[t_name]
        print(f"  - {t_name}: {type(tok).__name__}")
        if hasattr(tok, "g2p") and tok.g2p is not None:
            g2p = tok.g2p
            print(f"      G2P: {type(g2p).__name__} (locale={getattr(g2p, 'locale', None)})")

    print("\n--- Original NeMo LANGUAGE_TOKENIZER_MAP ---")
    print("Map keys:", list(tts_dataset_utils.LANGUAGE_TOKENIZER_MAP.keys()))
    print(f"Is 'pt' in map? {'pt' in tts_dataset_utils.LANGUAGE_TOKENIZER_MAP}")
    print(f"Is 'pt-BR' in map? {'pt-BR' in tts_dataset_utils.LANGUAGE_TOKENIZER_MAP}")

    # Set deterministic seed
    torch.manual_seed(42)
    torch.cuda.manual_seed(42)

    results = []

    # Matrix of configurations:
    # A1: apply_TN=False, unpatched (english_phoneme)
    # B1: apply_TN=True, unpatched (english_phoneme)
    # A2: apply_TN=False, patched with pt-BR phoneme
    # B2: apply_TN=True, patched with pt-BR phoneme
    
    configs = [
        ("A_TN_False_Default", False, False),
        ("B_TN_True_Default", True, False),
        ("C_TN_False_Patched_PTBR", False, True),
        ("D_TN_True_Patched_PTBR", True, True),
    ]

    for cfg_name, apply_tn, patch_map in configs:
        print("\n" + "=" * 60)
        print(f"RUNNING CONFIG: {cfg_name} (apply_TN={apply_tn}, patched_map={patch_map})")
        print("=" * 60)

        # Apply or remove patch to LANGUAGE_TOKENIZER_MAP
        if patch_map:
            tts_dataset_utils.LANGUAGE_TOKENIZER_MAP["pt"] = ["portuguese_Brazilian_phoneme"]
            tts_dataset_utils.LANGUAGE_TOKENIZER_MAP["pt-BR"] = ["portuguese_Brazilian_phoneme"]
        else:
            tts_dataset_utils.LANGUAGE_TOKENIZER_MAP.pop("pt", None)
            tts_dataset_utils.LANGUAGE_TOKENIZER_MAP.pop("pt-BR", None)

        for spk_name, spk_idx in SPEAKERS.items():
            for p_idx, phrase in enumerate([PHRASE_1, PHRASE_2], 1):
                # Reset seed for exact reproducibility
                torch.manual_seed(42)
                torch.cuda.manual_seed(42)

                t_start = time.time()
                try:
                    with torch.no_grad():
                        audio, audio_len = model.do_tts(
                            phrase,
                            language="pt",
                            apply_TN=apply_tn,
                            speaker_index=spk_idx
                        )
                    elapsed = time.time() - t_start
                    
                    audio_np = audio.detach().cpu().numpy().squeeze()
                    length_samples = int(audio_len.detach().cpu().reshape(-1)[0].item())
                    if 0 < length_samples <= audio_np.shape[-1]:
                        audio_np = audio_np[:length_samples]
                    
                    sr = 22050
                    duration_s = len(audio_np) / sr
                    
                    filename = f"{cfg_name}_{spk_name}_p{p_idx}.wav"
                    filepath = os.path.join(OUTPUT_DIR, filename)
                    sf.write(filepath, audio_np, sr, format="WAV", subtype="PCM_16")
                    
                    res_item = {
                        "config": cfg_name,
                        "speaker": spk_name,
                        "phrase": p_idx,
                        "apply_tn": apply_tn,
                        "patched": patch_map,
                        "time_s": elapsed,
                        "duration_s": duration_s,
                        "rms": float(np.sqrt(np.mean(audio_np**2))),
                        "file": filename
                    }
                    results.append(res_item)
                    print(f"[{spk_name.upper()} P{p_idx}] Time: {elapsed:.2f}s | Audio: {duration_s:.2f}s | RMS: {res_item['rms']:.4f} -> {filename}")
                except Exception as e:
                    print(f"[{spk_name.upper()} P{p_idx}] ERROR: {e}")
                    import traceback
                    traceback.print_exc()

    print("\n" + "=" * 70)
    print("SUMMARY TABLE OF GENERATIONS")
    print("=" * 70)
    print(f"{'Config':<25} {'Spk':<8} {'P':<3} {'TN':<6} {'Patched':<8} {'GenTime':<8} {'AudioDur':<9} {'File'}")
    print("-" * 95)
    for r in results:
        print(f"{r['config']:<25} {r['speaker']:<8} {r['phrase']:<3} {str(r['apply_tn']):<6} {str(r['patched']):<8} {r['time_s']:<8.2f} {r['duration_s']:<9.2f} {r['file']}")

if __name__ == "__main__":
    run_test()
