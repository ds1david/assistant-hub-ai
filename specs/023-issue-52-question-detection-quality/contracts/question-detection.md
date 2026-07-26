# Contract: detecção de pergunta e prosódia (issue #52)

## 1. Função lexical (shell)

```ts
looksLikeQuestion(text: string): boolean
```

- Regras: spec **FR-002** (prefixos, vocativo, segmentos, word boundary, min length 8).
- Pura, sem I/O.
- Supersedes **019 FR-004** (lexical legado) **no shell**. Não confundir com **FR-004** desta feature (= modo entrevista).

## 2. Gate multimodal (shell)

```ts
isQuestionCandidate(
  entry: {
    kind: "Final" | "Partial" | string;
    text: string;
    sourceType?: "system" | "microphone" | null;
    prosody?: { questionScore?: number } | null;
  },
  prefs: AssistantSessionPreferences
): boolean
```

Regras (spec FR-006):

```
candidate =
  kind == Final
  AND origin in prefs.enabledSourceTypes
  AND (
    looksLikeQuestion(text)
    OR (prefs.interviewMode AND origin == system AND len(trim(text)) >= 8)
    OR (prefs.useProsody AND entry.prosody?.questionScore >= prefs.prosodyThreshold)
  )
```

`shouldAutoAnswerFromEntry` / `extractNewQuestions` MUST delegar elegibilidade textual a este gate (além de `autoEnabled` e session match no orquestrador).

## 3. Preferências (shell ↔ Tauri)

Extensão aditiva do payload `get_assistant_prefs` / `set_assistant_prefs`:

```json
{
  "autoEnabled": false,
  "enabledSourceTypes": ["system"],
  "inputMode": "question-plus-recent-context",
  "interviewMode": false,
  "useProsody": false,
  "prosodyThreshold": 0.65
}
```

- Clientes antigos: normalizar campos ausentes para defaults.
- UI v1: toggles para `interviewMode` e `useProsody` apenas.

## 4. Transcript event — prosody (STT → feed → shell)

Extensão aditiva de `transcript.final.v2` via `contracts/transcript-event.v2.schema.json`:

```json
{
  "type": "transcript.final.v2",
  "sessionId": "…",
  "channelId": "remote_conference_output",
  "label": "Áudio remoto da conference cam",
  "sourceType": "system",
  "device": { "index": null, "name": "…", "endpointId": "…" },
  "text": "Você já usou Spring Boot em produção",
  "latencyMs": 120,
  "occurredAt": "2026-07-25T12:00:00Z",
  "prosody": {
    "questionScore": 0.78,
    "contour": "rising",
    "f0EndSlopeSemitones": 2.1
  }
}
```

| Regra | Detalhe |
|-------|---------|
| Partials | `prosody` SHOULD omitido |
| Ausência | consumidores MUST tolerar |
| PCM | MUST NOT no payload |
| Schema | propriedade `prosody` opcional no v2; `additionalProperties` do root permanece false |

## 5. STT settings / health

Health (ou status já existente) SHOULD incluir:

```json
{
  "model": "medium",
  "hotwordsConfigured": true,
  "prosodyEnabled": false
}
```

Env:

| Var | Default |
|-----|---------|
| `PROSODY_ENABLED` | false |
| `PROSODY_END_WINDOW_MS` | 500 |
| `WHISPER_MODEL` | small (produto; não mudar default) |

## 6. Compatibilidade

- Feed sem `prosody` permanece válido.
- Shell antigo que ignora campos extras continua funcional.
- Preferências: campos novos opcionais na leitura; defaults seguros.
- Não exigir major do shell para ignorar `prosody`.
