from __future__ import annotations

import re
import threading
import time
import unicodedata
from collections import defaultdict, deque
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass(frozen=True)
class EchoDecision:
    suppressed: bool
    similarity: float = 0.0
    matched_text: str | None = None


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", without_accents)).strip()


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    ratio = SequenceMatcher(None, left, right, autojunk=False).ratio()
    if left in right or right in left:
        containment = min(len(left), len(right)) / max(len(left), len(right))
        ratio = max(ratio, containment)
    return ratio


class TranscriptEchoSuppressor:
    """Suppress microphone text that duplicates recent system-audio text.

    Conference-camera microphones often physically hear their own speakers. The
    system channel remains the source of truth; a near-duplicate microphone event
    produced a few seconds later is dropped from the transcript feed.
    """

    def __init__(
        self,
        *,
        enabled: bool,
        window_seconds: float,
        similarity_threshold: float,
        min_chars: int,
    ) -> None:
        self._enabled = enabled
        self._window_seconds = window_seconds
        self._similarity_threshold = similarity_threshold
        self._min_chars = min_chars
        self._system_texts: dict[str, deque[tuple[float, str, str]]] = defaultdict(deque)
        self._lock = threading.Lock()

    def evaluate(
        self,
        *,
        session_id: str,
        source_type: str,
        text: str,
        now: float | None = None,
    ) -> EchoDecision:
        if not self._enabled:
            return EchoDecision(False)

        timestamp = time.monotonic() if now is None else now
        normalized = _normalize(text)
        if len(normalized) < self._min_chars:
            return EchoDecision(False)

        with self._lock:
            recent = self._system_texts[session_id]
            cutoff = timestamp - self._window_seconds
            while recent and recent[0][0] < cutoff:
                recent.popleft()

            if source_type == "system":
                recent.append((timestamp, normalized, text))
                return EchoDecision(False)

            if source_type != "microphone":
                return EchoDecision(False)

            best_score = 0.0
            best_text: str | None = None
            for _, candidate, original in recent:
                score = _similarity(normalized, candidate)
                if score > best_score:
                    best_score = score
                    best_text = original

            return EchoDecision(
                suppressed=best_score >= self._similarity_threshold,
                similarity=best_score,
                matched_text=best_text,
            )
