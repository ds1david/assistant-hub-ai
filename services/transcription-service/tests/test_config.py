import pytest

from app.config import Settings


def test_normalizes_brazilian_portuguese_locale() -> None:
    assert Settings(whisper_language="pt-BR").whisper_language == "pt"
    assert Settings(whisper_language="pt_BR").whisper_language == "pt"


def test_keeps_supported_language_code() -> None:
    assert Settings(whisper_language="pt").whisper_language == "pt"


def test_finalization_defaults() -> None:
    settings = Settings()
    assert settings.finalization_idle_windows == 1
    assert settings.finalization_max_open_seconds == 45.0


def test_finalization_idle_windows_rejects_below_one() -> None:
    with pytest.raises(Exception):
        Settings(finalization_idle_windows=0)


def test_finalization_max_open_seconds_rejects_non_positive() -> None:
    with pytest.raises(Exception):
        Settings(finalization_max_open_seconds=0)
    with pytest.raises(Exception):
        Settings(finalization_max_open_seconds=-1.0)
