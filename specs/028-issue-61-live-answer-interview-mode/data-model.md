# Data Model: Live-answer modo entrevista (issue #61)

## Entities

### AssistantSessionPreferences (extended)

Preferências do Assistente **por sessão** (019 + 023 + esta feature).

| Field | Type | Default (ausente) | Notes |
|-------|------|-------------------|-------|
| `autoEnabled` | boolean | `false` | 019 |
| `enabledSourceTypes` | `("microphone" \| "system")[]` | `["system"]` | **Disparo only** |
| `inputMode` | `"question-only" \| "question-plus-recent-context"` | `question-plus-recent-context` | 019 |
| `interviewMode` | boolean | `false` | 023 detecção + **estilo** desta feature |
| `useProsody` | boolean | `false` | 023 |
| `prosodyThreshold` | number [0,1] | `0.65` | 023 |
| **`includeMicrophoneInContext`** | boolean | **`true`** | **NOVO** — contexto only; não afeta disparo |

**Validation / normalize**:
- `includeMicrophoneInContext`: se raw field missing/null/undefined → `true`; se `false` → `false`; se non-boolean truthy → `Boolean(raw)`.
- Persistência: JSON `assistant-prefs.json` keyed by `sessionId` (Tauri).
- Isolamento: load/save por id de sessão (019 SC-010).

### RecentFinalSegment (buffer in-memory)

| Field | Type | Notes |
|-------|------|-------|
| `eventId` | string | Idempotência |
| `text` | string | trim; vazio não entra |
| `sourceType` | `"microphone" \| "system" \| null` | null = omitir do contexto (FR-007b) |

**Lifecycle**:
1. `markSeen` / `ingestTranscript` em cada Final com texto → `trackFinal`.
2. Buffer cap em memória (~200, trim to 100) — inalterado.
3. Builder aplica filtro de origem + preferência + janela 12/4000.
4. `resetSessionState` zera buffer.

### ContextLine (derived, not stored)

| Field | Type | Notes |
|-------|------|-------|
| `label` | `"Entrevistador"` \| `"Candidato (eu)"` | from sourceType |
| `text` | string | segment text |
| order | recency | oldest first in prompt numbering |

### InterviewInstructionBlock (constant)

Texto fixo (const TS) aplicado quando `interviewMode === true`. Não persistido. Versionável via testes de substring.

**Must cover** (FR-009–011):
- 1ª pessoa (eu/meu)
- pt-BR natural, ~30–90s oral
- só texto da fala
- proibir meta-assistente / markdown pesado
- não inventar fatos fora do contexto

### StylePatternSet (test utility)

Padrões FR-012 consumidos por `hasMetaAssistantStyle(text)`.

### AssistantTurn (unchanged shape)

Já possui `latencyMs: number | null` — FR-017 preserva exibição.

## Relationships

```text
Session
  └── AssistantSessionPreferences (1:1 por sessionId)
        ├── enabledSourceTypes ──► gate de DISPARO
        ├── includeMicrophoneInContext ──► filtro de CONTEXTO (mic)
        └── interviewMode ──► detecção (023) + instrução de estilo (028)

Transcript Final feed
  └── RecentFinalSegment[] (controller memory)
        └── buildInvokeInput(question, segments, prefs)
              ├── [optional] InterviewInstructionBlock
              ├── labeled context lines (system/mic)
              └── pergunta atual
```

## State transitions

Nenhuma nova máquina de estados de turn. Preferência booleana simples. Buffer append-only até reset de sessão.

## Compatibility

- Prefs JSON antigas **sem** o campo → default true (comportamento desejado em entrevista).
- Não quebra consumidores do feed; não altera HubEvent schema.
