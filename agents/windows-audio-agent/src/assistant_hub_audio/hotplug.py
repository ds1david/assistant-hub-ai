"""In-process hot-plug notification listener for WASAPI/MMDevice endpoints.

Intentionally pure, like `endpoints.py`: never imports comtypes/pycaw, so it
can run (and be tested) on any platform. The Windows-specific provider lives
in `mmdevice_notifications.py` and is loaded lazily by
`get_notification_provider`, mirroring `endpoints.get_endpoint_provider`.

Instantiated once per channel worker process (ADR-0007/P6) - never in the
supervisor - so a notification for one channel's endpoint never crosses into
another channel's isolated process.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from dataclasses import dataclass
from typing import Callable, Literal, Protocol

LOGGER = logging.getLogger(__name__)

HotplugEventType = Literal["arrived", "removed", "state_changed"]

# Absorbs driver bounce (FR-005) without perceptibly delaying real detection -
# well under the up-to-10s generic reconnect backoff this feature replaces.
_DEBOUNCE_SECONDS = 0.3


@dataclass(frozen=True)
class HotplugEvent:
    endpoint_id: str
    event_type: HotplugEventType
    timestamp: float

    def __post_init__(self) -> None:
        if not self.endpoint_id:
            raise ValueError("HotplugEvent.endpoint_id must not be empty")


class NotificationProvider(Protocol):
    def subscribe(self, on_event: Callable[[HotplugEvent], None]) -> None:
        """Register `on_event`. Called once per listener."""
        ...

    def close(self) -> None:
        """Release native resources. Idempotent."""
        ...


class NullNotificationProvider:
    """Fallback provider for non-Windows platforms or COM registration failures."""

    def subscribe(self, on_event: Callable[[HotplugEvent], None]) -> None:
        return None

    def close(self) -> None:
        return None


def get_notification_provider() -> NotificationProvider:
    if sys.platform != "win32":
        return NullNotificationProvider()
    try:
        from .mmdevice_notifications import MMDeviceNotificationProvider

        return MMDeviceNotificationProvider()
    except Exception as exc:  # noqa: BLE001 - COM/import failures must not break capture
        LOGGER.warning(
            "MMDevice notification provider unavailable; hot-plug detection disabled: %s", exc
        )
        return NullNotificationProvider()


def _clock() -> float:
    return time.monotonic()


class ChannelHotplugSignal:
    """Coordinates the native listener callback (a foreign thread) with the
    capture loop in `capture.py`, for one channel.

    `state_changed` is folded into `removed` (spec.md Edge Cases): an
    endpoint transitioning to `disabled`/`unplugged`/`notpresent` without
    enumerating as an explicit removal must still interrupt an active
    capture the same way an explicit removal does.
    """

    def __init__(self, configured_endpoint_id: str | None) -> None:
        self.configured_endpoint_id = configured_endpoint_id
        self.removed = threading.Event()
        self.arrived = threading.Event()
        self._last_event_at: dict[str, float] = {}

    def handle_event(self, event: HotplugEvent) -> None:
        if self.configured_endpoint_id is None:
            return
        if event.endpoint_id.casefold() != self.configured_endpoint_id.casefold():
            return

        reaction = "removed" if event.event_type in ("removed", "state_changed") else "arrived"

        now = _clock()
        last = self._last_event_at.get(reaction)
        if last is not None and (now - last) < _DEBOUNCE_SECONDS:
            return
        self._last_event_at[reaction] = now

        if reaction == "removed":
            self.removed.set()
        else:
            self.arrived.set()


class HotplugListener:
    """Wires a `NotificationProvider` to a channel's `ChannelHotplugSignal`."""

    def __init__(self, provider: NotificationProvider, signal: ChannelHotplugSignal) -> None:
        self._provider = provider
        self.signal = signal
        self._provider.subscribe(self.signal.handle_event)

    def close(self) -> None:
        self._provider.close()
