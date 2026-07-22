from __future__ import annotations

from typing import Any

import pytest

from assistant_hub_audio import devices
from assistant_hub_audio.endpoints import DataFlow, EndpointInfo
from assistant_hub_audio.profiles import AudioChannel, DeviceSelector

WASAPI = 2


class _FakePyAudioModule:
    paWASAPI = WASAPI


def _device(
    index: int,
    name: str,
    *,
    host_api: int = WASAPI,
    inputs: int = 1,
    outputs: int = 0,
    loopback: bool = False,
) -> dict[str, Any]:
    return {
        "index": index,
        "name": name,
        "hostApi": host_api,
        "maxInputChannels": inputs,
        "maxOutputChannels": outputs,
        "defaultSampleRate": 48_000,
        "isLoopbackDevice": loopback,
    }


def _endpoint(
    endpoint_id: str,
    name: str,
    flow: DataFlow,
    *,
    is_default: bool = False,
) -> EndpointInfo:
    return EndpointInfo(
        endpoint_id=endpoint_id,
        friendly_name=name,
        data_flow=flow,
        state="active",
        is_default=is_default,
    )


class _FakeEndpointProvider:
    def __init__(self, endpoints: list[EndpointInfo]) -> None:
        self._endpoints = endpoints

    def list_endpoints(self) -> list[EndpointInfo]:
        return list(self._endpoints)

    def default_endpoint(self, flow: DataFlow) -> EndpointInfo | None:
        return next((e for e in self._endpoints if e.data_flow == flow and e.is_default), None)


class _FakeWasapiAudio:
    """Fake pyaudio.PyAudio exposing a configurable WASAPI host API and device table."""

    def __init__(
        self,
        all_devices: list[dict[str, Any]],
        *,
        wasapi_host_api_index: int = WASAPI,
        default_input_device: int | None = None,
        default_output_device: int | None = None,
        loopback_devices: list[dict[str, Any]] | None = None,
    ) -> None:
        self._devices = {device["index"]: device for device in all_devices}
        self._wasapi_host_api_index = wasapi_host_api_index
        self._default_input_device = default_input_device
        self._default_output_device = default_output_device
        self._loopback_devices = loopback_devices or []

    def get_host_api_info_by_type(self, _host_api_type: int) -> dict[str, Any]:
        info: dict[str, Any] = {"index": self._wasapi_host_api_index}
        if self._default_input_device is not None:
            info["defaultInputDevice"] = self._default_input_device
        if self._default_output_device is not None:
            info["defaultOutputDevice"] = self._default_output_device
        return info

    def get_device_info_by_index(self, index: int) -> dict[str, Any]:
        return self._devices[index]

    def get_device_info_generator(self):
        return iter(self._devices.values())

    def get_loopback_device_info_generator(self):
        return iter(self._loopback_devices)


# --- User Story 1: default_microphone() resolves via WASAPI --------------------


def test_default_microphone_resolves_wasapi_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(devices, "pyaudio", _FakePyAudioModule, raising=False)
    wasapi_mic = _device(9, "Microfone (FHD Camera Audio)", host_api=WASAPI, inputs=1)
    mme_mic = _device(1, "Microfone (FHD Camera Audio)", host_api=99, inputs=1)
    audio = _FakeWasapiAudio([wasapi_mic, mme_mic], default_input_device=9)

    result = devices.default_microphone(audio)

    assert result["index"] == 9
    assert result["hostApi"] == WASAPI


def test_default_microphone_channel_gets_endpoint_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(devices, "pyaudio", _FakePyAudioModule, raising=False)
    wasapi_mic = _device(9, "Microfone (FHD Camera Audio)", host_api=WASAPI, inputs=1)
    audio = _FakeWasapiAudio([wasapi_mic], default_input_device=9)
    provider = _FakeEndpointProvider(
        [_endpoint("EP-MIC", "Microfone (FHD Camera Audio)", "capture", is_default=True)]
    )
    channel = AudioChannel(
        channel_id="local_microphone", kind="input", selector=DeviceSelector(use_default=True)
    )

    result = devices.resolve_device(audio, channel, provider)

    assert result["endpointId"] == "EP-MIC"


# --- User Story 2: explicit failure without a WASAPI default input device ------


@pytest.mark.parametrize("default_input_device", [None, -1])
def test_default_microphone_raises_without_wasapi_default(
    monkeypatch: pytest.MonkeyPatch, default_input_device: int | None
) -> None:
    monkeypatch.setattr(devices, "pyaudio", _FakePyAudioModule, raising=False)
    audio = _FakeWasapiAudio([], default_input_device=default_input_device)

    with pytest.raises(RuntimeError, match="Default WASAPI input device was not found"):
        devices.default_microphone(audio)


# --- User Story 3: default_loopback() stays unaffected --------------------------


def test_default_loopback_unaffected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(devices, "pyaudio", _FakePyAudioModule, raising=False)
    speaker = _device(
        10,
        "Alto-falantes (FHD Camera Audio) [Loopback]",
        host_api=WASAPI,
        inputs=2,
        loopback=True,
    )
    audio = _FakeWasapiAudio([speaker], default_output_device=10)

    result = devices.default_loopback(audio)

    assert result["index"] == 10
    assert result["isLoopbackDevice"] is True
