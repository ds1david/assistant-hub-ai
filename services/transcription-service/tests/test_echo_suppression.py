from app.echo_suppression import TranscriptEchoSuppressor


def build() -> TranscriptEchoSuppressor:
    return TranscriptEchoSuppressor(
        enabled=True,
        window_seconds=5.0,
        similarity_threshold=0.82,
        min_chars=5,
    )


def test_suppresses_near_duplicate_microphone_echo() -> None:
    suppressor = build()
    suppressor.evaluate(
        session_id="s1",
        source_type="system",
        text="Eu falei cassetada agora",
        now=10.0,
    )

    result = suppressor.evaluate(
        session_id="s1",
        source_type="microphone",
        text="Eu falei cassitada agora",
        now=10.4,
    )

    assert result.suppressed is True
    assert result.similarity >= 0.82


def test_does_not_suppress_unrelated_local_speech() -> None:
    suppressor = build()
    suppressor.evaluate(
        session_id="s1",
        source_type="system",
        text="Explique a arquitetura do sistema",
        now=10.0,
    )

    result = suppressor.evaluate(
        session_id="s1",
        source_type="microphone",
        text="Eu começaria separando os módulos",
        now=10.5,
    )

    assert result.suppressed is False


def test_expired_system_text_is_not_used() -> None:
    suppressor = build()
    suppressor.evaluate(
        session_id="s1",
        source_type="system",
        text="cassetada",
        now=1.0,
    )

    result = suppressor.evaluate(
        session_id="s1",
        source_type="microphone",
        text="cassitada",
        now=8.0,
    )

    assert result.suppressed is False
