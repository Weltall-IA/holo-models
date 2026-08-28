from __future__ import annotations

import gc
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .base import BaseTTSEngine


class MagpieEngine(BaseTTSEngine):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_path = os.path.expanduser(
            os.path.expandvars(str(config.get("model_path", "")))
        )
        self.default_speaker = str(config.get("default_speaker", "Sofia"))
        self.default_language = str(config.get("default_language", "pt"))
        self.sample_rate = int(config.get("sample_rate", 22050))
        self.configured_device = str(config.get("device", "auto")).lower()

        self.model = None
        self.active_device: Optional[str] = None

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

    def _torch(self):
        import torch

        return torch

    def _resolve_device(self) -> str:
        torch = self._torch()
        if self.configured_device == "cpu":
            return "cpu"
        if self.configured_device == "cuda":
            if not torch.cuda.is_available():
                raise RuntimeError("Magpie is configured for CUDA but CUDA is unavailable")
            return "cuda"
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
        if not self.model_path:
            raise RuntimeError("Magpie model_path is not configured")
        if not os.path.isfile(self.model_path):
            raise FileNotFoundError(f"Magpie model not found: {self.model_path}")

        device = self._resolve_device()
        print(f"[MagpieEngine] Loading MagpieTTSModel on {device}...")
        started = time.time()

        from nemo.collections.tts.models import MagpieTTSModel

        self.model = MagpieTTSModel.restore_from(
            self.model_path, map_location=device
        )
        self.model.eval()
        self.active_device = device
        print(
            f"[MagpieEngine] Loaded in {time.time() - started:.2f}s on {device}"
        )

    def unload(self) -> None:
        if self.model is None:
            return
        print("[MagpieEngine] Unloading model...")
        del self.model
        self.model = None
        self.active_device = None
        gc.collect()

        try:
            torch = self._torch()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
        except Exception:
            pass
        print("[MagpieEngine] Unloaded.")

    def is_loaded(self) -> bool:
        return self.model is not None

    def list_voices(self) -> List[Dict[str, Any]]:
        voices: List[Dict[str, Any]] = []
        named_speakers = ["Aria", "Jason", "John", "Leo", "Sofia"]
        for idx, speaker in enumerate(named_speakers):
            for lang in ["pt", "en"]:
                voice_id = f"{speaker}-{lang}"
                voices.append(
                    {
                        "id": voice_id,
                        "voice_id": voice_id,
                        "name": f"{speaker} ({lang.upper()})",
                        "engine": "magpie",
                        "language": lang,
                        "gender": "female"
                        if speaker in {"Aria", "Sofia"}
                        else "male",
                        "speaker_index": idx,
                        "aliases": [
                            f"magpie-speaker-{idx}",
                            f"speaker_{idx}",
                            speaker.lower(),
                            f"{speaker.lower()}-{lang}",
                        ],
                    }
                )
        return voices

    def _detect_language(self, text: str) -> str:
        pt_markers = {
            "que",
            "não",
            "para",
            "com",
            "uma",
            "estou",
            "está",
            "você",
            "olá",
            "português",
            "muito",
            "mais",
            "como",
            "mas",
            "por",
            "isso",
            "tarde",
            "noite",
            "bom",
            "dia",
        }
        words = set(re.findall(r"[\wÀ-ÿ]+", text.lower()))
        if words.intersection(pt_markers):
            return "pt"
        if any(char in text for char in "ãõáéíóúâêîôûàçÃÕÁÉÍÓÚÂÊÎÔÛÀÇ"):
            return "pt"
        return "en"

    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[np.ndarray, int]:
        if not self.is_loaded():
            self.load()

        options = options or {}
        speed = float(options.get("speed", 1.0))
        if abs(speed - 1.0) > 1e-6:
            raise ValueError(
                "Magpie adapter does not support speed != 1.0 without "
                "time-stretch post-processing"
            )

        voice_str = (voice or self.default_speaker).lower().strip()
        req_lang = options.get("language")
        base_voice = voice_str

        if "-" in voice_str:
            maybe_voice, maybe_lang = voice_str.rsplit("-", 1)
            if maybe_lang in {
                "ar",
                "de",
                "en",
                "es",
                "fr",
                "hi",
                "it",
                "ja",
                "ko",
                "pt",
                "vi",
                "zh",
            }:
                base_voice = maybe_voice
                req_lang = req_lang or maybe_lang

        if base_voice not in self.speaker_map:
            raise ValueError(f"Unknown Magpie voice: {voice!r}")

        speaker_idx = self.speaker_map[base_voice]
        language = str(req_lang or self._detect_language(text))

        print(
            f"[MagpieEngine] Synthesizing voice={voice_str}, "
            f"speaker={speaker_idx}, language={language}"
        )

        torch = self._torch()
        with torch.no_grad():
            audio, audio_len = self.model.do_tts(
                text,
                language=language,
                apply_TN=False,
                speaker_index=speaker_idx,
            )

        if isinstance(audio, torch.Tensor):
            audio_np = audio.detach().cpu().numpy().squeeze()
        else:
            audio_np = np.asarray(audio).squeeze()

        try:
            length = int(audio_len.detach().cpu().reshape(-1)[0].item())
            if 0 < length <= audio_np.shape[-1]:
                audio_np = audio_np[:length]
        except Exception:
            pass

        return np.asarray(audio_np, dtype=np.float32), self.sample_rate
