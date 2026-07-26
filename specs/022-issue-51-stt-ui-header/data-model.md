# Data Model: STT dashboard header session state

**Feature**: `specs/022-issue-51-stt-ui-header`  
**Date**: 2026-07-25

Modelo **em memória no browser**. Política canônica implementada e testada em `app/header_session_state.py`; JS da página espelha (analyze U1). Não é persistência nem schema de rede.

## Entities

### HeaderSessionState

| Field | Type | Rules |
|-------|------|--------|
| `observedSessionIds` | ordered set of non-empty string | Adiciona `sessionId` a cada evento de transcript com id não vazio; ordem de primeira observação estável |
| `primarySessionId` | string \| null | **Último** sessionId observado no feed; `null` se nenhum |
| `profileName` | string \| null | **Sempre `null` nesta fatia** (sem fonte); UI usa nota FR-006 |
| `sttBaseUrl` | string | `location.origin` ao carregar a página (**MUST** no header) |
| `connectionStatus` | enum | `connecting` \| `connected` \| `reconnecting` (já existe como texto do `#status`) |
| `copyFeedback` | enum | `idle` \| `success` \| `failure` (transitório ~2s, FR-004) |

### HeaderView (derivado)

| Field | Derivation |
|-------|------------|
| `primaryDisplay` | `primarySessionId` ou placeholder «aguardando sessão» / «—» |
| `multiCount` | `len(observedSessionIds)` quando > 1; senão oculto |
| `multiLabel` | ex. «{multiCount} sessões» em `#session-multi` |
| `secondaryList` | ids ≠ primário (opcional na UI se couber) |
| `copyEnabled` | `primarySessionId` is non-empty string |
| `profileDisplay` | nota fixa de origem no agent (FR-006); MAY nome se `profileName` non-null (não usado nesta fatia) |
| `baseUrlDisplay` | `sttBaseUrl` |

## Transitions

```text
[empty]
  --transcript with sessionId X-->  primary=X, observed={X}
  --transcript with sessionId Y-->  primary=Y, observed={X,Y}  (multiCount=2)
  --transcript with sessionId X again--> primary=X (volta primário), membership estável
  --copy while primary set--> copyFeedback=success|failure → idle
  --ws reconnect (same page)--> state PRESERVED (não limpar observed/primary)
  --page reload--> empty (sem persistência)
```

## Validation

- SessionId em branco / só whitespace: **ignorar** (não vira primário).
- Copiar com `primarySessionId == null`: no-op; controle desabilitado/ausente.
- Profile inventado / query-string profile: **proibido**.
- Channel cards: **sem** campos de HeaderSessionState.
- Reconnect WS: **não** resetar estado; reload: resetar.

## Relationships

- `HeaderSessionState` ← 1:N eventos transcript (`sessionId`)
- `HeaderSessionState` 1:N channel cards (cards **não** embutem session/profile)
- Independente de session-core active session (shell 021) — só observação no STT
