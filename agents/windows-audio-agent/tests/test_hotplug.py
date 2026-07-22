from __future__ import annotations

import sys
import time
from typing import Callable

import pytest

from assistant_hub_audio import hotplug
from assistant_hub_audio.hotplug import (
    ChannelHotplugSignal,
    HotplugEvent,
    HotplugListener,
    NullNotificationProvider,
)
from assistant_hub_audio.mmdevice_notifications import _NotificationCallbacks


class FakeNotificationProvider:
    """Test double for `NotificationProvider`: synchronous, no hardware/COM."""

    def __init__(self) -> None:
        self._callback: Callable[[HotplugEvent], None] | None = None
        self.closed = False

    def subscribe(self, on_event: Callable[[HotplugEvent], None]) -> None:
        self._callback = on_event

    def close(self) -> None:
        self.closed = True

    def emit(self, endpoint_id: str, event_type: str, timestamp: float | None = None) -> None:
        assert self._callback is not None, "subscribe() was not called"
        self._callback(
            HotplugEvent(
                endpoint_id=endpoint_id,
                event_type=event_type,  # type: ignore[arg-type]
                timestamp=timestamp if timestamp is not None else time.monotonic(),
            )
        )


# --- HotplugEvent -----------------------------------------------------------


def test_hotplug_event_rejects_empty_endpoint_id() -> None:
    with pytest.raises(ValueError):
        HotplugEvent(endpoint_id="", event_type="removed", timestamp=0.0)


# --- ChannelHotplugSignal.handle_event (FR-004, FR-005) --------------------


def test_own_endpoint_filtering_ignores_other_ids() -> None:
    signal = ChannelHotplugSignal(configured_endpoint_id="EP1")
    signal.handle_event(HotplugEvent("EP2", "removed", 0.0))
    assert not signal.removed.is_set()
    assert not signal.arrived.is_set()


def test_own_endpoint_filtering_is_case_insensitive() -> None:
    signal = ChannelHotplugSignal(configured_endpoint_id="{Endpoint-ID}")
    signal.handle_event(HotplugEvent("{endpoint-id}", "removed", 0.0))
    assert signal.removed.is_set()


def test_configured_endpoint_id_none_is_always_inert() -> None:
    """A channel selected by index/nameRegex/default has no endpointId; its
    signal must never react to any notification (T018)."""
    signal = ChannelHotplugSignal(configured_endpoint_id=None)
    signal.handle_event(HotplugEvent("EP1", "removed", 0.0))
    signal.handle_event(HotplugEvent("EP1", "arrived", 0.0))
    signal.handle_event(HotplugEvent("EP1", "state_changed", 0.0))
    assert not signal.removed.is_set()
    assert not signal.arrived.is_set()


def test_state_changed_is_treated_as_removed() -> None:
    """spec.md Edge Cases: an endpoint going unplugged/disabled without an
    explicit removal event still reacts as a removal."""
    signal = ChannelHotplugSignal(configured_endpoint_id="EP1")
    signal.handle_event(HotplugEvent("EP1", "state_changed", 0.0))
    assert signal.removed.is_set()
    assert not signal.arrived.is_set()


def test_arrived_event_sets_arrived_only() -> None:
    signal = ChannelHotplugSignal(configured_endpoint_id="EP1")
    signal.handle_event(HotplugEvent("EP1", "arrived", 0.0))
    assert signal.arrived.is_set()
    assert not signal.removed.is_set()


