# Local TTS Gateway

Single local API for multiple TTS engines. Clients keep one base URL and select
the engine through `model` or a namespaced voice such as
`magpie:Sofia-pt` / `kokoro:af_heart`.

## API

Default base URL:

```text
http://127.0.0.1:5050/v1
```

Main endpoints:

```text
GET  /health
GET  /ready
GET  /v1/models
GET  /v1/audio/voices
GET  /v1/engines
POST /v1/audio/speech
POST /v1/engines/{engine}/load
POST /v1/engines/{engine}/unload
```

OpenAI-style request:

```json
{
  "model": "magpie",
  "voice": "Sofia-pt",
  "input": "Olá.",
  "response_format": "wav",
  "speed": 1.0
}
```

Equivalent request using a globally unique voice:

```json
{
  "voice": "kokoro:af_heart",
  "input": "Hello.",
  "response_format": "wav"
}
```

A namespaced voice takes precedence over `model`.

## Load policies

- `lazy`: load engines on first use and leave them loaded.
- `keep-current`: keep only the currently selected engine loaded; switching
  engines unloads the previous one before loading the next.
- `unload-after`: unload the selected engine after every request.

The manager serializes switching + inference so another request cannot unload
an engine while it is synthesizing. Heavy synchronous inference runs in
FastAPI's thread pool instead of blocking the event loop.

## Voices

`GET /v1/audio/voices` exposes globally unique IDs:

```text
magpie:Sofia-pt
magpie:Leo-pt
kokoro:af_heart
kokoro:am_onyx
```

Invalid engine and voice IDs return errors instead of silently falling back.

## Output formats

Configured formats are `wav`, `flac`, `mp3`, and `pcm`. WAV/FLAC/PCM are
handled directly. MP3 requires MP3 support in the system `libsndfile`; if it
is unavailable the gateway returns an explicit error rather than returning a
different format.

Magpie currently supports `speed=1.0` in this adapter. Kokoro supports variable
speed. The gateway does not silently pretend Magpie supports time stretching.

## Long text

Long text is split on paragraph/sentence/word boundaries using
`chunk_chars`, synthesized sequentially, and joined with the configured
`chunk_pause_ms` silence.

## Configuration

Copy `config.example.yaml` for another machine. Paths support `${HOME}` and
environment-variable expansion. `TTS_GATEWAY_CONFIG` can point to a different
config file.

## SillyTavern

Use the single gateway base URL and map characters to namespaced voices:

```text
Weltall      -> magpie:Leo-pt
Narrador     -> magpie:Sofia-pt
Personagem A -> kokoro:af_heart
Personagem B -> kokoro:am_onyx
```

Changing the voice changes the engine without changing the endpoint.

## Tests

Fast unit tests for manager behavior:

```bash
pytest -q tasks/tts-gateway/tests/test_manager.py
```

Real integration test (gateway must already be running):

```bash
python tasks/tts-gateway/tests/test_gateway.py
```

The integration test verifies actual engine switching through `/health`; it
does not claim VRAM was released solely because synthesis succeeded.

## Future heavy engines

The public API should remain on `:5050`. F5-TTS, XTTS, or other engines with
conflicting Python/CUDA dependencies should preferably run as isolated local
workers/processes behind the gateway. That keeps client configuration stable
while allowing each heavy engine to have its own virtual environment and
process lifetime.
