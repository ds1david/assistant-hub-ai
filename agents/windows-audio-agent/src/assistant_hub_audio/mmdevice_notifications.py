"""Windows MMDevice hot-plug notification provider backed by pycaw/comtypes.

Only imported on Windows, lazily, by `hotplug.get_notification_provider`. Each
worker process registers its own `IMMNotificationClient` (ADR-0007: no native
state is shared between channel processes) on the same `IMMDeviceEnumerator`
kind already used in `mmdevice.py` for `list_endpoints()`.
"""

from __future__ import annotations

import logging
import time

from .hotplug import HotplugEvent

LOGGER = logging.getLogger(__name__)

# mmdeviceapi.h DEVICE_STATE_* values (kept literal, like mmdevice.py, so this
# module does not depend on the exact layout of pycaw's constant enums).
_DEVICE_STATE_ACTIVE = 0x1


def _event_type_for_state(new_state: int) -> str:
    return "arrived" if new_state == _DEVICE_STATE_ACTIVE else "removed"


class MMDeviceNotificationProvider:
    def __init__(self) -> None:
        from comtypes import COMObject
        from pycaw.utils import AudioUtilities

        self._audio_utilities = AudioUtilities
        self._enumerator = self._audio_utilities.GetDeviceEnumerator()
        self._client: object | None = None
        self._com_object_base = COMObject

    def subscribe(self, on_event) -> None:  # noqa: ANN001 - Callable[[HotplugEvent], None]
        from comtypes import COMObject
        from comtypes.gen.MMDeviceAPILib import IMMNotificationClient

        class _NotificationClient(COMObject):
            _com_interfaces_ = [IMMNotificationClient]

            def IMMNotificationClient_OnDeviceAdded(self, device_id: str) -> None:
                on_event(
                    HotplugEvent(
                        endpoint_id=str(device_id), event_type="arrived", timestamp=time.monotonic()
                    )
                )

            def IMMNotificationClient_OnDeviceRemoved(self, device_id: str) -> None:
                on_event(
                    HotplugEvent(
                        endpoint_id=str(device_id), event_type="removed", timestamp=time.monotonic()
                    )
                )

            def IMMNotificationClient_OnDeviceStateChanged(
                self, device_id: str, new_state: int
            ) -> None:
                on_event(
                    HotplugEvent(
                        endpoint_id=str(device_id),
                        event_type=_event_type_for_state(int(new_state)),
                        timestamp=time.monotonic(),
                    )
                )

            def IMMNotificationClient_OnDefaultDeviceChanged(self, *_args: object) -> None:
                return None

            def IMMNotificationClient_OnPropertyValueChanged(self, *_args: object) -> None:
                return None

        self._client = _NotificationClient()
        self._enumerator.RegisterEndpointNotificationCallback(self._client)

    def close(self) -> None:
        if self._client is not None:
            try:
                self._enumerator.UnregisterEndpointNotificationCallback(self._client)
            except Exception as exc:  # noqa: BLE001 - close() must stay idempotent/safe
                LOGGER.warning("Failed to unregister hot-plug notification callback: %s", exc)
            self._client = None
