"""Lightweight prosody features for optional question-intonation scoring.

Runs only when PROSODY_ENABLED is true, on Final windows. Failures return None
so callers omit `prosody` without dropping the transcript event.
Must not log PCM samples or audio file paths (constitution P9).
"""

from __future__ import annotations

import logging
import math
import struct
from typing import Any

LOGGER = logging.getLogger(__name__)


def _pcm16_mono_to_floats(pcm: bytes) -> list[float]:
    if len(pcm) < 4 or len(pcm) % 2 != 0:
        return []
    n = len(pcm) // 2
    samples = struct.unpack(f"<{n}h", pcm)
    return [s / 32768.0 for s in samples]


def _frame_energies(samples: list[float], frame: int, hop: int) -> list[float]:
    if len(samples) < frame:
        return []
    energies: list[float] = []
    for start in range(0, len(samples) - frame + 1, hop):
        window = samples[start : start + frame]
        energies.append(math.sqrt(sum(x * x for x in window) / frame))
    return energies


def _autocorr_f0_hz(frame: list[float], sample_rate: int, fmin: float = 80.0, fmax: float = 400.0) -> float | None:
    """Very small autocorrelation pitch estimate for a single frame."""
    n = len(frame)
    if n < 32:
        return None
    mean = sum(frame) / n
    centered = [x - mean for x in frame]
    energy = sum(x * x for x in centered)
    if energy < 1e-8:
        return None
    min_lag = max(1, int(sample_rate / fmax))
    max_lag = min(n - 1, int(sample_rate / fmin))
    if min_lag >= max_lag:
        return None
    best_lag = 0
    best_corr = 0.0
    for lag in range(min_lag, max_lag + 1):
        corr = 0.0
        for i in range(n - lag):
            corr += centered[i] * centered[i + lag]
        corr /= energy
        if corr > best_corr:
            best_corr = corr
            best_lag = lag
    if best_lag <= 0 or best_corr < 0.25:
        return None
    return sample_rate / best_lag


def estimate_prosody(
    pcm: bytes,
    *,
    sample_rate: int = 16_000,
    end_window_ms: int = 500,
) -> dict[str, Any] | None:
    """Return prosody dict or None on failure / insufficient audio.

    Algorithm (v1, numpy-free):
    - Take the last `end_window_ms` of mono PCM16.
    - Frame RMS energy + coarse F0 via autocorrelation.
    - End slope of log-F0 → semitones; map rising slope to questionScore in [0,1].
    """
    try:
        samples = _pcm16_mono_to_floats(pcm)
        if not samples:
            return None
        end_n = max(1, int(sample_rate * (end_window_ms / 1000.0)))
        tail = samples[-end_n:]
        if len(tail) < int(sample_rate * 0.08):
            return None

        frame = max(64, int(sample_rate * 0.025))
        hop = max(32, int(sample_rate * 0.010))
        f0s: list[float] = []
        for start in range(0, len(tail) - frame + 1, hop):
            f0 = _autocorr_f0_hz(tail[start : start + frame], sample_rate)
            if f0 is not None:
                f0s.append(f0)

        energies = _frame_energies(tail, frame, hop)
        if not f0s and not energies:
            return None

        slope_semitones = 0.0
        contour = "unknown"
        if len(f0s) >= 2:
            # Linear regression slope of log2(f0) over frame index → convert to semitones/frame * span
            xs = list(range(len(f0s)))
            n = len(f0s)
            mean_x = (n - 1) / 2.0
            logs = [math.log2(max(f0, 1e-3)) for f0 in f0s]
            mean_y = sum(logs) / n
            num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, logs, strict=True))
            den = sum((x - mean_x) ** 2 for x in xs) or 1.0
            slope_per_frame = num / den
            # 12 semitones per octave; scale by number of frames to end-window slope
            slope_semitones = 12.0 * slope_per_frame * (n - 1)
            if slope_semitones > 0.75:
                contour = "rising"
            elif slope_semitones < -0.75:
                contour = "falling"
            else:
                contour = "flat"
        elif energies:
            # Energy-only fallback: rising energy near the end → mild question score
            mid = len(energies) // 2
            first = sum(energies[:mid]) / max(1, mid)
            second = sum(energies[mid:]) / max(1, len(energies) - mid)
            if first > 1e-8:
                ratio = second / first
                slope_semitones = (ratio - 1.0) * 2.0  # heuristic scale
                contour = "rising" if ratio > 1.15 else ("falling" if ratio < 0.85 else "flat")

        # Map slope to [0,1]: ~0 at flat, ~1 at +4 semitones or more
        question_score = 1.0 / (1.0 + math.exp(-(slope_semitones - 1.0)))
        question_score = max(0.0, min(1.0, question_score))

        return {
            "questionScore": round(question_score, 4),
            "contour": contour,
            "f0EndSlopeSemitones": round(slope_semitones, 3),
        }
    except Exception:
        # Never break transcript path; omit prosody only.
        LOGGER.debug("prosody extraction failed; omitting prosody field", exc_info=False)
        return None
