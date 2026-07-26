"""Canonical header session-state policy for the STT Streaming Foundation dashboard.

UI JavaScript in ``static/index.html`` MUST mirror these rules (analyze U1).
Does not persist; does not invent profile or session ids from the browser URL.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def normalize_session_id(raw: object) -> str | None:
    """Return a non-empty session id, or None if blank/invalid."""
    if raw is None:
        return None
    if not isinstance(raw, str):
        raw = str(raw)
    value = raw.strip()
    return value if value else None


def copy_enabled(primary_session_id: str | None) -> bool:
    """Copy control is enabled only when a primary id is present."""
    return bool(primary_session_id and primary_session_id.strip())


@dataclass
class HeaderSessionState:
    """In-memory observe/primary/multi state for the STT dashboard header."""

    observed_session_ids: list[str] = field(default_factory=list)
    primary_session_id: str | None = None

    def observe(self, session_id: object) -> bool:
        """Record a sessionId from a transcript feed event.

        Returns True if state changed (new primary and/or new membership).
        Blank/whitespace ids are ignored (FR-009/FR-014).
        """
        sid = normalize_session_id(session_id)
        if sid is None:
            return False

        changed = False
        if sid not in self.observed_session_ids:
            self.observed_session_ids.append(sid)
            changed = True
        if self.primary_session_id != sid:
            self.primary_session_id = sid
            changed = True
        return changed

    @property
    def multi_count(self) -> int:
        return len(self.observed_session_ids)

    @property
    def is_multi(self) -> bool:
        return self.multi_count > 1

    def multi_label(self) -> str | None:
        """Label for #session-multi when more than one id observed."""
        if not self.is_multi:
            return None
        n = self.multi_count
        return f"{n} sessões"

    def secondary_ids(self) -> list[str]:
        primary = self.primary_session_id
        return [s for s in self.observed_session_ids if s != primary]

    def primary_display(self, empty_placeholder: str = "aguardando sessão") -> str:
        if self.primary_session_id:
            return self.primary_session_id
        return empty_placeholder

    def can_copy(self) -> bool:
        return copy_enabled(self.primary_session_id)

    def profile_display(self, profile_name: str | None = None) -> str:
        """FR-006 note by default; FR-005 MAY only if a real name is supplied."""
        name = normalize_session_id(profile_name) if profile_name is not None else None
        if name:
            return name
        return "Profile: definido no agent (--profile)"
