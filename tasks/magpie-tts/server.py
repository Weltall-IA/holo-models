import os
import io
import time
import torch
import soundfile as sf
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(title="Magpie TTS OpenAI-Compatible API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_PATH = "/home/alpha/Playstoria/models/audio/voz/nvidia-magpie_tts_multilingual_357m/magpie_tts_multilingual_357m.nemo"

SPEAKER_MAP = {
    "aria": 0,
    "jason": 1,
    "john": 2,
    "leo": 3,
    "sofia": 4,
}

DEFAULT_SPEAKER = 4  # Sofia
SAMPLE_RATE = 22050

model = None
model_device = None

def get_best_device():
    if torch.cuda.is_available():
        try:
            free_bytes, total_bytes = torch.cuda.mem_get_info()
            if free_bytes > 2.0 * (1024**3):
                return "cuda"
        except Exception:
            pass
    return "cpu"

def load_magpie():
    global model, model_device
    if model is not None:
        return model
    
    device = get_best_device()
    print(f"Loading Magpie TTS Model on {device}...")
    t0 = time.time()
    
    from nemo.collections.tts.models import MagpieTTSModel
    
    # If using CPU, prevent PyTorch from attempting CUDA allocations
    if device == "cpu":
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
        
    model = MagpieTTSModel.restore_from(MODEL_PATH, map_location=device)
    model.eval()
    model_device = device
    print(f"Magpie TTS Model loaded successfully on {device} in {time.time() - t0:.2f}s")
    return model

@app.on_event("startup")
def startup_event():
    try:
        load_magpie()
    except Exception as e:
        print(f"Startup model load notice: {e}")

class OpenAISpeechRequest(BaseModel):
    model: Optional[str] = "magpie-tts"
    input: str
    voice: Optional[str] = "Sofia"
    response_format: Optional[str] = "wav"
    speed: Optional[float] = 1.0

def detect_language(text: str) -> str:
    # Portuguese indicators
    pt_words = {"que", "não", "para", "com", "uma", "estou", "está", "você", "olá", "fala", "português", "muito", "mais", "como", "mas", "por", "isso", "esse", "esta"}
    words = set(text.lower().replace(",", "").replace(".", "").replace("!", "").replace("?", "").split())
    if len(words.intersection(pt_words)) > 0 or any(c in text for c in "ãõáéíóúâêîôûàçÃÕÁÉÍÓÚÂÊÎÔÛÀÇ"):
        return "pt"
    return "en"

@app.post("/v1/audio/speech")
async def generate_speech(req: OpenAISpeechRequest):
    if not req.input or not req.input.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty")
    
    current_model = load_magpie()
    
    # Resolve speaker
    voice_key = (req.voice or "sofia").lower().strip()
    speaker_idx = DEFAULT_SPEAKER
    
    # Check if voice includes language suffix like Sofia-pt or Sofia-en
    req_lang = None
    if "-" in voice_key:
        parts = voice_key.split("-")
        voice_name = parts[0]
        if len(parts) > 1:
            req_lang = parts[1]
        if voice_name in SPEAKER_MAP:
            speaker_idx = SPEAKER_MAP[voice_name]
    elif voice_key in SPEAKER_MAP:
        speaker_idx = SPEAKER_MAP[voice_key]
        
    lang = req_lang if req_lang in ["ar", "de", "en", "es", "fr", "hi", "it", "ja", "ko", "pt", "vi", "zh"] else detect_language(req.input)
    
    print(f"TTS Request: text='{req.input[:60]}...' | voice={voice_key} (idx={speaker_idx}) | lang={lang}")
    
    try:
        with torch.no_grad():
            audio, audio_len = current_model.do_tts(
                req.input,
                language=lang,
                apply_TN=False,
                speaker_index=speaker_idx
            )
            
        if isinstance(audio, torch.Tensor):
            audio_np = audio.detach().cpu().numpy().squeeze()
        else:
            audio_np = audio
            
        out_io = io.BytesIO()
        sf.write(out_io, audio_np, SAMPLE_RATE, format="WAV")
        out_io.seek(0)
        
        return Response(
            content=out_io.read(),
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=speech.wav"}
        )
    except Exception as e:
        print(f"Error during TTS synthesis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/models")
@app.get("/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "magpie-tts", "object": "model", "owned_by": "nvidia"},
            {"id": "tts-1", "object": "model", "owned_by": "openai"}
        ]
    }

@app.get("/v1/audio/voices")
@app.get("/voices")
async def list_voices():
    voices = []
    for spk in ["Aria", "Jason", "John", "Leo", "Sofia"]:
        for lang in ["pt", "en"]:
            voices.append({
                "voice_id": f"{spk}-{lang}",
                "name": f"{spk} ({lang.upper()})",
                "language": lang
            })
    return {"voices": voices}

@app.get("/health")
async def health_check():
    return {"status": "ok", "device": model_device, "model_loaded": model is not None}
