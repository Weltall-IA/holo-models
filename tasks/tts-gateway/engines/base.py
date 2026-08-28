from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class BaseTTSEngine(ABC):
    """Common contract implemented by every TTS engine adapter."""

    execution_mode: str = "in-process"

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def load(self) -> None:
        """Load the model/runtime on demand."""
        pass

    @abstractmethod
    def unload(self) -> None:
        """Unload the model/runtime and release owned resources."""
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        pass

    @abstractmethod
    def list_voices(self) -> List[Dict[str, Any]]:
        """Return engine-local voice metadata."""
        pass

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[np.ndarray, int]:
        """Return mono float32 audio and its sample rate."""
        pass
