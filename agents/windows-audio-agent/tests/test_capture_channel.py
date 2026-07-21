import threading
from typing import Any

import pytest

from assistant_hub_audio import capture
from assistant_hub_audio.hotplug import ChannelHotplugSignal, HotplugEvent
from assistant_hub_audio.profiles import AudioChannel, DeviceSelector


def _channel(channel_id: str = "ch") -> AudioChannel:
    return AudioChannel(channel_id=channel_id, kind="input", selector=DeviceSelector(index=0))


def _channel_with_endpoint(endpoint_id: str, channel_id: str = "ch") -> AudioChannel:
    return AudioChannel(
        channel_id=channel_id, kind="input", selector=DeviceSelector(endpoint_id=endpoint_id)
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
