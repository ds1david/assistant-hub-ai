import threading
from typing import Any

import pytest

from assistant_hub_audio import capture
from assistant_hub_audio.profiles import AudioChannel, DeviceSelector


def _channel(channel_id: str = "ch") -> AudioChannel:
    return AudioChannel(channel_id=channel_id, kind="input", selector=DeviceSelector(index=0))


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
