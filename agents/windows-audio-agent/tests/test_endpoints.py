from __future__ import annotations

import logging
from typing import Any

import pytest

from assistant_hub_audio.endpoints import (
    DataFlow,
    EndpointInfo,
    NullEndpointProvider,
    correlate_devices,
    device_flow_and_base_name,
    find_device_for_endpoint,
    get_endpoint_provider,
)

WASAPI = 2


class FakeEndpointProvider:
    def __init__(self, endpoints: list[EndpointInfo]) -> None:
        self._endpoints = endpoints

    def list_endpoints(self) -> list[EndpointInfo]:
        return list(self._endpoints)

    def default_endpoint(self, flow: DataFlow) -> EndpointInfo | None:
        return next(
            (e for e in self._endpoints if e.data_flow == flow and e.is_default), None
        )


def make_device(
    index: int,
    name: str,
    *,
    host_api: int = WASAPI,
    inputs: int = 0,
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


def make_endpoint(
    endpoint_id: str,
    name: str,
    flow: DataFlow,
    state: str = "active",
    is_default: bool = False,
) -> EndpointInfo:
    return EndpointInfo(
        endpoint_id=endpoint_id,
        friendly_name=name,
        data_flow=flow,
        state=state,  # type: ignore[arg-type]
        is_default=is_default,
    )


MIC_ID = "{0.0.1.00000000}.{aaaaaaaa-1111-2222-3333-444444444444}"
SPEAKER_ID = "{0.0.0.00000000}.{bbbbbbbb-1111-2222-3333-444444444444}"


def test_classifies_devices_by_flow() -> None:
    assert device_flow_and_base_name(make_device(0, "Mic USB", inputs=2)) == ("capture", "Mic USB")
    assert device_flow_and_base_name(make_device(1, "Speakers", outputs=2)) == ("render", "Speakers")
    assert device_flow_and_base_name(
        make_device(2, "Speakers [Loopback]", inputs=2, loopback=True)
    ) == ("render", "Speakers")
    assert device_flow_and_base_name(make_device(3, "Nothing")) is None


def test_correlates_exact_names_including_loopback() -> None:
    devices = [
        make_device(0, "Microfone (USB Audio)", inputs=2),
        make_device(1, "Alto-falantes (Realtek)", outputs=2),
        make_device(2, "Alto-falantes (Realtek) [Loopback]", inputs=2, loopback=True),
    ]
    endpoints = [
        make_endpoint(SPEAKER_ID, "Alto-falantes (Realtek)", "render"),
        make_endpoint(MIC_ID, "Microfone (USB Audio)", "capture"),
    ]

    correlation = correlate_devices(devices, endpoints, WASAPI)

    assert correlation[0].endpoint_id == MIC_ID
    # The output device and its loopback sibling share the render endpoint.
    assert correlation[1].endpoint_id == SPEAKER_ID
    assert correlation[2].endpoint_id == SPEAKER_ID


def test_correlates_truncated_portaudio_name_by_prefix() -> None:
    devices = [make_device(0, "Microfone (Conference Cam X", inputs=2)]
    endpoints = [
        make_endpoint(MIC_ID, "Microfone (Conference Cam XL-2000 Pro)", "capture"),
    ]

    correlation = correlate_devices(devices, endpoints, WASAPI)

    assert correlation[0].endpoint_id == MIC_ID


def test_short_names_never_prefix_match() -> None:
    devices = [make_device(0, "Mic", inputs=2)]
    endpoints = [make_endpoint(MIC_ID, "Microfone (USB Audio)", "capture")]

    assert correlate_devices(devices, endpoints, WASAPI) == {}


def test_duplicated_names_use_enumeration_order(caplog: pytest.LogCaptureFixture) -> None:
    other_id = "{0.0.1.00000000}.{cccccccc-1111-2222-3333-444444444444}"
    devices = [
        make_device(0, "Microfone USB", inputs=2),
        make_device(1, "Microfone USB", inputs=2),
    ]
    endpoints = [
        make_endpoint(MIC_ID, "Microfone USB", "capture"),
        make_endpoint(other_id, "Microfone USB", "capture"),
    ]

    with caplog.at_level(logging.WARNING):
        correlation = correlate_devices(devices, endpoints, WASAPI)

    assert correlation[0].endpoint_id == MIC_ID
    assert correlation[1].endpoint_id == other_id
    assert any("enumeration order" in record.message for record in caplog.records)


def test_non_wasapi_devices_are_excluded() -> None:
    devices = [make_device(0, "Microfone (USB Audio)", inputs=2, host_api=0)]
    endpoints = [make_endpoint(MIC_ID, "Microfone (USB Audio)", "capture")]

    assert correlate_devices(devices, endpoints, WASAPI) == {}


def test_unmatched_device_warns_and_stays_uncorrelated(
    caplog: pytest.LogCaptureFixture,
) -> None:
    devices = [make_device(0, "Microfone Fantasma XYZ", inputs=2)]
    endpoints = [make_endpoint(MIC_ID, "Microfone (USB Audio)", "capture")]

    with caplog.at_level(logging.WARNING):
        correlation = correlate_devices(devices, endpoints, WASAPI)

    assert correlation == {}
    assert any("No MMDevice endpoint matched" in record.message for record in caplog.records)


def test_count_mismatch_emits_warning(caplog: pytest.LogCaptureFixture) -> None:
    devices = [make_device(0, "Microfone (USB Audio)", inputs=2)]
    endpoints = [
        make_endpoint(MIC_ID, "Microfone (USB Audio)", "capture"),
        make_endpoint(SPEAKER_ID, "Outro Microfone (Webcam)", "capture"),
    ]

    with caplog.at_level(logging.WARNING):
        correlate_devices(devices, endpoints, WASAPI)

    assert any("may be degraded" in record.message for record in caplog.records)


def test_inactive_endpoints_are_not_correlation_candidates() -> None:
    devices = [make_device(0, "Microfone (USB Audio)", inputs=2)]
    endpoints = [
        make_endpoint(SPEAKER_ID, "Microfone (USB Audio)", "capture", state="unplugged"),
        make_endpoint(MIC_ID, "Microfone (USB Audio)", "capture"),
    ]

    correlation = correlate_devices(devices, endpoints, WASAPI)

    assert correlation[0].endpoint_id == MIC_ID


class TestFindDeviceForEndpoint:
    devices = [
        make_device(0, "Microfone (USB Audio)", inputs=2),
        make_device(1, "Alto-falantes (Realtek)", outputs=2),
        make_device(2, "Alto-falantes (Realtek) [Loopback]", inputs=2, loopback=True),
    ]
    endpoints = [
        make_endpoint(SPEAKER_ID, "Alto-falantes (Realtek)", "render"),
        make_endpoint(MIC_ID, "Microfone (USB Audio)", "capture"),
    ]
    correlation = correlate_devices(devices, endpoints, WASAPI)

    def test_resolves_microphone_by_endpoint_id(self) -> None:
        device = find_device_for_endpoint(
            self.devices, self.correlation, self.endpoints, MIC_ID, "input"
        )
        assert device["index"] == 0

    def test_render_endpoint_resolves_to_loopback_device(self) -> None:
        device = find_device_for_endpoint(
            self.devices, self.correlation, self.endpoints, SPEAKER_ID, "loopback"
        )
        assert device["index"] == 2
        assert device["isLoopbackDevice"] is True

    def test_endpoint_id_comparison_is_case_insensitive(self) -> None:
        device = find_device_for_endpoint(
            self.devices, self.correlation, self.endpoints, MIC_ID.upper(), "input"
        )
        assert device["index"] == 0

    def test_unknown_endpoint_lists_alternatives(self) -> None:
        with pytest.raises(RuntimeError) as excinfo:
            find_device_for_endpoint(
                self.devices, self.correlation, self.endpoints, "{0.0.1.0}.{missing}", "input"
            )
        message = str(excinfo.value)
        assert "was not found" in message
        assert MIC_ID in message
        assert "list-devices --json" in message
        assert SPEAKER_ID not in message  # only capture alternatives for kind=input

    def test_inactive_endpoint_reports_state(self) -> None:
        unplugged = "{0.0.1.00000000}.{dddddddd-1111-2222-3333-444444444444}"
        endpoints = self.endpoints + [
            make_endpoint(unplugged, "Headset Bluetooth", "capture", state="unplugged")
        ]
        with pytest.raises(RuntimeError, match="unplugged"):
            find_device_for_endpoint(self.devices, self.correlation, endpoints, unplugged, "input")

    def test_wrong_flow_reports_kind_mismatch(self) -> None:
        with pytest.raises(RuntimeError, match="cannot serve channel kind=input"):
            find_device_for_endpoint(
                self.devices, self.correlation, self.endpoints, SPEAKER_ID, "input"
            )

    def test_active_but_uncorrelated_endpoint_suggests_workaround(self) -> None:
        with pytest.raises(RuntimeError, match="no PortAudio device could be correlated"):
            find_device_for_endpoint(self.devices, {}, self.endpoints, MIC_ID, "input")


def test_null_provider_returns_nothing() -> None:
    provider = NullEndpointProvider()
    assert provider.list_endpoints() == []
    assert provider.default_endpoint("capture") is None


def test_factory_degrades_to_null_provider_off_windows() -> None:
    import sys

    if sys.platform == "win32":
        pytest.skip("factory behavior on Windows is exercised manually")
    assert isinstance(get_endpoint_provider(), NullEndpointProvider)


def test_fake_provider_reports_default() -> None:
    provider = FakeEndpointProvider(
        [make_endpoint(MIC_ID, "Microfone (USB Audio)", "capture", is_default=True)]
    )
    default = provider.default_endpoint("capture")
    assert default is not None and default.endpoint_id == MIC_ID
    assert provider.default_endpoint("render") is None
