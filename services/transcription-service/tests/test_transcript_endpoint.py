from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from app.consolidation import TranscriptConsolidationRegistry
from app.main import create_app
from conftest import FakeTranscriptionEngine, make_test_settings

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "contracts" / "transcript-event.v2.schema.json"
VALIDATOR = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))

SAMPLE_RATE = 16_000


def sine_pcm16(seconds: float, frequency: float = 440.0) -> bytes:
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    return (np.sin(2 * np.pi * frequency * t) * 0.3 * 32767).astype(np.int16).tobytes()


# Exactly one transcription window under the test settings (0.5 s). After a
# window fires, the buffer keeps 0.1 s of overlap, so 0.4 s completes the next.
WINDOW = sine_pcm16(0.5)
NEXT_WINDOW = sine_pcm16(0.4)


def get_transcript(client: TestClient, session_id: str) -> dict:
    response = client.get(f"/v1/sessions/{session_id}/transcript")
    assert response.status_code == 200
    return response.json()


def test_overlapping_windows_are_consolidated(client, fake_engine) -> None:
    fake_engine.script(
        "vamos revisar a arquitetura do serviço",
        "arquitetura do serviço antes da implementação",
    )
    url = (
        "/ws/audio/sess-cons/mic-1"
        "?sourceType=microphone&label=Headset&deviceIndex=2&deviceName=Microfone"
    )
    with client.websocket_connect(url) as ws:
        ws.send_bytes(WINDOW)
        first = ws.receive_json()
        ws.send_bytes(NEXT_WINDOW)
        second = ws.receive_json()

    # Os eventos v2 continuam brutos e válidos: a consolidação é um read-model.
    VALIDATOR.validate(first)
    VALIDATOR.validate(second)
    assert first["text"] == "vamos revisar a arquitetura do serviço"
    assert second["text"] == "arquitetura do serviço antes da implementação"

    payload = get_transcript(client, "sess-cons")
    assert payload["sessionId"] == "sess-cons"
    assert len(payload["channels"]) == 1
    channel = payload["channels"][0]
    assert channel["channelId"] == "mic-1"
    assert channel["sourceType"] == "microphone"
    assert channel["label"] == "Headset"
    assert channel["text"] == (
        "vamos revisar a arquitetura do serviço antes da implementação"
    )
    # 2 partials + 1 disconnect final (#55); final repeats last text → overlap dedupe.
    assert channel["segmentCount"] == 2
    assert channel["totalEvents"] == 3
    assert channel["duplicateWordsRemoved"] >= 3
    assert channel["truncated"] is False
    assert channel["firstEventAt"] is not None
    assert channel["lastEventAt"] is not None


def test_consolidation_does_not_change_latency_metrics(client, fake_engine) -> None:
    fake_engine.script("primeira janela", "janela seguinte distinta")
    with client.websocket_connect(
        "/ws/audio/sess-both/mic-1?sourceType=microphone"
    ) as ws:
        ws.send_bytes(WINDOW)
        ws.receive_json()
        ws.send_bytes(NEXT_WINDOW)
        ws.receive_json()

    metrics = client.get("/v1/sessions/sess-both/metrics").json()["channels"][0]
    # 2 partials + 1 disconnect final
    assert metrics["sampleCount"] == 3
    assert metrics["totalEvents"] == 3


def test_suppressed_echo_is_not_consolidated(client, fake_engine) -> None:
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
            # A primeira janela do microfone duplica o sistema e é suprimida
            # antes do ponto de consolidação; só a fala local entra.
            mic_ws.send_bytes(WINDOW)
            mic_ws.send_bytes(NEXT_WINDOW)
            assert mic_ws.receive_json()["text"] == "fala local diferente agora"

    channels = get_transcript(client, "sess-echo")["channels"]
    assert [channel["channelId"] for channel in channels] == ["mic-1", "system-main"]
    mic, system = channels
    assert mic["text"] == "fala local diferente agora"
    # partial + disconnect final
    assert mic["totalEvents"] == 2
    assert system["text"] == "reuniao comeca as dez"


def test_sessions_and_channels_are_isolated_over_http(client, fake_engine) -> None:
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

    payload_a = get_transcript(client, "sess-a")
    payload_b = get_transcript(client, "sess-b")
    assert payload_a["channels"][0]["text"] == "fala da sessao a"
    assert payload_b["channels"][0]["text"] == "fala da sessao b"


def test_unknown_session_returns_empty_channels(client) -> None:
    payload = get_transcript(client, "sess-inexistente")
    assert payload["channels"] == []


def test_retention_limit_is_enforced_over_http(fake_engine) -> None:
    consolidator = TranscriptConsolidationRegistry(max_segments_per_channel=1)
    client = TestClient(
        create_app(
            settings=make_test_settings(),
            engine=fake_engine,
            consolidator=consolidator,
        )
    )
    fake_engine.script("trecho antigo", "trecho recente")
    with client.websocket_connect(
        "/ws/audio/sess-ret/mic-1?sourceType=microphone"
    ) as ws:
        ws.send_bytes(WINDOW)
        ws.receive_json()
        ws.send_bytes(NEXT_WINDOW)
        ws.receive_json()

    payload = get_transcript(client, "sess-ret")
    assert payload["maxSegmentsPerChannel"] == 1
    channel = payload["channels"][0]
    assert channel["text"] == "trecho recente"
    assert channel["segmentCount"] == 1
    assert channel["droppedSegments"] >= 1
    assert channel["truncated"] is True
    # 2 partials + 1 disconnect final
    assert channel["totalEvents"] == 3


def test_injected_consolidator_receives_records(client, fake_engine, consolidator) -> None:
    fake_engine.script("registro injetado")
    with client.websocket_connect(
        "/ws/audio/sess-inj/mic-1?sourceType=microphone"
    ) as ws:
        ws.send_bytes(WINDOW)
        ws.receive_json()

    snapshot = consolidator.session_transcript("sess-inj")
    assert len(snapshot.channels) == 1
    assert snapshot.channels[0].text == "registro injetado"


def test_fake_engine_never_loads_model(client, fake_engine) -> None:
    fake_engine.script("sem gpu")
    with client.websocket_connect(
        "/ws/audio/sess-cpu/mic-1?sourceType=microphone"
    ) as ws:
        ws.send_bytes(WINDOW)
        ws.receive_json()
    get_transcript(client, "sess-cpu")
    assert fake_engine.loaded is False
