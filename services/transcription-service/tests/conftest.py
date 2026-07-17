from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.engine import EngineResult, EngineSegment, TranscriptionEngine
from app.main import create_app


@dataclass
class FakeTranscriptionEngine(TranscriptionEngine):
    """In-memory TranscriptionEngine: no model, no download, no GPU.

    Returns scripted texts in FIFO order, one per transcribe() call, so tests
    control exactly what each audio window "says".
    """

    scripted_texts: list[str] = field(default_factory=list)
    calls: list[dict] = field(default_factory=list)
    _loaded: bool = False

    @property
    def loaded(self) -> bool:
        return self._loaded

    def load(self) -> None:
        self._loaded = True

    def script(self, *texts: str) -> None:
        self.scripted_texts.extend(texts)

    def transcribe(self, audio, language: str | None = None) -> EngineResult:
        self.calls.append({"language": language})
        text = self.scripted_texts.pop(0) if self.scripted_texts else "transcricao sintetica"
        return EngineResult(
            segments=(EngineSegment(text=text, start=0.0, end=1.0),),
            language="pt",
            language_probability=0.99,
        )


def make_test_settings() -> Settings:
    # Small windows keep the synthetic streams short; zero mic delay keeps the
    # echo-suppression path fast. min_audio > overlap so the leftover overlap
    # bytes never trigger a final flush after the client disconnects.
    return Settings(
        whisper_device="cpu",
        whisper_window_seconds=0.5,
        whisper_overlap_seconds=0.1,
        whisper_min_audio_seconds=0.2,
        echo_suppression_enabled=True,
        echo_suppression_mic_delay_ms=0,
        whisper_hotwords_file=None,
    )


@pytest.fixture()
def fake_engine() -> FakeTranscriptionEngine:
    return FakeTranscriptionEngine()


@pytest.fixture()
def client(fake_engine: FakeTranscriptionEngine) -> TestClient:
    return TestClient(create_app(settings=make_test_settings(), engine=fake_engine))
