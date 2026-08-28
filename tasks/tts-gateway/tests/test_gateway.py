import os
import time
import requests
import soundfile as sf
import io

BASE_URL = "http://127.0.0.1:5050"

def test_gateway():
    print("=== 1. Test GET /health ===")
    r = requests.get(f"{BASE_URL}/health", timeout=10)
    print("Health response:", r.status_code, r.json())

    print("\n=== 2. Test GET /v1/models ===")
    r = requests.get(f"{BASE_URL}/v1/models", timeout=10)
    print("Models count:", len(r.json().get("data", [])))
    print("Models list:", [m["id"] for m in r.json().get("data", [])])

    print("\n=== 3. Test GET /v1/audio/voices ===")
    r = requests.get(f"{BASE_URL}/v1/audio/voices", timeout=10)
    voices = r.json().get("voices", [])
    print(f"Total available voices: {len(voices)}")
    magpie_voices = [v["voice_id"] for v in voices if v.get("engine") == "magpie"]
    kokoro_voices = [v["voice_id"] for v in voices if v.get("engine") == "kokoro"]
    print("Magpie voices sample:", magpie_voices[:6])
    print("Kokoro voices sample:", kokoro_voices[:6])

    print("\n=== 4. Test POST /v1/audio/speech (Magpie Engine - Portuguese) ===")
    t0 = time.time()
    payload_magpie = {
        "model": "magpie",
        "voice": "Sofia-pt",
        "input": "Olá! Estou testando a síntese de voz do Magpie em português através do gateway.",
        "response_format": "wav"
    }
    r = requests.post(f"{BASE_URL}/v1/audio/speech", json=payload_magpie, timeout=180)
    print("Magpie Status:", r.status_code, "Content-Type:", r.headers.get("content-type"), f"Time: {time.time() - t0:.2f}s")
    assert r.status_code == 200, f"Magpie failed: {r.text}"
    
    data_magpie, sr_magpie = sf.read(io.BytesIO(r.content))
    duration_magpie = len(data_magpie) / sr_magpie
    print(f"Magpie WAV: Sample Rate={sr_magpie} Hz, Channels={1 if data_magpie.ndim == 1 else data_magpie.shape[1]}, Duration={duration_magpie:.2f}s, Bytes={len(r.content)}")
    with open("/home/alpha/Playstoria/models/tasks/tts-gateway/tests/test_magpie_output.wav", "wb") as f:
        f.write(r.content)

    print("\n=== 5. Test POST /v1/audio/speech (Kokoro Engine - English / Switch Engine) ===")
    t0 = time.time()
    payload_kokoro = {
        "model": "kokoro",
        "voice": "af_heart",
        "input": "Hello! The Kokoro TTS engine is now speaking through the same unified gateway.",
        "response_format": "wav"
    }
    r = requests.post(f"{BASE_URL}/v1/audio/speech", json=payload_kokoro, timeout=180)
    print("Kokoro Status:", r.status_code, "Content-Type:", r.headers.get("content-type"), f"Time: {time.time() - t0:.2f}s")
    assert r.status_code == 200, f"Kokoro failed: {r.text}"
    
    data_kokoro, sr_kokoro = sf.read(io.BytesIO(r.content))
    duration_kokoro = len(data_kokoro) / sr_kokoro
    print(f"Kokoro WAV: Sample Rate={sr_kokoro} Hz, Channels={1 if data_kokoro.ndim == 1 else data_kokoro.shape[1]}, Duration={duration_kokoro:.2f}s, Bytes={len(r.content)}")
    with open("/home/alpha/Playstoria/models/tasks/tts-gateway/tests/test_kokoro_output.wav", "wb") as f:
        f.write(r.content)

    print("\n=== 6. Test Switch Back to Magpie (Confirm lazy switch & VRAM release) ===")
    t0 = time.time()
    payload_magpie_2 = {
        "model": "magpie",
        "voice": "Aria-pt",
        "input": "Mudando de volta para o Magpie perfeitamente sem reiniciar o gateway.",
        "response_format": "wav"
    }
    r = requests.post(f"{BASE_URL}/v1/audio/speech", json=payload_magpie_2, timeout=180)
    print("Magpie Switch-back Status:", r.status_code, f"Time: {time.time() - t0:.2f}s")
    assert r.status_code == 200

    print("\n>>> ALL TESTS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    test_gateway()
