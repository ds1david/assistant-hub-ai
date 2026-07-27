# Data Model: STT disconnect final + session metrics

**Feature**: `specs/034-stt-echo-metrics-disconnect`  
**Date**: 2026-07-27

Nenhuma entidade persistida nova. Modelo em memória já existente no transcription-service; esta feature fixa **regras de contagem e ciclo de vida no disconnect**.

## Entities

### SessionMetricsSnapshot

| Campo | Tipo lógico | Notas |
|-------|-------------|--------|
| `sessionId` | string | Isolamento de leitura |
| `generatedAt` | timestamp ISO-8601 | Instantâneo da consulta |
| `maxSamplesPerChannel` | int | Retenção do ring buffer (config) |
| `channels` | list[ChannelLatencySnapshot] | Ordenados por `channelId` |

### ChannelLatencySnapshot

| Campo | Tipo lógico | Notas |
|-------|-------------|--------|
| `channelId` | string | Identidade do canal |
| `sourceType` | string | `system` \| `microphone` \| … |
| `label` | string | Label de UI/operação |
| `sampleCount` | int | Amostras no ring de latência (≤ max); base dos percentis |
| `totalEvents` | int | **Fonte da verdade** do número de eventos entregues desde o início do canal (pode ser > `sampleCount` se retenção cortou) |
| `droppedWindows` | int | Janelas descartadas (path de backpressure antigo; com emit sequencial tende a 0) |
| `p50Ms` / `p95Ms` / min/max/avg | int \| null | Sobre amostras retidas |
| `lastEventAt` | timestamp \| null | Último `record_transcription` |

**Regra de contagem (FR-002 / clarify)**:
- `+1` em `totalEvents` e uma amostra de latência por chamada a `record_transcription` no ponto de publicação de partial/final.
- Eco suprimido: **0** chamadas.
- Fan-out N clientes: **1** chamada.

### TranscriptEvent (entregue)

Reutiliza `transcript.partial.v2` / `transcript.final.v2` (schema v2 existente).

| Campo relevante | Uso nesta feature |
|-----------------|-------------------|
| `sessionId`, `channelId`, `sourceType`, `label` | Identidade (P5); métricas usam os mesmos ids |
| `type` | partial vs final |
| `text` | Não entra em métricas de contagem; eco compara texto antes de publicar |
| `latencyMs` | Valor da amostra de métrica |

### UtteranceFinalizer (estado por conexão)

| Estado | Transições relevantes no disconnect |
|--------|-------------------------------------|
| `idle` | `on_disconnect` sem residual útil → none; residual com texto novo → emit_final (disconnect) |
| `open` | `on_disconnect` → emit_final (disconnect) com último texto útil; **sem** double final se já fechou por idle |

Campos de contagem: `finals_emitted`, `idle_closes`, `max_open_closes`, `disconnect_closes` (observabilidade de log; não expostos no endpoint de métricas).

### EchoEvaluation (por janela mic)

| Campo | Efeito |
|-------|--------|
| `suppressed: true` | Não publica evento; não registra métrica; não avança idle via `on_text` |
| `suppressed: false` | Segue path normal de partial |

## Relationships

```text
Session (sessionId)
  └── Channel (channelId) ──1:1── ChannelLatencySnapshot (em registry)
  └── Connection task ──1:1── UtteranceFinalizer + StreamingTranscriber
  └── published events ──N──► TranscriptBroadcaster subscribers
```

## Validation rules

1. `sampleCount` / `totalEvents` só incrementam em eventos **não** suprimidos.
2. Disconnect com utterance aberta e texto útil → no máximo **um** final de disconnect adicional (024: sem double após idle final sem residual novo).
3. Chave de métricas: `(sessionId, channelId)` — sessões não se misturam.
4. `record_transcription` é idempotente só no sentido de “uma chamada por evento”; **não** há dedupe de conteúdo no registry.

## State transitions (disconnect path)

```text
[WS active] --receive bytes--> emit(window, disconnect=False)
       |
       +-- websocket.disconnect / WebSocketDisconnect --> finally
              --> finalize_disconnect() [shielded]
                    --> flush residual PCM (optional window)
                    --> emit(remaining|None, disconnect=True)
                          --> on_disconnect → emit_final?
                                --> record_transcription
                                --> skip_direct_send
                                --> fan-out (timeouts)
```
