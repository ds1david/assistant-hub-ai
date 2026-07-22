# Phase 1 Data Model: Publicar eventos transcript v2 no session-core (SF-021)

## TranscriptEventV2 (entrada, não persistida como tal)

Espelha `contracts/transcript-event.v2.schema.json`. Representa um evento recebido do feed `/ws/transcripts` do `transcription-service`, antes de virar um `HubEvent`.

| Campo | Tipo | Obrigatório | Observações |
|---|---|---|---|
| `type` | enum (`transcript.partial.v2`, `transcript.final.v2`) | sim | Determina se é rascunho ou final. |
| `sessionId` | string | sim | Correlacionado com `ConversationSession.id().toString()` (ver research.md #3). |
| `channelId` | string (`^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$`) | sim | Identifica o canal dentro da sessão; nunca fundido com outro canal (FR-003). |
| `label` | string | sim | Rótulo legível do canal. |
| `sourceType` | enum (`system`, `microphone`) | sim | Origem do áudio do canal. |
| `device` | objeto `{index, name, endpointId}` | sim (objeto); `index`/`name`/`endpointId` podem ser `null` | `endpointId` pode ser `null` em cenários pré-SF-018 (US1, cenário 2). |
| `text` | string | sim | Conteúdo transcrito. |
| `language`, `languageProbability` | string\|null, number\|null | não | Metadados do STT. |
| `latencyMs` | integer ≥ 0 | sim | Latência de produção do evento. |
| `audioSeconds`, `droppedWindows` | number, integer | não | Métricas adicionais. |
| `occurredAt` | string (date-time) | sim | Instante de ocorrência no publisher. |

**Regras de validação**: um `TranscriptEventV2` que falhe a validação contra o schema (campo obrigatório ausente, enum inválido, `channelId` fora do padrão) é rejeitado antes de qualquer mapeamento — nunca vira um `HubEvent` parcial (FR-004).

## Mapeamento para `HubEvent` (existente, `plugin-sdk-java`)

Não é uma entidade nova — é a regra de tradução que materializa "o evento chegou preservando os metadados" (FR-002) dentro do modelo que o `session-core` já usa hoje.

| Campo `HubEvent` | Origem em `TranscriptEventV2` |
|---|---|
| `sessionId` | Resolvido para o `UUID` da `ConversationSession` correspondente a `event.sessionId` (não é o `sessionId` string bruto). |
| `type` | `event.type` (`transcript.partial.v2` / `transcript.final.v2`) |
| `source` | Constante `"transcription-service"` |
| `occurredAt` | `event.occurredAt` |
| `ingestedAt` | Instante em que o `session-core` processou o evento (não vem do publisher) |
| `payload` | `{text, language, languageProbability, latencyMs, audioSeconds, droppedWindows}` |
| `correlation` | `{channelId, sourceType, label, "device.index", "device.name", "device.endpointId"}` — chaves sempre presentes; valor ausente vira string vazia ou chave omitida (detalhe de implementação, não de contrato) |

**Regra de separação por canal (FR-003)**: dois `HubEvent` originados de `channelId` diferentes na mesma sessão nunca compartilham a mesma entrada de `correlation` nem se sobrescrevem — cada evento vira um registro `HubEvent` independente em `SessionRepository.append`.

## ConversationSession (existente, sem alteração de schema)

Usada apenas para resolver `event.sessionId` → sessão existente. Nenhum campo novo é adicionado a `ConversationSession` por esta feature — canais não são pré-cadastrados nela (ver spec Assumptions); um canal só existe implicitamente através dos `HubEvent.correlation` já registrados para a sessão.

**Estados relevantes** (`SessionStatus`, existente: `CREATED`, `ACTIVE`, `ENDED`): eventos para uma sessão em `ENDED` — ou para um `sessionId` sem `ConversationSession` correspondente — são tratados como "sessão desconhecida" e descartados (FR-004, Edge Cases).

## Canal (conceito derivado, não é uma tabela/entidade própria)

Um "canal" é a combinação `channelId` + `sourceType` + `device` observada nos `HubEvent.correlation` de uma sessão. Não há registro prévio de canais — o primeiro evento de um `channelId` o torna implicitamente conhecido dentro da sessão (research.md, spec Assumptions). Não há relação formal 1:N persistida entre sessão e canal além do que já existe hoje entre sessão e sua lista de `HubEvent`.
