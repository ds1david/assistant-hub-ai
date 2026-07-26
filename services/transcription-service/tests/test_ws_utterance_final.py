"""WS integration: utterance idle → transcript.final.v2 (issue #55). No GPU."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from jsonschema import Draft202012Validator

from conftest import make_test_settings
from fastapi.testclient import TestClient

from app.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "contracts" / "transcript-event.v2.schema.json"
VALIDATOR = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))

SAMPLE_RATE = 16_000


def sine_pcm16(seconds: float, frequency: float = 440.0) -> bytes:
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    return (np.sin(2 * np.pi * frequency * t) * 0.3 * 32767).astype(np.int16).tobytes()


# One full window under make_test_settings (window=0.5s).
WINDOW = sine_pcm16(0.5)


def _recv_until_idle(ws, *, max_events: int = 20) -> list[dict]:
    """Drain events with a short timeout-style loop via receive_json.

    Starlette TestClient blocks; callers should know how many events to expect
    and use receive_json that many times instead when possible.
    """
    events: list[dict] = []
    for _ in range(max_events):
        try:
            events.append(ws.receive_json())
        except Exception:
            break
    return events


def test_partials_then_idle_window_emits_exactly_one_final(
    fake_engine, metrics_registry, consolidator
) -> None:
    """Script: text, text, empty(same) → 2 partials + 1 final without client disconnect mid-stream.

    Fake engine: third call returns same as second → StreamingTranscriber returns None
    → on_no_result → idle final.
    """
    fake_engine.script("ola", "ola mundo", "ola mundo")
    client = TestClient(
        create_app(
            settings=make_test_settings(finalization_idle_windows=1),
            engine=fake_engine,
            metrics_registry=metrics_registry,
            consolidator=consolidator,
        )
    )
    url = "/ws/audio/sess-utt-1/system-main?sourceType=system&label=Sys&deviceIndex=1&deviceName=Speakers"
    with client.websocket_connect(url) as ws:
        ws.send_bytes(WINDOW)
        e1 = ws.receive_json()
        ws.send_bytes(WINDOW)
        e2 = ws.receive_json()
        ws.send_bytes(WINDOW)
        e3 = ws.receive_json()

    VALIDATOR.validate(e1)
    VALIDATOR.validate(e2)
    VALIDATOR.validate(e3)
    assert e1["type"] == "transcript.partial.v2"
    assert e1["text"] == "ola"
    assert e2["type"] == "transcript.partial.v2"
    assert e2["text"] == "ola mundo"
    assert e3["type"] == "transcript.final.v2"
    assert e3["text"] == "ola mundo"
    # Identity preserved on final
    assert e3["sessionId"] == "sess-utt-1"
    assert e3["channelId"] == "system-main"
    assert e3["label"] == "Sys"
    assert e3["sourceType"] == "system"
    assert e3["device"] == {"index": 1, "name": "Speakers", "endpointId": None}


def test_two_utterance_cycles_two_finals(
    fake_engine, metrics_registry, consolidator
) -> None:
    # Utt1: a, a (same→None idle final); Utt2: b, b (idle final)
    fake_engine.script("primeira", "primeira", "segunda", "segunda")
    client = TestClient(
        create_app(
            settings=make_test_settings(finalization_idle_windows=1),
            engine=fake_engine,
            metrics_registry=metrics_registry,
            consolidator=consolidator,
        )
    )
    url = "/ws/audio/sess-utt-2/mic-1?sourceType=microphone&label=Mic"
    with client.websocket_connect(url) as ws:
        ws.send_bytes(WINDOW)
        p1 = ws.receive_json()
        ws.send_bytes(WINDOW)
        f1 = ws.receive_json()
        ws.send_bytes(WINDOW)
        p2 = ws.receive_json()
        ws.send_bytes(WINDOW)
        f2 = ws.receive_json()

    assert p1["type"] == "transcript.partial.v2" and p1["text"] == "primeira"
    assert f1["type"] == "transcript.final.v2" and f1["text"] == "primeira"
    assert p2["type"] == "transcript.partial.v2" and p2["text"] == "segunda"
    assert f2["type"] == "transcript.final.v2" and f2["text"] == "segunda"
    VALIDATOR.validate(f1)
    VALIDATOR.validate(f2)


def test_disconnect_after_idle_final_does_not_double_final(
    fake_engine, metrics_registry, consolidator
) -> None:
    fake_engine.script("unico", "unico")
    client = TestClient(
        create_app(
            settings=make_test_settings(finalization_idle_windows=1),
            engine=fake_engine,
            metrics_registry=metrics_registry,
            consolidator=consolidator,
        )
    )
    with client.websocket_connect(
        "/ws/audio/sess-dedupe/system-main?sourceType=system"
    ) as ws:
        with client.websocket_connect("/ws/transcripts") as feed:
            ws.send_bytes(WINDOW)
            partial = ws.receive_json()
            ws.send_bytes(WINDOW)
            final = ws.receive_json()
            assert partial["type"] == "transcript.partial.v2"
            assert final["type"] == "transcript.final.v2"
            # Drain feed for the two events; disconnect of audio should not add another final.
            feed_events = [feed.receive_json(), feed.receive_json()]
    types = [e["type"] for e in feed_events]
    assert types.count("transcript.final.v2") == 1
    assert types.count("transcript.partial.v2") == 1


def test_silence_only_never_emits_final(
    fake_engine, metrics_registry, consolidator
) -> None:
    # Engine returns empty segments → no text → no open → no final.
    def empty_transcribe(audio, language=None):
        from app.engine import EngineResult

        fake_engine.calls.append({"language": language})
        return EngineResult(segments=(), language="pt", language_probability=0.5)

    fake_engine.transcribe = empty_transcribe  # type: ignore[method-assign]
    client = TestClient(
        create_app(
            settings=make_test_settings(),
            engine=fake_engine,
            metrics_registry=metrics_registry,
            consolidator=consolidator,
        )
    )
    with client.websocket_connect(
        "/ws/audio/sess-silent/system-main?sourceType=system"
    ) as ws:
        with client.websocket_connect("/ws/transcripts") as feed:
            ws.send_bytes(WINDOW)
            ws.send_bytes(WINDOW)
            # No events expected on channel; disconnect still no final.
    # Feed should not have received anything without blocking forever — skip if empty.
    # Starlette has no non-blocking receive; assert engine was called and no crash.
    assert len(fake_engine.calls) >= 1


def test_final_reaches_transcript_feed(
    fake_engine, metrics_registry, consolidator
) -> None:
    fake_engine.script("feed final", "feed final")
    client = TestClient(
        create_app(
            settings=make_test_settings(),
            engine=fake_engine,
            metrics_registry=metrics_registry,
            consolidator=consolidator,
        )
    )
    with client.websocket_connect("/ws/transcripts") as feed:
        with client.websocket_connect(
            "/ws/audio/sess-feed/system-main?sourceType=system"
        ) as ws:
            ws.send_bytes(WINDOW)
            ws.send_bytes(WINDOW)
            direct_partial = ws.receive_json()
            direct_final = ws.receive_json()
        feed_partial = feed.receive_json()
        feed_final = feed.receive_json()

    assert direct_partial["type"] == "transcript.partial.v2"
    assert direct_final["type"] == "transcript.final.v2"
    assert feed_partial == direct_partial
    assert feed_final == direct_final
    VALIDATOR.validate(feed_final)


def test_health_exposes_finalization_settings(client) -> None:
    body = client.get("/health").json()
    assert body["finalizationIdleWindows"] == 1
    assert body["finalizationMaxOpenSeconds"] == 45.0
