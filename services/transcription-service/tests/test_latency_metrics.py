from __future__ import annotations

import threading

from app.metrics import LatencyMetricsRegistry


def record_series(
    registry: LatencyMetricsRegistry,
    values: list[int],
    *,
    session_id: str = "sess",
    channel_id: str = "mic-1",
) -> None:
    for value in values:
        registry.record_transcription(
            session_id=session_id,
            channel_id=channel_id,
            source_type="microphone",
            label="Headset",
            latency_ms=value,
        )


def only_channel(registry: LatencyMetricsRegistry, session_id: str = "sess"):
    snapshot = registry.session_snapshot(session_id)
    assert len(snapshot.channels) == 1
    return snapshot.channels[0]


def test_percentiles_over_uniform_distribution() -> None:
    registry = LatencyMetricsRegistry()
    record_series(registry, list(range(1, 101)))

    channel = only_channel(registry)
    assert channel.sample_count == 100
    assert channel.p50_ms == 50
    assert channel.p95_ms == 95
    assert channel.min_ms == 1
    assert channel.max_ms == 100
    assert channel.avg_ms == 50


def test_percentiles_with_single_sample() -> None:
    registry = LatencyMetricsRegistry()
    record_series(registry, [730])

    channel = only_channel(registry)
    assert channel.sample_count == 1
    assert channel.p50_ms == channel.p95_ms == 730


def test_percentiles_with_small_even_count() -> None:
    registry = LatencyMetricsRegistry()
    record_series(registry, [40, 10, 30, 20])

    channel = only_channel(registry)
    # Nearest-rank: p50 -> ceil(0.5 * 4) = 2º valor; p95 -> ceil(0.95 * 4) = 4º.
    assert channel.p50_ms == 20
    assert channel.p95_ms == 40


def test_retention_keeps_only_most_recent_samples() -> None:
    registry = LatencyMetricsRegistry(max_samples_per_channel=5)
    record_series(registry, list(range(1, 11)))

    channel = only_channel(registry)
    assert channel.sample_count == 5
    assert channel.min_ms == 6
    assert channel.max_ms == 10
    assert channel.p50_ms == 8
    # O contador cumulativo sobrevive à rotação do ring buffer.
    assert channel.total_events == 10


def test_sessions_are_isolated() -> None:
    registry = LatencyMetricsRegistry()
    record_series(registry, [100], session_id="sess-a")
    record_series(registry, [900, 950], session_id="sess-b")

    channel_a = only_channel(registry, "sess-a")
    channel_b = only_channel(registry, "sess-b")
    assert channel_a.sample_count == 1
    assert channel_a.p95_ms == 100
    assert channel_b.sample_count == 2
    assert channel_b.p95_ms == 950
    assert registry.session_snapshot("sess-desconhecida").channels == ()


def test_channels_are_isolated_within_session() -> None:
    registry = LatencyMetricsRegistry()
    record_series(registry, [100, 200], channel_id="mic-1")
    record_series(registry, [800], channel_id="system-main")
    registry.record_dropped_window(session_id="sess", channel_id="system-main")

    snapshot = registry.session_snapshot("sess")
    assert [channel.channel_id for channel in snapshot.channels] == ["mic-1", "system-main"]
    mic, system = snapshot.channels
    assert mic.sample_count == 2
    assert mic.dropped_windows == 0
    assert system.sample_count == 1
    assert system.dropped_windows == 1


def test_dropped_windows_do_not_create_samples() -> None:
    registry = LatencyMetricsRegistry()
    registry.record_dropped_window(session_id="sess", channel_id="mic-1")
    registry.record_dropped_window(session_id="sess", channel_id="mic-1")

    channel = only_channel(registry)
    assert channel.sample_count == 0
    assert channel.dropped_windows == 2
    assert channel.p50_ms is None
    assert channel.p95_ms is None
    assert channel.last_event_at is None


def test_least_recently_touched_channel_is_evicted() -> None:
    registry = LatencyMetricsRegistry(max_channels=2)
    record_series(registry, [10], channel_id="old")
    record_series(registry, [20], channel_id="kept")
    record_series(registry, [30], channel_id="new")

    snapshot = registry.session_snapshot("sess")
    assert [channel.channel_id for channel in snapshot.channels] == ["kept", "new"]


def test_concurrent_records_are_not_lost() -> None:
    registry = LatencyMetricsRegistry()
    threads = [
        threading.Thread(target=record_series, args=(registry, [worker] * 50))
        for worker in range(8)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    channel = only_channel(registry)
    assert channel.total_events == 400
    assert channel.sample_count == 400
