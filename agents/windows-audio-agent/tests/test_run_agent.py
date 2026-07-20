import subprocess

import pytest

from assistant_hub_audio import capture
from assistant_hub_audio.profiles import AudioChannel, AudioProfile, DeviceSelector


class FakeProcess:
    """Popen stand-in whose poll() dies after a configurable number of calls."""

    def __init__(self, channel_id: str, fail_after_polls: int) -> None:
        self.channel_id = channel_id
        self.pid = abs(hash(channel_id)) % 60_000
        self._poll_count = 0
        self._fail_after_polls = fail_after_polls
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        self._poll_count += 1
        if self._poll_count > self._fail_after_polls:
            return 1
        return None

    def wait(self, timeout: float | None = None) -> int:
        return_code = self.poll()
        if return_code is None:
            raise subprocess.TimeoutExpired(cmd="fake", timeout=timeout or 0)
        return return_code

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True


def _channel(channel_id: str) -> AudioChannel:
    return AudioChannel(channel_id=channel_id, kind="input", selector=DeviceSelector(index=0))


def test_one_channel_failure_does_not_abort_the_others(monkeypatch: pytest.MonkeyPatch) -> None:
    """A channel dying mid-capture must not take the other channels down (P6/ADR-0007)."""
    bad = FakeProcess("bad", fail_after_polls=1)  # alive for the startup poll, dead on the 1st monitor poll
    good = FakeProcess("good", fail_after_polls=3)  # outlives several monitor iterations after "bad" dies

    fakes = iter([bad, good])
    monkeypatch.setattr(capture.subprocess, "Popen", lambda command: next(fakes))
    monkeypatch.setattr(capture.time, "sleep", lambda _seconds: None)

    profile = AudioProfile(name="test", channels=(_channel("bad"), _channel("good")))

    with pytest.raises(RuntimeError) as excinfo:
        capture.run_agent(
            session_id="s1",
            server_url="ws://example.invalid",
            profile=profile,
            record_dir=None,
        )

    message = str(excinfo.value)
    assert "bad" in message
    assert "good" in message
    # "good" was polled past the point where "bad" already died, proving the
    # monitor loop kept running instead of aborting on the first failure.
    assert good._poll_count >= 4


def test_all_channels_failing_at_startup_raises_with_all_reasons(monkeypatch: pytest.MonkeyPatch) -> None:
    first = FakeProcess("first", fail_after_polls=0)
    second = FakeProcess("second", fail_after_polls=0)

    fakes = iter([first, second])
    monkeypatch.setattr(capture.subprocess, "Popen", lambda command: next(fakes))
    monkeypatch.setattr(capture.time, "sleep", lambda _seconds: None)

    profile = AudioProfile(name="test", channels=(_channel("first"), _channel("second")))

    with pytest.raises(RuntimeError, match="All enabled audio channels failed during startup"):
        capture.run_agent(
            session_id="s1",
            server_url="ws://example.invalid",
            profile=profile,
            record_dir=None,
        )
