from __future__ import annotations

import numpy as np
from fastapi.testclient import TestClient

from app.main import create_app
from app.metrics import LatencyMetricsRegistry
from conftest import FakeTranscriptionEngine, make_test_settings

SAMPLE_RATE = 16_000


def sine_pcm16(seconds: float, frequency: float = 440.0) -> bytes:
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    return (np.sin(2 * np.pi * frequency * t) * 0.3 * 32767).astype(np.int16).tobytes()


# Exactly one transcription window under the test settings (0.5 s).
WINDOW = sine_pcm16(0.5)


def get_metrics(client: TestClient, session_id: str) -> dict:
    response = client.get(f"/v1/sessions/{session_id}/metrics")
    assert response.status_code == 200
    return response.json()


def test_delivered_event_is_measured_once(client, fake_engine) -> None:
    fake_engine.script("primeira janela")
    url = (
        "/ws/audio/sess-m1/mic-1"
        "?sourceType=microphone&label=Headset&deviceIndex=2&deviceName=Microfone"
    )
    with client.websocket_connect(url) as ws:
        ws.send_bytes(WINDOW)
        event = ws.receive_json()

    payload = get_metrics(client, "sess-m1")
    assert payload["sessionId"] == "sess-m1"
    assert len(payload["channels"]) == 1
    channel = payload["channels"][0]
    assert channel["channelId"] == "mic-1"
    assert channel["sourceType"] == "microphone"
    assert channel["label"] == "Headset"
    assert channel["sampleCount"] == 1
    assert channel["totalEvents"] == 1
    assert channel["droppedWindows"] == 0
    assert isinstance(channel["p50Ms"], int) and channel["p50Ms"] >= 0
    assert channel["p50Ms"] == channel["p95Ms"] == event["latencyMs"]
    assert channel["lastEventAt"] is not None


def test_feed_subscribers_do_not_duplicate_samples(client, fake_engine) -> None:
    fake_engine.script("evento no feed")
    with client.websocket_connect("/ws/transcripts") as feed:
        with client.websocket_connect(
            "/ws/audio/sess-feed/system-main?sourceType=system"
        ) as ws:
            ws.send_bytes(WINDOW)
            ws.receive_json()
        feed.receive_json()

    channel = get_metrics(client, "sess-feed")["channels"][0]
    assert channel["sampleCount"] == 1
    assert channel["totalEvents"] == 1


def test_sessions_are_isolated_over_http(client, fake_engine) -> None:
    fake_engine.script("fala da sessao a", "fala da sessao b")
    with client.websocket_connect(
        "/ws/audio/sess-a/mic-1?sourceType=microphone"
    ) as ws:
        ws.send_bytes(WINDOW)
        ws.receive_json()
    with client.websocket_connect(
        "/ws/audio/sess-b/mic-1?sourceType=microphone"
    ) as ws:
        ws.send_bytes(WINDOW)
        ws.receive_json()

    payload_a = get_metrics(client, "sess-a")
    payload_b = get_metrics(client, "sess-b")
    assert len(payload_a["channels"]) == 1
    assert len(payload_b["channels"]) == 1
    assert payload_a["channels"][0]["sampleCount"] == 1
    assert payload_b["channels"][0]["sampleCount"] == 1


def test_channels_are_isolated_over_http(client, fake_engine) -> None:
    fake_engine.script("audio da reuniao", "pergunta do usuario")
    with client.websocket_connect(
        "/ws/audio/sess-multi/system-main?sourceType=system&label=Speakers"
    ) as system_ws:
        system_ws.send_bytes(WINDOW)
        system_ws.receive_json()
        with client.websocket_connect(
            "/ws/audio/sess-multi/mic-1?sourceType=microphone&label=Headset"
        ) as mic_ws:
            mic_ws.send_bytes(WINDOW)
            mic_ws.receive_json()

    channels = get_metrics(client, "sess-multi")["channels"]
    assert [channel["channelId"] for channel in channels] == ["mic-1", "system-main"]
    for channel in channels:
        assert channel["sampleCount"] == 1
        assert channel["totalEvents"] == 1


def test_suppressed_echo_is_not_counted_as_delivered(client, fake_engine) -> None:
    fake_engine.script(
        "reuniao comeca as dez",
        "reuniao comeca as dez",
        "fala local diferente agora",
    )
    with client.websocket_connect(
        "/ws/audio/sess-echo/system-main?sourceType=system"
    ) as system_ws:
        system_ws.send_bytes(WINDOW)
        system_ws.receive_json()
        with client.websocket_connect(
            "/ws/audio/sess-echo/mic-1?sourceType=microphone"
        ) as mic_ws:
            # A primeira janela duplica o transcript do sistema e é suprimida.
            # Receber o evento da segunda garante que a suprimida já passou
            # pelo worker (FIFO) quando o GET abaixo roda.
            mic_ws.send_bytes(WINDOW)
            mic_ws.send_bytes(WINDOW)
            assert mic_ws.receive_json()["text"] == "fala local diferente agora"

    channels = get_metrics(client, "sess-echo")["channels"]
    assert [channel["channelId"] for channel in channels] == ["mic-1", "system-main"]
    mic, system = channels
    assert mic["sampleCount"] == 1
    assert mic["totalEvents"] == 1
    assert system["sampleCount"] == 1


def test_retention_limit_is_enforced_over_http(fake_engine) -> None:
    registry = LatencyMetricsRegistry(max_samples_per_channel=3)
    client = TestClient(
        create_app(
            # overlap=0 so 5 whole-window sends map 1:1 to 5 emitted events.
            # With the default overlap (0.1s over a 0.4s step), 5 windows of
            # 0.5s each leave a growing remainder that crosses
            # whisper_min_audio_seconds and gets flushed as a 6th event on
            # disconnect - correct sliding-window math (2.5s of audio at a
            # 0.4s step yields 6 windows), not a bug, but irrelevant noise
            # for a test that's only about the sampleCount/totalEvents
            # retention-cap behavior.
            settings=make_test_settings(whisper_overlap_seconds=0.0),
            engine=fake_engine,
            metrics_registry=registry,
        )
    )
    fake_engine.script(*[f"janela numero {index}" for index in range(5)])
    with client.websocket_connect(
        "/ws/audio/sess-ret/mic-1?sourceType=microphone"
    ) as ws:
        for _ in range(5):
            ws.send_bytes(WINDOW)
            ws.receive_json()

    payload = get_metrics(client, "sess-ret")
    assert payload["maxSamplesPerChannel"] == 3
    channel = payload["channels"][0]
    assert channel["sampleCount"] == 3
    assert channel["totalEvents"] == 5


def test_unknown_session_returns_empty_channels(client) -> None:
    payload = get_metrics(client, "sess-inexistente")
    assert payload["channels"] == []


def test_injected_registry_receives_records(client, fake_engine, metrics_registry) -> None:
    fake_engine.script("registro injetado")
    with client.websocket_connect(
        "/ws/audio/sess-inj/mic-1?sourceType=microphone"
    ) as ws:
        ws.send_bytes(WINDOW)
        ws.receive_json()

    snapshot = metrics_registry.session_snapshot("sess-inj")
    assert len(snapshot.channels) == 1
    assert snapshot.channels[0].total_events == 1


def test_fake_engine_never_loads_model(client, fake_engine) -> None:
    fake_engine.script("sem gpu")
    with client.websocket_connect(
        "/ws/audio/sess-cpu/mic-1?sourceType=microphone"
    ) as ws:
        ws.send_bytes(WINDOW)
        ws.receive_json()
    get_metrics(client, "sess-cpu")
    assert fake_engine.loaded is False
