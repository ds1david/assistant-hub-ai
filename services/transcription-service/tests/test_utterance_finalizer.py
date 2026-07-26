"""Unit tests for UtteranceFinalizer (issue #55). No GPU / no WS."""

from __future__ import annotations

import pytest

from app.utterance import UtteranceFinalizer


def test_open_partials_then_idle_close_exactly_one_final() -> None:
    f = UtteranceFinalizer(idle_windows=1, max_open_seconds=45.0)
    t0 = 100.0

    a1 = f.on_text("ola mundo", now=t0)
    assert a1.kind == "emit_partial"
    assert a1.text == "ola mundo"
    assert f.state == "open"

    a2 = f.on_text("ola mundo completo", now=t0 + 1)
    assert a2.kind == "emit_partial"
    assert f.partial_count == 2

    a3 = f.on_no_result(now=t0 + 2)
    assert a3.kind == "emit_final"
    assert a3.text == "ola mundo completo"
    assert a3.reason == "idle"
    assert f.state == "idle"
    assert f.finals_emitted == 1
    assert f.idle_closes == 1

    # Second no-result while idle: nothing
    assert f.on_no_result(now=t0 + 3).kind == "none"


def test_second_utterance_yields_second_final() -> None:
    f = UtteranceFinalizer(idle_windows=1)
    t = 0.0
    assert f.on_text("primeira", now=t).kind == "emit_partial"
    assert f.on_no_result(now=t + 1).kind == "emit_final"
    assert f.on_text("segunda frase", now=t + 2).kind == "emit_partial"
    final2 = f.on_no_result(now=t + 3)
    assert final2.kind == "emit_final"
    assert final2.text == "segunda frase"
    assert f.finals_emitted == 2


def test_empty_and_whitespace_never_final() -> None:
    f = UtteranceFinalizer(idle_windows=1)
    assert f.on_text("", now=0).kind == "none"
    assert f.on_text("   ", now=1).kind == "none"
    assert f.on_no_result(now=2).kind == "none"
    assert f.state == "idle"
    assert f.finals_emitted == 0


def test_n_partials_zero_finals_until_idle() -> None:
    f = UtteranceFinalizer(idle_windows=1)
    t = 0.0
    for i in range(5):
        action = f.on_text(f"parcial {i}", now=t + i)
        assert action.kind == "emit_partial"
        assert f.finals_emitted == 0
    assert f.on_no_result(now=t + 10).kind == "emit_final"
    assert f.finals_emitted == 1


def test_idle_windows_two_requires_two_no_results() -> None:
    f = UtteranceFinalizer(idle_windows=2)
    t = 0.0
    assert f.on_text("texto", now=t).kind == "emit_partial"
    assert f.on_no_result(now=t + 1).kind == "none"
    assert f.state == "open"
    assert f.idle_windows == 1
    final = f.on_no_result(now=t + 2)
    assert final.kind == "emit_final"
    assert final.reason == "idle"


def test_max_open_force_final() -> None:
    f = UtteranceFinalizer(idle_windows=99, max_open_seconds=45.0)
    t0 = 1000.0
    assert f.on_text("monologo longo", now=t0).kind == "emit_partial"
    assert f.on_tick(now=t0 + 44.9).kind == "none"
    final = f.on_tick(now=t0 + 45.0)
    assert final.kind == "emit_final"
    assert final.text == "monologo longo"
    assert final.reason == "max_open"
    assert f.state == "idle"
    assert f.max_open_closes == 1
    # No double on further ticks
    assert f.on_tick(now=t0 + 100).kind == "none"


def test_max_open_via_on_no_result() -> None:
    f = UtteranceFinalizer(idle_windows=99, max_open_seconds=10.0)
    t0 = 0.0
    f.on_text("aberto", now=t0)
    final = f.on_no_result(now=t0 + 10.0)
    assert final.kind == "emit_final"
    assert final.reason == "max_open"


def test_disconnect_emits_final_when_open() -> None:
    f = UtteranceFinalizer(idle_windows=5)
    f.on_text("ainda aberto", now=0.0)
    final = f.on_disconnect(residual_text=None, now=1.0)
    assert final.kind == "emit_final"
    assert final.text == "ainda aberto"
    assert final.reason == "disconnect"
    assert f.disconnect_closes == 1


def test_disconnect_after_final_does_not_double() -> None:
    f = UtteranceFinalizer(idle_windows=1)
    f.on_text("fechado por idle", now=0.0)
    assert f.on_no_result(now=1.0).kind == "emit_final"
    assert f.finals_emitted == 1
    # Typical disconnect residual path: no new text after idle final → none.
    assert f.on_disconnect(residual_text=None, now=2.0).kind == "none"
    assert f.finals_emitted == 1


def test_disconnect_once_while_open() -> None:
    f = UtteranceFinalizer(idle_windows=5)
    f.on_text("residual", now=0.0)
    assert f.on_disconnect(residual_text="residual", now=1.0).kind == "emit_final"
    assert f.finals_emitted == 1
    # Second disconnect after already idle with no residual: none
    assert f.on_disconnect(residual_text=None, now=2.0).kind == "none"
    assert f.finals_emitted == 1


def test_disconnect_residual_new_text_when_idle() -> None:
    f = UtteranceFinalizer(idle_windows=1)
    action = f.on_disconnect(residual_text="so no flush", now=0.0)
    assert action.kind == "emit_final"
    assert action.text == "so no flush"
    assert action.reason == "disconnect"


def test_disconnect_residual_updates_open_text() -> None:
    f = UtteranceFinalizer(idle_windows=5)
    f.on_text("parcial", now=0.0)
    final = f.on_disconnect(residual_text="parcial completo", now=1.0)
    assert final.kind == "emit_final"
    assert final.text == "parcial completo"


def test_rejects_invalid_ctor_args() -> None:
    with pytest.raises(ValueError):
        UtteranceFinalizer(idle_windows=0)
    with pytest.raises(ValueError):
        UtteranceFinalizer(max_open_seconds=0)
