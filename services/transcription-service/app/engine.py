from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


@dataclass(frozen=True)
class EngineSegment:
    text: str
    start: float = 0.0
    end: float = 0.0


@dataclass(frozen=True)
class EngineResult:
    segments: tuple[EngineSegment, ...]
    language: str | None = None
    language_probability: float | None = None


class TranscriptionEngine(ABC):
    """Boundary between the service and the STT backend.

    Implementations own model lifecycle and decoding options; callers only
    hand over audio (float32 mono waveform or a file path) and read segments.
    """

    @property
    @abstractmethod
    def loaded(self) -> bool:
        """Whether the underlying model is in memory."""

    @abstractmethod
    def load(self) -> None:
        """Load the underlying model eagerly. Blocking; call from a thread."""

    @abstractmethod
    def transcribe(self, audio: "np.ndarray | str", language: str | None = None) -> EngineResult:
        """Transcribe a waveform or an audio file path. Blocking; call from a thread."""
