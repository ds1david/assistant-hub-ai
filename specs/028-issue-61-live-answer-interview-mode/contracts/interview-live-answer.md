# Contract: Interview live-answer input & preferences (issue #61)

**Feature**: `specs/028-issue-61-live-answer-interview-mode`  
**Status**: Draft for implement  
**Compatibility**: Additive only — no transcript v2 / hub invoke schema change

## 1. Preference field (shell storage)

**JSON key** (camelCase, matches TS/serde): `includeMicrophoneInContext`

| Value | Meaning |
|-------|---------|
| `true` / absent | Finais `microphone` elegíveis no bloco de contexto |
| `false` | Excluir `microphone` do contexto |

Does **not** appear in session-core HTTP APIs. Local shell file only (`assistant-prefs.json`).

### Persistence shape (excerpt)

```json
{
  "bySessionId": {
    "<uuid>": {
      "autoEnabled": false,
      "enabledSourceTypes": ["system"],
      "inputMode": "question-plus-recent-context",
      "interviewMode": true,
      "useProsody": false,
      "prosodyThreshold": 0.65,
      "includeMicrophoneInContext": true
    }
  }
}
```

Missing field on load → treat as `true`.

## 2. Context labels (prompt surface)

| Canonical `sourceType` | Label prefix in input |
|------------------------|----------------------|
| `system` | `Entrevistador:` |
| `microphone` | `Candidato (eu):` |
| other / null | **omit segment** |

## 3. `buildInvokeInput` behavior (logical contract)

### Inputs

- `question: string`
- `recentFinals: { eventId, text, sourceType }[]`
- `inputMode: question-only | question-plus-recent-context`
- `includeMicrophoneInContext: boolean`
- `interviewMode: boolean`
- `excludeEventId?: string` (pergunta atual)

### Rules

1. If `inputMode === question-only` → output is optional instruction prefix (if interview) + question only (no transcript context). Prefer: instruction + blank line + question when interview; else question alone.
2. If `question-plus-recent-context`:
   - Filter finals: non-empty text; `eventId !== excludeEventId`; `sourceType` in {system, microphone}; if `!includeMicrophoneInContext` drop microphone.
   - Apply 019 window: max 12 segments / 4000 chars, oldest drop first (walk from newest).
   - Format:
     ```text
     Contexto recente do transcript:
     1. Entrevistador: ...
     2. Candidato (eu): ...
     
     Pergunta atual:
     <question>
     ```
3. If `interviewMode`:
   - Prefix full body with `INTERVIEW_ANSWER_INSTRUCTION` + blank line separator.
4. If not `interviewMode`: no instruction prefix (019 body only).

### Invariants

- **Disparo** remains outside this builder (gate `enabledSourceTypes` + question candidate).
- Builder MUST NOT change which events trigger invoke.
- MUST NOT include partials.

## 4. Interview instruction block (content requirements)

Must be a single exported constant. Minimum semantic requirements (substring tests OK):

| Theme | Must express |
|-------|----------------|
| Person | 1ª pessoa (eu/meu) |
| Language | português do Brasil / pt-BR natural |
| Length | resposta curta / ~30–90s leitura oral |
| Output shape | somente o texto da fala; sem prefácio |
| Forbidden meta | não orientar o candidato; não “você poderia dizer” |
| Honesty | não inventar fatos fora do contexto |

Exact wording is implementation-owned; tests lock critical phrases.

## 5. Style detector (test contract)

`hasMetaAssistantStyle(text: string): boolean`

Returns `true` if **any** FR-012 pattern matches (case-sensitive for listed phrases unless tests say otherwise; implement may use case-insensitive for PT prefixes — document in code).

Not part of invoke wire protocol.

## 6. Invoke wire (unchanged)

```
POST/session-core invoke path via Tauri:
  sessionId, route="live-answer", capability="chat", input=<string>, channelId=null
```

No new fields. `latencyMs` in `InvocationResult` unchanged.

## 7. UI contract (minimal)

| Control | testid (suggested) | Effect |
|---------|-------------------|--------|
| Incluir minha voz no contexto | `assistant-include-mic-context` | toggles `includeMicrophoneInContext` |
| Modo entrevista (existing) | `assistant-interview-mode` | toggles style + 023 detection |

## 8. Non-goals (contract)

- No `transcript.final.v2` field changes
- No hub systemPrompt API
- No TTS payload
- No automatic style reject on response body
