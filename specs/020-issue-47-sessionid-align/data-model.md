# Data Model: Session alignment UI↔agent

**Feature**: `specs/020-issue-47-sessionid-align`  
**Date**: 2026-07-25

Modelo de **estado de UI/processo** no shell. Sem persistência nova e sem entidades no session-core.

## Entities

### ActiveSession (UI)

| Field | Type | Notes |
|-------|------|--------|
| `sessionId` | `string \| null` | Sessão selecionada/criada no picker; escopo do feed e do Assistente. |

Fonte: estado em `main.ts` (`activeSessionId`), já existente.

### AgentProcessStatus (extensão de AgentStatus)

| Field | Type | Notes |
|-------|------|--------|
| `running` | `boolean` | Processo agent detectado ou handle vivo (existente). |
| `controlMode` | `"Direct" \| "Guided"` | Handle gerenciado vs externo/ausente (existente). |
| `guidanceCommand` | `string` | Comando com **sessão ativa** da UI quando houver (existente; deve ser preenchido). |
| `lastError` | `string \| null` | Erro de start/stop (existente). |
| `agentSessionId` | `string \| null` | Sessão resolvida do agent (novo). `null` = desconhecida ou agent parado sem id. |
| `agentSessionSource` | `"cmdline" \| "managed" \| "unknown"` | Como `agentSessionId` foi obtido (novo; opcional na UI, útil em testes). |

#### Resolução de `agentSessionId` (FR-005)

```text
if not running:
  agentSessionId = null  (estado “parado”; sem mismatch de ids)
else:
  cmdline_id = parse --session from matching process cmd (if any)
  if cmdline_id present:
    agentSessionId = cmdline_id; source = cmdline
  else if last_managed_session_id present and controlMode == Direct:
    agentSessionId = last_managed_session_id; source = managed
  else:
    agentSessionId = null; source = unknown
```

`last_managed_session_id`: string opcional em `AppState`, setada no `start_agent` OK, limpa no `stop_agent` OK (ou quando handle some).

### SessionAlignment

Estado derivado puro (TS), não persistido.

| Value | Condition |
|-------|-----------|
| `no_active_session` | `activeSessionId == null` |
| `agent_stopped` | agent not running |
| `agent_session_unknown` | running && `agentSessionId == null` |
| `aligned` | both ids known && equal (exact string) |
| `mismatched` | both ids known && not equal |

**Mismatch banner** (FR-007): somente `mismatched`.  
**CTA restart** (FR-016): `mismatched && controlMode == Direct` (e ideally `running`).

### AssistantEmptyKind

Quando `turns.length === 0`, kind de orientação (FR-010). Precedência top-down:

| Kind | Condition (resumo) |
|------|---------------------|
| `session_mismatch` | alignment == `mismatched` |
| `prefs_auto_off` | autoEnabled == false |
| `prefs_no_origin` | enabledSourceTypes empty |
| `awaiting_transcript` | feed entries length == 0 (sem Partial e sem Final) |
| `awaiting_final` | feed has **≥1 Partial** e **nenhum** Final elegível como pergunta sob origens habilitadas (FR-010 item 4: “somente partials” / ainda sem pergunta final elegível). **MUST NOT** usar este kind para feed vazio — isso é `awaiting_transcript` (analyze I4) |
| `no_eligible_question` | feed has ≥1 Final; none look like question under enabled origins (e não se aplica awaiting_final) |
| `generic` | fallback residual (evitar se possível) |

Entradas de feed relevantes: `TranscriptFeedEntry.kind` ∈ `{ Partial, Final }` (já no api-client).

### RestartIntent

Não é entidade persistida — ação:

1. Preconditions: `activeSessionId` set; `controlMode == Direct`; (tipicamente) mismatch.
2. `stop_agent` → `start_agent(activeSessionId, DEFAULT_PROFILE_PATH)`.
3. Sem dialog de confirmação.
4. Pós-sucesso: `agentSessionId` deve igualar `activeSessionId` (aligned).

## Relationships

```text
ActiveSession.sessionId  ──compare──►  AgentProcessStatus.agentSessionId
        │                                        │
        │                                        ▼
        └──────────────► SessionAlignment ◄──────┘
                                │
                                ▼
                     AssistantEmptyKind (priority)
                                │
                                ▼
                     Assistente panel empty copy
```

## Validation rules

- MUST NOT invent `agentSessionId` quando parse e managed falham.
- Comparação de mismatch: igualdade exata; sem normalização de case/UUID canonical form nesta fatia (ids vêm do session-core como string opaca).
- Start sem `activeSessionId`: bloqueado na UI (FR-003); não invocar Tauri com string vazia.
- Guided + running: não chamar kill externo; CTA de restart Direct **não** substitui kill (pode ocultar restart Direct ou desabilitar com texto de parada manual).

## State transitions (agent)

```text
[stopped] --start(activeId)--> [running Direct, agentSessionId=activeId]
[running Direct, A] --select session B--> [running Direct, agentSessionId=A, alignment=mismatched]  (no process change)
[running Direct, mismatched] --CTA restart--> stop --> start(B) --> [running Direct, agentSessionId=B, aligned]
[running Guided, cmdline T] --(no kill)--> still Guided until operator stops externally
[running Guided] --operator stops + start(active)--> [running Direct, aligned]
```
