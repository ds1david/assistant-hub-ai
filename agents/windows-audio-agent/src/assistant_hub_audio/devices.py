from __future__ import annotations

import re
from typing import Any

import pyaudiowpatch as pyaudio

from .profiles import AudioChannel, DeviceSelector


def _normalized_device(info: dict[str, Any]) -> dict[str, Any]:
    return {
        "index": int(info["index"]),
        "name": str(info["name"]),
        "hostApi": int(info.get("hostApi", -1)),
        "maxInputChannels": int(info.get("maxInputChannels", 0)),
        "maxOutputChannels": int(info.get("maxOutputChannels", 0)),
        "defaultSampleRate": int(float(info.get("defaultSampleRate", 0))),
        "isLoopbackDevice": bool(info.get("isLoopbackDevice", False)),
    }


def list_devices() -> list[dict[str, Any]]:
    with pyaudio.PyAudio() as audio:
        return [_normalized_device(dict(info)) for info in audio.get_device_info_generator()]


def default_microphone(audio: pyaudio.PyAudio) -> dict[str, Any]:
    return _normalized_device(dict(audio.get_default_input_device_info()))


def default_loopback(audio: pyaudio.PyAudio) -> dict[str, Any]:
    wasapi_info = audio.get_host_api_info_by_type(pyaudio.paWASAPI)
    speakers = dict(audio.get_device_info_by_index(wasapi_info["defaultOutputDevice"]))
    if speakers.get("isLoopbackDevice"):
        return _normalized_device(speakers)

    speaker_name = str(speakers["name"])
    for loopback in audio.get_loopback_device_info_generator():
        if speaker_name.casefold() in str(loopback["name"]).casefold():
            return _normalized_device(dict(loopback))
    raise RuntimeError("Default WASAPI loopback device was not found")


def device_by_index(audio: pyaudio.PyAudio, index: int) -> dict[str, Any]:
    return _normalized_device(dict(audio.get_device_info_by_index(index)))


def _is_eligible(device: dict[str, Any], channel: AudioChannel) -> bool:
    if channel.kind == "loopback":
        return bool(device.get("isLoopbackDevice"))
    return int(device.get("maxInputChannels", 0)) > 0 and not bool(device.get("isLoopbackDevice"))


def resolve_device(
    audio: pyaudio.PyAudio,
    channel: AudioChannel,
) -> dict[str, Any]:
    selector: DeviceSelector = channel.selector
    if selector.index is not None:
        device = device_by_index(audio, selector.index)
        if not _is_eligible(device, channel):
            raise RuntimeError(
                f"Device index {selector.index} is not eligible for channel kind {channel.kind}"
            )
        return device

    if selector.use_default:
        return default_loopback(audio) if channel.kind == "loopback" else default_microphone(audio)

    assert selector.name_regex is not None
    pattern = re.compile(selector.name_regex, re.IGNORECASE)
    candidates = [
        _normalized_device(dict(info))
        for info in audio.get_device_info_generator()
        if pattern.search(str(info["name"]))
    ]
    eligible = [device for device in candidates if _is_eligible(device, channel)]
    if not eligible:
        raise RuntimeError(
            f"No {channel.kind} device matched nameRegex={selector.name_regex!r}. "
            "Run 'assistant-hub-audio list-devices' and adjust the profile."
        )
    if len(eligible) > 1:
        indexes = ", ".join(str(device["index"]) for device in eligible)
        raise RuntimeError(
            f"Device selector nameRegex={selector.name_regex!r} is ambiguous; matched indexes: {indexes}"
        )
    return eligible[0]


def resolve_profile(profile_channels: tuple[AudioChannel, ...]) -> list[tuple[AudioChannel, dict[str, Any]]]:
    with pyaudio.PyAudio() as audio:
        return [
            (channel, resolve_device(audio, channel))
            for channel in profile_channels
            if channel.enabled
        ]
