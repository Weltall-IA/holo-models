import os
import gc
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import onnxruntime as rt
import torch

from .base import BaseTTSEngine

class KokoroEngine(BaseTTSEngine):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_path = config.get(
            "model_path",
            "/home/alpha/Playstoria/models/audio/voz/hexgrad-Kokoro-82M-ONNX/kokoro-v1.0.onnx"
        )
        self.voices_path = config.get(
            "voices_path",
            "/home/alpha/Playstoria/models/audio/voz/hexgrad-Kokoro-82M-ONNX/voices-v1.0.bin"
        )
        self.default_voice = config.get("default_voice", "af_heart")
        self.sample_rate = config.get("sample_rate", 24000)

        self.kokoro = None
        self._cached_voices = None

    @property
    def name(self) -> str:
        return "kokoro"

    def load(self) -> None:
        if self.kokoro is not None:
            return

        print(f"[KokoroEngine] Loading Kokoro ONNX model from: {self.model_path}...")
        t0 = time.time()
        from kokoro_onnx import Kokoro

        # Use CPUExecutionProvider for instant lightweight CPU execution (82M model)
        session = rt.InferenceSession(self.model_path, providers=["CPUExecutionProvider"])
        self.kokoro = Kokoro.from_session(session=session, voices_path=self.voices_path)
        self._cached_voices = self.kokoro.get_voices()
        print(f"[KokoroEngine] Loaded in {time.time() - t0:.2f}s with {len(self._cached_voices)} voices.")

    def unload(self) -> None:
        if self.kokoro is not None:
            print("[KokoroEngine] Unloading Kokoro from memory...")
            del self.kokoro
            self.kokoro = None
            self._cached_voices = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("[KokoroEngine] Unloaded successfully.")

    def is_loaded(self) -> bool:
        return self.kokoro is not None

    def list_voices(self) -> List[Dict[str, Any]]:
        # If not loaded, peek cached or load voices metadata
        voice_names = self._cached_voices
        if voice_names is None:
            if os.path.exists(self.voices_path):
                try:
                    voices_data = np.load(self.voices_path)
                    voice_names = list(voices_data.files)
                except Exception:
                    voice_names = [
                        "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica", "af_kore",
                        "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky", "am_adam",
                        "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael", "am_onyx",
                        "am_puck", "am_santa", "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
                        "bm_daniel", "bm_fable", "bm_george", "bm_lewis"
                    ]
            else:
                voice_names = ["af_heart"]

        voices_list = []
        for v in voice_names:
            # Parse language code from prefix (e.g. af_ -> en-us female, am_ -> en-us male, bf_ -> en-gb female)
            lang = "en-us"
            if v.startswith("b"):
                lang = "en-gb"
            elif v.startswith("j"):
                lang = "ja"
            elif v.startswith("z"):
                lang = "zh"
            elif v.startswith("e"):
                lang = "es"
            elif v.startswith("f"):
                lang = "fr"
            elif v.startswith("h"):
                lang = "hi"
            elif v.startswith("i"):
                lang = "it"
            elif v.startswith("p"):
                lang = "pt-br"

            voices_list.append({
                "id": v,
                "voice_id": v,
                "name": v,
                "engine": "kokoro",
                "language": lang
            })
        return voices_list

    def synthesize(self, text: str, voice: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, int]:
        if not self.is_loaded():
            self.load()

        options = options or {}
        v_name = voice or self.default_voice
        speed = float(options.get("speed", 1.0))

        # Check if voice exists in kokoro, otherwise fallback to default
        available = self.kokoro.get_voices()
        if v_name not in available:
            # Check lowercase / matching
            matched = next((av for av in available if av.lower() == v_name.lower()), self.default_voice)
            v_name = matched

        print(f"[KokoroEngine] Synthesizing: voice={v_name}, speed={speed}, text='{text[:60]}...'")
        samples, sr = self.kokoro.create(text, voice=v_name, speed=speed)
        return np.asarray(samples, dtype=np.float32), sr
