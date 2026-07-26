from __future__ import annotations

import json
import logging
import math
import os
import re
import subprocess
import sys
import threading
import time
import wave
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

import numpy as np
from scipy.signal import resample_poly
from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect

try:
    import pyaudiowpatch as pyaudio
except ImportError:  # pragma: no cover - PyAudioWPatch only ships wheels for Windows (P3)
    pyaudio = None  # type: ignore[assignment]

from .devices import resolve_device
from .hotplug import ChannelHotplugSignal, HotplugListener, get_notification_provider
from .process_resolver import process_is_alive, resolve_process
from .profiles import AudioChannel, AudioProfile, channel_to_dict

LOGGER = logging.getLogger(__name__)
TARGET_RATE = 16_000
SAMPLE_WIDTH_BYTES = 2
_WORKER_STARTUP_DELAY_SECONDS = 0.8
_WORKER_SHUTDOWN_TIMEOUT_SECONDS = 4.0
# Long-lived Win→WSL localhost PCM streams can stall briefly under STT load or
# port-forward jitter. Default websockets ping_timeout=20s is too aggressive and
# produced noisy 1011 keepalive drops; keep pings for half-open detection but
# allow a longer pong window before reconnecting.
_WS_OPEN_TIMEOUT_SECONDS = 10.0
_WS_CLOSE_TIMEOUT_SECONDS = 3.0
_WS_PING_INTERVAL_SECONDS = 20.0
_WS_PING_TIMEOUT_SECONDS = 60.0


