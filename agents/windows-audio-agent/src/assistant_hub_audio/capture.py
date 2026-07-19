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
from typing import Any
from urllib.parse import urlencode

import numpy as np
import pyaudiowpatch as pyaudio
from scipy.signal import resample_poly
from websockets.sync.client import connect

from .devices import resolve_device
from .profiles import AudioChannel, AudioProfile, channel_to_dict

LOGGER = logging.getLogger(__name__)
TARGET_RATE = 16_000
SAMPLE_WIDTH_BYTES = 2
_WORKER_STARTUP_DELAY_SECONDS = 0.8
_WORKER_SHUTDOWN_TIMEOUT_SECONDS = 4.0


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
    reconnect_delay = 1.0
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
            )
        except KeyboardInterrupt:
            stop_event.set()
        except Exception as exc:
            LOGGER.exception("Capture failed for channel=%s: %s", channel.channel_id, exc)
            if stop_event.wait(reconnect_delay):
                return
            reconnect_delay = min(reconnect_delay * 2, 10.0)
        else:
            reconnect_delay = 1.0


def _capture_once(
    *,
    audio: pyaudio.PyAudio,
    channel: AudioChannel,
    session_id: str,
    server_url: str,
    stop_event: threading.Event,
    record_path: Path | None,
    chunk_size: int,
) -> None:
    device: dict[str, Any] = resolve_device(audio, channel)
    channels = max(1, min(int(device["maxInputChannels"]), 2))
    source_rate = int(device["defaultSampleRate"])

    query_params = {
        "sourceType": channel.source_type,
        "deviceName": device["name"],
        "deviceIndex": device["index"],
        "label": channel.label or channel.channel_id,
    }
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
            open_timeout=10,
            close_timeout=3,
            max_size=None,
        ) as websocket:
            while not stop_event.is_set():
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

    The command intentionally remains in the foreground. Returning to the
    PowerShell prompt before Ctrl+C means the supervisor or a worker failed.
    """
    workers: list[tuple[AudioChannel, subprocess.Popen[bytes]]] = []

    try:
        for channel in profile.channels:
            if not channel.enabled:
                continue
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
            workers.append((channel, process))
            LOGGER.info("Started worker channel=%s pid=%s", channel.channel_id, process.pid)

            # Opening multiple WASAPI endpoints simultaneously can crash native
            # PortAudio drivers. Stagger worker startup and fail explicitly if
            # a channel dies during initialization.
            time.sleep(_WORKER_STARTUP_DELAY_SECONDS)
            return_code = process.poll()
            if return_code is not None:
                raise RuntimeError(
                    f"Audio worker failed during startup: channel={channel.channel_id} "
                    f"exit={_format_exit_code(return_code)}"
                )

        if not workers:
            raise RuntimeError("The selected profile has no enabled audio channels")

        LOGGER.info(
            "Capture supervisor is running in FOREGROUND with profile=%s channels=%s. "
            "Press Ctrl+C to stop.",
            profile.name,
            ",".join(channel.channel_id for channel, _ in workers),
        )

        while True:
            for channel, process in workers:
                return_code = process.poll()
                if return_code is not None:
                    raise RuntimeError(
                        f"Audio worker stopped unexpectedly: channel={channel.channel_id} "
                        f"pid={process.pid} exit={_format_exit_code(return_code)}"
                    )
            time.sleep(0.25)
    except KeyboardInterrupt:
        LOGGER.info("Stopping audio capture...")
    finally:
        _stop_processes(workers)
