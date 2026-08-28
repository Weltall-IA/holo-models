from __future__ import annotations

import gc
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .base import BaseTTSEngine


class KokoroEngine(BaseTTSEngine):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_path = os.path.expanduser(
            os.path.expandvars(str(config.get("model_path", "")))
        )
        self.voices_path = os.path.expanduser(
            os.path.expandvars(str(config.get("voices_path", "")))
        )
        self.default_voice = str(config.get("default_voice", "af_heart"))
        self.sample_rate = int(config.get("sample_rate", 24000))
        self.provider = str(config.get("provider", "CPUExecutionProvider"))

        self.kokoro = None
        self._cached_voices: Optional[List[str]] = None

    @property
    def name(self) -> str:
        return "kokoro"

    def load(self) -> None:
        if self.kokoro is not None:
            return
        if not os.path.isfile(self.model_path):
            raise FileNotFoundError(f"Kokoro model not found: {self.model_path}")
        if not os.path.isfile(self.voices_path):
            raise FileNotFoundError(f"Kokoro voices file not found: {self.voices_path}")

        print(
            f"[KokoroEngine] Loading ONNX model with provider {self.provider}..."
        )
        started = time.time()

        import onnxruntime as rt
        from kokoro_onnx import Kokoro

        available_providers = rt.get_available_providers()
        provider = (
            self.provider
            if self.provider in available_providers
            else "CPUExecutionProvider"
        )
        session = rt.InferenceSession(self.model_path, providers=[provider])
        self.kokoro = Kokoro.from_session(
            session=session, voices_path=self.voices_path
        )
        self._cached_voices = list(self.kokoro.get_voices())
        if self.default_voice not in self._cached_voices:
            raise RuntimeError(
                f"Configured Kokoro default_voice {self.default_voice!r} "
                "is not present in the voices file"
            )
        print(
            f"[KokoroEngine] Loaded in {time.time() - started:.2f}s "
            f"with {len(self._cached_voices)} voices."
        )

    def unload(self) -> None:
        if self.kokoro is None:
            return
        print("[KokoroEngine] Unloading...")
        del self.kokoro
        self.kokoro = None
        self._cached_voices = None
        gc.collect()
        print("[KokoroEngine] Unloaded.")

    def is_loaded(self) -> bool:
        return self.kokoro is not None

    def _voice_names_without_loading_model(self) -> List[str]:
        if self._cached_voices is not None:
            return list(self._cached_voices)

        if self.voices_path and os.path.isfile(self.voices_path):
            try:
                voices_data = np.load(self.voices_path, allow_pickle=False)
                if hasattr(voices_data, "files"):
                    return list(voices_data.files)
            except Exception as exc:
                print(f"[KokoroEngine] Could not inspect voices file: {exc}")

        configured = self.config.get("known_voices", [])
        if configured:
            return [str(item) for item in configured]
        return [self.default_voice]

    def list_voices(self) -> List[Dict[str, Any]]:
        voices_list: List[Dict[str, Any]] = []
        for voice in self._voice_names_without_loading_model():
            lang = "en-us"
            if voice.startswith("b"):
                lang = "en-gb"
            elif voice.startswith("j"):
                lang = "ja"
            elif voice.startswith("z"):
                lang = "zh"
            elif voice.startswith("e"):
                lang = "es"
            elif voice.startswith("f"):
                lang = "fr"
            elif voice.startswith("h"):
                lang = "hi"
            elif voice.startswith("i"):
                lang = "it"
            elif voice.startswith("p"):
                lang = "pt-br"

            voices_list.append(
                {
                    "id": voice,
                    "voice_id": voice,
                    "name": voice,
                    "engine": "kokoro",
                    "language": lang,
                }
            )
        return voices_list

    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[np.ndarray, int]:
        if not self.is_loaded():
            self.load()

        options = options or {}
        voice_name = voice or self.default_voice
        speed = float(options.get("speed", 1.0))

        available = list(self.kokoro.get_voices())
        match = next(
            (item for item in available if item.lower() == voice_name.lower()),
            None,
        )
        if match is None:
            raise ValueError(f"Unknown Kokoro voice: {voice_name!r}")

        print(
            f"[KokoroEngine] Synthesizing voice={match}, speed={speed}"
        )
        samples, sample_rate = self.kokoro.create(
            text, voice=match, speed=speed
        )
        return np.asarray(samples, dtype=np.float32), int(sample_rate)
