# UI Contract: STT Streaming Foundation header

**Feature**: `specs/022-issue-51-stt-ui-header`  
**Surface**: `services/transcription-service/app/static/index.html`  
**Date**: 2026-07-25

Contrato **feature-local** de marcadores de UI (não é schema JSON de rede). Testes de estrutura assertam presença e semântica.

## Stable element markers

| Marker | Role | Required |
|--------|------|----------|
| `#status` | Connection status text (existing) | yes |
| `#session-id` or `[data-testid="session-id"]` | Primary sessionId full text (or empty placeholder) | yes |
| `#session-copy` or `[data-testid="session-copy"]` | Copy control for primary sessionId | yes |
| `#session-copy-feedback` or feedback on the copy control | Success/failure text | yes (may share control) |
| `#session-multi` or `[data-testid="session-multi"]` | Multi-session indicator: count label e.g. «N sessões» (hidden/empty when size ≤ 1) | yes |
| `#session-profile` or `[data-testid="session-profile"]` | Agent-origin profile **note** (default this slice); name only if FR-005 MAY applies | yes |
| `#stt-base-url` or `[data-testid="stt-base-url"]` | Document origin / STT base URL (**required**) | yes |

## Behavioral contract

1. **Empty**: no observed sessions → session-id shows non-invented empty state; copy disabled/hidden; multi empty.
2. **Observe**: on transcript event with non-empty `sessionId`, that id becomes primary; full string visible in session-id.
3. **Multi**: when ≥2 distinct ids observed, multi shows count («N sessões»); optional compact secondary list; copy still targets primary only.
4. **Copy**: with primary set, activating copy attempts clipboard write of **exact** primary string; brief textual feedback success/failure on control (~2s, FR-004); no crash; id remains selectable on failure.
5. **Profile**: default = note that profile comes from agent / `--profile` (PT-BR ok). MUST NOT invent name. No query-string profile.
6. **Base URL**: stt-base-url reflects page origin (no secrets) — always shown.
7. **Channels**: channel `section` cards MUST NOT gain sessionId/profile session fields (device/channel metrics only).
8. **Reconnect**: WebSocket reconnect MUST NOT clear observed sessions / primary; full page reload clears.

## Policy source of truth

- Canonical pure policy: `app/header_session_state.py` (pytest).
- `index.html` JS mirrors that policy (comment in script).

## Non-goals (contract)

- No change to transcript-event.v2 payload.
- No new HTTP/WebSocket endpoints required.
- No desktop-shell markers.
- No profile discovery beyond FR-006 note in this slice.

## Test hooks

- Structure tests: load `index.html`, assert markers exist once each in header region.
- State policy tests: `header_session_state` observe → primary/multi/blank (see data-model).
