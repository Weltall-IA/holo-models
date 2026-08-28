from __future__ import annotations

import io
import time
from pathlib import Path

import requests
import soundfile as sf


BASE_URL = "http://127.0.0.1:5050"
OUTPUT_DIR = Path(__file__).resolve().parent


def _health():
    response = requests.get(f"{BASE_URL}/health", timeout=10)
    response.raise_for_status()
    return response.json()


def _speech(payload, timeout=240):
    started = time.time()
    response = requests.post(
        f"{BASE_URL}/v1/audio/speech",
        json=payload,
        timeout=timeout,
    )
    elapsed = time.time() - started
    return response, elapsed


def _validate_soundfile(response, suffix):
    assert response.status_code == 200, response.text
    assert response.content
    audio, sample_rate = sf.read(io.BytesIO(response.content))
    assert sample_rate > 0
    assert len(audio) > 0
    assert len(audio) / sample_rate > 0
    output = OUTPUT_DIR / f"test_output.{suffix}"
    output.write_bytes(response.content)
    return sample_rate, len(audio) / sample_rate, output


def test_gateway():
    print("=== health/models/voices ===")
    health = _health()
    print(health)

    models = requests.get(f"{BASE_URL}/v1/models", timeout=10)
    models.raise_for_status()
    model_ids = [item["id"] for item in models.json()["data"]]
    print("models:", model_ids)

    voices_response = requests.get(
        f"{BASE_URL}/v1/audio/voices", timeout=10
    )
    voices_response.raise_for_status()
    voices = voices_response.json()["voices"]
    voice_ids = [item["voice_id"] for item in voices]
    assert "magpie:Sofia-pt" in voice_ids
    assert "kokoro:af_heart" in voice_ids
    print("voice count:", len(voices))

    print("=== invalid model/voice must fail explicitly ===")
    bad_model, _ = _speech(
        {"model": "invalid-engine", "voice": "whatever", "input": "teste"},
        timeout=30,
    )
    assert bad_model.status_code == 400

    bad_voice, _ = _speech(
        {"model": "kokoro", "voice": "invalid-voice", "input": "test"},
        timeout=30,
    )
    assert bad_voice.status_code == 400

    print("=== Magpie via namespaced voice ===")
    response, elapsed = _speech(
        {
            "voice": "magpie:Sofia-pt",
            "input": "Olá. Este é um teste do Magpie através do gateway.",
            "response_format": "wav",
        }
    )
    sample_rate, duration, output = _validate_soundfile(response, "wav")
    print(
        f"Magpie: {elapsed:.2f}s, {sample_rate}Hz, "
        f"{duration:.2f}s -> {output}"
    )
    health = _health()
    assert health["loaded_engines"]["magpie"] is True

    print("=== switch to Kokoro ===")
    response, elapsed = _speech(
        {
            "voice": "kokoro:af_heart",
            "input": "Hello. Kokoro is speaking through the same gateway.",
            "response_format": "flac",
        }
    )
    sample_rate, duration, output = _validate_soundfile(response, "flac")
    print(
        f"Kokoro: {elapsed:.2f}s, {sample_rate}Hz, "
        f"{duration:.2f}s -> {output}"
    )
    health = _health()
    if health["load_policy"] == "keep-current":
        assert health["loaded_engines"]["magpie"] is False
        assert health["loaded_engines"]["kokoro"] is True

    print("=== switch back to Magpie ===")
    response, elapsed = _speech(
        {
            "model": "magpie",
            "voice": "Aria-pt",
            "input": "Voltando para o Magpie sem trocar o endpoint.",
            "response_format": "wav",
        }
    )
    _validate_soundfile(response, "wav")
    health = _health()
    if health["load_policy"] == "keep-current":
        assert health["loaded_engines"]["magpie"] is True
        assert health["loaded_engines"]["kokoro"] is False

    print(">>> integration tests passed <<<")


if __name__ == "__main__":
    test_gateway()
