from __future__ import annotations

import threading

import pytest

from app.consolidation import TranscriptConsolidationRegistry


def ingest(
    consolidator: TranscriptConsolidationRegistry,
    text: str,
    *,
    session_id: str = "sess-1",
    channel_id: str = "mic-1",
    source_type: str = "microphone",
    label: str = "Headset",
) -> None:
    consolidator.ingest(
        session_id=session_id,
        channel_id=channel_id,
        source_type=source_type,
        label=label,
        text=text,
    )


def channel_snapshot(
    consolidator: TranscriptConsolidationRegistry,
    session_id: str = "sess-1",
    channel_id: str = "mic-1",
):
    snapshot = consolidator.session_transcript(session_id)
    matches = [channel for channel in snapshot.channels if channel.channel_id == channel_id]
    assert matches, f"canal {channel_id} ausente na sessão {session_id}"
    return matches[0]


def test_boundary_overlap_is_trimmed() -> None:
    consolidator = TranscriptConsolidationRegistry()
    ingest(consolidator, "vamos revisar a arquitetura do serviço")
    ingest(consolidator, "arquitetura do serviço antes da implementação")

    channel = channel_snapshot(consolidator)
    assert channel.text == "vamos revisar a arquitetura do serviço antes da implementação"
    assert channel.duplicate_words_removed == 3
    assert channel.total_events == 2
    assert channel.segment_count == 2


def test_complete_duplicate_is_ignored() -> None:
    consolidator = TranscriptConsolidationRegistry()
    ingest(consolidator, "reunião começa às dez horas")
    ingest(consolidator, "reunião começa às dez horas")

    channel = channel_snapshot(consolidator)
    assert channel.text == "reunião começa às dez horas"
    assert channel.segment_count == 1
    assert channel.total_events == 2
    assert channel.duplicate_words_removed == 5


def test_final_flush_suffix_is_ignored() -> None:
    # O flush de desconexão re-transcreve a cauda de overlap; se o texto for
    # apenas o fim do que já foi consolidado, nada é anexado.
    consolidator = TranscriptConsolidationRegistry()
    ingest(consolidator, "reunião começa às dez horas")
    ingest(consolidator, "às dez horas")

    channel = channel_snapshot(consolidator)
    assert channel.text == "reunião começa às dez horas"
    assert channel.segment_count == 1


def test_window_without_overlap_is_appended_whole() -> None:
    # Janela perdida por descarte na fila: sem casamento na borda, nenhum
    # corte acontece.
    consolidator = TranscriptConsolidationRegistry()
    ingest(consolidator, "primeira parte da fala")
    ingest(consolidator, "assunto completamente novo")

    channel = channel_snapshot(consolidator)
    assert channel.text == "primeira parte da fala assunto completamente novo"
    assert channel.duplicate_words_removed == 0


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        # Duplicata exata é ignorada.
        ("olá mundo", "olá mundo", "olá mundo"),
        # Sobreposição de borda anexa apenas as palavras novas.
        (
            "vamos revisar a arquitetura",
            "a arquitetura antes da implementação",
            "vamos revisar a arquitetura antes da implementação",
        ),
        # Prefixo compartilhado fora da borda não é sobreposição: os dois
        # textos são preservados por inteiro.
        (
            "o serviço iniciou",
            "o serviço encerrou",
            "o serviço iniciou o serviço encerrou",
        ),
    ],
)
def test_issue_6_required_cases(first: str, second: str, expected: str) -> None:
    consolidator = TranscriptConsolidationRegistry()
    ingest(consolidator, first)
    ingest(consolidator, second)

    assert channel_snapshot(consolidator).text == expected


def test_legitimate_repetition_inside_text_is_preserved() -> None:
    consolidator = TranscriptConsolidationRegistry()
    ingest(consolidator, "ele disse sim sim senhor")

    channel = channel_snapshot(consolidator)
    assert channel.text == "ele disse sim sim senhor"


def test_matching_is_case_insensitive_and_keeps_original_text() -> None:
    consolidator = TranscriptConsolidationRegistry()
    ingest(consolidator, "Vamos revisar a Arquitetura")
    ingest(consolidator, "vamos revisar a arquitetura do serviço")

    channel = channel_snapshot(consolidator)
    assert channel.text == "Vamos revisar a Arquitetura do serviço"
    assert channel.duplicate_words_removed == 4


