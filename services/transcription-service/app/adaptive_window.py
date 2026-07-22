from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Literal

from .config import Settings

Direction = Literal["down", "up", "stable"]


@dataclass
class AdaptiveWindowState:
    window_seconds: float
    active_direction: Direction = "stable"
    pending_direction: Literal["down", "up"] | None = None
    pending_count: int = 0


class AdaptiveWindowChannel:
    """Decide o tamanho da janela de captura/segmentação de um canal a partir do p95
    de latência (SF-016), com histerese e passo controlado (SF-022). Vive e morre com a
    conexão do canal — nunca persiste entre reconexões (ver spec.md Edge Cases).
    """

    def __init__(self, settings: Settings) -> None:
        if settings.adaptive_window_min_seconds <= settings.whisper_overlap_seconds:
            raise ValueError(
                "ADAPTIVE_WINDOW_MIN_SECONDS must be greater than WHISPER_OVERLAP_SECONDS"
            )
        self._settings = settings
        self._state = AdaptiveWindowState(window_seconds=settings.whisper_window_seconds)

    @property
    def window_seconds(self) -> float:
        return self._state.window_seconds

    @property
    def at_floor(self) -> bool:
        return self._state.window_seconds <= self._settings.adaptive_window_min_seconds

    def evaluate(self, *, p95_ms: int | None, sample_count: int) -> float:
        state = self._state
        settings = self._settings

        if p95_ms is None or sample_count < settings.adaptive_window_min_samples:
            state.pending_direction = None
            state.pending_count = 0
            return state.window_seconds

        if p95_ms > settings.adaptive_window_latency_high_ms and (
            state.window_seconds > settings.adaptive_window_min_seconds
        ):
            desired: Direction = "down"
        elif p95_ms < settings.adaptive_window_latency_low_ms and (
            state.window_seconds < settings.whisper_window_seconds
        ):
            desired = "up"
        else:
            desired = "stable"

        if desired == "stable":
            state.active_direction = "stable"
            state.pending_direction = None
            state.pending_count = 0
            return state.window_seconds

        if desired == state.active_direction:
            self._apply_step(desired)
            return state.window_seconds

        if state.pending_direction == desired:
            state.pending_count += 1
        else:
            state.pending_direction = desired
            state.pending_count = 1

        if state.pending_count >= settings.adaptive_window_stable_evaluations:
            state.active_direction = desired
            state.pending_direction = None
            state.pending_count = 0
            self._apply_step(desired)

        return state.window_seconds

    def _apply_step(self, direction: Literal["down", "up"]) -> None:
        state = self._state
        settings = self._settings
        step = settings.adaptive_window_step_seconds
        if direction == "down":
            state.window_seconds = max(
                settings.adaptive_window_min_seconds, state.window_seconds - step
            )
        else:
            state.window_seconds = min(
                settings.whisper_window_seconds, state.window_seconds + step
            )


class AdaptiveWindowRegistry:
    """Espelha, por app (não por conexão), o último valor de janela aplicado por
    canal — só para observabilidade via HTTP (FR-007). Não decide nada; quem decide
    é o `AdaptiveWindowChannel` de cada conexão, que chama `record()` a cada mudança.
    """

    def __init__(self, max_channels: int = 64) -> None:
        if max_channels < 1:
            raise ValueError("max_channels must be >= 1")
        self._max_channels = max_channels
        self._windows: dict[tuple[str, str], int] = {}
        self._touch_order: list[tuple[str, str]] = []
        self._lock = threading.Lock()

    def record(self, *, session_id: str, channel_id: str, window_seconds: float) -> None:
        key = (session_id, channel_id)
        with self._lock:
            if key not in self._windows and len(self._windows) >= self._max_channels:
                oldest = self._touch_order.pop(0)
                del self._windows[oldest]
            elif key in self._touch_order:
                self._touch_order.remove(key)
            self._windows[key] = round(window_seconds * 1000)
            self._touch_order.append(key)

    def window_ms(self, *, session_id: str, channel_id: str) -> int | None:
        with self._lock:
            return self._windows.get((session_id, channel_id))
