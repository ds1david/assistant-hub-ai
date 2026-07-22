from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from app.main import create_app
from app.metrics import LatencyMetricsRegistry
from conftest import FakeTranscriptionEngine, make_test_settings

SAMPLE_RATE = 16_000
REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "contracts" / "transcript-event.v2.schema.json"
VALIDATOR = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def sine_pcm16(seconds: float, frequency: float = 440.0) -> bytes:
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    return (np.sin(2 * np.pi * frequency * t) * 0.3 * 32767).astype(np.int16).tobytes()


def make_adaptive_settings(**overrides):
    values = dict(
        whisper_window_seconds=0.5,
        whisper_overlap_seconds=0.1,
        whisper_min_audio_seconds=0.05,
        echo_suppression_enabled=False,
        adaptive_window_enabled=True,
        adaptive_window_min_seconds=0.2,
        adaptive_window_latency_high_ms=100,
        adaptive_window_latency_low_ms=20,
        adaptive_window_step_seconds=0.1,
        adaptive_window_stable_evaluations=1,
        adaptive_window_min_samples=5,
    )
    values.update(overrides)
    return make_test_settings(**values)


def prepopulate_high_latency(
    registry: LatencyMetricsRegistry,
    *,
    session_id: str,
    channel_id: str,
    count: int = 20,
    latency_ms: int = 2000,
) -> None:
    for _ in range(count):
        registry.record_transcription(
            session_id=session_id,
            channel_id=channel_id,
            source_type="microphone",
            label="Headset",
            latency_ms=latency_ms,
        )


# --- User Story 1: janela encolhe de ponta a ponta --------------------------


def test_window_shrinks_end_to_end_when_flag_enabled(
    fake_engine: FakeTranscriptionEngine,
) -> None:
    settings = make_adaptive_settings()
    registry = LatencyMetricsRegistry()
    prepopulate_high_latency(registry, session_id="sess-shrink", channel_id="mic-1")

    app = create_app(settings=settings, engine=fake_engine, metrics_registry=registry)
    client = TestClient(app)

    fake_engine.script("primeira janela", "segunda janela")
    with client.websocket_connect(
        "/ws/audio/sess-shrink/mic-1?sourceType=microphone"
    ) as ws:
        # Janela cheia (0.5s) — primeira transcrição usa o tamanho estático original;
        # a avaliação da política (após o registro) já encolhe a janela para 0.4s
        # (adaptive_window_stable_evaluations=1, p95 dominado pelas amostras pré-populadas).
        ws.send_bytes(sine_pcm16(0.5))
        event1 = ws.receive_json()
        assert event1["audioSeconds"] == pytest.approx(0.5, abs=1e-3)

        # 0.1s de overlap já fica no buffer; bastam mais 0.3s para fechar os 0.4s da
        # nova janela — se a janela não tivesse encolhido, isso não seria suficiente.
        ws.send_bytes(sine_pcm16(0.3))
        event2 = ws.receive_json()
        assert event2["text"] == "segunda janela"
        assert event2["audioSeconds"] == pytest.approx(0.4, abs=1e-3)


def test_window_stays_static_end_to_end_when_flag_disabled(
    fake_engine: FakeTranscriptionEngine,
) -> None:
    settings = make_adaptive_settings(adaptive_window_enabled=False)
    registry = LatencyMetricsRegistry()
    prepopulate_high_latency(registry, session_id="sess-static", channel_id="mic-1")

    app = create_app(settings=settings, engine=fake_engine, metrics_registry=registry)
    client = TestClient(app)

    fake_engine.script("primeira janela", "segunda janela")
    with client.websocket_connect(
        "/ws/audio/sess-static/mic-1?sourceType=microphone"
    ) as ws:
        ws.send_bytes(sine_pcm16(0.5))
        event1 = ws.receive_json()
        assert event1["audioSeconds"] == pytest.approx(0.5, abs=1e-3)

        # Com a flag desabilitada, mesmo com métricas de latência alta já
        # registradas para o canal, a janela continua exigindo 0.4s adicionais
        # (0.5s - 0.1s de overlap) — comportamento idêntico ao pré-SF-022 (SC-007).
        ws.send_bytes(sine_pcm16(0.4))
        event2 = ws.receive_json()
        assert event2["text"] == "segunda janela"
        assert event2["audioSeconds"] == pytest.approx(0.5, abs=1e-3)


# --- User Story 3: isolamento, contrato inalterado e observabilidade -------


