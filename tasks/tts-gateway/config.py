from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
import os

ROOT_DIR = Path(__file__).resolve().parent

@dataclass
class GatewayConfig:
    host: str = "127.0.0.1"
    port: int = 5050
    default_engine: str = "magpie"
    device: str = "cuda"
    load_policy: str = "keep-current"
    engines: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "GatewayConfig":
        if config_path is None:
            config_path = os.environ.get("TTS_GATEWAY_CONFIG", str(ROOT_DIR / "config.yaml"))
        
        path = Path(config_path)
        if not path.is_file():
            # Return defaults
            return cls(
                engines={
                    "magpie": {
                        "model_path": "/home/alpha/Playstoria/models/audio/voz/nvidia-magpie_tts_multilingual_357m/magpie_tts_multilingual_357m.nemo",
                        "default_speaker": "Sofia",
                        "default_language": "pt",
                        "device": "auto",
                        "sample_rate": 22050
                    },
                    "kokoro": {
                        "model_path": "/home/alpha/Playstoria/models/audio/voz/hexgrad-Kokoro-82M-ONNX/kokoro-v1.0.onnx",
                        "voices_path": "/home/alpha/Playstoria/models/audio/voz/hexgrad-Kokoro-82M-ONNX/voices-v1.0.bin",
                        "default_voice": "af_heart",
                        "sample_rate": 24000
                    }
                }
            )
        
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return cls(
            host=data.get("host", "127.0.0.1"),
            port=int(data.get("port", 5050)),
            default_engine=data.get("default_engine", "magpie"),
            device=data.get("device", "cuda"),
            load_policy=data.get("load_policy", "keep-current"),
            engines=data.get("engines", {})
        )
