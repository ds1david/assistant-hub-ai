from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

ChannelKind = Literal["input", "loopback"]


@dataclass(frozen=True)
class DeviceSelector:
    index: int | None = None
    name_regex: str | None = None
    use_default: bool = False

    def validate(self) -> None:
        configured = sum(
            value is not None and value is not False
            for value in (self.index, self.name_regex, self.use_default)
        )
        if configured != 1:
            raise ValueError("A device selector must define exactly one of: index, nameRegex, default")
        if self.name_regex is not None:
            re.compile(self.name_regex)


@dataclass(frozen=True)
class AudioProcessing:
    """Low-cost per-channel preprocessing applied by the Windows capture agent.

    The noise gate helps when a conference-camera microphone picks up quiet audio
    emitted by nearby speakers. It is not a full acoustic echo canceller; the
    transcription service also performs cross-channel transcript deduplication.
    """

    gain_db: float = 0.0
    noise_gate_db: float | None = None

    def validate(self) -> None:
        if not -24.0 <= self.gain_db <= 24.0:
            raise ValueError("processing.gainDb must be between -24 and 24")
        if self.noise_gate_db is not None and not -90.0 <= self.noise_gate_db <= -3.0:
            raise ValueError("processing.noiseGateDb must be between -90 and -3 dBFS")


@dataclass(frozen=True)
class AudioChannel:
    channel_id: str
    kind: ChannelKind
    selector: DeviceSelector
    enabled: bool = True
    label: str | None = None
    processing: AudioProcessing = field(default_factory=AudioProcessing)

    @property
    def source_type(self) -> str:
        return "microphone" if self.kind == "input" else "system"

    def validate(self) -> None:
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}", self.channel_id):
            raise ValueError(
                f"Invalid channel id '{self.channel_id}'. Use 1-64 letters, numbers, '.', '_' or '-'."
            )
        if self.kind not in {"input", "loopback"}:
            raise ValueError(f"Unsupported channel kind: {self.kind}")
        self.selector.validate()
        self.processing.validate()


@dataclass(frozen=True)
class AudioProfile:
    name: str
    channels: tuple[AudioChannel, ...]
    server_url: str | None = None

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("Profile name cannot be empty")
        ids = [channel.channel_id for channel in self.channels if channel.enabled]
        if len(ids) != len(set(ids)):
            raise ValueError("Enabled channel ids must be unique")
        if not ids:
            raise ValueError("Profile must contain at least one enabled channel")
        for channel in self.channels:
            channel.validate()


def _selector_from_dict(data: dict[str, Any]) -> DeviceSelector:
    return DeviceSelector(
        index=int(data["index"]) if data.get("index") is not None else None,
        name_regex=str(data["nameRegex"]) if data.get("nameRegex") is not None else None,
        use_default=bool(data.get("default", False)),
    )


def _processing_from_dict(data: dict[str, Any] | None) -> AudioProcessing:
    data = data or {}
    return AudioProcessing(
        gain_db=float(data.get("gainDb", 0.0)),
        noise_gate_db=(
            float(data["noiseGateDb"])
            if data.get("noiseGateDb") is not None
            else None
        ),
    )


def channel_to_dict(channel: AudioChannel) -> dict[str, Any]:
    selector: dict[str, Any] = {}
    if channel.selector.index is not None:
        selector["index"] = channel.selector.index
    elif channel.selector.name_regex is not None:
        selector["nameRegex"] = channel.selector.name_regex
    else:
        selector["default"] = channel.selector.use_default

    processing: dict[str, Any] = {"gainDb": channel.processing.gain_db}
    if channel.processing.noise_gate_db is not None:
        processing["noiseGateDb"] = channel.processing.noise_gate_db

    return {
        "id": channel.channel_id,
        "label": channel.label,
        "kind": channel.kind,
        "enabled": channel.enabled,
        "device": selector,
        "processing": processing,
    }


def channel_from_dict(data: dict[str, Any]) -> AudioChannel:
    selector_raw = data.get("device")
    if not isinstance(selector_raw, dict):
        raise ValueError("Serialized audio channel must contain a device selector")
    processing_raw = data.get("processing")
    if processing_raw is not None and not isinstance(processing_raw, dict):
        raise ValueError("Serialized audio channel processing must be an object")
    channel = AudioChannel(
        channel_id=str(data.get("id", "")),
        label=str(data["label"]) if data.get("label") is not None else None,
        kind=str(data.get("kind", "")),  # type: ignore[arg-type]
        enabled=bool(data.get("enabled", True)),
        selector=_selector_from_dict(selector_raw),
        processing=_processing_from_dict(processing_raw),
    )
    channel.validate()
    return channel


def load_profile(path: Path) -> AudioProfile:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Audio profile must be a YAML object")
    version = raw.get("version")
    if version != 1:
        raise ValueError(f"Unsupported audio profile version: {version!r}; expected 1")

    channels_raw = raw.get("channels")
    if not isinstance(channels_raw, list):
        raise ValueError("Audio profile field 'channels' must be a list")

    channels: list[AudioChannel] = []
    for item in channels_raw:
        if not isinstance(item, dict):
            raise ValueError("Each audio channel must be a YAML object")
        selector_raw = item.get("device")
        if not isinstance(selector_raw, dict):
            raise ValueError(f"Channel {item.get('id')!r} must define a 'device' selector")
        processing_raw = item.get("processing")
        if processing_raw is not None and not isinstance(processing_raw, dict):
            raise ValueError(f"Channel {item.get('id')!r} processing must be a YAML object")
        channels.append(
            AudioChannel(
                channel_id=str(item.get("id", "")),
                label=str(item["label"]) if item.get("label") is not None else None,
                kind=str(item.get("kind", "")),  # type: ignore[arg-type]
                enabled=bool(item.get("enabled", True)),
                selector=_selector_from_dict(selector_raw),
                processing=_processing_from_dict(processing_raw),
            )
        )

    profile = AudioProfile(
        name=str(raw.get("name", path.stem)),
        server_url=str(raw["server"]) if raw.get("server") else None,
        channels=tuple(channels),
    )
    profile.validate()
    return profile


def default_profile(
    microphone_device: int | None = None,
    system_device: int | None = None,
) -> AudioProfile:
    microphone_selector = (
        DeviceSelector(index=microphone_device)
        if microphone_device is not None
        else DeviceSelector(use_default=True)
    )
    system_selector = (
        DeviceSelector(index=system_device)
        if system_device is not None
        else DeviceSelector(use_default=True)
    )
    profile = AudioProfile(
        name="default-dual-channel",
        channels=(
            AudioChannel(
                channel_id="local_microphone",
                label="Minha voz",
                kind="input",
                selector=microphone_selector,
                processing=AudioProcessing(noise_gate_db=-38.0),
            ),
            AudioChannel(
                channel_id="remote_audio",
                label="Áudio remoto",
                kind="loopback",
                selector=system_selector,
            ),
        ),
    )
    profile.validate()
    return profile
