# Contratos — SF-021 (delta)

O contrato autoritativo vive em `contracts/` na raiz do monorepo (P4). Esta feature **não altera** nenhum schema — apenas passa a consumir um contrato já existente. Este arquivo documenta só a interface interna nova que resulta desse consumo.

## Compatibilidade de versão (fronteira do consumidor)

| Schema | Suporte neste consumidor (`session-core` / SF-021) |
|--------|-----------------------------------------------------|
| `contracts/transcript-event.v2.schema.json` | **Suportado** — único formato ingerido do feed `/ws/transcripts`. |
| `contracts/transcript-event.v1.schema.json` | **Não suportado** — eventos v1 no feed são rejeitados/ignorados de forma isolada (não derrubam a sessão); não há caminho de mapeamento v1 → `HubEvent` nesta feature. |

Quem publica no feed de transcrição deve emitir **somente** o contrato v2 (`transcript.partial.v2` / `transcript.final.v2`). Documentação de assumptions da feature: `spec.md` (Assumptions).

## 1. `contracts/transcript-event.v2.schema.json` (inalterado)

Consumido como está pelo novo cliente WebSocket do `session-core`, a partir do feed `/ws/transcripts` já publicado por `services/transcription-service`. Nenhum campo, `required` ou versão muda. Ver `data-model.md` para o mapeamento campo a campo consumido.

## 2. Mapeamento interno v2 → `HubEvent` (novo, dentro do `session-core`)

Não é um contrato entre serviços — é a forma como o `session-core` expõe, via o endpoint já existente `GET /api/sessions/{id}/events`, o que foi ingerido do feed de transcrição. Documentado aqui porque qualquer consumidor futuro desse endpoint (dashboard, memória) precisa saber onde encontrar os metadados de canal:

```json
{
  "type": "transcript.final.v2",
  "source": "transcription-service",
  "payload": {
    "text": "...",
    "language": "pt",
    "languageProbability": 0.98,
    "latencyMs": 240,
    "audioSeconds": 3.2,
    "droppedWindows": 0
  },
  "correlation": {
    "channelId": "mic-1",
    "sourceType": "microphone",
    "label": "Microfone principal",
    "device.index": "2",
    "device.name": "Headset USB",
    "device.endpointId": "{0.0.1.00000000}.{guid}"
  }
}
```

- `correlation` é o único lugar onde `channelId`/`sourceType`/`label`/`device.*` aparecem — nenhum desses campos é promovido a atributo de topo do `HubEvent` por esta feature (ver research.md #4).
- `device.index`/`device.name`/`device.endpointId` viram string vazia (`""`) em `correlation` quando o evento de origem trouxe `null` (cenário legado pré-SF-018) — `correlation` é `Map<String,String>` e não aceita valor nulo.
- Em `payload`, os campos opcionais do schema v2 (`language`, `languageProbability`, `audioSeconds`, `droppedWindows`) são **omitidos** (chave ausente), não incluídos como `null`, quando o evento de origem não os traz. `text` e `latencyMs` são sempre obrigatórios pelo schema e sempre aparecem.

## 3. `GET /api/sessions/{id}/events` (endpoint existente, sem mudança de assinatura)

Já existe em `SessionController` e já retorna `List<HubEvent>`. Esta feature não adiciona endpoint novo — apenas passa a popular esse retorno também com eventos originados do `transcription-service`, ao lado de quaisquer outros eventos genéricos já suportados hoje (`POST /api/sessions/{id}/events`).
