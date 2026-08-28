from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

class BaseTTSEngine(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the engine (e.g. 'magpie', 'kokoro')"""
        pass

    @abstractmethod
    def load(self) -> None:
        """Load the model into memory/GPU."""
        pass

    @abstractmethod
    def unload(self) -> None:
        """Unload model from memory and free GPU resources."""
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        """Return True if model is currently loaded in memory."""
        pass

    @abstractmethod
    def list_voices(self) -> List[Dict[str, Any]]:
        """Return a list of available voices/speakers with metadata."""
        pass

    @abstractmethod
    def synthesize(self, text: str, voice: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, int]:
        """
        Synthesize text into raw waveform numpy array and return (audio_numpy, sample_rate).
        Audio array should be float32 1D numpy array.
        """
        pass
