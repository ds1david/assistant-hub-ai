# Contract: Session alignment — shell AgentStatus & UI signals

**Feature**: `specs/020-issue-47-sessionid-align`  
**Date**: 2026-07-25  
**Scope**: Contrato **interno** shell (Rust ↔ webview ↔ painéis). Não é API HTTP pública.

## 1. AgentStatus (Tauri → webview)

Serialização camelCase (serde existente).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `running` | boolean | yes | Agent process detected / managed |
| `controlMode` | `"Direct"` \| `"Guided"` | yes | **Direct** se o shell pode parar (handle) **ou** se o agent **não** está em execução (pode iniciar — analyze I1). **Guided** somente quando `running &&` sem handle gerenciado (processo externo). |
| `guidanceCommand` | string | yes | Reproducible CLI; MUST use **active UI session** when caller provides it |
| `lastError` | string \| null | yes | Last start/stop error |
| `agentSessionId` | string \| null | yes (new) | Resolved agent session; null if unknown or N/A |
| `agentSessionSource` | `"cmdline"` \| `"managed"` \| `"unknown"` | yes (new) | Resolution source for tests/diagnostics |

### Resolution rules (server/Rust)

See [data-model.md](../data-model.md). Priority: cmdline `--session` → last managed start → unknown.

### Tauri commands (behavior deltas)

| Command | Input | Behavior change |
|---------|-------|-----------------|
| `get_agent_status` | (optional: `activeSessionId` for guidance) | Fill `agentSessionId` + `agentSessionSource`; `controlMode` per I1 (`Direct` when `!running`). Guidance MAY be empty from Rust if webview always fills on paint (T016) |
| `start_agent` | `sessionId`, `profilePath` | Unchanged spawn; on success set last managed session = `sessionId` and return status with that id |
| `stop_agent` | — | On success clear managed handle + last managed session; **MUST NOT** kill non-managed processes |

**No new HTTP endpoints.**

## 2. UI test contracts (data-testid)

Stable selectors for vitest / manual:

| testid | Meaning |
|--------|---------|
| `agent-status` | Existing running status |
| `agent-session-id` | Display of agent session id or “desconhecida” |
| `ui-session-id` | Optional echo of active session near agent panel |
| `session-mismatch-banner` | Present iff alignment == mismatched |
| `agent-restart-active-button` | CTA restart with active session (Direct + mismatch) |
| `agent-start-button` / `agent-stop-button` | Existing |
| `agent-guidance` | Guided command text |
| `agent-manual-stop-hint` | Guided recovery: stop manually then start with command |
| `assistant-empty` | Empty interactions container |
| `assistant-empty-kind` | Attribute or nested testid suffix: `session_mismatch` \| `prefs_auto_off` \| `prefs_no_origin` \| `awaiting_transcript` \| `awaiting_final` \| `no_eligible_question` |

Exact copy may evolve; tests MUST assert **kind** (testid/attr) first, text optionally.

## 3. Alignment pure API (TypeScript)

Suggested export (names flexible if tests map):

```ts
type AlignmentState =
  | "no_active_session"
  | "agent_stopped"
  | "agent_session_unknown"
  | "aligned"
  | "mismatched";

function resolveAlignment(
  activeSessionId: string | null,
  agent: { running: boolean; agentSessionId: string | null },
): AlignmentState;

type AssistantEmptyKind =
  | "session_mismatch"
  | "prefs_auto_off"
  | "prefs_no_origin"
  | "awaiting_transcript"
  | "awaiting_final"
  | "no_eligible_question"
  | "generic";

function resolveAssistantEmptyKind(input: {
  alignment: AlignmentState;
  autoEnabled: boolean;
  enabledSourceTypes: string[];
  feed: { kind: "Partial" | "Final"; text: string; sourceType?: string | null }[];
  // uses 019 looksLikeQuestion + origin filter for finals
}): AssistantEmptyKind | null; // null if turns non-empty (caller checks turns)
```

## 4. Out of contract

- transcript-event.v2 schema
- session-core REST
- agent Python CLI flags (reuse existing `--session`)
- Force-terminating external processes
