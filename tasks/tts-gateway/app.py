import io
import os
import gc
import socket
import sys
import threading
import time
from typing import Any, Dict, List, Optional
import numpy as np
import soundfile as sf
import uvicorn
from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import GatewayConfig
from engines.base import BaseTTSEngine
from engines.magpie import MagpieEngine
from engines.kokoro import KokoroEngine

app = FastAPI(
    title="Local TTS Gateway",
    description="Unified OpenAI-compatible TTS Gateway for Magpie, Kokoro, and future engines",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Manager
class EngineManager:
    def __init__(self, cfg: GatewayConfig):
        self.cfg = cfg
        self.lock = threading.Lock()
        self.current_engine_name: Optional[str] = None
        self.active_engine: Optional[BaseTTSEngine] = None
        self.registry: Dict[str, BaseTTSEngine] = {
            "magpie": MagpieEngine(cfg.engines.get("magpie", {})),
            "kokoro": KokoroEngine(cfg.engines.get("kokoro", {})),
        }

    def list_available_models(self) -> List[Dict[str, Any]]:
        models = []
        for name in self.registry.keys():
            models.append({
                "id": name,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "local-tts-gateway",
                "permission": [],
                "root": name,
                "parent": None,
            })
        # Add aliases for OpenAI compatibility
        models.append({
            "id": "tts-1",
            "object": "model",
            "created": int(time.time()),
            "owned_by": "openai",
            "permission": [],
            "root": "tts-1",
            "parent": None,
        })
        models.append({
            "id": "tts-1-hd",
            "object": "model",
            "created": int(time.time()),
            "owned_by": "openai",
            "permission": [],
            "root": "tts-1-hd",
            "parent": None,
        })
        return models

    def list_all_voices(self) -> List[Dict[str, Any]]:
        all_voices = []
        for name, engine in self.registry.items():
            try:
                all_voices.extend(engine.list_voices())
            except Exception as e:
                print(f"[EngineManager] Error listing voices for {name}: {e}")
        return all_voices

    def get_or_switch_engine(self, engine_name: str) -> BaseTTSEngine:
        with self.lock:
            engine_name = engine_name.lower().strip()
            if engine_name in ["tts-1", "tts-1-hd", "default"]:
                engine_name = self.cfg.default_engine

            if engine_name not in self.registry:
                # Try finding if voice belongs to a specific engine
                for name, eng in self.registry.items():
                    voices = eng.list_voices()
                    if any(v["voice_id"].lower() == engine_name or v["name"].lower() == engine_name for v in voices):
                        engine_name = name
                        break
                else:
                    engine_name = self.cfg.default_engine

            target_engine = self.registry[engine_name]
            if not target_engine.is_loaded():
                print(f"[EngineManager] Loading engine on demand: {engine_name}...")
                target_engine.load()
            
            self.current_engine_name = engine_name
            self.active_engine = target_engine
            return target_engine

config = GatewayConfig.load()
manager = EngineManager(config)

class SpeechRequest(BaseModel):
    model: Optional[str] = None
    input: str
    voice: Optional[str] = None
    response_format: Optional[str] = "wav"
    speed: Optional[float] = 1.0

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "active_engine": manager.current_engine_name,
        "is_loaded": manager.active_engine.is_loaded() if manager.active_engine else False,
        "available_engines": list(manager.registry.keys()),
        "default_engine": config.default_engine,
    }

@app.get("/v1/models")
@app.get("/models")
async def get_models():
    return {"object": "list", "data": manager.list_available_models()}

@app.get("/v1/audio/voices")
@app.get("/voices")
async def get_voices():
    return {"voices": manager.list_all_voices()}

@app.post("/v1/audio/speech")
@app.post("/audio/speech")
async def create_speech(req: SpeechRequest):
    if not req.input or not req.input.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty")

    # Determine requested engine
    target_engine_name = req.model or config.default_engine
    
    # Also allow voice name to specify engine (e.g. voice="kokoro:af_heart" or voice="magpie:Sofia")
    voice_name = req.voice
    if voice_name and ":" in voice_name:
        eng_prefix, v_suffix = voice_name.split(":", 1)
        if eng_prefix.lower() in manager.registry:
            target_engine_name = eng_prefix.lower()
            voice_name = v_suffix

    # If voice starts with af_, am_, bf_, bm_ etc., infer kokoro
    if voice_name and any(voice_name.startswith(p) for p in ["af_", "am_", "bf_", "bm_", "ef_", "em_", "ff_", "hf_", "hm_", "if_", "im_", "jf_", "jm_", "pf_", "pm_", "zf_", "zm_"]):
        target_engine_name = "kokoro"
    elif voice_name and any(voice_name.lower().startswith(p) for p in ["sofia", "aria", "jason", "john", "leo", "speaker_"]):
        target_engine_name = "magpie"

    try:
        engine = manager.get_or_switch_engine(target_engine_name)
        audio_np, sample_rate = engine.synthesize(
            text=req.input,
            voice=voice_name,
            options={"speed": req.speed}
        )

        out_io = io.BytesIO()
        sf.write(out_io, audio_np, sample_rate, format="WAV")
        out_io.seek(0)
        audio_bytes = out_io.read()

        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=speech.wav",
                "Content-Type": "audio/wav"
            }
        )
    except Exception as e:
        print(f"[TTS Gateway Error] Synthesis failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

def main():
    cfg = GatewayConfig.load()
    if is_port_in_use(cfg.port, cfg.host):
        print(f"[TTS Gateway] ERROR: Port {cfg.port} on {cfg.host} is already in use by another process!")
        print("Please stop the conflicting process before starting TTS Gateway.")
        sys.exit(1)

    print(f"=======================================================")
    print(f"Starting Local TTS Gateway on http://{cfg.host}:{cfg.port}")
    print(f"Default Engine: {cfg.default_engine}")
    print(f"Engines: {list(manager.registry.keys())}")
    print(f"=======================================================")
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")

if __name__ == "__main__":
    main()