def _normalize_pcm(
    raw: bytes,
    channels: int,
    source_rate: int,
    *,
    gain_db: float = 0.0,
    noise_gate_db: float | None = None,
) -> bytes:
    samples = np.frombuffer(raw, dtype=np.int16)
    if channels > 1:
        usable = len(samples) - (len(samples) % channels)
        if usable == 0:
            return b""
        samples = samples[:usable].reshape(-1, channels).astype(np.float32).mean(axis=1)
    else:
        samples = samples.astype(np.float32)

    if gain_db != 0.0:
        samples *= 10.0 ** (gain_db / 20.0)

    if source_rate != TARGET_RATE:
        divisor = math.gcd(source_rate, TARGET_RATE)
        samples = resample_poly(samples, TARGET_RATE // divisor, source_rate // divisor)

    samples = np.clip(samples, -32768, 32767)
    if noise_gate_db is not None and samples.size:
        rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
        dbfs = 20.0 * math.log10(max(rms, 1.0) / 32768.0)
        if dbfs < noise_gate_db:
            samples = np.zeros_like(samples)

    return samples.astype(np.int16).tobytes()


class WavRecorder:
    def __init__(self, path: Path | None) -> None:
        self._path = path
        self._file: wave.Wave_write | None = None

    def __enter__(self) -> "WavRecorder":
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._file = wave.open(str(self._path), "wb")
            self._file.setnchannels(1)
            self._file.setsampwidth(SAMPLE_WIDTH_BYTES)
            self._file.setframerate(TARGET_RATE)
        return self

    def write(self, pcm: bytes) -> None:
        if self._file is not None and pcm:
            self._file.writeframes(pcm)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._file is not None:
            self._file.close()


def _safe_filename(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("._") or "channel"


class EndpointResolutionError(RuntimeError):
    """Device resolution failed in a way retrying cannot fix.

    Covers the four find_device_for_endpoint failure modes (FR-007/P7 — no
    silent fallback) and other resolve_device configuration errors (bad
    index/nameRegex/ambiguous match): none of these improve by retrying, so
    the worker exits instead of looping forever with a reconnect backoff.
    """


class EndpointRemovedError(RuntimeError):
    """The configured endpoint was removed while capture was in progress.

    Unlike EndpointResolutionError, this is not permanent: the device may
    come back (SF-019 FR-003), so capture_channel keeps retrying with the
    normal reconnect backoff instead of exiting the worker.
    """


class ProcessExitedError(RuntimeError):
    """The target process of a process-based channel exited mid-capture.

    Handled distinctly from EndpointResolutionError/EndpointRemovedError
    (SF-020): permanent for a channel selected by PID (FR-006 - PID is an
    exact identity, no re-follow); for a channel selected by name, the next
    `_capture_once` attempt re-resolves the name immediately (FR-012) - if
    that re-resolution is itself ambiguous or finds nothing, it raises
    EndpointResolutionError, which is always permanent for a process-based
    channel regardless of any prior successful capture (FR-005/FR-012),
    unlike the transient "notpresent after a prior success" policy that
    applies to device-based channels (SF-019 Issue #22 Bug B).
    """


# Poll granularity for the reconnect wait: short enough that an "arrived"
# notification (FR-003) wakes the wait promptly, without needing a combined
# wait primitive across stop_event and signal.arrived.
_RECONNECT_POLL_SECONDS = 0.1


def _wait_for_reconnect(
    stop_event: threading.Event, signal: ChannelHotplugSignal, delay: float
) -> str:
    """Wait up to `delay` seconds in short slices, waking early on stop or an
    endpoint arrival (FR-003), instead of always waiting out the full backoff.

    Returns "stop", "arrived" or "timeout". `stop_event` always takes
    priority over a pending arrival (FR-008): a deliberately stopped channel
    must never be woken back up by an arrival notification. Budget is
    tracked as a slice countdown rather than a wall-clock deadline so a
    monkeypatched `stop_event.wait` (as used in tests) still bounds the loop.
    """
    remaining = delay
    while remaining > 0:
        if stop_event.is_set():
            return "stop"
        if signal.arrived.is_set():
            signal.arrived.clear()
            return "arrived"
        slice_seconds = min(remaining, _RECONNECT_POLL_SECONDS)
        if stop_event.wait(slice_seconds):
            return "stop"
        remaining -= slice_seconds
    return "timeout"


def capture_channel(
    *,
    audio: pyaudio.PyAudio,
    channel: AudioChannel,
    session_id: str,
    server_url: str,
    stop_event: threading.Event,
    record_path: Path | None,
    chunk_size: int = 1024,
) -> None:
    signal = ChannelHotplugSignal(configured_endpoint_id=channel.selector.endpoint_id)
    listener = HotplugListener(get_notification_provider(), signal)
    try:
        reconnect_delay = 1.0
        # True only for the one _capture_once attempt immediately following an
        # arrival wake-up. Used to relax EndpointResolutionError's normally
        # permanent contract (FR-003 / Clarifications Q3): a still-failing
        # re-resolution right after an arrival is treated as if the
        # notification hadn't happened, not as a fatal misconfiguration.
        woke_on_arrival = False
        # True once this channel has captured successfully at least once.
        # Distinguishes a transient `notpresent` unplug (SF-019 Issue #22 Bug
        # B) - which must not kill the worker - from a resolution failure
        # that has never succeeded (bad index/nameRegex, or an endpointId
        # that never existed), which must keep failing fast per SF-018
        # (FR-004/FR-005).
        resolved_at_least_once = False

        def _mark_resolved() -> None:
            nonlocal resolved_at_least_once
            resolved_at_least_once = True

        def _retry_after_wait() -> bool:
            nonlocal reconnect_delay, woke_on_arrival
            outcome = _wait_for_reconnect(stop_event, signal, reconnect_delay)
            woke_on_arrival = outcome == "arrived"
            if outcome == "stop":
                return True
            reconnect_delay = min(reconnect_delay * 2, 10.0)
            return False

        while not stop_event.is_set():
            try:
                _capture_once(
                    audio=audio,
                    channel=channel,
                    session_id=session_id,
                    server_url=server_url,
                    stop_event=stop_event,
                    record_path=record_path,
                    chunk_size=chunk_size,
                    signal=signal,
                    on_resolved=_mark_resolved,
                )
            except KeyboardInterrupt:
                stop_event.set()
            except EndpointResolutionError:
                if channel.selector.process_id is not None or channel.selector.process_name is not None:
                    # SF-020: a process-based channel's resolution failure is
                    # always permanent - at startup (never resolved, FR-005),
                    # or after a ProcessExitedError re-resolution that turned
                    # out ambiguous/absent (FR-012) - never the device-only
                    # resolved_at_least_once/woke_on_arrival relaxations below.
                    LOGGER.error(
                        "Process resolution failed permanently for channel=%s; not retrying.",
                        channel.channel_id,
                    )
                    raise
                if resolved_at_least_once:
                    LOGGER.warning(
                        "Endpoint resolution failed for channel=%s after a prior successful "
                        "capture (likely a transient unplug/notpresent); falling back to the "
                        "generic reconnect backoff instead of exiting.",
                        channel.channel_id,
                    )
                elif not woke_on_arrival:
                    LOGGER.error(
                        "Endpoint resolution failed permanently for channel=%s; not retrying.",
                        channel.channel_id,
                    )
                    raise
                else:
                    LOGGER.warning(
                        "Endpoint still not resolvable right after an arrival notification for "
                        "channel=%s; falling back to the generic reconnect backoff.",
                        channel.channel_id,
                    )
                if _retry_after_wait():
                    return
            except EndpointRemovedError as exc:
                LOGGER.error("Endpoint removed for channel=%s: %s", channel.channel_id, exc)
                if _retry_after_wait():
                    return
            except ProcessExitedError as exc:
                if channel.selector.process_id is not None:
                    LOGGER.error(
                        "Target process exited for channel=%s (selected by pid): %s; not retrying.",
                        channel.channel_id,
                        exc,
                    )
                    raise
                LOGGER.warning(
                    "Target process exited for channel=%s (selected by name): %s; "
                    "re-resolving immediately.",
                    channel.channel_id,
                    exc,
                )
                # No _retry_after_wait(): the next while-loop iteration calls
                # _capture_once again right away, which re-resolves
                # process_name fresh (FR-012) - not the generic device
                # reconnect backoff.
            except ConnectionClosed as exc:
                # Expected on STT restart (1012), keepalive timeout (1011), or
                # half-open sockets: reconnect with backoff, without a full
                # traceback (the reconnect INFO line is the useful signal).
                LOGGER.warning(
                    "WebSocket closed for channel=%s: %s; reconnecting",
                    channel.channel_id,
                    exc,
                )
                if _retry_after_wait():
                    return
            except ConnectionError as exc:
                # Connection refused / reset while STT is down or restarting.
                LOGGER.warning(
                    "WebSocket connection error for channel=%s: %s; reconnecting",
                    channel.channel_id,
                    exc,
                )
                if _retry_after_wait():
                    return
            except Exception as exc:
                LOGGER.exception("Capture failed for channel=%s: %s", channel.channel_id, exc)
                if _retry_after_wait():
                    return
            else:
                reconnect_delay = 1.0
                woke_on_arrival = False
    finally:
        listener.close()


def _capture_once(
    *,
    audio: pyaudio.PyAudio,
    channel: AudioChannel,
    session_id: str,
    server_url: str,
    stop_event: threading.Event,
    record_path: Path | None,
    chunk_size: int,
    signal: ChannelHotplugSignal,
    on_resolved: Callable[[], None],
) -> None:
    is_process_channel = (
        channel.selector.process_id is not None or channel.selector.process_name is not None
    )
    resolved_pid: int | None = None

    if is_process_channel:
        try:
            resolution = resolve_process(channel.selector)
        except Exception as exc:
            raise EndpointResolutionError(str(exc)) from exc
        resolved_pid = resolution.pid
        # SF-020: no PortAudio index/MMDevice endpointId exists for a
        # process-scoped IAudioClient (research.md §2/§5) - both stay None,
        # already-nullable transcript-event.v2 fields (data-model.md), no
        # contract change needed.
        device: dict[str, Any] = {
            "index": None,
            "name": f"{resolution.name} (pid {resolution.pid})",
            "maxInputChannels": 2,
            "defaultSampleRate": 48_000,
            "endpointId": None,
        }
    else:
        try:
            device = resolve_device(audio, channel)
        except Exception as exc:
            raise EndpointResolutionError(str(exc)) from exc
    # Signal success as soon as resolution succeeds, not only when this whole
    # call returns without raising: the read loop below runs until stop_event
    # is set, an unplug, or a stream error - it never "returns cleanly after
    # capturing a while" on its own, so the caller's success flag has to be
    # set here to distinguish a later notpresent failure from one that has
    # never resolved (SF-019 Issue #22 Bug B, FR-004/FR-005).
    on_resolved()
    channels = max(1, min(int(device["maxInputChannels"]), 2))
    source_rate = int(device["defaultSampleRate"])

    query_params = {
        "sourceType": channel.source_type,
        "deviceName": device["name"],
        "label": channel.label or channel.channel_id,
    }
    # SF-020: a process-based channel's device["index"] is None (research.md
    # §5/data-model.md) - omitted from the query, same as endpointId already
    # was, instead of urlencode-ing the literal string "None".
    if device["index"] is not None:
        query_params["deviceIndex"] = device["index"]
    if device.get("endpointId"):
        query_params["endpointId"] = device["endpointId"]
    query = urlencode(query_params)
    endpoint = f"{server_url.rstrip('/')}/ws/audio/{session_id}/{channel.channel_id}?{query}"

    LOGGER.info(
        "channel=%s source_type=%s device=(%s) %s endpoint_id=%s channels=%s rate=%s "
        "gain_db=%s noise_gate_db=%s endpoint=%s",
        channel.channel_id,
        channel.source_type,
        device["index"],
        device["name"],
        device.get("endpointId"),
        channels,
        source_rate,
        channel.processing.gain_db,
        channel.processing.noise_gate_db,
        endpoint,
    )

    if is_process_channel:
        # SF-020: bypasses PyAudioWPatch/PortAudio entirely - there is no
        # device index for a process-scoped IAudioClient (research.md §2).
        from .process_capture import ProcessLoopbackStream

        stream = ProcessLoopbackStream(resolved_pid, sample_rate=source_rate, channels=channels)
    else:
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=source_rate,
            input=True,
            input_device_index=int(device["index"]),
            frames_per_buffer=chunk_size,
        )

    try:
        with WavRecorder(record_path) as recorder, connect(
            endpoint,
            open_timeout=_WS_OPEN_TIMEOUT_SECONDS,
            close_timeout=_WS_CLOSE_TIMEOUT_SECONDS,
            ping_interval=_WS_PING_INTERVAL_SECONDS,
            ping_timeout=_WS_PING_TIMEOUT_SECONDS,
            max_size=None,
        ) as websocket:
            while not stop_event.is_set():
                if signal.removed.is_set():
                    signal.removed.clear()
                    raise EndpointRemovedError(
                        f"Endpoint {channel.selector.endpoint_id!r} was removed while "
                        f"channel={channel.channel_id} was capturing."
                    )
                if is_process_channel and not process_is_alive(resolved_pid):
                    raise ProcessExitedError(
                        f"Process pid={resolved_pid} ({device['name']}) exited while "
                        f"channel={channel.channel_id} was capturing."
                    )
                raw = stream.read(chunk_size, exception_on_overflow=False)
                pcm = _normalize_pcm(
                    raw,
                    channels=channels,
                    source_rate=source_rate,
                    gain_db=channel.processing.gain_db,
                    noise_gate_db=channel.processing.noise_gate_db,
                )
                if pcm:
                    recorder.write(pcm)
                    websocket.send(pcm)
    finally:
        stream.stop_stream()
        stream.close()


def run_channel_worker(
    *,
    channel: AudioChannel,
    session_id: str,
    server_url: str,
    record_path: Path | None,
) -> None:
    """Run exactly one WASAPI endpoint in an isolated native process."""
    stop_event = threading.Event()
    LOGGER.info("Starting isolated worker for channel=%s pid=%s", channel.channel_id, os.getpid())
    try:
        with pyaudio.PyAudio() as audio:
            capture_channel(
                audio=audio,
                channel=channel,
                session_id=session_id,
                server_url=server_url,
                stop_event=stop_event,
                record_path=record_path,
            )
    except KeyboardInterrupt:
        LOGGER.info("Worker interrupted channel=%s", channel.channel_id)
        stop_event.set()


def _worker_command(
    *,
    channel: AudioChannel,
    session_id: str,
    server_url: str,
    record_path: Path | None,
    log_level: str,
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "assistant_hub_audio.main",
        "--log-level",
        log_level,
        "_worker",
        "--session",
        session_id,
        "--server",
        server_url,
        "--channel-json",
        json.dumps(channel_to_dict(channel), ensure_ascii=False, separators=(",", ":")),
    ]
    if record_path is not None:
        command.extend(["--record-path", str(record_path)])
    return command


def _format_exit_code(return_code: int) -> str:
    if os.name == "nt":
        return f"{return_code} (0x{return_code & 0xFFFFFFFF:08X})"
    if return_code < 0:
        return f"{return_code} (signal {-return_code})"
    return str(return_code)


def _stop_processes(workers: list[tuple[AudioChannel, subprocess.Popen[bytes]]]) -> None:
    # Ctrl+C is normally delivered to the whole Windows console process tree.
    # Give workers a short grace period to close WAV files and sockets cleanly.
    deadline = time.monotonic() + _WORKER_SHUTDOWN_TIMEOUT_SECONDS
    for _, process in workers:
        remaining = max(0.0, deadline - time.monotonic())
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            pass

    for channel, process in workers:
        if process.poll() is None:
            LOGGER.warning("Terminating unresponsive worker channel=%s pid=%s", channel.channel_id, process.pid)
            process.terminate()

    for _, process in workers:
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


def run_agent(
    *,
    session_id: str,
    server_url: str,
    profile: AudioProfile,
    record_dir: Path | None,
    log_level: str = "INFO",
) -> None:
    """Supervise one OS process per enabled audio endpoint.

    Each channel is isolated in its own process (ADR-0007/P6): a channel that
    fails to start or dies mid-capture is logged and dropped from
    supervision, but the remaining channels keep running. The supervisor
    only raises — and the command only exits non-zero — once every enabled
    channel has failed.

    The command intentionally remains in the foreground. Returning to the
    PowerShell prompt before Ctrl+C means every channel failed or the
    supervisor itself failed.
    """
    workers: list[tuple[AudioChannel, subprocess.Popen[bytes]]] = []
    failures: dict[str, str] = {}

    def _start_channel(channel: AudioChannel) -> None:
        record_path = (
            record_dir / f"{_safe_filename(session_id)}-{_safe_filename(channel.channel_id)}.wav"
            if record_dir
            else None
        )
        command = _worker_command(
            channel=channel,
            session_id=session_id,
            server_url=server_url,
            record_path=record_path,
            log_level=log_level,
        )
        process = subprocess.Popen(command)
        LOGGER.info("Started worker channel=%s pid=%s", channel.channel_id, process.pid)

        # Opening multiple WASAPI endpoints simultaneously can crash native
        # PortAudio drivers. Stagger worker startup and detect an immediate
        # failure without taking the other channels down with it.
        time.sleep(_WORKER_STARTUP_DELAY_SECONDS)
        return_code = process.poll()
        if return_code is not None:
            reason = f"failed during startup exit={_format_exit_code(return_code)}"
            failures[channel.channel_id] = reason
            LOGGER.error("Audio worker %s: channel=%s", reason, channel.channel_id)
            return
        workers.append((channel, process))

    try:
        for channel in profile.channels:
            if channel.enabled:
                _start_channel(channel)

        if not workers:
            details = "; ".join(f"{cid} ({reason})" for cid, reason in failures.items())
            if details:
                raise RuntimeError(f"All enabled audio channels failed during startup: {details}")
            raise RuntimeError("The selected profile has no enabled audio channels")

        LOGGER.info(
            "Capture supervisor is running in FOREGROUND with profile=%s channels=%s. "
            "Press Ctrl+C to stop.",
            profile.name,
            ",".join(channel.channel_id for channel, _ in workers),
        )

        while True:
            still_running: list[tuple[AudioChannel, subprocess.Popen[bytes]]] = []
            for channel, process in workers:
                return_code = process.poll()
                if return_code is None:
                    still_running.append((channel, process))
                    continue
                reason = f"stopped unexpectedly pid={process.pid} exit={_format_exit_code(return_code)}"
                failures[channel.channel_id] = reason
                LOGGER.error(
                    "Audio worker %s: channel=%s. Other channels keep running.",
                    reason,
                    channel.channel_id,
                )
            workers = still_running

            if not workers:
                details = "; ".join(f"{cid} ({reason})" for cid, reason in failures.items())
                raise RuntimeError(f"All audio channels stopped: {details}")
            time.sleep(0.25)
    except KeyboardInterrupt:
        LOGGER.info("Stopping audio capture...")
    finally:
        _stop_processes(workers)
