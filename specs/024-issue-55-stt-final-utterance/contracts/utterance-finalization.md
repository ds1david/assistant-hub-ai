# Contract: Utterance finalization (issue #55)

**Status**: Additive behavior on existing transcript v2 events  
**Schema**: `contracts/transcript-event.v2.schema.json` — **unchanged**  
**Date**: 2026-07-25

## Event types (unchanged enum)

| type | When |
|------|------|
| `transcript.partial.v2` | Texto novo durante utterance aberta (streaming UI) |
| `transcript.final.v2` | Utterance fechada (idle windows, max-open timeout, ou disconnect residual) |

## Behavioral contract (new)

### Open

1. Canal WS ativo em `/ws/audio/{sessionId}/{channelId}`.
2. Primeira janela com texto útil (pós echo-suppression) → **open** + partial.

### Close (emit exactly one final)

| Trigger | Condition | Final text |
|---------|-----------|------------|
| Idle | `idle_windows >= FINALIZATION_IDLE_WINDOWS` (default 1) após open | `last_text` |
| Max open | `(now - opened_at) >= FINALIZATION_MAX_OPEN_SECONDS` (default 45) | `last_text` |
| Disconnect | residual/flush com texto e utterance open / final ainda não emitido | texto residual ou `last_text` |

### Must / Must not

- **MUST** preserve `sessionId`, `channelId`, `label`, `sourceType`, `device` iguais aos partials do canal.
- **MUST NOT** emit final with empty text.
- **MUST NOT** emit more than one final per closed utterance.
- **MUST** continue emitting partials while open and text grows/changes.
- **MUST NOT** require client disconnect to produce finals during conversation.
- **MUST NOT** introduce new event type names.

## Settings surface

| Env / setting | Default | Meaning |
|---------------|---------|---------|
| `FINALIZATION_IDLE_WINDOWS` | `1` | Janelas sem texto novo para fechar |
| `FINALIZATION_MAX_OPEN_SECONDS` | `45` | Timeout de utterance aberta |

## Downstream consumers (read-only for this feature)

| Consumer | Expected behavior |
|----------|-------------------|
| session-core feed ingest | Persist HubEvent with `type=transcript.final.v2` (already supported) |
| desktop-shell Assistente | Treat Final as candidate for question detection / live-answer (019/023) |
| STT dashboard | May show both partial and final; streaming continues |

## Compatibility

- Clientes que ignoram `type` e só leem `text` continuam válidos.
- Clientes que filtram só partials não quebram; passam a ver finais se escutarem o enum completo.
- Sem dual-read de versão de schema.
