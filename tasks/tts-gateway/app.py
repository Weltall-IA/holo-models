from __future__ import annotations

import io
import re
import socket
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import soundfile as sf
import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import GatewayConfig
from engines.base import BaseTTSEngine
from engines.kokoro import KokoroEngine
from engines.magpie import MagpieEngine


app = FastAPI(
    title="Local TTS Gateway",
    description="Unified OpenAI-compatible TTS gateway for local speech engines.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GatewayError(RuntimeError):
    """Base error for expected gateway/client failures."""


class UnknownEngineError(GatewayError):
    pass


class UnknownVoiceError(GatewayError):
    pass


class UnsupportedFormatError(GatewayError):
    pass


def _split_text(text: str, max_chars: int) -> List[str]:
    """Split text on paragraph/sentence/word boundaries without cutting words."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: List[str] = []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]

    def append_piece(piece: str) -> None:
        piece = piece.strip()
        if not piece:
            return
        if len(piece) <= max_chars:
            if chunks and len(chunks[-1]) + 1 + len(piece) <= max_chars:
                chunks[-1] = f"{chunks[-1]} {piece}"
            else:
                chunks.append(piece)
            return

        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?…])\s+", piece)
            if s.strip()
        ]
        if len(sentences) == 1 and len(sentences[0]) > max_chars:
            words = sentences[0].split()
            current: List[str] = []
            current_len = 0
            for word in words:
                extra = len(word) + (1 if current else 0)
                if current and current_len + extra > max_chars:
                    chunks.append(" ".join(current))
                    current = [word]
                    current_len = len(word)
                else:
                    current.append(word)
                    current_len += extra
            if current:
                chunks.append(" ".join(current))
            return

        for sentence in sentences:
            append_piece(sentence)

    for paragraph in paragraphs or [text]:
        append_piece(paragraph)

    return chunks


def _ensure_float32_mono(audio: np.ndarray) -> np.ndarray:
    arr = np.asarray(audio, dtype=np.float32).squeeze()
    if arr.ndim == 0:
        arr = arr.reshape(1)
    if arr.ndim > 1:
        arr = np.mean(arr, axis=-1, dtype=np.float32)
    if not np.all(np.isfinite(arr)):
        raise GatewayError("TTS engine returned non-finite audio samples")
    return np.ascontiguousarray(arr, dtype=np.float32)


def _concat_audio(
    pieces: List[np.ndarray], sample_rate: int, pause_ms: int
) -> np.ndarray:
    if not pieces:
        raise GatewayError("TTS engine returned no audio")
    if len(pieces) == 1:
        return pieces[0]

    pause_samples = max(0, int(sample_rate * pause_ms / 1000))
    silence = np.zeros(pause_samples, dtype=np.float32)
    output: List[np.ndarray] = []
    for idx, piece in enumerate(pieces):
        if idx and pause_samples:
            output.append(silence)
        output.append(piece)
    return np.concatenate(output)


def _encode_audio(audio: np.ndarray, sample_rate: int, fmt: str) -> Tuple[bytes, str]:
    fmt = fmt.lower()

    if fmt == "pcm":
        clipped = np.clip(audio, -1.0, 1.0)
        pcm16 = (clipped * 32767.0).astype("<i2", copy=False)
        return pcm16.tobytes(), "audio/pcm"

    sf_formats = {
        "wav": ("WAV", "audio/wav"),
        "flac": ("FLAC", "audio/flac"),
        "mp3": ("MP3", "audio/mpeg"),
        "ogg": ("OGG", "audio/ogg"),
    }
    if fmt not in sf_formats:
        raise UnsupportedFormatError(f"Unsupported response_format: {fmt}")

    sf_format, media_type = sf_formats[fmt]
    available = {name.upper() for name in sf.available_formats()}
    if sf_format not in available:
        raise UnsupportedFormatError(
            f"response_format '{fmt}' is not supported by the installed libsndfile"
        )

    out = io.BytesIO()
    kwargs: Dict[str, Any] = {"format": sf_format}
    if sf_format == "WAV":
        kwargs["subtype"] = "PCM_16"
    sf.write(out, audio, sample_rate, **kwargs)
    return out.getvalue(), media_type


class EngineManager:
    def __init__(
        self,
        cfg: GatewayConfig,
        registry: Optional[Dict[str, BaseTTSEngine]] = None,
    ):
        self.cfg = cfg
        self.lock = threading.RLock()
        self.current_engine_name: Optional[str] = None
        self.active_engine: Optional[BaseTTSEngine] = None
        self.registry: Dict[str, BaseTTSEngine] = registry or {
            "magpie": MagpieEngine(cfg.engines.get("magpie", {})),
            "kokoro": KokoroEngine(cfg.engines.get("kokoro", {})),
        }

    def list_available_models(self) -> List[Dict[str, Any]]:
        now = int(time.time())
        models: List[Dict[str, Any]] = []
        for name in self.registry:
            models.append(
                {
                    "id": name,
                    "object": "model",
                    "created": now,
                    "owned_by": "local-tts-gateway",
                    "root": name,
                    "parent": None,
                }
            )
        for alias in self.cfg.model_aliases:
            if alias not in self.registry:
                models.append(
                    {
                        "id": alias,
                        "object": "model",
                        "created": now,
                        "owned_by": "local-tts-gateway",
                        "root": self.cfg.default_engine,
                        "parent": None,
                    }
                )
        return models

    def list_all_voices(self) -> List[Dict[str, Any]]:
        voices: List[Dict[str, Any]] = []
        for engine_name, engine in self.registry.items():
            try:
                for raw in engine.list_voices():
                    item = dict(raw)
                    raw_id = str(item.get("voice_id") or item.get("id") or "").strip()
                    if not raw_id:
                        continue
                    local_id = (
                        raw_id.split(":", 1)[1]
                        if raw_id.startswith(f"{engine_name}:")
                        else raw_id
                    )
                    global_id = f"{engine_name}:{local_id}"
                    item["id"] = global_id
                    item["voice_id"] = global_id
                    item["engine"] = engine_name
                    item["local_voice_id"] = local_id
                    raw_name = str(item.get("name") or local_id)
                    prefix = engine_name.capitalize()
                    if not raw_name.lower().startswith(prefix.lower()):
                        item["name"] = f"{prefix} — {raw_name}"
                    voices.append(item)
            except Exception as exc:
                print(f"[EngineManager] Could not list voices for {engine_name}: {exc}")
        return voices

    def resolve_engine_name(self, requested: Optional[str]) -> str:
        name = (requested or self.cfg.default_engine).strip().lower()
        if name in self.cfg.model_aliases:
            name = self.cfg.default_engine
        if name not in self.registry:
            raise UnknownEngineError(f"Unknown TTS model/engine: {requested!r}")
        return name

    def resolve_request(
        self, model: Optional[str], voice: Optional[str]
    ) -> Tuple[str, Optional[str]]:
        requested_model = model or self.cfg.default_engine
        local_voice = voice.strip() if voice else None

        if local_voice and ":" in local_voice:
            prefix, suffix = local_voice.split(":", 1)
            prefix = prefix.strip().lower()
            if prefix not in self.registry:
                raise UnknownEngineError(
                    f"Unknown engine prefix in voice {voice!r}: {prefix!r}"
                )
            requested_model = prefix
            local_voice = suffix.strip()

        engine_name = self.resolve_engine_name(requested_model)
        return engine_name, local_voice

    def _validate_voice(
        self, engine_name: str, engine: BaseTTSEngine, voice: Optional[str]
    ) -> Optional[str]:
        if not voice:
            return None
        wanted = voice.strip().lower()
        for item in engine.list_voices():
            candidates = {
                str(item.get("id", "")).lower(),
                str(item.get("voice_id", "")).lower(),
                str(item.get("name", "")).lower(),
            }
            candidates.update(str(alias).lower() for alias in item.get("aliases", []))
            candidates = {c.split(":", 1)[-1] for c in candidates if c}
            if wanted in candidates:
                return str(item.get("voice_id") or item.get("id") or voice).split(":", 1)[-1]
        raise UnknownVoiceError(
            f"Unknown voice {voice!r} for engine {engine_name!r}"
        )

    def _switch_if_needed(self, engine_name: str) -> BaseTTSEngine:
        target = self.registry[engine_name]
        policy = self.cfg.load_policy

        if (
            policy == "keep-current"
            and self.current_engine_name
            and self.current_engine_name != engine_name
        ):
            previous = self.registry[self.current_engine_name]
            if previous.is_loaded():
                print(
                    f"[EngineManager] Switching {self.current_engine_name} -> "
                    f"{engine_name}; unloading previous engine"
                )
                previous.unload()

        if not target.is_loaded():
            print(f"[EngineManager] Loading engine on demand: {engine_name}")
            target.load()

        self.current_engine_name = engine_name
        self.active_engine = target
        return target

    def _synthesize_chunks(
        self,
        engine: BaseTTSEngine,
        text: str,
        voice: Optional[str],
        options: Dict[str, Any],
    ) -> Tuple[np.ndarray, int]:
        chunks = (
            _split_text(text, self.cfg.chunk_chars)
            if self.cfg.chunking_enabled
            else [text]
        )
        if not chunks:
            raise GatewayError("Input text cannot be empty")

        audio_parts: List[np.ndarray] = []
        sample_rate: Optional[int] = None
        for chunk in chunks:
            audio, sr = engine.synthesize(chunk, voice=voice, options=options)
            audio = _ensure_float32_mono(audio)
            if sample_rate is None:
                sample_rate = int(sr)
            elif int(sr) != sample_rate:
                raise GatewayError(
                    f"Engine changed sample rate between chunks: {sample_rate} -> {sr}"
                )
            if audio.size:
                audio_parts.append(audio)

        if sample_rate is None:
            raise GatewayError("TTS engine did not return a sample rate")
        return (
            _concat_audio(audio_parts, sample_rate, self.cfg.chunk_pause_ms),
            sample_rate,
        )

    def synthesize(
        self,
        *,
        model: Optional[str],
        voice: Optional[str],
        text: str,
        speed: float,
        language: Optional[str],
    ) -> Tuple[np.ndarray, int, str, Optional[str]]:
        # One lock covers switching, loading, inference and optional unload.
        # This prevents a second request from unloading an engine still in use.
        with self.lock:
            engine_name, local_voice = self.resolve_request(model, voice)
            target = self.registry[engine_name]
            local_voice = self._validate_voice(engine_name, target, local_voice)
            engine = self._switch_if_needed(engine_name)

            options: Dict[str, Any] = {"speed": speed}
            if language:
                options["language"] = language

            try:
                audio, sr = self._synthesize_chunks(
                    engine, text, local_voice, options
                )
                return audio, sr, engine_name, local_voice
            finally:
                if self.cfg.load_policy == "unload-after" and engine.is_loaded():
                    engine.unload()
                    if self.current_engine_name == engine_name:
                        self.current_engine_name = None
                        self.active_engine = None

    def load_engine(self, engine_name: str) -> Dict[str, Any]:
        with self.lock:
            resolved = self.resolve_engine_name(engine_name)
            engine = self._switch_if_needed(resolved)
            return {"engine": resolved, "loaded": engine.is_loaded()}

    def unload_engine(self, engine_name: str) -> Dict[str, Any]:
        with self.lock:
            resolved = self.resolve_engine_name(engine_name)
            engine = self.registry[resolved]
            if engine.is_loaded():
                engine.unload()
            if self.current_engine_name == resolved:
                self.current_engine_name = None
                self.active_engine = None
            return {"engine": resolved, "loaded": engine.is_loaded()}


config = GatewayConfig.load()
manager = EngineManager(config)


class SpeechRequest(BaseModel):
    model: Optional[str] = None
    input: str = Field(min_length=1)
    voice: Optional[str] = None
    response_format: str = "wav"
    speed: float = Field(default=1.0, ge=0.25, le=4.0)
    language: Optional[str] = None
    instructions: Optional[str] = None


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "active_engine": manager.current_engine_name,
        "is_loaded": manager.active_engine.is_loaded() if manager.active_engine else False,
        "loaded_engines": {
            name: engine.is_loaded() for name, engine in manager.registry.items()
        },
        "available_engines": list(manager.registry),
        "default_engine": config.default_engine,
        "load_policy": config.load_policy,
    }


@app.get("/ready")
async def readiness_check():
    return {
        "ready": True,
        "configured_engines": list(manager.registry),
        "default_engine": config.default_engine,
    }


@app.get("/v1/models")
@app.get("/models")
async def get_models():
    return {"object": "list", "data": manager.list_available_models()}


@app.get("/v1/audio/voices")
@app.get("/voices")
async def get_voices():
    voices = manager.list_all_voices()
    return {"object": "list", "data": voices, "voices": voices}


@app.get("/v1/engines")
async def get_engines():
    return {
        "data": [
            {
                "id": name,
                "loaded": engine.is_loaded(),
                "active": name == manager.current_engine_name,
            }
            for name, engine in manager.registry.items()
        ]
    }


@app.post("/v1/engines/{engine_name}/load")
async def load_engine(engine_name: str):
    try:
        return await run_in_threadpool(manager.load_engine, engine_name)
    except UnknownEngineError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/v1/engines/{engine_name}/unload")
async def unload_engine(engine_name: str):
    try:
        return await run_in_threadpool(manager.unload_engine, engine_name)
    except UnknownEngineError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/v1/audio/speech")
@app.post("/audio/speech")
async def create_speech(req: SpeechRequest):
    text = req.input.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Input text cannot be empty")

    fmt = req.response_format.lower().strip()
    if fmt not in config.response_formats:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported response_format {fmt!r}. "
                f"Allowed: {', '.join(config.response_formats)}"
            ),
        )

    try:
        audio, sample_rate, engine_name, local_voice = await run_in_threadpool(
            manager.synthesize,
            model=req.model,
            voice=req.voice,
            text=text,
            speed=req.speed,
            language=req.language,
        )
        audio_bytes, media_type = await run_in_threadpool(
            _encode_audio, audio, sample_rate, fmt
        )
        return Response(
            content=audio_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f'inline; filename="speech.{fmt}"',
                "X-TTS-Engine": engine_name,
                "X-TTS-Voice": local_voice or "",
                "X-Audio-Sample-Rate": str(sample_rate),
            },
        )
    except (UnknownEngineError, UnknownVoiceError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UnsupportedFormatError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except GatewayError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        print(f"[TTS Gateway Error] Synthesis failed: {exc}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail="TTS synthesis failed") from exc


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((host, port)) == 0


def main():
    cfg = GatewayConfig.load()
    if is_port_in_use(cfg.port, cfg.host):
        print(
            f"[TTS Gateway] ERROR: Port {cfg.port} on {cfg.host} "
            "is already in use."
        )
        raise SystemExit(1)

    print("=" * 55)
    print(f"Starting Local TTS Gateway on http://{cfg.host}:{cfg.port}")
    print(f"Default engine: {cfg.default_engine}")
    print(f"Load policy: {cfg.load_policy}")
    print(f"Engines: {list(manager.registry)}")
    print("=" * 55)
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")


if __name__ == "__main__":
    main()
