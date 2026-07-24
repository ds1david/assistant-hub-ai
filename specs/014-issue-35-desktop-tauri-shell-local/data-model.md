# Phase 1 Data Model: Desktop Tauri — shell local do Assistant Hub (R5)

O shell não é dono de nenhuma destas entidades — são vistas locais derivadas do que o `session-core` já expõe (`ConversationSession`/`HubEvent`, via `SessionController`) e do estado observável do processo do agent Windows. Nenhum schema novo é adicionado a `contracts/`.

## SessionStatusView

Derivada de `GET /api/sessions/{id}` (`ConversationSession`, ver `services/session-core/.../ConversationSession.java`).

| Campo | Origem | Notas |
|---|---|---|
| `id` | `ConversationSession.id` | UUID da sessão |
| `title` | `ConversationSession.title` | |
| `profileId` | `ConversationSession.profileId` | |
| `status` | `ConversationSession.status` | `CREATED` / ativo / `ENDED` (enum já existente em `SessionStatus`) |
| `createdAt` / `startedAt` / `endedAt` | idem | `startedAt`/`endedAt` podem ser nulos |
| `connectivity` | derivado localmente (não vem do `session-core`) | `connected` \| `disconnected` \| `error`; alimentado pelo polling de `GET /actuator/health` (FR-009) |

## ChannelStatusView

Derivada agregando `HubEvent.correlation` de `GET /api/sessions/{id}/events` por `channelId` (US1/FR-002).

| Campo | Origem | Notas |
|---|---|---|
| `channelId` | `HubEvent.correlation["channelId"]` | chave de agrupamento — nunca agrupar só por `label` (edge case da spec) |
| `sourceType` | `HubEvent.correlation["sourceType"]` | ex.: `microphone`, `system_audio` |
| `label` | `HubEvent.correlation["label"]` | |
| `device` | `HubEvent.correlation["device.index"|"device.name"|"device.endpointId"]` | `endpointId` pode ser vazio (dispositivo legado por `index`/`name`, ver `specs/007-sf-021-session-core-events/`) |
| `lastEventAt` | `max(HubEvent.occurredAt)` do canal | |
| `eventCount` | contagem de eventos do canal | informativo, não é requisito funcional |

## TranscriptFeedEntry

Derivada de cada `HubEvent` de `GET /api/sessions/{id}/events` cujo `type` é `transcript.partial.v2`/`transcript.final.v2` (US2/FR-003/FR-004).

| Campo | Origem | Notas |
|---|---|---|
| `eventId` | `HubEvent.id` | usado para deduplicar entre chamadas sucessivas de polling |
| `channelId` / `sourceType` / `label` | `HubEvent.correlation[...]` | mesma origem de `ChannelStatusView` |
| `text` | `HubEvent.payload["text"]` | |
| `kind` | `HubEvent.type` | `partial` vs `final`, deriva de `transcript.partial.v2`/`transcript.final.v2` |
| `occurredAt` | `HubEvent.occurredAt` | usado para ordenação cronológica (FR-005) |

Regra de renderização: entradas são ordenadas por `occurredAt` crescente; entradas de canais diferentes nunca são combinadas em uma única linha/entrada visual (FR-004, edge case da spec).

## AgentStatus

Estado local, observado pelo processo Rust do shell — não vem do `session-core`.

| Campo | Origem | Notas |
|---|---|---|
| `state` | `sysinfo` (processo detectado) ou handle do processo filho spawnado pelo shell | `running` \| `stopped` \| `unknown` |
| `controlMode` | derivado de como o processo foi observado | `direct` (o shell tem o handle e pode parar) \| `guided` (processo externo ou parada não seura — shell só orienta) |
| `guidanceCommand` | construído localmente a partir do perfil/sessão em uso | comando exato reproduzível (`assistant-hub-audio run --session <id> --profile <perfil>`) exibido quando `controlMode = guided` ou quando parado |
| `lastError` | capturado do spawn/kill ou da tentativa de start | mensagem específica, nunca genérica (FR-008) |

## ShellConfig

Único dado que o shell efetivamente possui — persistido localmente em JSON no diretório de config do app (Tauri).

| Campo | Notas |
|---|---|
| `sessionCoreBaseUrl` | padrão `http://localhost:8080`, ajustável |
| `windowState` | posição/tamanho da janela |

Nenhum segredo, chave de API ou token é armazenado por esta feature (FR-013 exclui AI Provider Hub).

## DistributionArtifact

Entidade conceitual usada apenas em `docs/desktop-shell/packaging.md`/`quickstart.md` para descrever o resultado do build (US4/FR-011) — não é uma estrutura de runtime.

| Campo | Notas |
|---|---|
| `installerPath` | caminho do `.msi`/`.exe` (NSIS) gerado pelo bundler do Tauri |
| `version` | alinhada ao `VERSION` do monorepo (ver seção "Versionamento" da constituição) |
| `builtOn` | referência à máquina/toolchain Windows de referência usada |

## Relações

```text
ConversationSession (session-core, fonte de verdade)
        │  GET /api/sessions/{id}
        ▼
SessionStatusView (shell, view local)
        │
        │  GET /api/sessions/{id}/events
        ▼
HubEvent[] (session-core, fonte de verdade)
   ├── agrupado por channelId ──▶ ChannelStatusView[]
   └── filtrado por type transcript.*.v2 ──▶ TranscriptFeedEntry[] (ordenado por occurredAt)

Processo assistant-hub-audio (Windows, observado via sysinfo/handle)
        ▼
AgentStatus (shell, view local)
```

Nenhuma dessas views é escrita de volta no `session-core`; o shell é somente-leitura em relação a sessão/eventos (FR-010).
