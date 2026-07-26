"""Pure utterance finalization state machine (issue #55).

Closes an open utterance after N windows without new text (idle), on max-open
timeout, or on disconnect residual — emitting at most one final per utterance.

Callers should invoke ``on_tick`` (or rely on ``on_no_result``) for max-open
before feeding new text so a timeout final is published before a new partial.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

ActionKind = Literal["none", "emit_partial", "emit_final"]
FinalReason = Literal["idle", "max_open", "disconnect"]
UtteranceState = Literal["idle", "open"]


@dataclass(frozen=True)
class FinalizerAction:
    kind: ActionKind
    text: str = ""
    reason: FinalReason | None = None


NONE = FinalizerAction(kind="none")


class UtteranceFinalizer:
    """Per-channel utterance open/close policy.

    Clock is injectible via ``now`` (monotonic seconds) for deterministic tests.
    """

    def __init__(
        self,
        *,
        idle_windows: int = 1,
        max_open_seconds: float = 45.0,
    ) -> None:
        if idle_windows < 1:
            raise ValueError("idle_windows must be >= 1")
        if max_open_seconds <= 0:
            raise ValueError("max_open_seconds must be > 0")
        self._idle_threshold = idle_windows
        self._max_open_seconds = max_open_seconds

        self.state: UtteranceState = "idle"
        self.last_text: str = ""
        self.partial_count: int = 0
        self.idle_windows: int = 0
        self.opened_at: float | None = None
        self.final_emitted: bool = False

        # Counters for ops (no transcript text).
        self.finals_emitted: int = 0
        self.idle_closes: int = 0
        self.max_open_closes: int = 0
        self.disconnect_closes: int = 0

    def _now(self, now: float | None) -> float:
        return time.monotonic() if now is None else now

    def _reset_to_idle(self) -> None:
        self.state = "idle"
        self.last_text = ""
        self.partial_count = 0
        self.idle_windows = 0
        self.opened_at = None
        self.final_emitted = False

    def _close_final(self, reason: FinalReason) -> FinalizerAction:
        text = self.last_text.strip()
        if not text or self.final_emitted:
            self._reset_to_idle()
            return NONE
        self.final_emitted = True
        self.finals_emitted += 1
        if reason == "idle":
            self.idle_closes += 1
        elif reason == "max_open":
            self.max_open_closes += 1
        else:
            self.disconnect_closes += 1
        action = FinalizerAction(kind="emit_final", text=text, reason=reason)
        self._reset_to_idle()
        return action

    def _maybe_max_open(self, now: float) -> FinalizerAction | None:
        if self.state != "open" or self.opened_at is None:
            return None
        if (now - self.opened_at) < self._max_open_seconds:
            return None
        return self._close_final("max_open")

    def on_text(self, text: str, now: float | None = None) -> FinalizerAction:
        """Useful new text after echo-suppression. Opens or updates utterance."""
        cleaned = (text or "").strip()
        if not cleaned:
            return NONE
        now = self._now(now)

        if self.state == "idle":
            self.state = "open"
            self.last_text = cleaned
            self.partial_count = 1
            self.idle_windows = 0
            self.opened_at = now
            self.final_emitted = False
            return FinalizerAction(kind="emit_partial", text=cleaned)

        self.last_text = cleaned
        self.partial_count += 1
        self.idle_windows = 0
        return FinalizerAction(kind="emit_partial", text=cleaned)

    def on_no_result(self, now: float | None = None) -> FinalizerAction:
        """Window evaluated with no new useful text (None / empty / same)."""
        now = self._now(now)
        max_action = self._maybe_max_open(now)
        if max_action is not None:
            return max_action

        if self.state != "open":
            return NONE

        self.idle_windows += 1
        if self.idle_windows >= self._idle_threshold:
            return self._close_final("idle")
        return NONE

    def on_tick(self, now: float | None = None) -> FinalizerAction:
        """Periodic max-open check without a window evaluation."""
        return self._maybe_max_open(self._now(now)) or NONE

    def on_disconnect(
        self,
        residual_text: str | None = None,
        now: float | None = None,
    ) -> FinalizerAction:
        """Flush residual on WS disconnect without double-finalizing."""
        now = self._now(now)
        residual = (residual_text or "").strip()

        if residual:
            if self.state == "idle":
                self.state = "open"
                self.last_text = residual
                self.partial_count = 1
                self.idle_windows = 0
                self.opened_at = now
                self.final_emitted = False
                return self._close_final("disconnect")
            if residual != self.last_text:
                self.last_text = residual
                self.idle_windows = 0
            if not self.final_emitted and self.last_text.strip():
                return self._close_final("disconnect")
            return NONE

        if self.state == "open" and not self.final_emitted and self.last_text.strip():
            return self._close_final("disconnect")
        return NONE
