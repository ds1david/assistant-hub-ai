from __future__ import annotations

import pytest

from app.adaptive_window import AdaptiveWindowChannel
from conftest import make_test_settings


def make_channel(**overrides) -> AdaptiveWindowChannel:
    values = dict(
        whisper_window_seconds=3.2,
        whisper_overlap_seconds=0.8,
        adaptive_window_enabled=True,
        adaptive_window_min_seconds=1.6,
        adaptive_window_latency_high_ms=1600,
        adaptive_window_latency_low_ms=600,
        adaptive_window_step_seconds=0.4,
        adaptive_window_stable_evaluations=3,
        adaptive_window_min_samples=5,
    )
    values.update(overrides)
    settings = make_test_settings(**values)
    return AdaptiveWindowChannel(settings)


# --- User Story 1: janela encolhe quando a latência sobe -------------------


def test_stable_healthy_p95_no_change() -> None:
    channel = make_channel()
    for _ in range(5):
        window = channel.evaluate(p95_ms=1000, sample_count=10)
        assert window == pytest.approx(3.2)


def test_single_spike_does_not_shrink() -> None:
    channel = make_channel()
    window = channel.evaluate(p95_ms=2000, sample_count=10)
    assert window == pytest.approx(3.2)


def test_sustained_high_latency_shrinks_after_confirmation() -> None:
    channel = make_channel()

    # adaptive_window_stable_evaluations=3: as duas primeiras avaliações apenas
    # acumulam confirmação, a janela só muda na terceira.
    assert channel.evaluate(p95_ms=2000, sample_count=10) == pytest.approx(3.2)
    assert channel.evaluate(p95_ms=2000, sample_count=10) == pytest.approx(3.2)
    assert channel.evaluate(p95_ms=2000, sample_count=10) == pytest.approx(2.8)

    # Continuação na mesma direção não exige nova confirmação.
    assert channel.evaluate(p95_ms=2000, sample_count=10) == pytest.approx(2.4)
    assert channel.evaluate(p95_ms=2000, sample_count=10) == pytest.approx(2.0)


def test_floor_respected_and_observable() -> None:
    channel = make_channel()
    for _ in range(20):
        channel.evaluate(p95_ms=2000, sample_count=10)

    assert channel.window_seconds == pytest.approx(1.6)
    assert channel.at_floor is True

    # Latência ainda alta no piso: nenhuma redução adicional é tentada.
    assert channel.evaluate(p95_ms=2000, sample_count=10) == pytest.approx(1.6)
    assert channel.at_floor is True


def test_insufficient_samples_no_change() -> None:
    channel = make_channel()
    for _ in range(5):
        window = channel.evaluate(p95_ms=2000, sample_count=2)
        assert window == pytest.approx(3.2)


def test_missing_p95_no_change() -> None:
    channel = make_channel()
    for _ in range(5):
        window = channel.evaluate(p95_ms=None, sample_count=10)
        assert window == pytest.approx(3.2)


def test_insufficient_samples_reset_pending_confirmation() -> None:
    channel = make_channel()
    # Duas avaliações com sinal alto começam a acumular confirmação...
    assert channel.evaluate(p95_ms=2000, sample_count=10) == pytest.approx(3.2)
    assert channel.evaluate(p95_ms=2000, sample_count=10) == pytest.approx(3.2)
    # ...uma avaliação sem amostras suficientes zera a confirmação pendente
    # (research.md §3: dado insuficiente não deve "contar" para nenhuma direção)...
    assert channel.evaluate(p95_ms=2000, sample_count=1) == pytest.approx(3.2)
    # ...então são necessárias 3 avaliações novas e consecutivas para confirmar.
    assert channel.evaluate(p95_ms=2000, sample_count=10) == pytest.approx(3.2)
    assert channel.evaluate(p95_ms=2000, sample_count=10) == pytest.approx(3.2)
    assert channel.evaluate(p95_ms=2000, sample_count=10) == pytest.approx(2.8)


def test_min_window_must_exceed_overlap() -> None:
    with pytest.raises(ValueError):
        make_channel(adaptive_window_min_seconds=0.5, whisper_overlap_seconds=0.8)


# --- User Story 2: janela volta a crescer quando a latência normaliza ------


def shrink_once(channel: AdaptiveWindowChannel) -> None:
    for _ in range(3):
        channel.evaluate(p95_ms=2000, sample_count=10)


def test_recovery_after_shrink_grows_toward_default() -> None:
    channel = make_channel()
    shrink_once(channel)
    assert channel.window_seconds == pytest.approx(2.8)

    # p95 saudável e baixo por 3 avaliações consecutivas confirma a reversão e
    # aplica um passo controlado de volta em direção ao padrão (3.2s).
    assert channel.evaluate(p95_ms=200, sample_count=10) == pytest.approx(2.8)
    assert channel.evaluate(p95_ms=200, sample_count=10) == pytest.approx(2.8)
    assert channel.evaluate(p95_ms=200, sample_count=10) == pytest.approx(3.2)


def test_recovery_never_exceeds_default() -> None:
    channel = make_channel()
    shrink_once(channel)
    for _ in range(3):
        channel.evaluate(p95_ms=200, sample_count=10)
    assert channel.window_seconds == pytest.approx(3.2)

    # Já no padrão/teto: p95 continua baixo, mas nada cresce além dele.
    for _ in range(5):
        assert channel.evaluate(p95_ms=200, sample_count=10) == pytest.approx(3.2)


def test_oscillating_latency_does_not_flip_direction_every_evaluation() -> None:
    channel = make_channel()
    shrink_once(channel)
    assert channel.window_seconds == pytest.approx(2.8)

    # p95 oscila entre "saudável baixo" (200, sugeriria crescer) e "zona saudável
    # intermediária" (700, nem alto nem baixo o bastante) a cada avaliação — nunca
    # três leituras "up" consecutivas, então a confirmação nunca fecha e a janela
    # permanece parada, sem reverter de direção a cada avaliação.
    for p95 in (200, 700, 200, 700, 200):
        assert channel.evaluate(p95_ms=p95, sample_count=10) == pytest.approx(2.8)
