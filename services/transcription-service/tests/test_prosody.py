"""Unit tests for optional prosody extraction (023 FR-008 / FR-011). No GPU."""

from __future__ import annotations

import math
import struct
import time

from jsonschema import Draft202012Validator
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.prosody import estimate_prosody
from conftest import make_test_settings

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "contracts" / "transcript-event.v2.schema.json"
VALIDATOR = Draft202012Validator(
    __import__("json").loads(SCHEMA_PATH.read_text(encoding="utf-8"))
)


def _pcm_sine(seconds: float, freq_hz: float, sample_rate: int = 16_000, amp: float = 0.4) -> bytes:
    n = int(seconds * sample_rate)
    samples = []
    for i in range(n):
        t = i / sample_rate
        samples.append(int(max(-1.0, min(1.0, amp * math.sin(2 * math.pi * freq_hz * t))) * 32767))
    return struct.pack(f"<{n}h", *samples)


def _pcm_rising_f0(seconds: float = 0.6, sample_rate: int = 16_000) -> bytes:
    """Synthesize a chirp from ~120 Hz to ~220 Hz (rising end contour)."""
    n = int(seconds * sample_rate)
    samples = []
    phase = 0.0
    for i in range(n):
        # Linear chirp in Hz
        f = 120.0 + (100.0 * i / max(1, n - 1))
        phase += 2 * math.pi * f / sample_rate
        samples.append(int(0.35 * math.sin(phase) * 32767))
    return struct.pack(f"<{n}h", *samples)


def test_estimate_prosody_returns_shape_on_voiced_audio():
    pcm = _pcm_sine(0.5, 180.0)
    result = estimate_prosody(pcm, sample_rate=16_000, end_window_ms=500)
    assert result is not None
    assert 0.0 <= result["questionScore"] <= 1.0
    assert result["contour"] in {"rising", "falling", "flat", "unknown"}
    assert "f0EndSlopeSemitones" in result


def test_estimate_prosody_rising_chirp_tends_higher_score_than_silence_like():
    rising = estimate_prosody(_pcm_rising_f0(), sample_rate=16_000, end_window_ms=500)
    quiet = estimate_prosody(b"\x00\x00" * 8000, sample_rate=16_000, end_window_ms=500)
    # Quiet may be None; rising should produce a score.
    assert rising is not None
    if quiet is not None:
        assert rising["questionScore"] >= quiet["questionScore"]


def test_estimate_prosody_too_short_returns_none():
    assert estimate_prosody(b"\x00\x00" * 10, sample_rate=16_000) is None


def test_schema_accepts_final_without_and_with_prosody():
    base = {
        "type": "transcript.final.v2",
        "sessionId": "s1",
        "channelId": "remote_1",
        "label": "Áudio remoto",
        "sourceType": "system",
        "device": {"index": None, "name": "loopback", "endpointId": None},
        "text": "voce ja usou spring boot",
        "latencyMs": 100,
        "occurredAt": "2026-07-25T12:00:00Z",
    }
    VALIDATOR.validate(base)
    with_prosody = {
        **base,
        "prosody": {
            "questionScore": 0.78,
            "contour": "rising",
            "f0EndSlopeSemitones": 2.1,
        },
    }
    VALIDATOR.validate(with_prosody)


def test_schema_rejects_invalid_question_score():
    event = {
        "type": "transcript.final.v2",
        "sessionId": "s1",
        "channelId": "remote_1",
        "label": "Áudio remoto",
        "sourceType": "system",
        "device": {"index": None, "name": "loopback", "endpointId": None},
        "text": "texto",
        "latencyMs": 10,
        "occurredAt": "2026-07-25T12:00:00Z",
        "prosody": {"questionScore": 1.5},
    }
    errors = list(VALIDATOR.iter_errors(event))
    assert errors


def test_prosody_budget_rough_fixture_timing():
    """NFR-002: document rough CPU cost; soft assert (not a hard CI gate)."""
    pcm = _pcm_rising_f0(1.0)
    started = time.perf_counter()
    for _ in range(5):
        estimate_prosody(pcm, sample_rate=16_000, end_window_ms=500)
    elapsed_ms = (time.perf_counter() - started) * 1000 / 5
    # Soft budget: tens of ms per short final on CPU; allow headroom for CI noise.
    assert elapsed_ms < 500, f"prosody average {elapsed_ms:.1f} ms exceeds soft budget"


def test_health_exposes_prosody_enabled_default_false(client):
    """T051 / FR-008: /health reports prosodyEnabled (default false)."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "prosodyEnabled" in body
    assert body["prosodyEnabled"] is False


def test_health_exposes_prosody_enabled_when_on(fake_engine, metrics_registry, consolidator):
    app = create_app(
        settings=make_test_settings(prosody_enabled=True),
        engine=fake_engine,
        metrics_registry=metrics_registry,
        consolidator=consolidator,
    )
    body = TestClient(app).get("/health").json()
    assert body["prosodyEnabled"] is True
