from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest

from app import (
    EngineManager,
    UnknownEngineError,
    UnknownVoiceError,
    _split_text,
)
from config import GatewayConfig
from engines.base import BaseTTSEngine


class FakeEngine(BaseTTSEngine):
    def __init__(self, name: str, voices: list[str], delay: float = 0.0):
        self._name = name
        self.voices = voices
        self.loaded = False
        self.load_calls = 0
        self.unload_calls = 0
        self.delay = delay
        self.active = 0
        self.max_active = 0
        self.state_lock = threading.Lock()

    @property
    def name(self) -> str:
        return self._name

    def load(self) -> None:
        self.loaded = True
        self.load_calls += 1

    def unload(self) -> None:
        self.loaded = False
        self.unload_calls += 1

    def is_loaded(self) -> bool:
        return self.loaded

    def list_voices(self):
        return [
            {
                "id": voice,
                "voice_id": voice,
                "name": voice,
                "engine": self._name,
            }
            for voice in self.voices
        ]

    def synthesize(self, text, voice=None, options=None):
        with self.state_lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            if self.delay:
                time.sleep(self.delay)
            return np.ones(200, dtype=np.float32) * 0.1, 24000
        finally:
            with self.state_lock:
                self.active -= 1


def make_manager(policy="keep-current"):
    cfg = GatewayConfig(
        default_engine="magpie",
        load_policy=policy,
        engines={},
        chunking_enabled=False,
    )
    magpie = FakeEngine("magpie", ["Sofia-pt", "Leo-pt"])
    kokoro = FakeEngine("kokoro", ["af_heart", "am_onyx"])
    return EngineManager(cfg, {"magpie": magpie, "kokoro": kokoro}), magpie, kokoro


def synth(manager, model, voice):
    return manager.synthesize(
        model=model,
        voice=voice,
        text="hello",
        speed=1.0,
        language=None,
    )


def test_voice_namespace_and_prefix_precedence():
    manager, _, _ = make_manager()
    voices = manager.list_all_voices()
    ids = {voice["voice_id"] for voice in voices}
    assert "magpie:Sofia-pt" in ids
    assert "kokoro:af_heart" in ids

    engine, voice = manager.resolve_request("magpie", "kokoro:af_heart")
    assert engine == "kokoro"
    assert voice == "af_heart"


def test_invalid_engine_and_voice_do_not_fallback():
    manager, _, _ = make_manager()
    with pytest.raises(UnknownEngineError):
        synth(manager, "does-not-exist", None)
    with pytest.raises(UnknownVoiceError):
        synth(manager, "magpie", "does-not-exist")


def test_keep_current_unloads_previous_engine():
    manager, magpie, kokoro = make_manager("keep-current")

    synth(manager, "magpie", "Sofia-pt")
    assert magpie.loaded is True
    assert kokoro.loaded is False

    synth(manager, "kokoro", "af_heart")
    assert magpie.loaded is False
    assert kokoro.loaded is True
    assert magpie.unload_calls == 1


def test_lazy_keeps_already_loaded_engines():
    manager, magpie, kokoro = make_manager("lazy")
    synth(manager, "magpie", "Sofia-pt")
    synth(manager, "kokoro", "af_heart")
    assert magpie.loaded is True
    assert kokoro.loaded is True


def test_unload_after_releases_engine():
    manager, magpie, _ = make_manager("unload-after")
    synth(manager, "magpie", "Sofia-pt")
    assert magpie.loaded is False
    assert manager.active_engine is None
    assert manager.current_engine_name is None


def test_synthesis_lock_serializes_requests():
    manager, magpie, _ = make_manager("keep-current")
    magpie.delay = 0.05
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(synth, manager, "magpie", "Sofia-pt")
            for _ in range(2)
        ]
        for future in futures:
            future.result(timeout=2)
    assert magpie.max_active == 1


def test_chunker_respects_limit_and_words():
    text = (
        "Primeira frase curta. Segunda frase também. "
        "Terceira frase é um pouco maior e continua aqui. "
    ) * 10
    chunks = _split_text(text, 100)
    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert "".join(chunks).replace(" ", "") == text.strip().replace(" ", "")
