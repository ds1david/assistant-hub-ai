# Data Model: Utterance finalization (issue #55)

**Date**: 2026-07-25  
**Feature**: `specs/024-issue-55-stt-final-utterance`

## Entities

### Utterance (runtime, per channel connection)

| Field | Type | Rules |
|-------|------|-------|
| state | enum `idle` \| `open` | Start `idle` |
| last_text | string | Último texto útil; vazio quando idle limpo |
| partial_count | int ≥ 0 | Partials emitidos nesta utterance |
| idle_windows | int ≥ 0 | Janelas consecutivas sem texto novo enquanto open |
| opened_at | monotonic timestamp \| null | Quando passou a open |
| final_emitted | bool | True após emitir final desta utterance |

**Transitions**:

```text
idle  --on_text(non-empty)-->  open   (emit partial; reset idle_windows=0; opened_at=now)
open  --on_text(new)------->  open   (emit partial; reset idle_windows=0; update last_text)
open  --on_no_result------>  open   (idle_windows++)
open  --idle_windows >= N-->  idle   (emit final once with last_text; final_emitted; clear)
open  --max_open exceeded-->  idle   (emit final once with last_text)
open  --disconnect-------->  idle   (emit final if text and not final_emitted)
idle  --on_no_result------>  idle   (noop)
idle  --disconnect-------->  idle   (noop unless residual new text → treat as open then final)
```

N = `finalization_idle_windows` (default 1).  
max_open = `finalization_max_open_seconds` (default 45).

### Transcript.partial.v2 / transcript.final.v2 (contract existing)

Sem novos campos. Mapeamento:

| Field | Source |
|-------|--------|
| type | `transcript.partial.v2` ou `transcript.final.v2` |
| sessionId, channelId, label, sourceType, device | canal WS |
| text | last_text da utterance no final; texto do partial no partial |
| latencyMs, audioSeconds, … | resultado de transcrição (no final: do último window útil ou 0 se só timeout) |
| prosody | só final se flag prosody (023) |

### Settings (config)

| Name | Default | Validation |
|------|---------|------------|
| `finalization_idle_windows` | 1 | int ≥ 1 |
| `finalization_max_open_seconds` | 45.0 | float > 0 |

Env names (pydantic-settings): `FINALIZATION_IDLE_WINDOWS`, `FINALIZATION_MAX_OPEN_SECONDS`.

## Relationships

```text
Session
  └── ChannelConnection (WS /ws/audio/{sessionId}/{channelId})
        └── UtteranceFinalizer (1:1 while connected)
              └── 0..N partial events + 0..1 final per closed utterance
```

Canais não compartilham finalizer (P5 / P6).

## Validation rules

1. Nunca emitir final com `text` vazio ou whitespace-only.
2. Nunca emitir segundo final da mesma utterance sem transição open de novo texto.
3. Partial só quando há texto novo útil e suppress não bloqueou.
4. Estado destruído ao fim da conexão (sem persistência).

## Idempotency notes (consumers)

Shell (019) já trata reprocessamento de feed por identidade de trecho. Esta feature não introduz `utteranceId`; consumidores devem tratar cada evento final como trecho fechado distinto por `(sessionId, channelId, occurredAt, text)` prático.
