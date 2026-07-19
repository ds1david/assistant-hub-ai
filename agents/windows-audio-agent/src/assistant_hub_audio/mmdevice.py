"""Windows MMDevice endpoint provider backed by pycaw/comtypes.

Only imported on Windows, lazily, by `endpoints.get_endpoint_provider`. Each
worker process creates its own provider instance (ADR-0007: no native state is
shared between channel processes); comtypes initializes COM for the calling
thread on demand.
"""

from __future__ import annotations

import logging

from .endpoints import DataFlow, EndpointInfo, EndpointState

LOGGER = logging.getLogger(__name__)

# Windows SDK values (mmdeviceapi.h); kept literal so this module does not
# depend on the exact layout of pycaw's constant enums.
_EDATAFLOW = {"render": 0, "capture": 1}
_EROLE_CONSOLE = 0
_DEVICE_STATEMASK_ALL = 0x0000000F
_STATE_BY_VALUE: dict[int, EndpointState] = {
    0x1: "active",
    0x2: "disabled",
    0x4: "notpresent",
    0x8: "unplugged",
}


class MMDeviceEndpointProvider:
    def __init__(self) -> None:
        from pycaw.utils import AudioUtilities

        self._audio_utilities = AudioUtilities

    def _friendly_name(self, com_device: object) -> str:
        try:
            wrapped = self._audio_utilities.CreateDevice(com_device)
            name = getattr(wrapped, "FriendlyName", None)
            return str(name) if name else ""
        except Exception as exc:  # noqa: BLE001 - property stores of broken drivers may fail
            LOGGER.warning("Could not read endpoint friendly name: %s", exc)
            return ""

    def _default_endpoint_id(self, enumerator: object, flow_value: int) -> str | None:
        try:
            device = enumerator.GetDefaultAudioEndpoint(flow_value, _EROLE_CONSOLE)
            return str(device.GetId())
        except Exception:  # no default endpoint for this flow (e.g. no microphone)
            return None

    def list_endpoints(self) -> list[EndpointInfo]:
        enumerator = self._audio_utilities.GetDeviceEnumerator()
        endpoints: list[EndpointInfo] = []
        for flow_name, flow_value in _EDATAFLOW.items():
            default_id = self._default_endpoint_id(enumerator, flow_value)
            collection = enumerator.EnumAudioEndpoints(flow_value, _DEVICE_STATEMASK_ALL)
            for position in range(collection.GetCount()):
                com_device = collection.Item(position)
                try:
                    endpoint_id = str(com_device.GetId())
                    state = _STATE_BY_VALUE.get(int(com_device.GetState()), "notpresent")
                except Exception as exc:  # noqa: BLE001
                    LOGGER.warning("Skipping unreadable %s endpoint: %s", flow_name, exc)
                    continue
                endpoints.append(
                    EndpointInfo(
                        endpoint_id=endpoint_id,
                        friendly_name=self._friendly_name(com_device),
                        data_flow=flow_name,  # type: ignore[arg-type]
                        state=state,
                        is_default=default_id is not None and endpoint_id == default_id,
                    )
                )
        return endpoints

    def default_endpoint(self, flow: DataFlow) -> EndpointInfo | None:
        for endpoint in self.list_endpoints():
            if endpoint.data_flow == flow and endpoint.is_default:
                return endpoint
        return None
