import os

import psutil
import pytest

from assistant_hub_audio import process_resolver
from assistant_hub_audio.process_resolver import ProcessResolution, process_is_alive, resolve_process
from assistant_hub_audio.profiles import DeviceSelector


def test_resolve_by_pid_success() -> None:
    """The test process itself always exists and belongs to the current user."""
    selector = DeviceSelector(process_id=os.getpid())

    result = resolve_process(selector)

    assert result.pid == os.getpid()
    assert result.username == psutil.Process().username()


def test_resolve_by_pid_nonexistent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(process_resolver, "_current_username", lambda: "me")

    def _raise_no_such_process(pid: int) -> None:
        raise psutil.NoSuchProcess(pid)

    monkeypatch.setattr(psutil, "Process", _raise_no_such_process)

    with pytest.raises(RuntimeError, match="does not exist"):
        resolve_process(DeviceSelector(process_id=999999))


def test_resolve_by_pid_different_user_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(process_resolver, "_current_username", lambda: "me")

    class _FakeProcess:
        def __init__(self, pid: int) -> None:
            self._pid = pid

        def name(self) -> str:
            return "other-user-app.exe"

        def username(self) -> str:
            return "someone-else"

    monkeypatch.setattr(psutil, "Process", _FakeProcess)

    with pytest.raises(RuntimeError, match="different user"):
        resolve_process(DeviceSelector(process_id=4242))


def test_resolve_by_name_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(process_resolver, "_current_username", lambda: "me")

    class _FakeEntry:
        def __init__(self, info: dict) -> None:
            self.info = info

    def _fake_process_iter(_attrs: list[str]):
        return [
            _FakeEntry({"pid": 111, "name": "chrome.exe", "username": "me"}),
            _FakeEntry({"pid": 222, "name": "notepad.exe", "username": "me"}),
        ]

    monkeypatch.setattr(psutil, "process_iter", _fake_process_iter)

    result = resolve_process(DeviceSelector(process_name="chrome.exe"))

    assert result == ProcessResolution(pid=111, name="chrome.exe", username="me")


def test_resolve_by_name_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(process_resolver, "_current_username", lambda: "me")

    class _FakeEntry:
        def __init__(self, info: dict) -> None:
            self.info = info

    monkeypatch.setattr(
        psutil,
        "process_iter",
        lambda _attrs: [_FakeEntry({"pid": 111, "name": "Chrome.EXE", "username": "me"})],
    )

    result = resolve_process(DeviceSelector(process_name="chrome.exe"))

    assert result.pid == 111


def test_resolve_by_name_zero_matches_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(process_resolver, "_current_username", lambda: "me")
    monkeypatch.setattr(psutil, "process_iter", lambda _attrs: [])

    with pytest.raises(RuntimeError, match="No process named"):
        resolve_process(DeviceSelector(process_name="ghost.exe"))


def test_resolve_by_name_multiple_matches_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(process_resolver, "_current_username", lambda: "me")

    class _FakeEntry:
        def __init__(self, info: dict) -> None:
            self.info = info

    def _fake_process_iter(_attrs: list[str]):
        return [
            _FakeEntry({"pid": 111, "name": "chrome.exe", "username": "me"}),
            _FakeEntry({"pid": 333, "name": "chrome.exe", "username": "me"}),
        ]

    monkeypatch.setattr(psutil, "process_iter", _fake_process_iter)

    with pytest.raises(RuntimeError, match="ambiguous"):
        resolve_process(DeviceSelector(process_name="chrome.exe"))


def test_resolve_by_name_ignores_other_users(monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-011: a process with a matching name but a different owner is never a match."""
    monkeypatch.setattr(process_resolver, "_current_username", lambda: "me")

    class _FakeEntry:
        def __init__(self, info: dict) -> None:
            self.info = info

    def _fake_process_iter(_attrs: list[str]):
        return [
            _FakeEntry({"pid": 111, "name": "chrome.exe", "username": "someone-else"}),
            _FakeEntry({"pid": 222, "name": "chrome.exe", "username": "me"}),
        ]

    monkeypatch.setattr(psutil, "process_iter", _fake_process_iter)

    result = resolve_process(DeviceSelector(process_name="chrome.exe"))

    assert result.pid == 222


def test_process_is_alive_true_for_current_process() -> None:
    assert process_is_alive(os.getpid()) is True


def test_process_is_alive_false_for_nonexistent_pid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(psutil, "pid_exists", lambda pid: False)

    assert process_is_alive(999999) is False
