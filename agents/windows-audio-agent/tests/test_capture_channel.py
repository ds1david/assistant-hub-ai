import threading
from typing import Any

import pytest

from assistant_hub_audio import capture, process_capture
from assistant_hub_audio.hotplug import ChannelHotplugSignal, HotplugEvent
from assistant_hub_audio.process_resolver import ProcessResolution
from assistant_hub_audio.profiles import AudioChannel, DeviceSelector


def _channel(channel_id: str = "ch") -> AudioChannel:
    return AudioChannel(channel_id=channel_id, kind="input", selector=DeviceSelector(index=0))


def _channel_with_endpoint(endpoint_id: str, channel_id: str = "ch") -> AudioChannel:
    return AudioChannel(
        channel_id=channel_id, kind="input", selector=DeviceSelector(endpoint_id=endpoint_id)
    )


def _channel_with_process_name(process_name: str, channel_id: str = "app_audio") -> AudioChannel:
    return AudioChannel(
        channel_id=channel_id, kind="loopback", selector=DeviceSelector(process_name=process_name)
    )


def _fake_device(endpoint_id: str = "EP1") -> dict[str, Any]:
    return {
        "index": 0,
        "name": "Fake Mic",
        "hostApi": 2,
        "maxInputChannels": 1,
        "maxOutputChannels": 0,
        "defaultSampleRate": 16_000,
        "isLoopbackDevice": False,
        "endpointId": endpoint_id,
    }


class _FakeStream:
    def __init__(self, on_read: Any = None) -> None:
        self.read_count = 0
        self.on_read = on_read

    def read(self, chunk_size: int, exception_on_overflow: bool = False) -> bytes:
        self.read_count += 1
        if self.on_read is not None:
            self.on_read(self.read_count)
        return b"\x00\x00" * chunk_size

    def stop_stream(self) -> None:
        return None

    def close(self) -> None:
        return None


class _FakePyAudioModule:
    paInt16 = 8  # arbitrary sentinel; the fake stream ignores the format


class _FakeAudio:
    def __init__(self, stream: _FakeStream) -> None:
        self._stream = stream

    def open(self, **_kwargs: Any) -> _FakeStream:
        return self._stream


class _FakeWebsocket:
    def send(self, _data: bytes) -> None:
        return None


class _FakeConnection:
    def __enter__(self) -> _FakeWebsocket:
        return _FakeWebsocket()

    def __exit__(self, *_exc: Any) -> bool:
        return False


def _patch_capture_once_dependencies(monkeypatch: pytest.MonkeyPatch, endpoint_id: str) -> None:
    monkeypatch.setattr(capture, "resolve_device", lambda audio, channel: _fake_device(endpoint_id))
    monkeypatch.setattr(capture, "connect", lambda *_a, **_k: _FakeConnection())
    monkeypatch.setattr(capture, "pyaudio", _FakePyAudioModule, raising=False)


# --- Process-based channels (SF-020) -----------------------------------------


