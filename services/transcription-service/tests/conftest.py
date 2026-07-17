from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

from app import main
from app.broadcast import TranscriptBroadcaster
from app.config import Settings
from app.echo_suppression import TranscriptEchoSuppressor
from app.transcriber import ModelManager


@dataclass(frozen=True)
class FakeSegment:
    text: str
    start: float = 0.0
    end: float = 1.0


@dataclass(frozen=True)
class FakeInfo:
    language: str | None = "pt"
    language_probability: float | None = 0.99


@dataclass
class FakeWhisperModel:
    """Duck-typed stand-in for faster_whisper.WhisperModel.

    Returns scripted texts in FIFO order, one per transcribe() call, so tests
    control exactly what each audio window "says".
    """

    scripted_texts: list[str] = field(default_factory=list)
    calls: list[dict] = field(default_factory=list)

    def script(self, *texts: str) -> None:
        self.scripted_texts.extend(texts)

    def transcribe(self, audio, **options):
        self.calls.append(options)
        text = self.scripted_texts.pop(0) if self.scripted_texts else "transcricao sintetica"
        return [FakeSegment(text=text)], FakeInfo()


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
def fake_model() -> FakeWhisperModel:
    return FakeWhisperModel()


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, fake_model: FakeWhisperModel) -> TestClient:
    test_settings = make_test_settings()
    monkeypatch.setattr(main, "settings", test_settings)
    monkeypatch.setattr(
        main,
        "model_manager",
        ModelManager(test_settings, model_factory=lambda: fake_model),
    )
    monkeypatch.setattr(
        main,
        "echo_suppressor",
        TranscriptEchoSuppressor(
            enabled=test_settings.echo_suppression_enabled,
            window_seconds=test_settings.echo_suppression_window_seconds,
            similarity_threshold=test_settings.echo_suppression_similarity,
            min_chars=test_settings.echo_suppression_min_chars,
        ),
    )
    monkeypatch.setattr(main, "broadcaster", TranscriptBroadcaster())
    return TestClient(main.app)