def test_two_channels_same_session_converge_independently(
    fake_engine: FakeTranscriptionEngine,
) -> None:
    settings = make_adaptive_settings()
    registry = LatencyMetricsRegistry()
    prepopulate_high_latency(
        registry, session_id="sess-iso", channel_id="mic-1", latency_ms=2000
    )
    prepopulate_high_latency(
        registry, session_id="sess-iso", channel_id="system-main", latency_ms=50
    )

    app = create_app(settings=settings, engine=fake_engine, metrics_registry=registry)
    client = TestClient(app)

    fake_engine.script("canal degradado 1", "canal degradado 2", "canal saudavel 1", "canal saudavel 2")
    with client.websocket_connect(
        "/ws/audio/sess-iso/mic-1?sourceType=microphone"
    ) as mic_ws, client.websocket_connect(
        "/ws/audio/sess-iso/system-main?sourceType=system"
    ) as system_ws:
        # Canal degradado (p95 alto pré-populado): encolhe para 0.4s.
        mic_ws.send_bytes(sine_pcm16(0.5))
        mic_event1 = mic_ws.receive_json()
        assert mic_event1["audioSeconds"] == pytest.approx(0.5, abs=1e-3)
        mic_ws.send_bytes(sine_pcm16(0.3))
        mic_event2 = mic_ws.receive_json()
        assert mic_event2["audioSeconds"] == pytest.approx(0.4, abs=1e-3)

        # Canal saudável (p95 dentro da faixa saudável): permanece em 0.5s, sem
        # nenhuma influência do encolhimento do canal "mic-1" da mesma sessão.
        system_ws.send_bytes(sine_pcm16(0.5))
        system_event1 = system_ws.receive_json()
        assert system_event1["audioSeconds"] == pytest.approx(0.5, abs=1e-3)
        system_ws.send_bytes(sine_pcm16(0.4))
        system_event2 = system_ws.receive_json()
        assert system_event2["audioSeconds"] == pytest.approx(0.5, abs=1e-3)


def test_adjusted_window_event_still_matches_contract_v2(
    fake_engine: FakeTranscriptionEngine,
) -> None:
    settings = make_adaptive_settings()
    registry = LatencyMetricsRegistry()
    prepopulate_high_latency(registry, session_id="sess-contract", channel_id="mic-1")

    app = create_app(settings=settings, engine=fake_engine, metrics_registry=registry)
    client = TestClient(app)

    fake_engine.script("primeira janela", "janela ajustada")
    with client.websocket_connect(
        "/ws/audio/sess-contract/mic-1?sourceType=microphone&deviceIndex=2&deviceName=Microfone"
    ) as ws:
        ws.send_bytes(sine_pcm16(0.5))
        ws.receive_json()
        # Este evento já foi gerado com a janela encolhida (0.4s).
        ws.send_bytes(sine_pcm16(0.3))
        adjusted_event = ws.receive_json()

    VALIDATOR.validate(adjusted_event)
    assert adjusted_event["audioSeconds"] == pytest.approx(0.4, abs=1e-3)
    # Nenhum campo novo relacionado ao tamanho de janela vaza para o evento (FR-006).
    assert "windowMs" not in adjusted_event
    assert "windowSeconds" not in adjusted_event


def test_metrics_endpoint_reports_applied_window(
    fake_engine: FakeTranscriptionEngine,
) -> None:
    settings = make_adaptive_settings()
    registry = LatencyMetricsRegistry()
    prepopulate_high_latency(registry, session_id="sess-metrics", channel_id="mic-1")

    app = create_app(settings=settings, engine=fake_engine, metrics_registry=registry)
    client = TestClient(app)

    fake_engine.script("primeira janela", "segunda janela")
    with client.websocket_connect(
        "/ws/audio/sess-metrics/mic-1?sourceType=microphone"
    ) as ws:
        ws.send_bytes(sine_pcm16(0.5))
        ws.receive_json()
        ws.send_bytes(sine_pcm16(0.3))
        ws.receive_json()

    response = client.get("/v1/sessions/sess-metrics/metrics")
    assert response.status_code == 200
    channel = next(
        c for c in response.json()["channels"] if c["channelId"] == "mic-1"
    )
    # p95 continua dominado pelas amostras pré-populadas após os dois eventos, então
    # a política já reavaliou e encolheu mais uma vez (0.4s -> 0.3s) logo após o
    # segundo evento — windowMs reflete esse último valor efetivamente aplicado.
    assert channel["windowMs"] == pytest.approx(300, abs=1)


def test_metrics_endpoint_window_ms_is_null_when_flag_disabled(
    fake_engine: FakeTranscriptionEngine,
) -> None:
    settings = make_adaptive_settings(adaptive_window_enabled=False)
    registry = LatencyMetricsRegistry()
    prepopulate_high_latency(registry, session_id="sess-metrics-off", channel_id="mic-1")

    app = create_app(settings=settings, engine=fake_engine, metrics_registry=registry)
    client = TestClient(app)

    fake_engine.script("primeira janela")
    with client.websocket_connect(
        "/ws/audio/sess-metrics-off/mic-1?sourceType=microphone"
    ) as ws:
        ws.send_bytes(sine_pcm16(0.5))
        ws.receive_json()

    response = client.get("/v1/sessions/sess-metrics-off/metrics")
    channel = next(
        c for c in response.json()["channels"] if c["channelId"] == "mic-1"
    )
    assert channel["windowMs"] is None