class _FakeProcessStream:
    def __init__(self, on_read: Any = None) -> None:
        self.read_count = 0
        self.on_read = on_read
        self.closed = False

    def read(self, chunk_size: int, exception_on_overflow: bool = False) -> bytes:
        self.read_count += 1
        if self.on_read is not None:
            self.on_read(self.read_count)
        return b"\x00\x00" * chunk_size

    def stop_stream(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True


def test_process_channel_endpoint_query_has_no_index_or_endpoint_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-003/data-model.md: device.index and device.endpointId stay absent

    (never the literal string "None") for a process-based channel - only
    transcript-event.v2's already-nullable device fields are used, no schema
    change (research.md §5)."""
    captured_urls: list[str] = []

    def _fake_connect(url: str, **_kwargs: Any) -> _FakeConnection:
        captured_urls.append(url)
        return _FakeConnection()

    resolution = ProcessResolution(pid=4242, name="chrome.exe", username="me")
    stop_event = threading.Event()

    def _on_read(count: int) -> None:
        if count >= 1:
            stop_event.set()

    stream = _FakeProcessStream(on_read=_on_read)
    monkeypatch.setattr(capture, "resolve_process", lambda selector: resolution)
    monkeypatch.setattr(capture, "process_is_alive", lambda pid: True)
    monkeypatch.setattr(capture, "connect", _fake_connect)
    monkeypatch.setattr(process_capture, "ProcessLoopbackStream", lambda *_a, **_k: stream)

    capture._capture_once(
        audio=None,
        channel=_channel_with_process_name("chrome.exe"),
        session_id="s1",
        server_url="ws://example.invalid",
        stop_event=stop_event,
        record_path=None,
        chunk_size=1024,
        signal=ChannelHotplugSignal(configured_endpoint_id=None),
        on_resolved=lambda: None,
    )

    assert len(captured_urls) == 1
    assert "deviceIndex=" not in captured_urls[0]
    assert "endpointId=" not in captured_urls[0]
    assert "sourceType=system" in captured_urls[0]
    assert "chrome.exe" in captured_urls[0]
    assert "4242" in captured_urls[0]


def test_process_channel_isolated_from_device_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-002/ADR-0007: a process-based channel and a device-based channel

    running concurrently never share stream/state."""
    process_stop = threading.Event()
    device_stop = threading.Event()

    process_stream = _FakeProcessStream(on_read=lambda count: process_stop.set() if count >= 1 else None)
    device_stream = _FakeStream(on_read=lambda count: device_stop.set() if count >= 1 else None)

    monkeypatch.setattr(capture, "resolve_process", lambda selector: ProcessResolution(4242, "chrome.exe", "me"))
    monkeypatch.setattr(capture, "process_is_alive", lambda pid: True)
    monkeypatch.setattr(process_capture, "ProcessLoopbackStream", lambda *_a, **_k: process_stream)
    monkeypatch.setattr(capture, "resolve_device", lambda audio, channel: _fake_device("EP1"))
    monkeypatch.setattr(capture, "pyaudio", _FakePyAudioModule, raising=False)
    monkeypatch.setattr(capture, "connect", lambda *_a, **_k: _FakeConnection())

    capture._capture_once(
        audio=None,
        channel=_channel_with_process_name("chrome.exe"),
        session_id="s1",
        server_url="ws://example.invalid",
        stop_event=process_stop,
        record_path=None,
        chunk_size=1024,
        signal=ChannelHotplugSignal(configured_endpoint_id=None),
        on_resolved=lambda: None,
    )
    capture._capture_once(
        audio=_FakeAudio(device_stream),
        channel=_channel_with_endpoint("EP1"),
        session_id="s1",
        server_url="ws://example.invalid",
        stop_event=device_stop,
        record_path=None,
        chunk_size=1024,
        signal=ChannelHotplugSignal(configured_endpoint_id="EP1"),
        on_resolved=lambda: None,
    )

    assert process_stream.read_count == 1
    assert device_stream.read_count == 1
    assert process_stream.closed
    # _FakeStream has no `closed` attribute - close() is a no-op there, so
    # only asserting no exception/interference is the isolation proof.


def test_process_channel_pid_exit_is_permanent(monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-006: a channel selected by PID never re-follows a new instance."""
    calls = {"count": 0}

    def _fake_capture_once(*, stop_event: threading.Event, **_kwargs: Any) -> None:
        calls["count"] += 1
        raise capture.ProcessExitedError("process exited")

    monkeypatch.setattr(capture, "_capture_once", _fake_capture_once)

    channel = AudioChannel(channel_id="ch", kind="loopback", selector=DeviceSelector(process_id=4242))

    with pytest.raises(capture.ProcessExitedError):
        capture.capture_channel(
            audio=None,
            channel=channel,
            session_id="s1",
            server_url="ws://example.invalid",
            stop_event=threading.Event(),
            record_path=None,
        )
    assert calls["count"] == 1


def test_process_channel_name_exit_retries_immediately(monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-012: a channel selected by name re-resolves and resumes after the

    process exits, without waiting out the generic reconnect backoff."""
    calls = {"count": 0}

    def _fake_capture_once(*, stop_event: threading.Event, **_kwargs: Any) -> None:
        calls["count"] += 1
        if calls["count"] == 1:
            raise capture.ProcessExitedError("process exited")
        stop_event.set()

    monkeypatch.setattr(capture, "_capture_once", _fake_capture_once)

    channel = _channel_with_process_name("chrome.exe")
    stop_event = threading.Event()

    capture.capture_channel(
        audio=None,
        channel=channel,
        session_id="s1",
        server_url="ws://example.invalid",
        stop_event=stop_event,
        record_path=None,
    )
    assert calls["count"] == 2


def test_process_channel_hotplug_events_never_affect_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-007/FR-008: a process-based channel's `ChannelHotplugSignal` has

    `configured_endpoint_id=None` (its selector has no endpointId), so any
    hot-plug event (SF-019) for any device is always ignored - the device
    channel's own hot-plug handling (already covered by every pre-existing
    SF-019 test in this file, untouched by this feature) is what actually
    proves the "coexist without interference" half of FR-007."""
    calls = {"count": 0}

    def _fake_capture_once(
        *, signal: ChannelHotplugSignal, stop_event: threading.Event, **_kwargs: Any
    ) -> None:
        calls["count"] += 1
        signal.handle_event(HotplugEvent("EP-SOME-DEVICE", "removed", 0.0))
        signal.handle_event(HotplugEvent("EP-SOME-DEVICE", "arrived", 0.0))
        assert not signal.removed.is_set()
        assert not signal.arrived.is_set()
        stop_event.set()

    monkeypatch.setattr(capture, "_capture_once", _fake_capture_once)

    capture.capture_channel(
        audio=None,
        channel=_channel_with_process_name("chrome.exe"),
        session_id="s1",
        server_url="ws://example.invalid",
        stop_event=threading.Event(),
        record_path=None,
    )
    assert calls["count"] == 1


def test_process_channel_resolution_failure_is_always_permanent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-005/FR-012: unlike a device's transient notpresent handling, a

    process-based channel's resolution failure is always permanent - even on
    a later attempt after a prior successful capture (ambiguous replacement,
    FR-012), not just at startup."""
    calls = {"count": 0}

    def _fake_capture_once(*, stop_event: threading.Event, **_kwargs: Any) -> None:
        calls["count"] += 1
        raise capture.EndpointResolutionError("ambiguous process name")

    monkeypatch.setattr(capture, "_capture_once", _fake_capture_once)

    channel = _channel_with_process_name("chrome.exe")

    with pytest.raises(capture.EndpointResolutionError):
        capture.capture_channel(
            audio=None,
            channel=channel,
            session_id="s1",
            server_url="ws://example.invalid",
            stop_event=threading.Event(),
            record_path=None,
        )
    assert calls["count"] == 1


def test_endpoint_resolution_error_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-007/P7: a permanent resolution failure must not loop forever with a
    reconnect backoff — the worker should exit so run_agent can mark the
    channel as failed instead of silently retrying forever (CHK021)."""
    calls = {"count": 0}

    def _fake_capture_once(**_kwargs: Any) -> None:
        calls["count"] += 1
        raise capture.EndpointResolutionError("endpoint not found")

    monkeypatch.setattr(capture, "_capture_once", _fake_capture_once)

    with pytest.raises(capture.EndpointResolutionError):
        capture.capture_channel(
            audio=None,
            channel=_channel(),
            session_id="s1",
            server_url="ws://example.invalid",
            stop_event=threading.Event(),
            record_path=None,
        )
    assert calls["count"] == 1


def test_endpoint_resolution_error_after_prior_success_is_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SF-019 Issue #22 Bug B/FR-004: once a channel has captured successfully

    at least once, a later resolution failure (e.g. a transient `notpresent`
    right after an unplug) must not kill the worker - it falls back to the
    generic reconnect backoff instead of exiting, unlike a resolution failure
    that has never succeeded (test_endpoint_resolution_error_is_not_retried,
    FR-005, unaffected by this change).
    """
    calls = {"count": 0}

    def _fake_capture_once(
        *, stop_event: threading.Event, on_resolved: Any, **_kwargs: Any
    ) -> None:
        calls["count"] += 1
        if calls["count"] == 1:
            on_resolved()  # mirrors the real _capture_once signaling success right after resolve
            return
        if calls["count"] == 2:
            raise capture.EndpointResolutionError("endpoint exists but is notpresent")
        stop_event.set()

    monkeypatch.setattr(capture, "_capture_once", _fake_capture_once)

    stop_event = threading.Event()
    stop_event.wait = lambda timeout=None: False  # type: ignore[method-assign]

    capture.capture_channel(
        audio=None,
        channel=_channel(),
        session_id="s1",
        server_url="ws://example.invalid",
        stop_event=stop_event,
        record_path=None,
    )
    assert calls["count"] == 3


def test_notpresent_retry_resumes_on_arrival(monkeypatch: pytest.MonkeyPatch) -> None:
    """SF-019 Issue #22 Bug B/FR-004 integration: after a transient

    `notpresent` failure following a prior successful capture, an arrival
    notification wakes the reconnect wait and resumes on the same
    `endpointId` - the same behavior already specified for
    `EndpointRemovedError` (spec 006,
    test_capture_channel_resumes_on_arrival_after_removal).
    """
    channel = _channel_with_endpoint("EP1")
    seen_endpoint_ids: list[str | None] = []

    def _fake_capture_once(
        *,
        channel: AudioChannel,
        signal: ChannelHotplugSignal,
        stop_event: threading.Event,
        on_resolved: Any,
        **_kwargs: Any,
    ) -> None:
        seen_endpoint_ids.append(channel.selector.endpoint_id)
        if len(seen_endpoint_ids) == 1:
            on_resolved()  # mirrors the real _capture_once signaling success right after resolve
            return
        if len(seen_endpoint_ids) == 2:
            signal.handle_event(HotplugEvent("EP1", "arrived", 0.0))
            raise capture.EndpointResolutionError("endpoint exists but is notpresent")
        stop_event.set()

    monkeypatch.setattr(capture, "_capture_once", _fake_capture_once)
    stop_event = threading.Event()
    stop_event.wait = lambda timeout=None: False  # type: ignore[method-assign]

    capture.capture_channel(
        audio=None,
        channel=channel,
        session_id="s1",
        server_url="ws://example.invalid",
        stop_event=stop_event,
        record_path=None,
    )
    assert seen_endpoint_ids == ["EP1", "EP1", "EP1"]


def test_transient_error_is_retried_with_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-resolution error (e.g. a dropped WebSocket) is transient and
    should keep retrying instead of killing the channel."""
    calls = {"count": 0}

    def _fake_capture_once(*, stop_event: threading.Event, **_kwargs: Any) -> None:
        calls["count"] += 1
        if calls["count"] < 3:
            raise ConnectionError("ws dropped")
        stop_event.set()

    monkeypatch.setattr(capture, "_capture_once", _fake_capture_once)

    stop_event = threading.Event()
    stop_event.wait = lambda timeout=None: False  # type: ignore[method-assign]

    capture.capture_channel(
        audio=None,
        channel=_channel(),
        session_id="s1",
        server_url="ws://example.invalid",
        stop_event=stop_event,
        record_path=None,
    )
    assert calls["count"] == 3


def test_capture_once_raises_endpoint_removed_error_on_removal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """US1 Acceptance Scenario 1 / SC-001: a removal notification ends the
    attempt immediately (via signal.removed), not via a stream.read failure."""
    _patch_capture_once_dependencies(monkeypatch, "EP1")
    signal = ChannelHotplugSignal(configured_endpoint_id="EP1")

    def _on_read(count: int) -> None:
        if count == 2:
            signal.removed.set()  # simulate the native listener firing mid-capture

    stream = _FakeStream(on_read=_on_read)
    audio = _FakeAudio(stream)
    stop_event = threading.Event()

    with pytest.raises(capture.EndpointRemovedError):
        capture._capture_once(
            audio=audio,
            channel=_channel_with_endpoint("EP1"),
            session_id="s1",
            server_url="ws://example.invalid",
            stop_event=stop_event,
            record_path=None,
            chunk_size=1024,
            signal=signal,
            on_resolved=lambda: None,
        )
    # Ends right after the 2nd read set the flag, on the 3rd loop check -
    # not after a stream failure, and well before any generic backoff.
    assert stream.read_count == 2


def test_capture_once_ignores_removal_for_foreign_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """US1 Acceptance Scenario 2: a removal notification for an endpointId
    that isn't this channel's own must not affect its capture."""
    _patch_capture_once_dependencies(monkeypatch, "EP1")
    signal = ChannelHotplugSignal(configured_endpoint_id="EP1")
    signal.handle_event(HotplugEvent(endpoint_id="EP-OTHER", event_type="removed", timestamp=0.0))
    assert not signal.removed.is_set()

    stop_event = threading.Event()

    def _on_read(count: int) -> None:
        if count >= 3:
            stop_event.set()

    stream = _FakeStream(on_read=_on_read)
    audio = _FakeAudio(stream)

    capture._capture_once(
        audio=audio,
        channel=_channel_with_endpoint("EP1"),
        session_id="s1",
        server_url="ws://example.invalid",
        stop_event=stop_event,
        record_path=None,
        chunk_size=1024,
        signal=signal,
        on_resolved=lambda: None,
    )
    assert stream.read_count >= 3
    assert not signal.removed.is_set()


def test_capture_channel_resumes_on_arrival_after_removal(monkeypatch: pytest.MonkeyPatch) -> None:
    """US2 Acceptance Scenario 1 / SC-002 / SC-004: removed then arrived for
    the same endpointId resumes capture on that same endpoint, immediately -
    not after the reconnect backoff ceiling, and never on a different device."""
    channel = _channel_with_endpoint("EP1")
    seen_endpoint_ids: list[str | None] = []

    def _fake_capture_once(
        *, channel: AudioChannel, signal: ChannelHotplugSignal, stop_event: threading.Event, **_kwargs: Any
    ) -> None:
        seen_endpoint_ids.append(channel.selector.endpoint_id)
        if len(seen_endpoint_ids) == 1:
            signal.handle_event(HotplugEvent("EP1", "arrived", 0.0))
            raise capture.EndpointRemovedError("removed")
        stop_event.set()

    monkeypatch.setattr(capture, "_capture_once", _fake_capture_once)
    stop_event = threading.Event()
    stop_event.wait = lambda timeout=None: False  # type: ignore[method-assign]

    capture.capture_channel(
        audio=None,
        channel=channel,
        session_id="s1",
        server_url="ws://example.invalid",
        stop_event=stop_event,
        record_path=None,
    )
    assert seen_endpoint_ids == ["EP1", "EP1"]


def test_capture_channel_ignores_arrival_for_foreign_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """US2 Acceptance Scenario 2: an arrival for a different endpointId must
    not affect this channel's reconnect wait."""
    channel = _channel_with_endpoint("EP1")
    calls = {"count": 0}

    def _fake_capture_once(
        *, signal: ChannelHotplugSignal, stop_event: threading.Event, **_kwargs: Any
    ) -> None:
        calls["count"] += 1
        if calls["count"] == 1:
            signal.handle_event(HotplugEvent("EP-OTHER", "arrived", 0.0))
            assert not signal.arrived.is_set()
            raise capture.EndpointRemovedError("removed")
        stop_event.set()

    monkeypatch.setattr(capture, "_capture_once", _fake_capture_once)
    stop_event = threading.Event()
    stop_event.wait = lambda timeout=None: False  # type: ignore[method-assign]

    capture.capture_channel(
        audio=None,
        channel=channel,
        session_id="s1",
        server_url="ws://example.invalid",
        stop_event=stop_event,
        record_path=None,
    )
    assert calls["count"] == 2


def test_capture_channel_burst_of_removed_events_triggers_one_reaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """US2 Acceptance Scenario 3 / FR-005 / SC-005: a burst of duplicate
    notifications for the same endpointId triggers at most one reaction,
    verified by call count on the underlying Event.set()."""
    channel = _channel_with_endpoint("EP1")
    calls = {"count": 0}
    set_calls = {"count": 0}

    def _fake_capture_once(
        *, signal: ChannelHotplugSignal, stop_event: threading.Event, **_kwargs: Any
    ) -> None:
        calls["count"] += 1
        if calls["count"] == 1:
            original_set = signal.removed.set

            def _counting_set() -> None:
                set_calls["count"] += 1
                original_set()

            signal.removed.set = _counting_set  # type: ignore[method-assign]
            for _ in range(5):
                signal.handle_event(HotplugEvent("EP1", "removed", 0.0))
            raise capture.EndpointRemovedError("removed")
        stop_event.set()

    monkeypatch.setattr(capture, "_capture_once", _fake_capture_once)
    stop_event = threading.Event()
    stop_event.wait = lambda timeout=None: False  # type: ignore[method-assign]

    capture.capture_channel(
        audio=None,
        channel=channel,
        session_id="s1",
        server_url="ws://example.invalid",
        stop_event=stop_event,
        record_path=None,
    )
    assert set_calls["count"] == 1, "debounce must collapse the 5-event burst into one reaction"
    assert calls["count"] == 2


def test_wait_for_reconnect_prioritizes_stop_over_pending_arrival() -> None:
    """Edge case / FR-008: stop_event always wins over a pending arrival."""
    signal = ChannelHotplugSignal(configured_endpoint_id="EP1")
    signal.arrived.set()
    stop_event = threading.Event()
    stop_event.set()

    outcome = capture._wait_for_reconnect(stop_event, signal, delay=1.0)
    assert outcome == "stop"


def test_capture_channel_does_not_restart_after_deliberate_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Edge case / FR-008: an arrival delivered after stop_event is already
    set must not restart a deliberately stopped channel."""
    channel = _channel_with_endpoint("EP1")
    calls = {"count": 0}

    def _fake_capture_once(
        *, signal: ChannelHotplugSignal, stop_event: threading.Event, **_kwargs: Any
    ) -> None:
        calls["count"] += 1
        signal.handle_event(HotplugEvent("EP1", "arrived", 0.0))
        stop_event.set()  # the supervisor decided to stop this worker
        raise capture.EndpointRemovedError("removed")

    monkeypatch.setattr(capture, "_capture_once", _fake_capture_once)
    stop_event = threading.Event()
    stop_event.wait = lambda timeout=None: False  # type: ignore[method-assign]

    capture.capture_channel(
        audio=None,
        channel=channel,
        session_id="s1",
        server_url="ws://example.invalid",
        stop_event=stop_event,
        record_path=None,
    )
    assert calls["count"] == 1, "must not retry despite a pending arrival once stopped"


def test_capture_channel_arrival_with_failed_reresolution_falls_back_to_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Edge case / FR-003 / Clarifications Q3: if re-resolution still fails
    right after an arrival wake-up, fall back to the generic backoff without
    permanent termination, and without ever substituting another device."""
    channel = _channel_with_endpoint("EP1")
    seen_endpoint_ids: list[str | None] = []

    def _fake_capture_once(
        *, channel: AudioChannel, signal: ChannelHotplugSignal, stop_event: threading.Event, **_kwargs: Any
    ) -> None:
        seen_endpoint_ids.append(channel.selector.endpoint_id)
        count = len(seen_endpoint_ids)
        if count == 1:
            signal.handle_event(HotplugEvent("EP1", "arrived", 0.0))
            raise capture.EndpointRemovedError("removed")
        if count == 2:
            raise capture.EndpointResolutionError("still not correlated")
        stop_event.set()

    monkeypatch.setattr(capture, "_capture_once", _fake_capture_once)
    stop_event = threading.Event()
    stop_event.wait = lambda timeout=None: False  # type: ignore[method-assign]

    capture.capture_channel(
        audio=None,
        channel=channel,
        session_id="s1",
        server_url="ws://example.invalid",
        stop_event=stop_event,
        record_path=None,
    )
    assert seen_endpoint_ids == ["EP1", "EP1", "EP1"], "must never substitute a different device"
