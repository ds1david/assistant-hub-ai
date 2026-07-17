from app.config import Settings


def test_normalizes_brazilian_portuguese_locale() -> None:
    assert Settings(whisper_language="pt-BR").whisper_language == "pt"
    assert Settings(whisper_language="pt_BR").whisper_language == "pt"


def test_keeps_supported_language_code() -> None:
    assert Settings(whisper_language="pt").whisper_language == "pt"
