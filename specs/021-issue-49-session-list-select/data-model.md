# Data Model: Session list selection & active session

**Feature**: `specs/021-issue-49-session-list-select`  
**Date**: 2026-07-25

Modelo de **estado de UI** no shell. Sem persistência nova e sem entidades novas no session-core.

## Entities

### SessionSummary (existente — session-core)

| Field | Type | Notes |
|-------|------|--------|
| `id` | `string` | Identificador canônico (tipicamente UUID). Chave de seleção. |
| `title` | `string` | Rótulo de lista. |
| `profileId` | `string` | Perfil de sessão (existente). |
| `status` | `string` | Ex. CREATED; **não** filtra selecionabilidade nesta fatia. |
| `createdAt` / `startedAt` / `endedAt` | `string \| null` | Metadados de listagem. |

Fonte: `GET /api/sessions` / create response via `listSessions` / `createSession`.

### SessionListState (UI)

| Field | Type | Notes |
|-------|------|--------|
| `sessions` | `SessionSummary[]` | Última lista bem-sucedida; `[]` se falha ou vazia. |
| `error` | `string \| null` | Erro de list/create legível. |
| `busy` | `boolean` | Create (ou op. async) em curso. |

### ActiveSession (UI)

| Field | Type | Notes |
|-------|------|--------|
| `sessionId` | `string \| null` | Sessão ativa; escopo feed, Assistente, start agent. |

**Invariantes**:

1. Se `sessionId != null`, o valor é o id canônico do core (não inventado, não prefixado `session-` pelo shell).
2. Após refresh bem-sucedido: se `sessionId` ∉ `{s.id}`, então `sessionId` → `null` (orphan clear).
3. Bootstrap: `sessionId` inicia `null` até select ou create.
4. Sem auto-select do primeiro item da lista.

### SessionSelectionEvent (lógico)

| Kind | Effect |
|------|--------|
| `select(id)` | `activeSessionId = id` se id não vazio; **não** toca agent process. |
| `create_ok(session)` | `activeSessionId = session.id`; lista atualizada. |
| `create_fail` | active inalterado (ou permanece null); `error` setado. |
| `refresh_ok(list)` | `sessions = list`; `activeSessionId = reconcile(active, list)`. |
| `refresh_fail` | `sessions = []` ou mantém política atual de erro; **não** inventar lista; orphan policy: se lista esvaziada por erro de core, preferir limpar active **ou** manter e mostrar erro de core — **implementação recomendada**: em falha de list, manter `activeSessionId` (operador ainda tem contexto) e setar `error`; orphan clear aplica-se só quando list **sucesso** e id ausente. |

### Agent linkage (reuso 020)

Não redefinir entidades de 020. Relação:

- `ActiveSession.sessionId` → argumento de `start_agent` / guidance `--session`.
- Se `AgentStatus.agentSessionId` conhecido e ≠ active → `AlignmentState = mismatched`.
- Id no formato `session-YYYYMMDD-HHMMSS` no agent **não** entra em `SessionListState.sessions`.

### Pure helpers (contrato de dados)

```text
reconcileActiveSessionAfterList(active: string | null, sessions: { id: string }[]): string | null
  if active is null or blank → null
  if some session.id === active → active
  else → null

isSelectableSessionId(id: string): boolean
  id trimmed non-empty

afterCreateSuccess(createdSessionId: string, selectSession: (id: string) => void | Promise<void>)
  if isSelectableSessionId(createdSessionId) → selectSession(createdSessionId)
  else → no-op (MUST NOT invent active)
```

## State transitions (ActiveSession)

```text
null  --select(valid id)-->  id
null  --create_ok---------->  created.id
id    --select(other)------>  other
id    --refresh, id in list->  id
id    --refresh, id missing->  null
id    --select(invalid)---->  unchanged or no-op (must not set blank)
*     --create_fail-------->  unchanged
```

## Validation rules

| Rule | Spec |
|------|------|
| Select sets full canonical id | FR-001, FR-002, FR-004 |
| Create → active | FR-005 |
| Refresh preserve / orphan null | FR-006 |
| No STT-only injection into list | FR-007 |
| Empty id not selectable | Edge case |
| No auto-select first | FR-001 clarify |
