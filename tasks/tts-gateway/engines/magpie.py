import os
import gc
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import torch

from .base import BaseTTSEngine

class MagpieEngine(BaseTTSEngine):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_path = config.get(
            "model_path",
            "/home/alpha/Playstoria/models/audio/voz/nvidia-magpie_tts_multilingual_357m/magpie_tts_multilingual_357m.nemo"
        )
        self.default_speaker = config.get("default_speaker", "Sofia")
        self.default_language = config.get("default_language", "pt")
        self.sample_rate = config.get("sample_rate", 22050)
        self.configured_device = config.get("device", "auto")

        self.model = None
        self.active_device = None

        # Discovered speakers in baked context embedding (5 speakers: Aria, Jason, John, Leo, Sofia)
        self.speaker_map = {
            "aria": 0,
            "jason": 1,
            "john": 2,
            "leo": 3,
            "sofia": 4,
            "speaker_0": 0,
            "speaker_1": 1,
            "speaker_2": 2,
            "speaker_3": 3,
            "speaker_4": 4,
            "magpie-speaker-0": 0,
            "magpie-speaker-1": 1,
            "magpie-speaker-2": 2,
            "magpie-speaker-3": 3,
            "magpie-speaker-4": 4,
        }

    @property
    def name(self) -> str:
        return "magpie"

    def _resolve_device(self) -> str:
        if self.configured_device == "cpu":
            return "cpu"
        if self.configured_device == "cuda":
            return "cuda"
        # Auto: check if CUDA is available and has at least 1.5 GB free VRAM
        if torch.cuda.is_available():
            try:
                free_bytes, _ = torch.cuda.mem_get_info()
                if free_bytes > 1.5 * (1024**3):
                    return "cuda"
            except Exception:
                pass
        return "cpu"

    def load(self) -> None:
        if self.model is not None:
            return

        device = self._resolve_device()
        print(f"[MagpieEngine] Loading MagpieTTSModel on device: {device}...")
        t0 = time.time()

        from nemo.collections.tts.models import MagpieTTSModel

        self.model = MagpieTTSModel.restore_from(self.model_path, map_location=device)
        self.model.eval()
        self.active_device = device
        print(f"[MagpieEngine] Loaded in {time.time() - t0:.2f}s on {device}")

    def unload(self) -> None:
        if self.model is not None:
            print("[MagpieEngine] Unloading model from memory/GPU...")
            del self.model
            self.model = None
            self.active_device = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("[MagpieEngine] Unloaded successfully.")

    def is_loaded(self) -> bool:
        return self.model is not None

    def list_voices(self) -> List[Dict[str, Any]]:
        voices = []
        named_speakers = ["Aria", "Jason", "John", "Leo", "Sofia"]
        for idx, spk in enumerate(named_speakers):
            for lang in ["pt", "en"]:
                voices.append({
                    "id": f"{spk}-{lang}",
                    "voice_id": f"{spk}-{lang}",
                    "name": f"{spk} ({lang.upper()})",
                    "engine": "magpie",
                    "language": lang,
                    "gender": "female" if spk in ["Aria", "Sofia"] else "male",
                    "speaker_index": idx,
                    "aliases": [f"magpie-speaker-{idx}", f"speaker_{idx}", spk.lower(), f"{spk.lower()}-{lang}"]
                })
        return voices

    def _detect_language(self, text: str) -> str:
        pt_markers = {"que", "não", "para", "com", "uma", "estou", "está", "você", "olá", "fala", "português", "muito", "mais", "como", "mas", "por", "isso", "esse", "esta", "tarde", "noite", "bom", "dia"}
        words = set(text.lower().replace(",", "").replace(".", "").replace("!", "").replace("?", "").split())
        if len(words.intersection(pt_markers)) > 0 or any(c in text for c in "ãõáéíóúâêîôûàçÃÕÁÉÍÓÚÂÊÎÔÛÀÇ"):
            return "pt"
        return "en"

    def synthesize(self, text: str, voice: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, int]:
        if not self.is_loaded():
            self.load()

        options = options or {}
        voice_str = (voice or self.default_speaker).lower().strip()
        speaker_idx = self.speaker_map.get(voice_str, self.speaker_map.get(self.default_speaker.lower(), 4))

        # Check language from options or voice name or auto-detect
        req_lang = options.get("language")
        if not req_lang and "-" in voice_str:
            parts = voice_str.split("-")
            if len(parts) > 1 and parts[1] in ["ar", "de", "en", "es", "fr", "hi", "it", "ja", "ko", "pt", "vi", "zh"]:
                req_lang = parts[1]
                if parts[0] in self.speaker_map:
                    speaker_idx = self.speaker_map[parts[0]]

        lang = req_lang if req_lang else self._detect_language(text)

        print(f"[MagpieEngine] Synthesizing: voice={voice_str} (idx={speaker_idx}), lang={lang}, text='{text[:60]}...'")

        with torch.no_grad():
            audio, audio_len = self.model.do_tts(
                text,
                language=lang,
                apply_TN=False,
                speaker_index=speaker_idx
            )

        if isinstance(audio, torch.Tensor):
            audio_np = audio.detach().cpu().numpy().squeeze()
        else:
            audio_np = np.asarray(audio).squeeze()

        return audio_np.astype(np.float32), self.sample_rate
