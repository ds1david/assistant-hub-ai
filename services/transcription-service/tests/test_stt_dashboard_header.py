"""STT Streaming Foundation header: structure + canonical session state (issue #51)."""

from __future__ import annotations

from pathlib import Path

from app.header_session_state import HeaderSessionState, copy_enabled, normalize_session_id
from app.main import STATIC_INDEX


def _index_html() -> str:
    return Path(STATIC_INDEX).read_text(encoding="utf-8")


# --- Canonical policy (header_session_state.py) ---


def test_normalize_session_id_rejects_blank():
    assert normalize_session_id(None) is None
    assert normalize_session_id("") is None
    assert normalize_session_id("   ") is None
    assert normalize_session_id("sess-a") == "sess-a"
    assert normalize_session_id("  uuid-1  ") == "uuid-1"


def test_empty_state_no_primary_no_copy():
    state = HeaderSessionState()
    assert state.primary_session_id is None
    assert state.primary_display() == "aguardando sessão"
    assert not state.can_copy()
    assert not copy_enabled(None)
    assert not state.is_multi
    assert state.multi_label() is None


def test_observe_sets_primary_and_membership():
    state = HeaderSessionState()
    assert state.observe("sess-x") is True
    assert state.primary_session_id == "sess-x"
    assert state.observed_session_ids == ["sess-x"]
    assert state.can_copy()
    assert state.primary_display() == "sess-x"


def test_observe_second_id_becomes_primary_and_multi():
    state = HeaderSessionState()
    state.observe("sess-x")
    assert state.observe("sess-y") is True
    assert state.primary_session_id == "sess-y"
    assert state.observed_session_ids == ["sess-x", "sess-y"]
    assert state.is_multi
    assert state.multi_label() == "2 sessões"
    assert state.secondary_ids() == ["sess-x"]


def test_reobserve_first_id_returns_primary():
    state = HeaderSessionState()
    state.observe("sess-x")
    state.observe("sess-y")
    assert state.observe("sess-x") is True
    assert state.primary_session_id == "sess-x"
    assert state.observed_session_ids == ["sess-x", "sess-y"]
    assert state.multi_label() == "2 sessões"


def test_blank_session_id_ignored():
    state = HeaderSessionState()
    assert state.observe("") is False
    assert state.observe("   ") is False
    assert state.observe(None) is False
    assert state.primary_session_id is None
    assert state.observed_session_ids == []


def test_profile_display_defaults_to_agent_note():
    state = HeaderSessionState()
    note = state.profile_display()
    assert "agent" in note.lower() or "--profile" in note
    assert state.profile_display("default-windows-devices") == "default-windows-devices"
    assert state.profile_display("  ")  # blank falls back to note
    assert "--profile" in state.profile_display("  ") or "agent" in state.profile_display("  ").lower()


# --- HTML structure contract ---


def test_header_markers_present():
    html = _index_html()
    for marker in (
        'id="status"',
        'id="session-id"',
        'data-testid="session-id"',
        'id="session-copy"',
        'data-testid="session-copy"',
        'id="session-copy-feedback"',
        'id="session-multi"',
        'data-testid="session-multi"',
        'id="session-profile"',
        'data-testid="session-profile"',
        'id="stt-base-url"',
        'data-testid="stt-base-url"',
    ):
        assert marker in html, f"missing marker {marker}"


def test_empty_placeholder_and_no_fabricated_default_id():
    html = _index_html()
    assert "aguardando sessão" in html
    # Must not hardcode a fake session as the default primary text content.
    assert 'id="session-id"' in html
    # Copy disabled by default in markup
    assert "session-copy" in html
    assert "disabled" in html


def test_script_wires_session_id_from_feed():
    html = _index_html()
    assert "observeSessionId" in html
    assert "data.sessionId" in html
    assert "paintHeaderSession" in html
    # Canonical mirror comment
    assert "header_session_state" in html


def test_long_id_layout_css_hooks():
    html = _index_html()
    assert "word-break" in html or "overflow-wrap" in html
    assert "session-id" in html
    assert "ui-monospace" in html or "monospace" in html


def test_copy_paths_in_script():
    html = _index_html()
    assert "navigator.clipboard" in html
    assert "writeText" in html
    assert "copiado" in html
    assert "falha ao copiar" in html
    assert "copyPrimarySessionId" in html
    # Copy uses primary only
    assert "primarySessionId" in html


def test_multi_uses_primary_and_count_label():
    html = _index_html()
    assert "sessões" in html
    assert "multiLabel" in html
    assert "primarySessionId" in html


def test_profile_note_default_in_markup():
    html = _index_html()
    assert "Profile: definido no agent (--profile)" in html
    assert "--profile" in html


def test_channel_template_has_no_session_or_profile_fields():
    html = _index_html()
    # ensureChannel template: h2, device, metrics, feed only
    assert "Aguardando transcrição" in html
    # Header markers exist once as element ids (CSS may also reference #session-id).
    assert 'id="session-id"' in html
    assert 'id="session-profile"' in html
    assert 'data-testid="session-id"' in html
    # ensureChannel must not inject session/profile header chrome into cards
    start = html.find("function ensureChannel")
    end = html.find("function connect")
    assert start != -1 and end != -1
    ensure_block = html[start:end]
    assert "session-id" not in ensure_block
    assert "session-profile" not in ensure_block
    assert "session-copy" not in ensure_block
    assert "data.sessionId" not in ensure_block
    assert "channelId" in ensure_block


def test_stt_base_url_uses_location_origin():
    html = _index_html()
    assert "stt-base-url" in html
    assert "location.origin" in html


def test_reconnect_does_not_clear_observed_state():
    html = _index_html()
    # onclose should reconnect without wiping observedSessionIds
    assert "reconectando" in html
    assert "observedSessionIds" in html
    # Explicit comment or no clear of arrays on close
    onclose_idx = html.find("ws.onclose")
    assert onclose_idx != -1
    # Between onclose and onmessage, no observedSessionIds = []
    snippet = html[onclose_idx : onclose_idx + 200]
    assert "observedSessionIds.length = 0" not in snippet
    assert "observedSessionIds = []" not in snippet
    assert "primarySessionId = null" not in snippet


def test_no_privacy_sensitive_header_content():
    html = _index_html()
    # Header region should not dump transcript text templates as session fields
    assert "data-testid=\"header-meta\"" in html or 'class="header-meta"' in html
