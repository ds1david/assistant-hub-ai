# Data Model: Qualidade de detecção de pergunta (issue #52)

## AssistantSessionPreferences (shell — extensão 019)

| Campo | Tipo | Default | Notas |
|-------|------|---------|-------|
| autoEnabled | boolean | false | 019 — não mudar |
| enabledSourceTypes | `("microphone"\|"system")[]` | `["system"]` | 019 |
| inputMode | `question-only` \| `question-plus-recent-context` | question-plus-recent-context | 019 |
| interviewMode | boolean | false | **novo** — Final system ≥8 sempre candidato |
| useProsody | boolean | false | **novo** — habilita braço prosódia do gate |
| prosodyThreshold | number | 0.65 | **novo**; [0,1]; sem UI na v1 |

**Validação / normalização**:
- Campos ausentes → defaults (clientes legados).
- `prosodyThreshold` fora de [0,1] → clampar para [0,1] ou cair no default 0.65.
- `enabledSourceTypes` vazio → tratar como nenhum disparo por origem (comportamento 019).

**Persistência**: mesmo mecanismo 019 (`get_assistant_prefs` / `set_assistant_prefs` por sessionId). Sem segredos.

## ProsodyFeatures (evento transcript)

| Campo | Tipo | Obrigatório se objeto presente | Notas |
|-------|------|--------------------------------|-------|
| questionScore | number [0,1] | sim | score “soa como pergunta” |
| contour | enum string | não | rising \| falling \| flat \| unknown |
| f0EndSlopeSemitones | number | não | positivo ≈ subida no fim do window |

**Invariantes**: sem PCM, paths de áudio ou texto extra. Ausência do objeto = comportamento pré-feature.

## Transcript event (final) — extensão

Campos v2 existentes inalterados. Acrescentar:

| Campo | Tipo | Obrigatório |
|-------|------|-------------|
| prosody | ProsodyFeatures \| omitido | não |

Partials: `prosody` **SHOULD** ser omitido (não calcular em partials).

## QuestionCandidate (shell runtime)

| Campo | Tipo |
|-------|------|
| eventId | string |
| text | string |
| channelId | string \| null |
| sourceType | microphone \| system \| null |
| prosodyScore | number \| null |
| reason | opcional: `lexical` \| `interview` \| `prosody` (debug/test only; não expor na UI v1) |

## Settings (STT)

| Env / setting | Default | Notas |
|---------------|---------|-------|
| WHISPER_MODEL | small | medium / large-v3 opt-in (docs) |
| PROSODY_ENABLED | false | liga extrator no final |
| PROSODY_END_WINDOW_MS | 500 | janela final para F0 |

## Health (STT) — campos relevantes

| Campo | Tipo | Notas |
|-------|------|-------|
| model | string | modelo carregado (já parcialmente) |
| hotwordsConfigured | boolean | já existe |
| prosodyEnabled | boolean | **novo** Phase C |

## Relação com 019

- `looksLikeQuestion` / FR-004 de 019 → **substituído no shell** pela FR-002 desta feature (lista expandida + vocativo + sentença + word boundary). Documentar nota superseded em 019 (bloco curto).
- Orquestração de turns, conflito cancel/wait, rota `live-answer`: **inalterados**.
- Empty states de auto off / elegibilidade: **manter** copy genérica.
