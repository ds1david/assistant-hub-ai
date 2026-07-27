# Contract: Session metrics + disconnect finalization behavior

**Feature**: `specs/034-stt-echo-metrics-disconnect`  
**Date**: 2026-07-27  
**Status**: Behavior contract (no schema version bump)

## Endpoints (unchanged shapes)

### `GET /v1/sessions/{sessionId}/metrics`

Response JSON (campos canônicos já em produção):

```json
{
  "sessionId": "string",
  "generatedAt": "ISO-8601",
  "maxSamplesPerChannel": 512,
  "channels": [
    {
      "channelId": "string",
      "sourceType": "system|microphone|…",
      "label": "string",
      "sampleCount": 0,
      "p50Ms": 0,
      "p95Ms": 0,
      "minMs": 0,
      "maxMs": 0,
      "avgMs": 0,
      "totalEvents": 0,
      "droppedWindows": 0,
      "lastEventAt": "ISO-8601|null"
    }
  ]
}
```

**Comportamento adicionado/esclarecido**:

| Regra | Contrato |
|-------|----------|
| C1 | Cada evento de transcript **contado no publish path** (partial/final) incrementa **`totalEvents`** do canal em **1** e adiciona uma amostra de latência no ring (`sampleCount` ≤ max). **`totalEvents`** é a fonte da verdade do “quantos eventos”; `sampleCount` reflete o buffer de percentis. |
| C2 | Trecho de microfone **suprimido por eco** não incrementa `totalEvents` nem `sampleCount`. |
| C3 | Assinantes de `/ws/transcripts` **não** multiplicam contagens do produtor. |
| C4 | Após disconnect de um canal que emitiu 1 partial útil e 1 final residual, **`totalEvents ≥ 2`** e, com retenção suficiente, `sampleCount ≥ 2` para esse canal **sem perda permanente** de `totalEvents`. |
| C5 | Observador que lê cedo demais MAY reconsultar por até **2,0 s**; após estabilizar, contagens finais não regridem por race de teardown. |
| C6 | Sessões isoladas: métricas de `sessionId=A` não listam canais de `B`. |
| C7 | **Cancel residual extremo**: se o cancel do runtime impedir o caminho assíncrono completo de finalização, o serviço MAY registrar **apenas** a amostra de métrica (e fechar o finalizer) **sem** fan-out do evento no feed. Fan-out/evento completo é **best-effort**; perda permanente de contagem com utterance útil aberta é **falha**. |

### `WS /ws/audio/{sessionId}/{channelId}`

| Regra | Contrato |
|-------|----------|
| A1 | Em disconnect, o serviço executa finalização residual (flush + `UtteranceFinalizer.on_disconnect`) mesmo se o cliente já fechou. |
| A2 | Final com reason disconnect **pode** omitir frame no WS de áudio; identidade do evento (se publicado no feed) permanece P5-compliant. |
| A3 | Processamento de janelas no canal é **ordenado/sequencial** por conexão; o tick de disconnect não é descartado por política de “latest only” de fila. |
| A4 | No publish path, `record_transcription` ocorre **antes** de awaits de prosódia, send e fan-out. |

### `WS /ws/transcripts` (feed)

| Regra | Contrato |
|-------|----------|
| F1 | Fan-out de um evento tenta entregar a todos os assinantes com **timeout por envio ≤ 1,0 s**. |
| F2 | Publish do produtor no caminho de emit tem teto **≤ 0,5 s** para o conjunto do fan-out; falha/timeout não reverte métrica já registrada. |
| F3 | Assinante que falha ou estoura timeout é tratado como stale (removido); não derruba o canal produtor. |

## Event types

Sem novos `type`. Continuam:

- `transcript.partial.v2`
- `transcript.final.v2`

## Compatibility

- **Aditivo de comportamento** apenas.
- Clientes do endpoint de métricas e do feed não precisam mudar parsers.
- Testes que assumeam `totalEvents == 1` (ou só `sampleCount == 1`) após partial+disconnect estão **obsoletos** — esperar **2** quando final residual é emitido (preferir assert em `totalEvents`).

## Non-goals

- Novos campos em métricas (ex. `disconnectFinals`).
- Métricas Prometheus export.
- Mudança de thresholds de eco.
- Redação de logs INFO de supressão de eco (texto) — fora desta fatia.
