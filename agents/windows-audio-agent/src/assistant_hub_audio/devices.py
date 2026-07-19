from __future__ import annotations

import re
from typing import Any

import pyaudiowpatch as pyaudio

from .endpoints import (
    EndpointInfo,
    EndpointProvider,
    correlate_devices,
    find_device_for_endpoint,
    get_endpoint_provider,
)
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


def _endpoint_fields(endpoint: EndpointInfo | None) -> dict[str, Any]:
    if endpoint is None:
        return {"endpointId": None, "friendlyName": None, "dataFlow": None, "isDefault": False}
    return {
        "endpointId": endpoint.endpoint_id,
        "friendlyName": endpoint.friendly_name,
        "dataFlow": endpoint.data_flow,
        "isDefault": endpoint.is_default,
    }


def _wasapi_host_api_index(audio: pyaudio.PyAudio) -> int:
    try:
        return int(audio.get_host_api_info_by_type(pyaudio.paWASAPI)["index"])
    except Exception:
        return -1


def _snapshot(
    audio: pyaudio.PyAudio,
    provider: EndpointProvider,
) -> tuple[list[dict[str, Any]], list[EndpointInfo], dict[int, EndpointInfo]]:
    """Enumerate PyAudio devices and MMDevice endpoints in one correlation session."""
    devices = [_normalized_device(dict(info)) for info in audio.get_device_info_generator()]
    endpoints = provider.list_endpoints()
    correlation = correlate_devices(devices, endpoints, _wasapi_host_api_index(audio))
    return devices, endpoints, correlation


def list_devices(provider: EndpointProvider | None = None) -> list[dict[str, Any]]:
    provider = provider or get_endpoint_provider()
    with pyaudio.PyAudio() as audio:
        devices, _, correlation = _snapshot(audio, provider)
        return [
            {**device, **_endpoint_fields(correlation.get(device["index"]))}
            for device in devices
        ]


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
    provider: EndpointProvider | None = None,
) -> dict[str, Any]:
    provider = provider or get_endpoint_provider()
    devices, endpoints, correlation = _snapshot(audio, provider)
    selector: DeviceSelector = channel.selector

    # Selection priority: endpointId > index > default/nameRegex. The
    # endpointId resolves the *current* PortAudio index through the MMDevice
    # correlation of this snapshot; there is no silent fallback to index or
    # name when the endpoint cannot be resolved.
    if selector.endpoint_id is not None:
        device = find_device_for_endpoint(
            devices=devices,
            correlation=correlation,
            endpoints=endpoints,
            endpoint_id=selector.endpoint_id,
            kind=channel.kind,
        )
    elif selector.index is not None:
        device = device_by_index(audio, selector.index)
        if not _is_eligible(device, channel):
            raise RuntimeError(
                f"Device index {selector.index} is not eligible for channel kind {channel.kind}"
            )
    elif selector.use_default:
        device = default_loopback(audio) if channel.kind == "loopback" else default_microphone(audio)
    else:
        assert selector.name_regex is not None
        pattern = re.compile(selector.name_regex, re.IGNORECASE)
        candidates = [device for device in devices if pattern.search(device["name"])]
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
        device = eligible[0]

    return {**device, **_endpoint_fields(correlation.get(device["index"]))}


def resolve_profile(
    profile_channels: tuple[AudioChannel, ...],
    provider: EndpointProvider | None = None,
) -> list[tuple[AudioChannel, dict[str, Any]]]:
    provider = provider or get_endpoint_provider()
    with pyaudio.PyAudio() as audio:
        return [
            (channel, resolve_device(audio, channel, provider))
            for channel in profile_channels
            if channel.enabled
        ]
