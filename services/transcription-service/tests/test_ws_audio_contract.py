from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator
from starlette.websockets import WebSocketDisconnect

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "contracts" / "transcript-event.v2.schema.json"
VALIDATOR = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))

SAMPLE_RATE = 16_000


def sine_pcm16(seconds: float, frequency: float = 440.0) -> bytes:
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    return (np.sin(2 * np.pi * frequency * t) * 0.3 * 32767).astype(np.int16).tobytes()


# Exactly one transcription window under the test settings (0.5 s).
WINDOW = sine_pcm16(0.5)


def test_rejects_invalid_source_type(client) -> None:
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect("/ws/audio/sess-a/mic-1?sourceType=loopback"):
            pass
    assert excinfo.value.code == 1008


def test_rejects_missing_source_type(client) -> None:
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect("/ws/audio/sess-a/mic-1"):
            pass
    assert excinfo.value.code == 1008


def test_rejects_non_integer_device_index(client) -> None:
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(
            "/ws/audio/sess-b/mic-1?sourceType=microphone&deviceIndex=abc"
        ):
            pass
    assert excinfo.value.code == 1008


def test_system_channel_event_matches_contract_v2(client, fake_engine) -> None:
    fake_engine.script("ola do sistema")
    url = (
        "/ws/audio/sess-1/system-main"
        "?sourceType=system&label=Loopback%20Speakers&deviceIndex=7&deviceName=Alto-falantes"
    )
    with client.websocket_connect(url) as ws:
        ws.send_bytes(WINDOW)
        event = ws.receive_json()

    VALIDATOR.validate(event)
    assert event["type"] == "transcript.partial.v2"
    assert event["sessionId"] == "sess-1"
    assert event["channelId"] == "system-main"
    assert event["label"] == "Loopback Speakers"
    assert event["sourceType"] == "system"
    assert event["device"] == {"index": 7, "name": "Alto-falantes", "endpointId": None}
    assert event["text"] == "ola do sistema"
    assert event["droppedWindows"] == 0


def test_microphone_channel_event_matches_contract_v2(client, fake_engine) -> None:
    fake_engine.script("ola do microfone")
    endpoint_id = "{0.0.1.00000000}.{a1b2c3d4-1111-2222-3333-444444444444}"
    url = (
        "/ws/audio/sess-mic/mic-1"
        "?sourceType=microphone&label=Headset%20Mic&deviceIndex=2&deviceName=Microfone%20USB"
        "&endpointId=%7B0.0.1.00000000%7D.%7Ba1b2c3d4-1111-2222-3333-444444444444%7D"
    )
    with client.websocket_connect(url) as ws:
        ws.send_bytes(WINDOW)
        event = ws.receive_json()

    VALIDATOR.validate(event)
    assert event["type"] == "transcript.partial.v2"
    assert event["sessionId"] == "sess-mic"
    assert event["channelId"] == "mic-1"
    assert event["label"] == "Headset Mic"
    assert event["sourceType"] == "microphone"
    assert event["device"] == {"index": 2, "name": "Microfone USB", "endpointId": endpoint_id}
    assert event["text"] == "ola do microfone"
    assert event["droppedWindows"] == 0


def test_blank_endpoint_id_query_param_normalizes_to_null(client, fake_engine) -> None:
    """An empty ?endpointId= (e.g. Linux/legacy agents) must map to device.endpointId
    null, not the literal empty string, so it stays semantically "unknown" (CHK015)."""
    fake_engine.script("sem endpoint")
    url = (
        "/ws/audio/sess-blank/mic-1"
        "?sourceType=microphone&label=Mic&deviceIndex=2&deviceName=Microfone&endpointId="
    )
    with client.websocket_connect(url) as ws:
        ws.send_bytes(WINDOW)
        event = ws.receive_json()

    VALIDATOR.validate(event)
    assert event["device"] == {"index": 2, "name": "Microfone", "endpointId": None}


