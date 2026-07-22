"""Pure process resolution for process-based audio capture (SF-020).

No `comtypes` import here - only `psutil`, which is cross-platform - so this
module is testable on any OS, unlike `process_capture.py` (Windows-only COM
activation). Mirrors the fail-fast-without-silent-fallback convention already
used by `endpoints.find_device_for_endpoint` (FR-005/FR-011): callers get a
plain `RuntimeError` with an actionable message, never a silent match.
"""

from __future__ import annotations

from dataclasses import dataclass

import psutil

from .profiles import DeviceSelector


@dataclass(frozen=True)
class ProcessResolution:
    pid: int
    name: str
    username: str


def process_is_alive(pid: int) -> bool:
    return psutil.pid_exists(pid)


def _current_username() -> str:
    return psutil.Process().username()


def resolve_process(selector: DeviceSelector) -> ProcessResolution:
    """Resolve a process-based `DeviceSelector` to a single running process.

    Raises `RuntimeError` when the target cannot be resolved uniquely: the
    PID does not exist, the name matches zero or more than one process, or
    the resolved process does not belong to the current user/session
    (FR-005/FR-011 - no silent fallback, ever).
    """
    current_user = _current_username()

    if selector.process_id is not None:
        pid = selector.process_id
        try:
            proc = psutil.Process(pid)
            name = proc.name()
            username = proc.username()
        except psutil.NoSuchProcess as exc:
            raise RuntimeError(f"Process id {pid} does not exist.") from exc
        except psutil.AccessDenied as exc:
            raise RuntimeError(
                f"Process id {pid} exists but its owner could not be determined "
                "(access denied) - not eligible for capture."
            ) from exc
        if username != current_user:
            raise RuntimeError(
                f"Process id {pid} ({name!r}) belongs to a different user ({username!r}); "
                f"only processes owned by the current user ({current_user!r}) can be captured."
            )
        return ProcessResolution(pid=pid, name=name, username=username)

    assert selector.process_name is not None
    target_name = selector.process_name.casefold()
    matches: list[ProcessResolution] = []
    for proc in psutil.process_iter(["pid", "name", "username"]):
        try:
            info = proc.info
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        name = info.get("name")
        username = info.get("username")
        if name is None or username is None:
            continue
        if name.casefold() == target_name and username == current_user:
            matches.append(ProcessResolution(pid=info["pid"], name=name, username=username))

    if not matches:
        raise RuntimeError(
            f"No process named {selector.process_name!r} found for the current user "
            f"({current_user!r}). Run a process list and adjust the profile."
        )
    if len(matches) > 1:
        pids = ", ".join(str(match.pid) for match in matches)
        raise RuntimeError(
            f"Process selector processName={selector.process_name!r} is ambiguous; "
            f"matched pids: {pids}"
        )
    return matches[0]
