from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class ChannelTranscriptSnapshot:
    session_id: str
    channel_id: str
    source_type: str
    label: str
    text: str
    segment_count: int
    total_events: int
    duplicate_words_removed: int
    dropped_segments: int
    truncated: bool
    first_event_at: datetime | None
    last_event_at: datetime | None


@dataclass(frozen=True)
class SessionTranscriptSnapshot:
    session_id: str
    generated_at: datetime
    channels: tuple[ChannelTranscriptSnapshot, ...]


@dataclass
class _ChannelTranscript:
    segments: deque
    tail: list[str] = field(default_factory=list)
    source_type: str = "unknown"
    label: str = ""
    total_events: int = 0
    duplicate_words_removed: int = 0
    dropped_segments: int = 0
    first_event_at: datetime | None = None
    last_event_at: datetime | None = None
    last_touched: float = 0.0


def _overlap_words(tail: list[str], words: list[str]) -> int:
    # Maior sufixo do texto consolidado igual ao prefixo do texto novo,
    # comparando palavra a palavra em minúsculas. Sem fuzzy: um algoritmo
    # conservador preserva fala legítima parecida em vez de apagá-la.
    for size in range(min(len(tail), len(words)), 0, -1):
        if tail[-size:] == words[:size]:
            return size
    return 0


class TranscriptConsolidationRegistry:
    """Texto consolidado por (sessão, canal), inteiramente em memória.

    Cada janela do Whisper reprocessa a cauda de overlap da anterior, então as
    palavras da borda chegam duplicadas. A consolidação anexa apenas a parte
    não repetida, comparando o fim do texto do canal com o início do texto
    novo. A comparação normaliza somente minúsculas e espaços; o texto
    original é preservado para exibição. Canais nunca são comparados entre si.
    Escrita O(1) sob lock de thread, sem awaits; leitura via snapshot imutável.
    """

    def __init__(
        self,
        max_segments_per_channel: int = 256,
        max_channels: int = 64,
        overlap_tail_words: int = 12,
    ) -> None:
        if max_segments_per_channel < 1:
            raise ValueError("max_segments_per_channel must be >= 1")
        if max_channels < 1:
            raise ValueError("max_channels must be >= 1")
        if overlap_tail_words < 1:
            raise ValueError("overlap_tail_words must be >= 1")
        self._max_segments = max_segments_per_channel
        self._max_channels = max_channels
        self._tail_words = overlap_tail_words
        self._channels: dict[tuple[str, str], _ChannelTranscript] = {}
        self._lock = threading.Lock()

    @property
    def max_segments_per_channel(self) -> int:
        return self._max_segments

    def ingest(
        self,
        *,
        session_id: str,
        channel_id: str,
        source_type: str,
        label: str,
        text: str,
        occurred_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or datetime.now(timezone.utc)
        originals = text.split()
        normalized = [word.casefold() for word in originals]

        with self._lock:
            channel = self._get_or_create(session_id, channel_id)
            channel.source_type = source_type
            channel.label = label
            channel.total_events += 1
            channel.first_event_at = channel.first_event_at or timestamp
            channel.last_event_at = timestamp
            channel.last_touched = time.monotonic()

            overlap = _overlap_words(channel.tail, normalized)
            channel.duplicate_words_removed += overlap
            kept = originals[overlap:]
            if not kept:
                # Duplicata completa: a janela inteira já está no fim do canal.
                return

            if len(channel.segments) == channel.segments.maxlen:
                channel.dropped_segments += 1
            channel.segments.append(" ".join(kept))
            channel.tail = (channel.tail + normalized[overlap:])[-self._tail_words :]

    def session_transcript(self, session_id: str) -> SessionTranscriptSnapshot:
        with self._lock:
            copied = [
                (
                    channel_id,
                    list(channel.segments),
                    channel.source_type,
                    channel.label,
                    channel.total_events,
                    channel.duplicate_words_removed,
                    channel.dropped_segments,
                    channel.first_event_at,
                    channel.last_event_at,
                )
                for (owner, channel_id), channel in self._channels.items()
                if owner == session_id
            ]

        channels = tuple(
            ChannelTranscriptSnapshot(
                session_id=session_id,
                channel_id=channel_id,
                source_type=source_type,
                label=label,
                text=" ".join(segments),
                segment_count=len(segments),
                total_events=total_events,
                duplicate_words_removed=duplicates,
                dropped_segments=dropped,
                truncated=dropped > 0,
                first_event_at=first_event_at,
                last_event_at=last_event_at,
            )
            for (
                channel_id,
                segments,
                source_type,
                label,
                total_events,
                duplicates,
                dropped,
                first_event_at,
                last_event_at,
            ) in sorted(copied, key=lambda item: item[0])
        )
        return SessionTranscriptSnapshot(
            session_id=session_id,
            generated_at=datetime.now(timezone.utc),
            channels=channels,
        )

    def _get_or_create(self, session_id: str, channel_id: str) -> _ChannelTranscript:
        key = (session_id, channel_id)
        channel = self._channels.get(key)
        if channel is None:
            if len(self._channels) >= self._max_channels:
                oldest = min(self._channels, key=lambda k: self._channels[k].last_touched)
                del self._channels[oldest]
            channel = _ChannelTranscript(segments=deque(maxlen=self._max_segments))
            self._channels[key] = channel
        return channel
