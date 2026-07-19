"""Persistent audio endpoint identity based on Windows MMDevice endpoint IDs.

This module is intentionally pure: it never imports pyaudiowpatch, pycaw or
comtypes, so the correlation and selection logic can run (and be tested) on
any platform. The Windows-specific provider lives in `mmdevice.py` and is
loaded lazily by `get_endpoint_provider`.

PortAudio does not expose the MMDevice endpoint ID, so devices are correlated
structurally: WASAPI host API only, per data flow, by friendly name, with
enumeration order as the tie-break for duplicated names. Selecting a channel
by `endpointId` resolves the *current* PortAudio index through this
correlation at capture start; the stream is always opened by index.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from typing import Any, Literal, Protocol

LOGGER = logging.getLogger(__name__)

DataFlow = Literal["capture", "render"]
EndpointState = Literal["active", "disabled", "notpresent", "unplugged"]

LOOPBACK_SUFFIX = " [Loopback]"

# Below this length a PortAudio name is too generic for prefix matching against
# friendly names truncated by PortAudio.
_TRUNCATED_PREFIX_MIN_CHARS = 12


@dataclass(frozen=True)
class EndpointInfo:
    endpoint_id: str
    friendly_name: str
    data_flow: DataFlow
    state: EndpointState
    is_default: bool = False


class EndpointProvider(Protocol):
    def list_endpoints(self) -> list[EndpointInfo]:
        """Return endpoints for both data flows, all states, in system enumeration order."""
        ...

    def default_endpoint(self, flow: DataFlow) -> EndpointInfo | None: ...


class NullEndpointProvider:
    """Fallback provider for non-Windows platforms or MMDevice failures."""

    def list_endpoints(self) -> list[EndpointInfo]:
        return []

    def default_endpoint(self, flow: DataFlow) -> EndpointInfo | None:
        return None


def get_endpoint_provider() -> EndpointProvider:
    if sys.platform != "win32":
        return NullEndpointProvider()
    try:
        from .mmdevice import MMDeviceEndpointProvider

        return MMDeviceEndpointProvider()
    except Exception as exc:  # noqa: BLE001 - COM/import failures must not break capture
        LOGGER.warning("MMDevice endpoint provider unavailable; endpoint IDs disabled: %s", exc)
        return NullEndpointProvider()


def device_flow_and_base_name(device: dict[str, Any]) -> tuple[DataFlow, str] | None:
    """Classify a normalized PortAudio device into (data flow, comparable name)."""
    name = str(device.get("name", ""))
    if device.get("isLoopbackDevice"):
        base = name[: -len(LOOPBACK_SUFFIX)] if name.endswith(LOOPBACK_SUFFIX) else name
        return "render", base
    if int(device.get("maxInputChannels", 0)) > 0:
        return "capture", name
    if int(device.get("maxOutputChannels", 0)) > 0:
        return "render", name
    return None


def _device_serves_kind(device: dict[str, Any], kind: str) -> bool:
    if kind == "loopback":
        return bool(device.get("isLoopbackDevice"))
    return int(device.get("maxInputChannels", 0)) > 0 and not bool(device.get("isLoopbackDevice"))


def correlate_devices(
    devices: list[dict[str, Any]],
    endpoints: list[EndpointInfo],
    wasapi_host_api: int,
) -> dict[int, EndpointInfo]:
    """Map PortAudio device indexes to MMDevice endpoints.

    Only WASAPI devices participate; MME/DirectSound entries are duplicates
    with truncated names. Both a WASAPI output device and its PyAudioWPatch
    `[Loopback]` sibling correlate to the same eRender endpoint. Devices
    without a confident match are simply absent from the result — never a
    silent guess.
    """
    active_by_flow: dict[DataFlow, list[EndpointInfo]] = {"capture": [], "render": []}
    for endpoint in endpoints:
        if endpoint.state == "active":
            active_by_flow[endpoint.data_flow].append(endpoint)

    sequences: dict[str, tuple[DataFlow, list[tuple[dict[str, Any], str]]]] = {
        "capture": ("capture", []),
        "render": ("render", []),
        "loopback": ("render", []),
    }
    for device in devices:
        if int(device.get("hostApi", -1)) != wasapi_host_api:
            continue
        classified = device_flow_and_base_name(device)
        if classified is None:
            continue
        flow, base_name = classified
        if device.get("isLoopbackDevice"):
            sequences["loopback"][1].append((device, base_name))
        else:
            sequences[flow][1].append((device, base_name))

    correlation: dict[int, EndpointInfo] = {}
    for sequence_name, (flow, sequence) in sequences.items():
        candidates = active_by_flow[flow]
        if sequence and len(sequence) != len(candidates):
            LOGGER.warning(
                "Endpoint correlation may be degraded: %s WASAPI %s device(s) vs "
                "%s active %s endpoint(s)",
                len(sequence),
                sequence_name,
                len(candidates),
                flow,
            )
        occurrences: dict[str, int] = {}
        for device, base_name in sequence:
            key = base_name.casefold()
            occurrence = occurrences.get(key, 0)
            occurrences[key] = occurrence + 1

            pool = [e for e in candidates if e.friendly_name.casefold() == key]
            if not pool and len(base_name) >= _TRUNCATED_PREFIX_MIN_CHARS:
                pool = [e for e in candidates if e.friendly_name.casefold().startswith(key)]
            if not pool:
                LOGGER.warning(
                    "No MMDevice endpoint matched %s device [%s] %r",
                    sequence_name,
                    device.get("index"),
                    device.get("name"),
                )
                continue
            if len(pool) > 1:
                LOGGER.warning(
                    "Duplicated endpoint names for %r; correlating by enumeration order",
                    base_name,
                )
            if occurrence >= len(pool):
                LOGGER.warning(
                    "More %s devices named %r than matching endpoints; device [%s] left "
                    "without endpoint ID",
                    sequence_name,
                    base_name,
                    device.get("index"),
                )
                continue
            correlation[int(device["index"])] = pool[occurrence]
    return correlation


def _flow_for_kind(kind: str) -> DataFlow:
    return "render" if kind == "loopback" else "capture"


def _format_endpoint_alternatives(endpoints: list[EndpointInfo], flow: DataFlow) -> str:
    rows = [e for e in endpoints if e.data_flow == flow]
    if not rows:
        return f"  (no {flow} endpoints reported by Windows)"
    return "\n".join(
        f"  {e.endpoint_id}  state={e.state}  {e.friendly_name}" for e in rows
    )


def find_device_for_endpoint(
    devices: list[dict[str, Any]],
    correlation: dict[int, EndpointInfo],
    endpoints: list[EndpointInfo],
    endpoint_id: str,
    kind: str,
) -> dict[str, Any]:
    """Resolve the current PortAudio device for a configured MMDevice endpoint ID.

    For `kind == "loopback"` the configured ID is the original eRender endpoint;
    the resolved device is its `[Loopback]` sibling. Raises RuntimeError with
    actionable alternatives when the endpoint cannot be resolved.
    """
    wanted = endpoint_id.strip().casefold()
    flow = _flow_for_kind(kind)

    for device in devices:
        endpoint = correlation.get(int(device.get("index", -1)))
        if endpoint is None or endpoint.endpoint_id.casefold() != wanted:
            continue
        if _device_serves_kind(device, kind):
            return device

    known = next((e for e in endpoints if e.endpoint_id.casefold() == wanted), None)
    hint = "Run 'assistant-hub-audio list-devices --json' and update the profile."
    if known is None:
        raise RuntimeError(
            f"Endpoint ID {endpoint_id!r} was not found for channel kind={kind}. "
            f"Available {flow} endpoints:\n"
            f"{_format_endpoint_alternatives(endpoints, flow)}\n{hint}"
        )
    if known.state != "active":
        raise RuntimeError(
            f"Endpoint ID {endpoint_id!r} ({known.friendly_name}) exists but is "
            f"{known.state}. Enable or reconnect the device, or select another endpoint. {hint}"
        )
    if known.data_flow != flow:
        raise RuntimeError(
            f"Endpoint ID {endpoint_id!r} ({known.friendly_name}) is a {known.data_flow} "
            f"endpoint and cannot serve channel kind={kind}. Available {flow} endpoints:\n"
            f"{_format_endpoint_alternatives(endpoints, flow)}\n{hint}"
        )
    raise RuntimeError(
        f"Endpoint ID {endpoint_id!r} ({known.friendly_name}) is active but no PortAudio "
        f"device could be correlated to it. Run 'assistant-hub-audio probe' to inspect the "
        "correlation or select the device by index as a workaround."
    )