def test_matching_is_conservative_about_punctuation_and_accents() -> None:
    # Sem normalização de acentos ou pontuação: "dez." não é "dez", então o
    # texto é mantido em vez de cortado. Conservador por decisão.
    consolidator = TranscriptConsolidationRegistry()
    ingest(consolidator, "começa às dez.")
    ingest(consolidator, "dez horas da manhã")

    channel = channel_snapshot(consolidator)
    assert channel.text == "começa às dez. dez horas da manhã"
    assert channel.duplicate_words_removed == 0


def test_overlap_search_is_limited_to_tail_words() -> None:
    consolidator = TranscriptConsolidationRegistry(overlap_tail_words=2)
    ingest(consolidator, "um dois três quatro")
    # O prefixo repetido tem 3 palavras, mas a cauda guarda apenas as 2
    # últimas ("três quatro"), então o casamento não é encontrado.
    ingest(consolidator, "dois três quatro cinco")

    channel = channel_snapshot(consolidator)
    assert channel.text == "um dois três quatro dois três quatro cinco"


def test_retention_rotates_oldest_segments() -> None:
    consolidator = TranscriptConsolidationRegistry(max_segments_per_channel=2)
    ingest(consolidator, "primeiro trecho")
    ingest(consolidator, "segundo trecho")
    ingest(consolidator, "terceiro trecho")

    channel = channel_snapshot(consolidator)
    assert channel.text == "segundo trecho terceiro trecho"
    assert channel.segment_count == 2
    assert channel.dropped_segments == 1
    assert channel.truncated is True
    assert channel.total_events == 3


def test_sessions_are_isolated() -> None:
    consolidator = TranscriptConsolidationRegistry()
    ingest(consolidator, "fala da sessão a", session_id="sess-a")
    ingest(consolidator, "fala da sessão a", session_id="sess-b")

    channel_a = channel_snapshot(consolidator, session_id="sess-a")
    channel_b = channel_snapshot(consolidator, session_id="sess-b")
    assert channel_a.text == channel_b.text == "fala da sessão a"
    assert channel_a.total_events == channel_b.total_events == 1
    assert consolidator.session_transcript("sess-c").channels == ()


def test_channels_are_never_compared() -> None:
    consolidator = TranscriptConsolidationRegistry()
    ingest(consolidator, "mesmo texto nos dois canais", channel_id="system-main")
    ingest(consolidator, "mesmo texto nos dois canais", channel_id="mic-1")

    system = channel_snapshot(consolidator, channel_id="system-main")
    mic = channel_snapshot(consolidator, channel_id="mic-1")
    assert system.text == mic.text == "mesmo texto nos dois canais"
    assert system.duplicate_words_removed == mic.duplicate_words_removed == 0


def test_least_recently_touched_channel_is_evicted() -> None:
    consolidator = TranscriptConsolidationRegistry(max_channels=1)
    ingest(consolidator, "canal antigo", channel_id="mic-1")
    ingest(consolidator, "canal novo", channel_id="mic-2")

    snapshot = consolidator.session_transcript("sess-1")
    assert [channel.channel_id for channel in snapshot.channels] == ["mic-2"]


def test_concurrent_ingest_from_threads() -> None:
    consolidator = TranscriptConsolidationRegistry(max_channels=8)
    events_per_thread = 50

    def writer(channel_id: str) -> None:
        for index in range(events_per_thread):
            ingest(consolidator, f"palavra {index}", channel_id=channel_id)

    threads = [
        threading.Thread(target=writer, args=(f"mic-{index}",)) for index in range(4)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    snapshot = consolidator.session_transcript("sess-1")
    assert len(snapshot.channels) == 4
    for channel in snapshot.channels:
        assert channel.total_events == events_per_thread


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_segments_per_channel": 0},
        {"max_channels": 0},
        {"overlap_tail_words": 0},
    ],
)
def test_invalid_limits_are_rejected(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        TranscriptConsolidationRegistry(**kwargs)
