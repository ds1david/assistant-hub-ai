# Data Model: Qualidade de detecção de pergunta

## AssistantSessionPreferences (shell — extensão 019)

| Campo | Tipo | Default | Notas |
|-------|------|---------|-------|
| autoEnabled | boolean | false | 019 |
| enabledSourceTypes | `("microphone"\|"system")[]` | `["system"]` | 019 |
| inputMode | `question-only` \| `question-plus-recent-context` | question-plus-recent-context | 019 |
| interviewMode | boolean | false | **novo** — Final system ≥8 sempre candidato |
| useProsody | boolean | false | **novo** |
| prosodyThreshold | number | 0.65 | **novo**; [0,1] |

Persistência: mesmo mecanismo 019 (`assistant-prefs` Tauri / JSON por sessionId). Sem segredos.

## ProsodyFeatures (evento transcript)

| Campo | Tipo | Obrigatório | Notas |
|-------|------|-------------|-------|
| questionScore | number [0,1] | sim se objeto presente | |
| contour | enum string | não | rising \| falling \| flat \| unknown |
| f0EndSlopeSemitones | number | não | positivo ≈ subida no fim |

## Transcript event (final) — extensão

Campos v2 existentes inalterados. Acrescentar:

| Campo | Tipo | Obrigatório |
|-------|------|-------------|
| prosody | ProsodyFeatures \| omitido | não |

## QuestionCandidate (shell runtime)

| Campo | Tipo |
|-------|------|
| eventId | string |
| text | string |
| channelId | string \| null |
| sourceType | microphone \| system \| null |
| prosodyScore | number \| null |

## Settings (STT)

| Env | Default | Notas |
|-----|---------|-------|
| WHISPER_MODEL | small | medium / large-v3 opt-in |
| PROSODY_ENABLED | false | liga extrator no final |
| PROSODY_END_WINDOW_MS | 500 | janela final para F0 |

## Relação com 019

- `looksLikeQuestion` / FR-004 de 019 → **substituído no shell** pela FR-002 desta feature (lista expandida + vocativo + sentença + word boundary).
- Orquestração de turns, conflito cancel/wait, rota `live-answer`: **inalterados**.
