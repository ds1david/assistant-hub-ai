# Contract: detecção de pergunta e prosódia

## 1. Função lexical (shell)

```ts
looksLikeQuestion(text: string): boolean
```

Regras: spec FR-002. Pura, sem I/O.

## 2. Gate multimodal (shell)

```ts
isQuestionCandidate(
  entry: { kind; text; sourceType; prosody?: { questionScore?: number } },
  prefs: AssistantSessionPreferences
): boolean
```

Regras: spec FR-006. `shouldAutoAnswerFromEntry` DEVE delegar a este gate (além de kind Final).

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

Clientes antigos: normalizar campos ausentes para defaults.

## 4. Transcript event — prosody (STT → feed → shell)

Extensão aditiva de `transcript.final.v2` (schema a atualizar):

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

- Partials: `prosody` SHOULD ser omitido (não calcular em partials).
- Consumidores MUST tolerar ausência de `prosody`.

## 5. STT settings / health

Health (ou status já existente) SHOULD incluir:

```json
{
  "model": "medium",
  "prosodyEnabled": false
}
```

para o operador confirmar upgrade de modelo e flag de prosódia.

## 6. Compatibilidade

- Não quebrar feed sem `prosody`.
- Não exigir nova major do shell para ignorar campos.
- Schema: atualizar `contracts/transcript-event.v2.schema.json` **ou** v2.1 conforme plan.