def test_debounce_drops_duplicate_within_window(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_time = {"now": 0.0}
    monkeypatch.setattr(hotplug, "_clock", lambda: fake_time["now"])
    signal = ChannelHotplugSignal(configured_endpoint_id="EP1")

    signal.handle_event(HotplugEvent("EP1", "removed", fake_time["now"]))
    assert signal.removed.is_set()
    signal.removed.clear()

    fake_time["now"] = 0.05  # inside the debounce window
    signal.handle_event(HotplugEvent("EP1", "removed", fake_time["now"]))
    assert not signal.removed.is_set(), "duplicate within debounce window must be dropped"


def test_debounce_allows_event_after_window_elapses(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_time = {"now": 0.0}
    monkeypatch.setattr(hotplug, "_clock", lambda: fake_time["now"])
    signal = ChannelHotplugSignal(configured_endpoint_id="EP1")

    signal.handle_event(HotplugEvent("EP1", "removed", fake_time["now"]))
    assert signal.removed.is_set()
    signal.removed.clear()

    fake_time["now"] = 1.0  # outside the debounce window
    signal.handle_event(HotplugEvent("EP1", "removed", fake_time["now"]))
    assert signal.removed.is_set()


def test_debounce_is_tracked_independently_per_reaction(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_time = {"now": 0.0}
    monkeypatch.setattr(hotplug, "_clock", lambda: fake_time["now"])
    signal = ChannelHotplugSignal(configured_endpoint_id="EP1")

    signal.handle_event(HotplugEvent("EP1", "removed", fake_time["now"]))
    assert signal.removed.is_set()

    fake_time["now"] = 0.05
    signal.handle_event(HotplugEvent("EP1", "arrived", fake_time["now"]))
    assert signal.arrived.is_set(), "debounce window for 'removed' must not suppress 'arrived'"


# --- HotplugListener wiring (FR-004) ----------------------------------------


def test_listener_dispatches_only_to_matching_endpoint() -> None:
    provider = FakeNotificationProvider()
    signal = ChannelHotplugSignal(configured_endpoint_id="EP1")
    HotplugListener(provider, signal)

    provider.emit("EP-OTHER", "removed")
    assert not signal.removed.is_set()

    provider.emit("EP1", "removed")
    assert signal.removed.is_set()


def test_listener_dispatches_arrived_only_to_matching_endpoint() -> None:
    provider = FakeNotificationProvider()
    signal = ChannelHotplugSignal(configured_endpoint_id="EP1")
    HotplugListener(provider, signal)

    provider.emit("EP-OTHER", "arrived")
    assert not signal.arrived.is_set()

    provider.emit("EP1", "arrived")
    assert signal.arrived.is_set()


def test_listener_close_delegates_to_provider() -> None:
    provider = FakeNotificationProvider()
    signal = ChannelHotplugSignal(configured_endpoint_id="EP1")
    listener = HotplugListener(provider, signal)
    listener.close()
    assert provider.closed


def test_listener_subscribe_failure_degrades_without_raising() -> None:
    """SF-019 regression: a COM/import failure inside `subscribe()` (e.g. the
    missing `comtypes.gen.MMDeviceAPILib` typelib module) must not propagate
    out of `HotplugListener.__init__` and kill the channel worker."""

    class _BrokenSubscribeProvider:
        def __init__(self) -> None:
            self.closed = False

        def subscribe(self, on_event: Callable[[HotplugEvent], None]) -> None:
            raise ModuleNotFoundError("No module named 'comtypes.gen.MMDeviceAPILib'")

        def close(self) -> None:
            self.closed = True

    provider = _BrokenSubscribeProvider()
    signal = ChannelHotplugSignal(configured_endpoint_id="EP1")

    listener = HotplugListener(provider, signal)  # must not raise

    listener.close()
    assert provider.closed


# --- get_notification_provider degrade path (FR-006) ------------------------


def test_non_windows_platform_returns_null_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hotplug.sys, "platform", "linux")
    provider = hotplug.get_notification_provider()
    assert isinstance(provider, NullNotificationProvider)


def test_windows_registration_failure_degrades_to_null_without_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hotplug.sys, "platform", "win32")

    class _BrokenModule:
        class MMDeviceNotificationProvider:
            def __init__(self) -> None:
                raise RuntimeError("COM registration failed")

    monkeypatch.setitem(sys.modules, "assistant_hub_audio.mmdevice_notifications", _BrokenModule)

    provider = hotplug.get_notification_provider()
    assert isinstance(provider, NullNotificationProvider)
    assert "comtypes" not in sys.modules
    assert "pycaw" not in sys.modules


# --- _NotificationCallbacks arity/degrade (SF-019 Issue #22, FR-001/FR-002/FR-003) ---


def test_notification_callbacks_accept_this_without_type_error() -> None:
    """Bug A regression: comtypes always dispatches STDMETHOD-declared

    interface methods with the raw `this` pointer as the first argument
    (research.md §1) - each callback must accept it without a TypeError.
    """
    events: list[HotplugEvent] = []
    callbacks = _NotificationCallbacks(events.append)

    callbacks.IMMNotificationClient_OnDeviceAdded(None, "EP1")
    callbacks.IMMNotificationClient_OnDeviceRemoved(None, "EP1")
    callbacks.IMMNotificationClient_OnDeviceStateChanged(None, "EP1", 0x1)
    callbacks.IMMNotificationClient_OnDefaultDeviceChanged(None, 0, 0, "EP1")
    callbacks.IMMNotificationClient_OnPropertyValueChanged(None, "EP1", object())

    assert len(events) == 3


def test_notification_callbacks_map_device_added_and_removed() -> None:
    events: list[HotplugEvent] = []
    callbacks = _NotificationCallbacks(events.append)

    callbacks.IMMNotificationClient_OnDeviceAdded(None, "EP1")
    callbacks.IMMNotificationClient_OnDeviceRemoved(None, "EP2")

    assert [(e.endpoint_id, e.event_type) for e in events] == [("EP1", "arrived"), ("EP2", "removed")]


def test_notification_callbacks_state_changed_notpresent_maps_to_removed() -> None:
    """SF-019 Issue #22 Bug A/FR-003: once the callback is reachable, a

    `notpresent` (0x4) state change must still translate to a `removed`
    HotplugEvent, exactly as already specified for `state_changed` in
    specs/006-sf-019-hotplug-listener/.
    """
    events: list[HotplugEvent] = []
    callbacks = _NotificationCallbacks(events.append)

    callbacks.IMMNotificationClient_OnDeviceStateChanged(None, "EP1", 0x4)

    assert len(events) == 1
    assert events[0].endpoint_id == "EP1"
    assert events[0].event_type == "removed"


def test_notification_callbacks_state_changed_active_maps_to_arrived() -> None:
    events: list[HotplugEvent] = []
    callbacks = _NotificationCallbacks(events.append)

    callbacks.IMMNotificationClient_OnDeviceStateChanged(None, "EP1", 0x1)

    assert events[0].event_type == "arrived"


def test_notification_callbacks_swallow_on_event_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """FR-002: a callback must never propagate an exception into COM."""

    def _raising_on_event(event: HotplugEvent) -> None:
        raise RuntimeError("boom")

    callbacks = _NotificationCallbacks(_raising_on_event)

    with caplog.at_level("WARNING"):
        callbacks.IMMNotificationClient_OnDeviceAdded(None, "EP1")  # must not raise
        callbacks.IMMNotificationClient_OnDeviceRemoved(None, "EP1")  # must not raise
        callbacks.IMMNotificationClient_OnDeviceStateChanged(None, "EP1", 0x4)  # must not raise

    assert sum("callback failed" in message for message in caplog.messages) == 3


# --- Isolation from endpoints.py correlation logic (US3) --------------------


def test_hotplug_module_does_not_duplicate_correlation_logic() -> None:
    assert not hasattr(hotplug, "correlate_devices")
    assert not hasattr(hotplug, "find_device_for_endpoint")