def test_simultaneous_microphone_and_system_channels(client, fake_engine) -> None:
    fake_engine.script("audio da reuniao", "pergunta do usuario")
    system_url = (
        "/ws/audio/sess-multi/system-main"
        "?sourceType=system&label=Speakers&deviceIndex=7&deviceName=Alto-falantes"
    )
    microphone_url = (
        "/ws/audio/sess-multi/mic-1"
        "?sourceType=microphone&label=Headset&deviceIndex=2&deviceName=Microfone"
    )
    with client.websocket_connect(system_url) as system_ws:
        with client.websocket_connect(microphone_url) as mic_ws:
            system_ws.send_bytes(WINDOW)
            system_event = system_ws.receive_json()
            mic_ws.send_bytes(WINDOW)
            mic_event = mic_ws.receive_json()

    VALIDATOR.validate(system_event)
    VALIDATOR.validate(mic_event)
    assert system_event["sessionId"] == mic_event["sessionId"] == "sess-multi"
    assert system_event["channelId"] == "system-main"
    assert system_event["sourceType"] == "system"
    assert system_event["device"] == {"index": 7, "name": "Alto-falantes", "endpointId": None}
    assert system_event["text"] == "audio da reuniao"
    assert mic_event["channelId"] == "mic-1"
    assert mic_event["sourceType"] == "microphone"
    assert mic_event["device"] == {"index": 2, "name": "Microfone", "endpointId": None}
    assert mic_event["text"] == "pergunta do usuario"


def test_event_reaches_transcript_feed(client, fake_engine) -> None:
    fake_engine.script("evento no feed")
    with client.websocket_connect("/ws/transcripts") as feed:
        with client.websocket_connect(
            "/ws/audio/sess-2/system-main?sourceType=system"
        ) as ws:
            ws.send_bytes(WINDOW)
            direct = ws.receive_json()
        feed_event = feed.receive_json()

    VALIDATOR.validate(feed_event)
    assert feed_event == direct


def test_microphone_duplicate_of_system_is_suppressed(client, fake_engine) -> None:
    fake_engine.script(
        "reuniao comeca as dez",
        "reuniao comeca as dez",
        "fala local diferente agora",
    )
    with client.websocket_connect(
        "/ws/audio/sess-echo/system-main?sourceType=system"
    ) as system_ws:
        system_ws.send_bytes(WINDOW)
        assert system_ws.receive_json()["text"] == "reuniao comeca as dez"

        with client.websocket_connect(
            "/ws/audio/sess-echo/mic-1?sourceType=microphone"
        ) as mic_ws:
            # First window duplicates the system transcript and must be
            # suppressed; the second is distinct local speech, so the first
            # event to arrive must be the second text.
            mic_ws.send_bytes(WINDOW)
            mic_ws.send_bytes(WINDOW)
            mic_event = mic_ws.receive_json()

    VALIDATOR.validate(mic_event)
    assert mic_event["text"] == "fala local diferente agora"
    assert mic_event["sourceType"] == "microphone"


def test_contract_fails_when_metadata_is_lost(client, fake_engine) -> None:
    fake_engine.script("evento completo")
    with client.websocket_connect(
        "/ws/audio/sess-meta/mic-1?sourceType=microphone&deviceIndex=3&deviceName=Headset"
    ) as ws:
        ws.send_bytes(WINDOW)
        event = ws.receive_json()

    VALIDATOR.validate(event)
    for metadata_field in ("sessionId", "channelId", "sourceType", "device", "label"):
        stripped = {key: value for key, value in event.items() if key != metadata_field}
        assert not VALIDATOR.is_valid(stripped), f"schema aceitou evento sem {metadata_field}"


def test_microphone_local_speech_is_delivered(client, fake_engine) -> None:
    fake_engine.script("contexto vindo do sistema", "assunto totalmente diferente")
    with client.websocket_connect(
        "/ws/audio/sess-local/system-main?sourceType=system"
    ) as system_ws:
        system_ws.send_bytes(WINDOW)
        system_ws.receive_json()

        with client.websocket_connect(
            "/ws/audio/sess-local/mic-1?sourceType=microphone"
        ) as mic_ws:
            mic_ws.send_bytes(WINDOW)
            mic_event = mic_ws.receive_json()

    VALIDATOR.validate(mic_event)
    assert mic_event["text"] == "assunto totalmente diferente"
