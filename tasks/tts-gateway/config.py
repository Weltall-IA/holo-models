from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

import yaml


ROOT_DIR = Path(__file__).resolve().parent
VALID_LOAD_POLICIES = {"lazy", "keep-current", "unload-after"}
DEFAULT_MODEL_ALIASES = ["tts-1", "tts-1-hd", "gpt-4o-mini-tts"]
DEFAULT_RESPONSE_FORMATS = ["wav", "flac", "mp3", "pcm"]


def _expand(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expanduser(os.path.expandvars(value))
    if isinstance(value, dict):
        return {key: _expand(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand(item) for item in value]
    return value


@dataclass
class GatewayConfig:
    host: str = "127.0.0.1"
    port: int = 5050
    default_engine: str = "magpie"
    device: str = "cuda"
    load_policy: str = "keep-current"
    model_aliases: List[str] = field(default_factory=lambda: list(DEFAULT_MODEL_ALIASES))
    response_formats: List[str] = field(
        default_factory=lambda: list(DEFAULT_RESPONSE_FORMATS)
    )
    chunking_enabled: bool = True
    chunk_chars: int = 1200
    chunk_pause_ms: int = 120
    engines: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "GatewayConfig":
        if config_path is None:
            config_path = os.environ.get(
                "TTS_GATEWAY_CONFIG", str(ROOT_DIR / "config.yaml")
            )

        path = Path(_expand(config_path))
        data: Dict[str, Any] = {}
        if path.is_file():
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        data = _expand(data)

        cfg = cls(
            host=str(data.get("host", "127.0.0.1")),
            port=int(data.get("port", 5050)),
            default_engine=str(data.get("default_engine", "magpie")).lower(),
            device=str(data.get("device", "cuda")),
            load_policy=str(data.get("load_policy", "keep-current")).lower(),
            model_aliases=[
                str(item).lower()
                for item in data.get("model_aliases", DEFAULT_MODEL_ALIASES)
            ],
            response_formats=[
                str(item).lower()
                for item in data.get("response_formats", DEFAULT_RESPONSE_FORMATS)
            ],
            chunking_enabled=bool(data.get("chunking_enabled", True)),
            chunk_chars=int(data.get("chunk_chars", 1200)),
            chunk_pause_ms=int(data.get("chunk_pause_ms", 120)),
            engines=data.get("engines", {}),
        )
        cfg.validate()
        return cfg

    def validate(self) -> None:
        if self.load_policy not in VALID_LOAD_POLICIES:
            raise ValueError(
                f"Invalid load_policy {self.load_policy!r}; "
                f"expected one of {sorted(VALID_LOAD_POLICIES)}"
            )
        if self.port < 1 or self.port > 65535:
            raise ValueError("port must be between 1 and 65535")
        if self.chunk_chars < 64:
            raise ValueError("chunk_chars must be >= 64")
        if self.chunk_pause_ms < 0:
            raise ValueError("chunk_pause_ms must be >= 0")
        if not self.response_formats:
            raise ValueError("response_formats cannot be empty")
