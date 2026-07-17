# Modelo de dados conceitual

## Session

- `id`
- `title`
- `profileId`
- `status`
- `startedAt`
- `endedAt`
- `participants[]`
- `sources[]`
- `metadata`

## Source

- `id`
- `kind`: microphone, system-audio, screen, camera, file, chat
- `device`
- `format`
- `ownerParticipantId`

## Segment

- `id`
- `sessionId`
- `sourceId`
- `speakerId` opcional
- `startedAt`
- `endedAt`
- `text`
- `confidence`
- `isFinal`

## Artifact

- `id`
- `sessionId`
- `type`: audio, transcript, screenshot, summary, decision, action
- `uri`
- `checksum`
- `createdAt`
- `retentionPolicy`

## Profile

- `id`
- `displayName`
- `enabledPlugins[]`
- `personas[]`
- `policies`
- `providerPreferences`
- `promptTemplates`
