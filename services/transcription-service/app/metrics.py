from __future__ import annotations

import math
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ChannelLatencySnapshot:
    session_id: str
    channel_id: str
    source_type: str
    label: str
    sample_count: int
    p50_ms: int | None
    p95_ms: int | None
    min_ms: int | None
    max_ms: int | None
    avg_ms: int | None
    total_events: int
    dropped_windows: int
    last_event_at: datetime | None


@dataclass(frozen=True)
class SessionMetricsSnapshot:
    session_id: str
    generated_at: datetime
    channels: tuple[ChannelLatencySnapshot, ...]


@dataclass
class _ChannelStats:
    samples: deque
    source_type: str = "unknown"
    label: str = ""
    total_events: int = 0
    dropped_windows: int = 0
    last_event_at: datetime | None = None
    last_touched: float = 0.0


def _percentile(sorted_values: list[int], quantile: float) -> int:
    # Nearest-rank: o menor valor que cobre `quantile` das amostras.
    index = max(0, math.ceil(quantile * len(sorted_values)) - 1)
    return sorted_values[index]


class LatencyMetricsRegistry:
    """Latência de transcrição por (sessão, canal), inteiramente em memória.

    As amostras ficam em um ring buffer limitado por canal; os percentis são
    calculados apenas na leitura do snapshot. Os métodos de escrita são O(1) e
    protegidos por lock de thread sem awaits, então podem ser chamados tanto do
    event loop quanto de threads.
    """

    def __init__(self, max_samples_per_channel: int = 512, max_channels: int = 64) -> None:
        if max_samples_per_channel < 1:
            raise ValueError("max_samples_per_channel must be >= 1")
        if max_channels < 1:
            raise ValueError("max_channels must be >= 1")
        self._max_samples = max_samples_per_channel
        self._max_channels = max_channels
        self._channels: dict[tuple[str, str], _ChannelStats] = {}
        self._lock = threading.Lock()

    @property
    def max_samples_per_channel(self) -> int:
        return self._max_samples

    def record_transcription(
        self,
        *,
        session_id: str,
        channel_id: str,
        source_type: str,
        label: str,
        latency_ms: int,
    ) -> None:
        with self._lock:
            stats = self._get_or_create(session_id, channel_id)
            stats.source_type = source_type
            stats.label = label
            stats.samples.append(max(0, int(latency_ms)))
            stats.total_events += 1
            stats.last_event_at = datetime.now(timezone.utc)
            stats.last_touched = time.monotonic()

    def record_dropped_window(self, *, session_id: str, channel_id: str) -> None:
        with self._lock:
            stats = self._get_or_create(session_id, channel_id)
            stats.dropped_windows += 1
            stats.last_touched = time.monotonic()

    def session_snapshot(self, session_id: str) -> SessionMetricsSnapshot:
        with self._lock:
            copied = [
                (
                    channel_id,
                    list(stats.samples),
                    stats.source_type,
                    stats.label,
                    stats.total_events,
                    stats.dropped_windows,
                    stats.last_event_at,
                )
                for (owner, channel_id), stats in self._channels.items()
                if owner == session_id
            ]

        channels = []
        for channel_id, samples, source_type, label, total, dropped, last_event_at in sorted(
            copied, key=lambda item: item[0]
        ):
            ordered = sorted(samples)
            count = len(ordered)
            channels.append(
                ChannelLatencySnapshot(
                    session_id=session_id,
                    channel_id=channel_id,
                    source_type=source_type,
                    label=label,
                    sample_count=count,
                    p50_ms=_percentile(ordered, 0.50) if ordered else None,
                    p95_ms=_percentile(ordered, 0.95) if ordered else None,
                    min_ms=ordered[0] if ordered else None,
                    max_ms=ordered[-1] if ordered else None,
                    avg_ms=round(sum(ordered) / count) if ordered else None,
                    total_events=total,
                    dropped_windows=dropped,
                    last_event_at=last_event_at,
                )
            )
        return SessionMetricsSnapshot(
            session_id=session_id,
            generated_at=datetime.now(timezone.utc),
            channels=tuple(channels),
        )

    def _get_or_create(self, session_id: str, channel_id: str) -> _ChannelStats:
        key = (session_id, channel_id)
        stats = self._channels.get(key)
        if stats is None:
            if len(self._channels) >= self._max_channels:
                oldest = min(self._channels, key=lambda k: self._channels[k].last_touched)
                del self._channels[oldest]
            stats = _ChannelStats(samples=deque(maxlen=self._max_samples))
            self._channels[key] = stats
        return stats
