from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

from .config import Settings

LOGGER = logging.getLogger(__name__)


class ModelManager:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model: WhisperModel | None = None
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def get(self) -> WhisperModel:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    self._settings.model_cache_dir.mkdir(parents=True, exist_ok=True)
                    LOGGER.info(
                        "Loading model=%s device=%s compute_type=%s",
                        self._settings.whisper_model,
                        self._settings.whisper_device,
                        self._settings.whisper_compute_type,
                    )
                    self._model = WhisperModel(
                        self._settings.whisper_model,
                        device=self._settings.whisper_device,
                        compute_type=self._settings.whisper_compute_type,
                        download_root=str(self._settings.model_cache_dir),
                    )
        return self._model


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str | None
    language_probability: float | None
    latency_ms: int
    audio_seconds: float


def _transcription_options(settings: Settings, language: str | None) -> dict:
    return {
        "language": language or settings.whisper_language,
        "beam_size": settings.whisper_beam_size,
        "patience": settings.whisper_patience,
        "temperature": settings.whisper_temperature,
        "repetition_penalty": settings.whisper_repetition_penalty,
        "no_speech_threshold": settings.whisper_no_speech_threshold,
        "initial_prompt": settings.whisper_initial_prompt,
        "hotwords": settings.resolved_hotwords(),
        "vad_filter": True,
        "vad_parameters": {"min_silence_duration_ms": settings.whisper_vad_min_silence_ms},
        "condition_on_previous_text": False,
        "word_timestamps": False,
    }


class StreamingTranscriber:
    def __init__(self, settings: Settings, model_manager: ModelManager) -> None:
        self._settings = settings
        self._model_manager = model_manager
        self._buffer = bytearray()
        self._last_text = ""

        self._window_bytes = self._seconds_to_bytes(settings.whisper_window_seconds)
        self._overlap_bytes = self._seconds_to_bytes(settings.whisper_overlap_seconds)
        self._minimum_bytes = self._seconds_to_bytes(settings.whisper_min_audio_seconds)

        if self._overlap_bytes >= self._window_bytes:
            raise ValueError("WHISPER_OVERLAP_SECONDS must be smaller than WHISPER_WINDOW_SECONDS")

    def _seconds_to_bytes(self, seconds: float) -> int:
        # Mono signed PCM16.
        return int(seconds * self._settings.sample_rate * 2)

    def append(self, chunk: bytes) -> bytes | None:
        self._buffer.extend(chunk)
        if len(self._buffer) < self._window_bytes:
            return None

        window = bytes(self._buffer[: self._window_bytes])
        keep_from = self._window_bytes - self._overlap_bytes
        del self._buffer[:keep_from]
        return window

    def flush(self) -> bytes | None:
        if len(self._buffer) < self._minimum_bytes:
            self._buffer.clear()
            return None
        remaining = bytes(self._buffer)
        self._buffer.clear()
        return remaining

    def transcribe_pcm(self, pcm16: bytes, language: str | None = None) -> TranscriptionResult | None:
        if len(pcm16) < self._minimum_bytes:
            return None

        started = time.perf_counter()
        audio = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0
        model = self._model_manager.get()
        segments, info = model.transcribe(audio, **_transcription_options(self._settings, language))
        text = " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
        latency_ms = int((time.perf_counter() - started) * 1000)

        if not text or text == self._last_text:
            return None
        self._last_text = text

        return TranscriptionResult(
            text=text,
            language=getattr(info, "language", None),
            language_probability=getattr(info, "language_probability", None),
            latency_ms=latency_ms,
            audio_seconds=len(audio) / self._settings.sample_rate,
        )


def transcribe_file(path: Path, settings: Settings, manager: ModelManager, language: str | None) -> dict:
    started = time.perf_counter()
    segments, info = manager.get().transcribe(
        str(path),
        **_transcription_options(settings, language),
    )
    text_segments = [
        {"start": segment.start, "end": segment.end, "text": segment.text.strip()}
        for segment in segments
        if segment.text.strip()
    ]
    return {
        "text": " ".join(item["text"] for item in text_segments),
        "segments": text_segments,
        "language": getattr(info, "language", None),
        "languageProbability": getattr(info, "language_probability", None),
        "latencyMs": int((time.perf_counter() - started) * 1000),
    }
