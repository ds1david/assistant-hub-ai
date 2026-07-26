# Contract: Session picker — shell UI signals

**Feature**: `specs/021-issue-49-session-list-select`  
**Date**: 2026-07-25  
**Scope**: Contrato **interno** shell (webview session picker + estado de sessão ativa). Não é API HTTP pública. HTTP session-core (`GET/POST /api/sessions`) permanece o contrato de backend existente.

## 1. Session-core HTTP (consumo — sem mudança de schema)

| Operation | Method / path | Shell use |
|-----------|---------------|-----------|
| List | `GET /api/sessions` | Popular lista; fonte **única** de itens do seletor |
| Create | `POST /api/sessions` (ou path já usado pelo client) | Create → active com id da resposta |
| Status / feed | existentes por `sessionId` | Após active setado |

**MUST NOT**: inventar entradas de lista a partir de cmdline do agent ou ids `session-YYYYMMDD-…`.

## 2. UI test contracts (data-testid)

Stable selectors for vitest / manual:

| testid | Meaning |
|--------|---------|
| `session-picker` | Container do seletor |
| `session-active-id` | Texto de sessão ativa (full id) **ou** estado «Nenhuma sessão selecionada» |
| `session-list` | Lista (`ul`) |
| `session-list-empty` | Lista sem itens |
| `session-list-error` | Erro de list/create |
| `session-item` | Botão/item selecionável; atributo `data-session-id` = id canônico **completo** |
| `session-create` | Criar sessão |
| `session-refresh` | Atualizar lista (se presente) |

### Visual / class hooks

| Hook | Meaning |
|------|---------|
| class `session-selected` | Item cujo `id === activeSessionId` |
| class `session-none` | Estado sem sessão ativa (opcional no parágrafo active) |

Exact copy may evolve; tests MUST assert:

1. After select: `session-active-id` **contains full id** and `onSelect`/`activeSessionId` equals that id.
2. After create success path: active equals created id.
3. `data-session-id` is never truncated.

## 3. Pure API (TypeScript)

Suggested exports (names flexible if tests map):

```ts
/** FR-006: after successful list fetch */
function reconcileActiveSessionAfterList(
  activeSessionId: string | null,
  sessions: ReadonlyArray<{ id: string }>,
): string | null;

/** FR-001 / edge: reject blank */
function isSelectableSessionId(id: string): boolean;

/** FR-009: set active only — no agent process actions in signature */
function onSessionSelected(
  nextSessionId: string,
  setActiveSessionId: (id: string) => void,
): void;
```

### reconcile rules

| Input | Output |
|-------|--------|
| `active == null` | `null` |
| `active` blank after trim | `null` |
| `active` equals some `sessions[i].id` | `active` |
| else (orphan) | `null` |

### Create → active helper

```ts
/** FR-005: after successful create, activate without second list click */
function afterCreateSuccess(
  createdSessionId: string,
  selectSession: (id: string) => void | Promise<void>,
): void | Promise<void>;
// MUST call selectSession only if isSelectableSessionId(createdSessionId)
```

### Non-goals of pure API

- Auto-select first session when active is null and list non-empty
- Starting/stopping agent
- Writing to session-core

## 4. Agent start linkage (reuso 020)

| Signal | Rule |
|--------|------|
| Start agent | `sessionId` argument = current `activeSessionId` (block if null) — **021 FR-008 / FR-010** |
| Restart Direct | stop managed + start with active — **021 FR-009** (≠ **020 FR-009** select≠restart) |
| Guidance | `--session <activeSessionId>` — **021 FR-012** (assert in vitest) |
| Mismatch | `agentSessionId` known ≠ active → banner — **021 FR-011** / 020 contract |
| Select | MUST NOT restart agent — **020 FR-009** / **021 FR-011** |

No new Tauri commands required for this feature if 020 already exposes start/status.

## 5. Out of contract

- transcript-event.v2
- Forcing STT-only ids into list-sessions
- Cross-restart persistence of activeSessionId
- Multi-select sessions
