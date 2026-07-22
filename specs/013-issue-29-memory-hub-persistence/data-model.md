# Data Model: Memory Hub — persistência local de sessão e eventos (R3)

Modelo de armazenamento interno ao `session-core` (não um contrato público entre serviços — ver Constitution Check / Structure Decision no `plan.md`). Mapeia diretamente os tipos Java já existentes, `ConversationSession` e `HubEvent` (`packages/plugin-sdk-java`), sem alterá-los.

## Entidade: Sessão persistida (tabela `sessions`)

Espelha `ai.assistanthub.core.session.ConversationSession` linha a linha.

| Coluna | Tipo SQLite | Origem / Regra |
|---|---|---|
| `id` | `TEXT` (UUID), PK | `ConversationSession.id()` |
| `title` | `TEXT` | `ConversationSession.title()` |
| `profile_id` | `TEXT`, nullable | `ConversationSession.profileId()` |
| `status` | `TEXT` | `ConversationSession.status()` (`CREATED`/`ACTIVE`/`ENDED`, ver `SessionStatus`) |
| `created_at` | `INTEGER` (epoch **nanossegundos**) | `ConversationSession.createdAt()` |
| `started_at` | `INTEGER`, nullable (epoch nanossegundos) | `ConversationSession.startedAt()` |
| `ended_at` | `INTEGER`, nullable (epoch nanossegundos) | `ConversationSession.endedAt()` |
| `metadata_json` | `TEXT` (JSON) | `ConversationSession.metadata()` serializado via Jackson |

**Regras de validação**: `id` único (PK); `status` restrito aos valores de `SessionStatus`; `metadata_json` sempre um objeto JSON válido (mesmo que `{}`).

**Transições de estado**: reaproveita `SessionStatus` já existente (`CREATED` → `ACTIVE` → `ENDED`); esta feature não introduz nem altera transições — apenas persiste o estado atual a cada `save`.

## Entidade: Evento de sessão persistido (tabela `session_events`)

Espelha `ai.assistanthub.sdk.HubEvent`, incluindo o mapa `correlation` (onde `specs/007-sf-021-session-core-events/` grava `channelId`/`sourceType`/`label`/`device`).

| Coluna | Tipo SQLite | Origem / Regra |
|---|---|---|
| `event_id` | `TEXT` (UUID), `UNIQUE` | `HubEvent.id()` — não é a chave primária da tabela (ver `sequence`; SQLite só permite `AUTOINCREMENT` em uma única coluna `INTEGER PRIMARY KEY`) |
| `session_id` | `TEXT`, FK → `sessions.id` | `HubEvent.sessionId()` |
| `type` | `TEXT` | `HubEvent.type()` (ex.: `transcript.partial.v2`, `transcript.final.v2`) |
| `source` | `TEXT` | `HubEvent.source()` |
| `occurred_at` | `INTEGER` (epoch **nanossegundos**) | `HubEvent.occurredAt()` |
| `ingested_at` | `INTEGER` (epoch **nanossegundos**) | `HubEvent.ingestedAt()` |
| `payload_json` | `TEXT` (JSON) | `HubEvent.payload()` serializado via Jackson |
| `correlation_json` | `TEXT` (JSON) | `HubEvent.correlation()` serializado via Jackson — preserva `channelId`/`sourceType`/`label`/`device` (`index`/`name`/`endpointId`) tal como recebido (FR-002) |
| `sequence` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Usa o mecanismo nativo `AUTOINCREMENT` do SQLite (tabela auxiliar `sqlite_sequence`) para garantir que o valor nunca é reutilizado — mesmo que `session_events` fique temporariamente vazia após um expurgo de `RetentionPolicy` — evitando colisão de ordem entre uma sessão antiga totalmente expurgada e uma sessão nova (FR-003) |

**Regras de validação**: `session_id` MUST referenciar uma linha existente em `sessions` (FK); nenhuma dedução ou merge de `correlation_json` entre eventos de canais diferentes (P5) — cada linha é independente.

**Nota sobre precisão de tempo**: todas as colunas de instante (`created_at`, `started_at`, `ended_at`, `occurred_at`, `ingested_at`) armazenam nanossegundos desde a época, não milissegundos — `Instant.now()` tem resolução de nanossegundos no Linux, e truncar para milissegundos quebraria `equals()` ao reidratar uma sessão/evento a partir do SQLite (SC-001 exige campos "idênticos" após restart).

**Ordenação de consulta**: `SELECT ... WHERE session_id = ? ORDER BY sequence ASC` — reproduz exatamente a ordem de chegada já garantida hoje pela `List<HubEvent>` em memória (`SessionRepository.events`).

**Relação**: um `sessions` → muitos `session_events` (1:N por `session_id`); um evento nunca migra de sessão.

## Conceito: Política de retenção (não é uma tabela — é configuração + comportamento)

Representada por `MemoryHubProperties` (valores de `application.yml`) e aplicada por `RetentionPolicy`:

| Campo | Significado |
|---|---|
| `retention.max-age` | Idade máxima (ex.: `30d`) de uma sessão em status `ENDED` antes de ser elegível para expurgo. Ausente = sem limite de idade (retenção indefinida, default da spec). |
| `retention.max-sessions` | Número máximo de sessões `ENDED` retidas; ao exceder, as mais antigas (por `ended_at`) são expurgadas primeiro. Ausente = sem limite de contagem. |

**Regra de expurgo**: nunca remove uma sessão cujo `status` não seja `ENDED` (uma sessão ativa nunca é expurgada por retenção); expurgar uma sessão remove em cascata seus `session_events` (mesma transação).

## Conceito: Cache em memória (rehydration)

Não é uma entidade persistida — é a mesma estrutura `Map<UUID, ConversationSession>` / `Map<UUID, List<HubEvent>>` que `SessionRepository` já mantém hoje. Após esta feature, ela é populada a partir de `sessions`/`session_events` na subida do processo (`MemoryHubStartupRehydrator`) e mantida sincronizada a cada `save`/`append`, que passam a escrever nos dois lugares (memória + SQLite) na mesma operação.
